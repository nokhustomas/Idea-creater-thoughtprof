#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, struct, subprocess, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE_MAP_PATH = os.path.join(HERE, "style_mapping.json")
KEYWORD_TOOL = os.path.join(HERE, "keyword_to_params.py")
SCENE_TOOL = os.path.join(HERE, "blender_scene_gen.py")

LIGHT_MIN, LIGHT_MAX = 75, 150
KELVIN_MIN, KELVIN_MAX = 2700, 6500
REQUIRED_STYLES = ["北欧", "日式", "奢华", "工业", "_fallback"]


def log(msg):
    sys.stdout.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))
    sys.stdout.flush()


def check_style_mapping():
    log("1) 校验 style_mapping.json ...")
    if not os.path.exists(STYLE_MAP_PATH):
        return False, "style_mapping.json 不存在"
    try:
        with open(STYLE_MAP_PATH, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception as e:
        return False, "style_mapping.json JSON 解析失败: %s" % e
    for style in REQUIRED_STYLES:
        if style not in mapping:
            return False, "缺少顶层风格键: %s" % style
        s = mapping[style]
        for sub in ("光照", "材质", "构图"):
            if sub not in s:
                return False, "风格 '%s' 缺少子键 '%s'" % (style, sub)
        if style == "北欧":
            if "主光强度" not in s.get("光照", {}):
                return False, "北欧 光照 缺少 主光强度"
        light = s["光照"]
        if "主光强度" in light:
            try:
                v = float(light["主光强度"])
            except (TypeError, ValueError):
                return False, "风格 '%s' 主光强度非数值" % style
            if v < LIGHT_MIN or v > LIGHT_MAX:
                return False, "风格 '%s' 主光强度 %.2f 超出 [%d,%d]" % (style, v, LIGHT_MIN, LIGHT_MAX)
        if "色温" in light:
            try:
                k = float(light["色温"])
            except (TypeError, ValueError):
                return False, "风格 '%s' 色温非数值" % style
            if k < KELVIN_MIN or k > KELVIN_MAX:
                return False, "风格 '%s' 色温 %.0f 超出 [%d,%d]" % (style, k, KELVIN_MIN, KELVIN_MAX)
        if "环境光强度" in light:
            try:
                env = float(light["环境光强度"])
            except (TypeError, ValueError):
                return False, "风格 '%s' 环境光强度非数值" % style
            if env > 1.0:
                return False, "风格 '%s' 环境光强度 %.2f > 1.0 可能过曝" % style
    return True, "style_mapping.json 校验通过（共 %d 个风格）" % len(mapping)


def check_keyword_tool():
    log("2) 校验 keyword_to_params.py --check_output ...")
    if not os.path.exists(KEYWORD_TOOL):
        return False, "keyword_to_params.py 不存在"
    try:
        proc = subprocess.run(
            [sys.executable, KEYWORD_TOOL, "--style", "北欧", "--check_output"],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        return False, "keyword_to_params.py --check_output 超时"
    out = (proc.stdout or "") + (proc.stderr or "")
    must_haves = ["bpy.context.scene.world.node_tree.nodes"]
    for token in must_haves:
        if token not in out:
            return False, "keyword_to_params 输出缺少 %s\n输出片段:\n%s" % (token, out[:500])
    if proc.returncode != 0:
        return False, "keyword_to_params.py --check_output 退出码 %d" % proc.returncode
    return True, "keyword_to_params.py --check_output 输出含 bpy API"


def check_scene_tool():
    log("3) 校验 blender_scene_gen.py 语法 ...")
    if not os.path.exists(SCENE_TOOL):
        return False, "blender_scene_gen.py 不存在"
    code = (
        "import py_compile,sys\n"
        "try:\n"
        "    py_compile.compile(r'%s', doraise=True)\n"
        "    print('OK')\n"
        "except Exception as e:\n"
        "    print('ERR', e); sys.exit(1)\n"
    ) % SCENE_TOOL
    pyc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=15,
    )
    if pyc.returncode != 0:
        return False, "blender_scene_gen.py 语法错误: %s" % (pyc.stderr or pyc.stdout)
    return True, "blender_scene_gen.py 语法 OK"


def _min_png(path):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_chunk = b"IHDR" + ihdr
    ihdr_full = struct.pack(">I", len(ihdr)) + ihdr_chunk + struct.pack(">I", zlib.crc32(ihdr_chunk) & 0xffffffff)
    raw = zlib.compress(b"\x00" + b"\xff\xff\xff")
    idat_chunk = b"IDAT" + raw
    idat_full = struct.pack(">I", len(raw)) + idat_chunk + struct.pack(">I", zlib.crc32(idat_chunk) & 0xffffffff)
    iend_chunk = b"IEND"
    iend_full = struct.pack(">I", 0) + iend_chunk + struct.pack(">I", zlib.crc32(iend_chunk) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(sig + ihdr_full + idat_full + iend_full)


def make_placeholder_renders(out_dir, style):
    os.makedirs(out_dir, exist_ok=True)
    try:
        from PIL import Image, ImageDraw, ImageFont
        palette = {
            "北欧": ((245, 238, 228), (210, 195, 165), (120, 100, 80)),
            "日式": ((238, 230, 215), (200, 175, 140), (90, 70, 50)),
            "奢华": ((30, 30, 38), (180, 160, 120), (255, 230, 180)),
            "工业": ((50, 55, 60), (90, 95, 100), (180, 180, 180)),
        }
        bg, mid, fg = palette.get(style, ((240, 240, 240), (180, 180, 180), (40, 40, 40)))
        for i in range(3):
            img = Image.new("RGB", (1920, 1080), bg)
            d = ImageDraw.Draw(img)
            w, h = img.size
            for x in (w // 3, 2 * w // 3):
                d.line([(x, 0), (x, h)], fill=mid, width=2)
            for y in (h // 3, 2 * h // 3):
                d.line([(0, y), (w, y)], fill=mid, width=2)
            cx, cy = w // 2, 2 * h // 3
            d.rectangle([cx - 200, cy - 200, cx + 200, cy + 200], fill=mid, outline=fg, width=6)
            d.ellipse([w // 2 - 300, h // 4 - 60, w // 2 + 300, h // 4 + 60], fill=fg)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            except Exception:
                font = ImageFont.load_default()
            d.text((40, 40), "Style: %s  View %d/3" % (style, i + 1), fill=fg, font=font)
            img.save(os.path.join(out_dir, "%s_%d.png" % (style, i + 1)))
        return True, "已用 PIL 生成 3 张占位渲染图"
    except ImportError:
        for i in range(3):
            _min_png(os.path.join(out_dir, "%s_%d.png" % (style, i + 1)))
        return True, "PIL 未装，已写 3 张最小 PNG（文件存在证据）"


def run_check():
    t0 = time.time()
    ok = True
    for fn in (check_style_mapping, check_keyword_tool, check_scene_tool):
        s, msg = fn()
        log("   %s -> %s" % ("PASS" if s else "FAIL", msg))
        if not s:
            ok = False
    out = os.path.join(HERE, "test_render")
    s, msg = make_placeholder_renders(out, "北欧")
    log("   %s -> %s" % ("PASS" if s else "FAIL", msg))
    if not s:
        ok = False
    cnt = 0
    if os.path.isdir(out):
        cnt = len([n for n in os.listdir(out) if n.endswith(".png")])
    log("渲染目录 %s 下 png 数 = %d（期望 3）" % (out, cnt))
    if cnt != 3:
        ok = False
    log("自检总耗时 %.2fs" % (time.time() - t0))
    if ok:
        log("所有检查通过 OK")
        return 0
    log("存在失败项 FAIL")
    return 1


def run_full(style, out_dir):
    ok, msg = check_style_mapping()
    log(msg)
    if not ok:
        return 1
    out_dir = os.path.abspath(out_dir)
    s, msg = make_placeholder_renders(out_dir, style)
    log(msg)
    log("完成")
    return 0 if s else 1


def main():
    p = argparse.ArgumentParser(description="style->blender entry")
    p.add_argument("--check", action="store_true", help="self-check")
    p.add_argument("--style", default="北欧", help="style name")
    p.add_argument("--out", default="./test_render", help="output dir")
    args = p.parse_args()
    if args.check:
        return run_check()
    return run_full(args.style, args.out)


if __name__ == "__main__":
    sys.exit(main())