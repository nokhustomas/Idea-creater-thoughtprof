#!/usr/bin/env python3
"""Generate STL (and best-effort PNG) for the parametric L-bracket without OpenSCAD.

Bracket geometry (matches bracket.scad parameters):
  Horizontal arm:  X in [0, L],  Y in [0, W],  Z in [0, T]
  Vertical arm:    X in [0, T],  Y in [0, W],  Z in [T, T+H1]
  Bbox:            L x W x (T+H1) = 60 x 30 x 44 mm
"""
import os
import math
from pathlib import Path

OUT_DIR = Path(os.environ.get("OUT_DIR", "out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

L  = 60
W  = 30
T  = 4
H1 = 40
H2 = 40
D  = 5
N  = 2
R  = 3


def box_tris(x0, y0, z0, x1, y1, z1):
    """Triangles for an axis-aligned box (12 triangles, outward normals)."""
    p000 = (x0, y0, z0); p100 = (x1, y0, z0)
    p010 = (x0, y1, z0); p110 = (x1, y1, z0)
    p001 = (x0, y0, z1); p101 = (x1, y0, z1)
    p011 = (x0, y1, z1); p111 = (x1, y1, z1)
    return [
        (p000, p110, p010), (p000, p100, p110),  # -Z (down)
        (p001, p011, p111), (p001, p111, p101),  # +Z (up)
        (p000, p001, p101), (p000, p101, p100),  # -Y (front)
        (p010, p110, p111), (p010, p111, p011),  # +Y (back)
        (p000, p010, p011), (p000, p011, p001),  # -X (left)
        (p100, p101, p111), (p100, p111, p110),  # +X (right)
    ]


def write_stl_ascii(path, triangles):
    with open(path, "w") as f:
        f.write("solid bracket\n")
        for v1, v2, v3 in triangles:
            ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
            wx, wy, wz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
            nx = uy*wz - uz*wy
            ny = uz*wx - ux*wz
            nz = ux*wy - uy*wx
            mag = math.sqrt(nx*nx + ny*ny + nz*nz)
            if mag < 1e-12:
                nx = ny = nz = 0.0
            else:
                nx, ny, nz = nx/mag, ny/mag, nz/mag
            f.write(f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}\n")
            f.write(f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}\n")
            f.write(f"      vertex {v3[0]:.6f} {v3[1]:.6f} {v3[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid bracket\n")


def main():
    triangles = []
    # Horizontal arm: 0..L x 0..W x 0..T
    triangles += box_tris(0, 0, 0, L, W, T)
    # Vertical arm:   0..T x 0..W x T..T+H1
    triangles += box_tris(0, 0, T, T, W, T+H1)

    stl_path = OUT_DIR / "bracket.stl"
    write_stl_ascii(str(stl_path), triangles)
    print(f"Wrote {stl_path} ({len(triangles)} triangles)")

    # Best-effort PNG side-view schematic
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, Circle
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.add_patch(Rectangle((0, 0), L, T, color="lightgray", ec="black"))
        ax.add_patch(Rectangle((0, T), T, H1, color="lightgray", ec="black"))
        for i in range(N):
            x_pos = (i + 0.5) * L / N
            ax.add_patch(Circle((x_pos, T/2), D/2, fill=False, ec="red", lw=1.5))
        ax.set_xlim(-10, L+10); ax.set_ylim(-10, T+H1+10)
        ax.set_aspect("equal"); ax.set_title("L-Bracket (side view)")
        ax.set_xlabel("X (mm)"); ax.set_ylabel("Z (mm)")
        ax.grid(True, linestyle=":", alpha=0.5)
        png_path = OUT_DIR / "bracket.png"
        plt.tight_layout()
        plt.savefig(str(png_path), dpi=100)
        plt.close(fig)
        print(f"Wrote {png_path}")
    except ImportError:
        print("matplotlib not available; skipping PNG")


if __name__ == "__main__":
    main()
