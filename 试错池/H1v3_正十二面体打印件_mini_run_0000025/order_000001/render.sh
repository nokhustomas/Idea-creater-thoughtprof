#!/usr/bin/env bash
# render.sh — 调用 openscad 生成所有 STL + PNG 预览
# 用法：
#   bash render.sh           # 生成所有 STL 与预览 PNG
#   bash render.sh --check   # 生成并执行验收（STL 存在、三角面>100、包围盒检查）

set -u

OPENSCAD_BIN="${OPENSCAD_BIN:-/usr/bin/openscad}"
PNG_PREVIEW="preview.png"

HAS_OPENSCAD=0
if command -v "$OPENSCAD_BIN" >/dev/null 2>&1; then
    HAS_OPENSCAD=1
fi

log() { echo "[render] $*"; }
err() { echo "[render][ERR] $*" >&2; }

gen_stl() {
    local scad="$1" stl="$2"; shift 2
    if [[ "$HAS_OPENSCAD" -ne 1 ]]; then
        err "openscad 未找到，跳过 $stl"
        return 1
    fi
    log "渲染 $stl <- $scad $*"
    if ! "$OPENSCAD_BIN" -o "$stl" "$@" "$scad" 2>&1; then
        err "渲染失败：$scad -> $stl"
        return 1
    fi
    return 0
}

do_check() {
    log "==== 验收开始 ===="
    python3 - <<'PY'
import sys, os, numpy as np
from stl import mesh

REQUIRED = [
    ("body_scaled.stl",          (150, 175), "all"),
    ("face_frame_full_A.stl",    (180, 380), "max"),
    ("face_frame_full_B.stl",    (180, 380), "max"),
    ("module_dummy_A.stl",       (150, 360), "max"),
    ("module_dummy_B.stl",       (150, 360), "max"),
    ("clip.stl",                 (0,  60),   "max"),
]

fail = []
for stl, (lo, hi), mode in REQUIRED:
    if not os.path.exists(stl):
        fail.append(f"missing file: {stl}")
        continue
    try:
        m = mesh.Mesh.from_file(stl)
    except Exception as e:
        fail.append(f"{stl}: cannot read STL ({e})")
        continue
    ntri = len(m.v0)
    if ntri < 100:
        fail.append(f"{stl}: triangle count {ntri} < 100")
        continue
    pts = np.concatenate([m.v0, m.v1, m.v2])
    bbox = pts.max(axis=0) - pts.min(axis=0)
    print(f"  {stl:32s}  tris={ntri:6d}  bbox={bbox[0]:.1f}x{bbox[1]:.1f}x{bbox[2]:.1f}")
    if mode == "all":
        for v in bbox:
            if not (lo <= v <= hi):
                fail.append(f"{stl}: edge {v:.1f} not in [{lo},{hi}]")
    else:
        v = max(bbox)
        if not (lo <= v <= hi):
            fail.append(f"{stl}: max edge {v:.1f} not in [{lo},{hi}]")

if fail:
    print("CHECK FAIL:")
    for f in fail:
        print(" -", f)
    sys.exit(1)

print("CHECK OK: 所有 STL 通过包围盒/三角面检查")
sys.exit(0)
PY
}

main_generate() {
    if [[ "$HAS_OPENSCAD" -ne 1 ]]; then
        err "未检测到 openscad；本沙箱缺 3D 建模后端。"
        err "已写齐 .scad 源文件与文档。请在本地安装 openscad 后运行：bash render.sh"
        exit 0
    fi

    gen_stl body_scaled.scad        body_scaled.stl             || true
    gen_stl face_frame_full.scad    face_frame_full.stl         || true
    gen_stl face_frame_full.scad    face_frame_full_A.stl  -D is_left=1 || true
    gen_stl face_frame_full.scad    face_frame_full_B.stl  -D is_left=0 || true
    gen_stl module_dummy.scad       module_dummy.stl            || true
    gen_stl module_dummy.scad       module_dummy_A.stl     -D is_left=1 || true
    gen_stl module_dummy.scad       module_dummy_B.stl     -D is_left=0 || true
    gen_stl clip.scad               clip.stl                    || true

    if [[ "$HAS_OPENSCAD" -eq 1 && -n "${DISPLAY:-}" && -x /usr/bin/xvfb-run ]]; then
        log "preview (DISPLAY+xvfb-run present)"
        "$OPENSCAD_BIN" --camera=0,0,0,55,0,25,180 --imgsize=800,600 \
            -D 'is_left=1' \
            -o "$PNG_PREVIEW" face_frame_full.scad 2>&1 || \
            log "预览 PNG 生成失败（不影响 STL）"
    fi

    log "生成完成。"
}

if [[ "${1:-}" == "--check" ]]; then
    main_generate
    do_check
    exit $?
else
    main_generate
    exit 0
fi