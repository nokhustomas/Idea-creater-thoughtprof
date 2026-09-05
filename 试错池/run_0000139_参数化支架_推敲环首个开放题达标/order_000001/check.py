#!/usr/bin/env python3
"""Read out/bracket.stl, verify bbox and volume, write out/check.json.

Honors the N env var (default 2) so the N=3 volume-reduction check works.
"""
import json
import math
import os
import re
import struct
import sys
from pathlib import Path

OUT_DIR     = Path(os.environ.get("OUT_DIR", "out"))
STL_PATH    = OUT_DIR / "bracket.stl"
JSON_PATH   = OUT_DIR / "check.json"

L  = 60.0
W  = 30.0
T  = 4.0
H1 = 40.0
D  = 5.0
N  = int(os.environ.get("N", "2"))

TOL_BBOX_MM = 0.5
TOL_VOL_REL = 0.10


def parse_stl(path):
    """Parse ASCII or binary STL; return list of ((x,y,z), (x,y,z), (x,y,z))."""
    p = Path(path)
    raw = p.read_bytes()
    head = raw.lstrip()[:5]
    if head == b"solid":
        tris = parse_ascii_stl(raw)
        if tris:
            return tris
    return parse_binary_stl(p)


_VERT_RE = re.compile(
    r"vertex\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s+"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
)


def parse_ascii_stl(raw):
    text = raw.decode("utf-8", errors="replace")
    matches = _VERT_RE.findall(text)
    triangles = []
    for i in range(0, len(matches) - 2, 3):
        v1 = (float(matches[i][0]),     float(matches[i][1]),     float(matches[i][2]))
        v2 = (float(matches[i + 1][0]), float(matches[i + 1][1]), float(matches[i + 1][2]))
        v3 = (float(matches[i + 2][0]), float(matches[i + 2][1]), float(matches[i + 2][2]))
        triangles.append((v1, v2, v3))
    return triangles


def parse_binary_stl(path):
    triangles = []
    with open(path, "rb") as f:
        f.seek(80)
        (ntri,) = struct.unpack("<I", f.read(4))
        for _ in range(ntri):
            f.read(12)  # normal
            data = f.read(36)
            v1 = struct.unpack("<3f", data[0:12])
            v2 = struct.unpack("<3f", data[12:24])
            v3 = struct.unpack("<3f", data[24:36])
            triangles.append((v1, v2, v3))
            f.read(2)
    return triangles


def compute_bbox(triangles):
    xs, ys, zs = [], [], []
    for v1, v2, v3 in triangles:
        for v in (v1, v2, v3):
            xs.append(v[0]); ys.append(v[1]); zs.append(v[2])
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def compute_volume(triangles):
    """Signed-tetrahedron volume; assumes mesh is closed and outward-facing."""
    vol = 0.0
    for v1, v2, v3 in triangles:
        cx = v2[1] * v3[2] - v2[2] * v3[1]
        cy = v2[2] * v3[0] - v2[0] * v3[2]
        cz = v2[0] * v3[1] - v2[1] * v3[0]
        vol += v1[0] * cx + v1[1] * cy + v1[2] * cz
    return abs(vol) / 6.0


def main():
    if not STL_PATH.exists():
        print(f"ERROR: {STL_PATH} not found", file=sys.stderr)
        sys.exit(1)

    triangles = parse_stl(str(STL_PATH))
    if not triangles:
        print("ERROR: no triangles parsed from STL", file=sys.stderr)
        sys.exit(1)

    bbox = compute_bbox(triangles)
    bbox_size = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])

    expected_bbox = (L, W, T + H1)
    bbox_ok = all(abs(a - b) <= TOL_BBOX_MM
                  for a, b in zip(bbox_size, expected_bbox))

    expected_volume = L * W * T + T * W * H1 - N * math.pi * (D / 2) ** 2 * T
    actual_volume   = compute_volume(triangles)
    rel_diff        = abs(actual_volume - expected_volume) / expected_volume
    volume_ok       = rel_diff <= TOL_VOL_REL

    result = {
        "N": N,
        "triangles": len(triangles),
        "bbox_min":  [bbox[0], bbox[1], bbox[2]],
        "bbox_max":  [bbox[3], bbox[4], bbox[5]],
        "bbox_size": list(bbox_size),
        "expected_bbox_size": list(expected_bbox),
        "volume": actual_volume,
        "expected_volume": expected_volume,
        "volume_rel_diff": rel_diff,
        "bbox_ok":   bbox_ok,
        "volume_ok": volume_ok,
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

    sys.exit(0 if (bbox_ok and volume_ok) else 1)


if __name__ == "__main__":
    main()
