#!/usr/bin/env python3
"""
STL Analysis for printability assessment
Analyzes: min wall thickness, min feature size, max overhang angle, span/wall ratio
"""
import os
import json
import math
import numpy as np
from collections import defaultdict

def read_stl_vertices(filepath):
    """Read vertices from binary STL file"""
    vertices = []
    with open(filepath, 'rb') as f:
        f.read(80)  # header
        num_triangles = int.from_bytes(f.read(4), 'little')
        for _ in range(num_triangles):
            f.read(12)  # normal
            for _ in range(3):
                vertex = np.array([
                    float.from_bytes(f.read(4), 'little'),
                    float.from_bytes(f.read(4), 'little'),
                    float.from_bytes(f.read(4), 'little')
                ])
                vertices.append(vertex)
            f.read(2)  # attribute
    return np.array(vertices)

def compute_wall_thickness(vertices, bins=100):
    """Estimate minimum wall thickness using ray casting / distance analysis"""
    all_coords = vertices.reshape(-1, 3)
    
    # Get bounding box
    min_coords = all_coords.min(axis=0)
    max_coords = all_coords.max(axis=0)
    
    # Sample grid and find minimum cross-section
    thickness_estimates = []
    
    for axis in range(3):
        other_axes = [(axis + 1) % 3, (axis + 2) % 3]
        
        for i in range(bins):
            # Sample along this axis
            t = min_coords[axis] + (max_coords[axis] - min_coords[axis]) * i / bins
            
            # Project onto plane perpendicular to axis
            plane_coords = all_coords[:, other_axes]
            points = plane_coords[abs(all_coords[:, axis] - t) < 0.5]
            
            if len(points) > 0:
                # Find extent in this cross-section
                extents = points.max(axis=0) - points.min(axis=0)
                min_extent = min(extents)
                thickness_estimates.append(min_extent)
    
    return max(0.1, min(thickness_estimates) if thickness_estimates else 1.0)

def compute_min_feature_size(vertices):
    """Compute minimum feature size (edge length, small details)"""
    # Compute edge lengths
    min_edge = float('inf')
    for i in range(0, len(vertices) - 2, 3):
        v1, v2, v3 = vertices[i], vertices[i+1], vertices[i+2]
        e1 = np.linalg.norm(v2 - v1)
        e2 = np.linalg.norm(v3 - v2)
        e3 = np.linalg.norm(v1 - v3)
        min_edge = min(min_edge, e1, e2, e3)
    
    return max(0.05, min_edge) if min_edge != float('inf') else 0.1

def compute_max_overhang(filepath):
    """Estimate maximum overhang angle"""
    # Read normals from STL
    normals = []
    with open(filepath, 'rb') as f:
        f.read(80)
        num_triangles = int.from_bytes(f.read(4), 'little')
        for _ in range(num_triangles):
            n = np.array([
                float.from_bytes(f.read(4), 'little'),
                float.from_bytes(f.read(4), 'little'),
                float.from_bytes(f.read(4), 'little')
            ])
            normals.append(n)
            for _ in range(3):
                f.read(12)
            f.read(2)
    
    normals = np.array(normals)
    
    # Z is typically up direction
    up = np.array([0, 0, 1])
    
    # Angle between face normal and up direction
    angles = []
    for n in normals:
        if np.linalg.norm(n) > 0:
            n_norm = n / np.linalg.norm(n)
            cos_angle = np.dot(n_norm, up)
            angle = math.degrees(math.acos(abs(cos_angle)))
            angles.append(angle)
    
    # Max overhang = 90 - min angle to horizontal
    return 90 - min(angles) if angles else 45

def compute_span_wall_ratio(vertices, wall_thickness):
    """Compute span to wall thickness ratio"""
    all_coords = vertices.reshape(-1, 3)
    
    # Find maximum span (diagonal of bounding box)
    dims = all_coords.max(axis=0) - all_coords.min(axis=0)
    max_span = np.linalg.norm(dims)
    
    return max_span / wall_thickness if wall_thickness > 0 else 0

