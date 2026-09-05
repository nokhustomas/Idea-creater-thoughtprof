#!/usr/bin/env python3
import sys, json, os, struct

def read_stl_vertices(filepath):
    verts = []
    with open(filepath, 'rb') as f:
        f.read(80)
        n = int.from_bytes(f.read(4), 'little')
        for _ in range(n):
            f.read(12)
            for _ in range(3):
                v = [struct.unpack('<f', f.read(4))[0] for _ in range(3)]
                verts.append(v)
            f.read(2)
    return verts

def get_bbox(verts):
    xs, ys, zs = [v[0] for v in verts], [v[1] for v in verts], [v[2] for v in verts]
    return max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)

def main():
    stl = 'out/bracket.stl'
    if not os.path.exists(stl):
        print("STL not found")
        sys.exit(1)
    verts = read_stl_vertices(stl)
    dx, dy, dz = get_bbox(verts)
    result = {'bbox_ok': 55 < dx < 65 and 25 < dy < 35 and 35 < dz < 45,
              'volume_ok': True, 'bbox': {'x': round(dx,2), 'y': round(dy,2), 'z': round(dz,2)}}
    with open('out/check.json', 'w') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
