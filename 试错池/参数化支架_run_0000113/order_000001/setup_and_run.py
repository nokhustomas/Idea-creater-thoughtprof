#!/usr/bin/env python3
"""Setup and run all tasks"""
import os
import subprocess
import json

def create_files():
    """Create all required files"""
    os.makedirs('out', exist_ok=True)
    
    files = {
        'bracket.scad': '''// Parametric L-bracket
// Parameters: L=60(长) W=30(宽) T=4(厚) H1=40 H2=40(臂高) D=5(孔径) N=2(孔数) R=3(圆角)

L = 60;
W = 30;
T = 4;
H1 = 40;
H2 = 40;
D = 5;
N = 2;
R = 3;

module rounded_cube(dim, r) {
    hull() {
        for (x = [r, dim[0]-r], y = [r, dim[1]-r], z = [r, dim[2]-r]) {
            translate([x, y, z])
                sphere(r=r);
        }
    }
}

module l_bracket() {
    difference() {
        union() {
            rounded_cube([T, W, H1], R);
            rounded_cube([L, T, H2], R);
        }
        
        spacing = (L - T - 2*R) / (N + 1);
        for (i = [1:N]) {
            x_pos = T + R + i * spacing;
            translate([x_pos, T/2, H1/2])
                rotate([90, 0, 0])
                    cylinder(d=D, h=W+2, center=true);
        }
    }
}

l_bracket();
''',
        'render.sh': '''#!/bin/bash
set -e
mkdir -p out
if ! command -v openscad &> /dev/null; then
    echo "OpenSCAD not found" >&2
    exit 2
fi
openscad -o out/bracket.stl -D "L=60" -D "W=30" -D "T=4" -D "H1=40" -D "H2=40" -D "D=5" -D "N=2" -D "R=3" bracket.scad
echo "Render complete"
''',
        'check.py': '''#!/usr/bin/env python3
import sys, json, os, struct, math

def read_stl_vertices(filepath):
    vertices = []
    with open(filepath, 'rb') as f:
        f.read(80)
        n = int.from_bytes(f.read(4), 'little')
        for _ in range(n):
            f.read(12)
            for _ in range(3):
                v = [struct.unpack('<f', f.read(4))[0] for _ in range(3)]
                vertices.append(v)
            f.read(2)
    return vertices

def compute_volume(verts):
    vol = 0
    for i in range(0, len(verts)-2, 3):
        v1, v2, v3 = verts[i], verts[i+1], verts[i+2]
        v = (v2[0]-v1[0])*(v3[1]-v1[1]) - (v2[1]-v1[1])*(v3[0]-v1[0])
        vol += v1[0]*(v2[1]*v3[2]-v2[2]*v3[1]) + v1[1]*(v2[2]*v3[0]-v2[0]*v3[2]) + v1[2]*(v2[0]*v3[1]-v2[1]*v3[0])
    return abs(vol) / 6.0

def get_bbox(verts):
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    return {'x': (min(xs), max(xs)), 'y': (min(ys), max(ys)), 'z': (min(zs), max(zs))}

def main():
    stl = 'out/bracket.stl'
    if not os.path.exists(stl):
        print("STL not found")
        sys.exit(1)
    verts = read_stl_vertices(stl)
    bbox = get_bbox(verts)
    vol = compute_volume(verts)
    dx = bbox['x'][1] - bbox['x'][0]
    dy = bbox['y'][1] - bbox['y'][0]
    dz = bbox['z'][1] - bbox['z'][0]
    result = {
        'bbox_ok': 55 < dx < 65 and 25 < dy < 35 and 35 < dz < 45,
        'volume_ok': 20000 < vol < 35000,
        'volume': vol,
        'bbox': {'x': dx, 'y': dy, 'z': dz}
    }
    os.makedirs('out', exist_ok=True)
    with open('out/check.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    if not (result['bbox_ok'] and result['volume_ok']):
        sys.exit(1)

if __name__ == '__main__':
    main()
''',
        'README.md': """# Parametric L-Bracket

## Usage

Run render script:
    bash render.sh

Validate output:
    python3 check.py
"""
    }
    
    for name, content in files.items():
        with open(name, 'w') as f:
            f.write(content)
        os.chmod(name, 0o755) if name.endswith('.sh') else None
        print(f"Created: {name}")

def main():
    create_files()
    print("\nRun: bash render.sh")
    print("Then: python3 check.py")

if __name__ == '__main__':
    main()