def analyze_printability(min_wall, min_feature, max_overhang, span_ratio, profile):
    """Determine printability conclusions"""
    conclusions = []
    
    if profile == 'FDM_0.2_PLA':
        # FDM 0.2mm layer height, PLA
        layer_height = 0.2
        nozzle = 0.4
        min_wall_fdm = nozzle * 2  # 0.8mm typical min
        
        if min_wall < min_wall_fdm:
            conclusions.append("WARNING: Wall thickness below recommended minimum for FDM")
        if min_feature < layer_height * 2:
            conclusions.append("WARNING: Fine features may not print reliably")
        if max_overhang < 45:
            conclusions.append("WARNING: Overhangs may require supports")
        if span_ratio > 100:
            conclusions.append("CAUTION: High span/wall ratio - may sag or warp")
        if not conclusions:
            conclusions.append("LIKELY PRINTABLE with standard FDM settings")
            
    elif profile == 'SLA_0.05_Resin':
        # SLA 0.05mm layer height, standard resin
        layer_height = 0.05
        min_wall_sla = 0.5  # 0.5mm recommended minimum
        
        if min_wall < min_wall_sla:
            conclusions.append("WARNING: Wall thickness at risk for SLA - may be fragile")
        if min_feature < layer_height * 5:
            conclusions.append("WARNING: Fine features may not resolve well")
        if max_overhang > 80:
            conclusions.append("NOTE: Very shallow overhangs - may have adhesion issues")
        if not conclusions:
            conclusions.append("LIKELY PRINTABLE with standard SLA settings")
    
    return conclusions

def analyze_stl(filepath):
    """Full analysis of a single STL file"""
    print(f"Analyzing: {filepath}")
    
    try:
        vertices = read_stl_vertices(filepath)
    except Exception as e:
        return {'error': str(e)}
    
    min_wall = compute_wall_thickness(vertices)
    min_feature = compute_min_feature_size(vertices)
    max_overhang = compute_max_overhang(filepath)
    span_ratio = compute_span_wall_ratio(vertices, min_wall)
    
    results = {
        'file': os.path.basename(filepath),
        'analysis': {
            'min_wall_thickness_mm': round(min_wall, 3),
            'min_feature_size_mm': round(min_feature, 3),
            'max_overhang_angle_deg': round(max_overhang, 1),
            'span_wall_ratio': round(span_ratio, 2)
        },
        'printability': {}
    }
    
    # FDM analysis
    results['printability']['FDM_0.2mm_PLA'] = {
        'settings': 'Layer: 0.2mm, Material: PLA',
        'conclusions': analyze_printability(min_wall, min_feature, max_overhang, span_ratio, 'FDM_0.2_PLA')
    }
    
    # SLA analysis
    results['printability']['SLA_0.05mm_StandardResin'] = {
        'settings': 'Layer: 0.05mm, Material: Standard Resin',
        'conclusions': analyze_printability(min_wall, min_feature, max_overhang, span_ratio, 'SLA_0.05_Resin')
    }
    
    return results

def main():
    # Find STL files
    stl_dir = 'info_000010'
    target_files = ['fbspool-hub-v1-inner.stl', 'dospool-hub-v1-outer.stl']
    
    all_results = {'parts': []}
    
    for filename in target_files:
        filepath = os.path.join(stl_dir, filename)
        if os.path.exists(filepath):
            result = analyze_stl(filepath)
            all_results['parts'].append(result)
        else:
            all_results['parts'].append({
                'file': filename,
                'error': 'File not found'
            })
    
    # Save results
    os.makedirs('out', exist_ok=True)
    with open('out/slice_analysis.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("SLICE ANALYSIS SUMMARY")
    print("="*60)
    
    for part in all_results['parts']:
        print(f"\n{part.get('file', 'Unknown')}:")
        if 'error' in part:
            print(f"  ERROR: {part['error']}")
        else:
            a = part['analysis']
            print(f"  Min Wall Thickness: {a['min_wall_thickness_mm']} mm")
            print(f"  Min Feature Size: {a['min_feature_size_mm']} mm")
            print(f"  Max Overhang Angle: {a['max_overhang_angle_deg']}°")
            print(f"  Span/Wall Ratio: {a['span_wall_ratio']}")
            print("  Printability:")
            for profile, data in part['printability'].items():
                print(f"    [{profile}]")
                for c in data['conclusions']:
                    print(f"      - {c}")

if __name__ == '__main__':
    main()
