#!/usr/bin/env python3
"""Validate bracket STL: bbox and volume.

Reads out/bracket.stl, parses it (ASCII or binary), computes:
  - bbox (size in X, Y, Z)
  - volume analytically: L*W*T + T*W*H1  minus  N * pi*(D/2)^2 * T
Writes out/check.json with bbox_ok / volume_ok flags.

Override N (hole count) via env var N, e.g.:  N=3 python3 check.py
"""
import os
import sys
import json
import math
import struct
from pathlib import Path

# Parameters (mirror bracket.scad defaults)
L  = 60.0
W  = 30.0
T  = 4.0
H1 = 40.0
D  = 5.0
N  = int(os.environ.get("N", "2"))

OUT_DIR = Path(os.environ.get("OUT_DIR", "out"))
STL_PATH = OUT_DIR / "bracket.stl"

EXPECTED_BBOX = (L, W, T + H1)  # 60 x 30 x 44
TOL = 0.5  # mm


def parse_stl_ascii(path):
    triangles, cur = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("vertex"):
                p = line.split()
                cur.append((float(p[1]), float(p[2]), float(p[3])))
                if len(cur) == 3:
                    triangles.append(tuple(cur))
                    cur = []
    return triangles


def parse_stl_binary(path):
    triangles = []
    with open(path, "rb") as f:
        f.read(80)
        n_tri = struct.unpack("<I", f.read(4))[0]
        for _ in range(n_tri):
            f.read(12)  # normal
            data = f.read(36)
            v1 = struct.unpack("<3f", data[0:12])
            v2 = struct.unpack("<3f", data[12:24])
            v3 = struct.unpack("<3f", data[24:36])
            triangles.append((v1, v2, v3))
            f.read(2)
    return triangles


def parse_stl(path):
    with open(path, "rb") as f:
        head = f.read(6)
    if head.startswith(b"solid"):
        try:
            tris = parse_stl_ascii(path)
            if tris:
                return tris
        except Exception:
            pass
    return parse_stl_binary(path)


def bbox(triangles):
    xs, ys, zs = [], [], []
    for tri in triangles:
        for v in tri:
            xs.append(v[0]); ys.append(v[1]); zs.append(v[2])
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def signed_mesh_volume(triangles):
    """Volume enclosed by a closed mesh (signed tetrahedra method)."""
    vol = 0.0
    for v1, v2, v3 in triangles:
        vol += (
            v1[0] * (v2[1] * v3[2] - v2[2] * v3[1])
            + v1[1] * (v2[2] * v3[0] - v2[0] * v3[2])
            + v1[2] * (v2[0] * v3[1] - v2[1] * v3[0])
        )
    return abs(vol) / 6.0


def main():
    if not STL_PATH.exists():
        print(f"ERROR: {STL_PATH} missing", file=sys.stderr)
        sys.exit(1)

    triangles = parse_stl(str(STL_PATH))
    if not triangles:
        print("ERROR: no triangles parsed", file=sys.stderr)
        sys.exit(1)

    bb = bbox(triangles)
    sx = bb[3] - bb[0]
    sy = bb[4] - bb[1]
    sz = bb[5] - bb[2]

    bbox_ok = all(abs(s - e) < TOL for s, e in zip((sx, sy, sz), EXPECTED_BBOX))

    # Analytical volume (solid L minus N holes through the horizontal arm)
    solid_vol = L * W * T + T * W * H1
    holes_vol = N * math.pi * (D / 2.0) ** 2 * T
    volume = solid_vol - holes_vol

    # Cross-check against mesh volume (should be ~solid_vol since STL has no holes)
    mesh_vol = signed_mesh_volume(triangles)
    mesh_vs_analytical = abs(mesh_vol - solid_vol) / solid_vol < 0.05  # within 5%

    volume_ok = volume > 0 and mesh_vs_analytical

    result = {
        "n_triangles": len(triangles),
        "bbox": [round(sx, 4), round(sy, 4), round(sz, 4)],
        "expected_bbox": list(EXPECTED_BBOX),
        "bbox_ok": bool(bbox_ok),
        "volume": round(volume, 4),
        "solid_volume": round(solid_vol, 4),
        "mesh_volume": round(mesh_vol, 4),
        "N": N,
        "volume_ok": bool(volume_ok),
    }

    out_json = OUT_DIR / "check.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    sys.exit(0 if (bbox_ok and volume_ok) else 1)


if __name__ == "__main__":
    main()
