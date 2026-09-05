#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode

def main():
    # Step 1: Run slice analysis
    run_command("python3 stl_analysis.py", "Running STL Slice Analysis")
    
    # Step 2: Generate bracket
    os.makedirs('out', exist_ok=True)
    run_command("bash render.sh", "Generating L-Bracket STL")
    
    # Step 3: Run validation
    ret = run_command("python3 check.py", "Validating STL")
    
    # Step 4: Check N=3 volume reduction
    print("\n" + "="*60)
    print("Testing N=3 Volume Reduction")
    print("="*60)
    
    # Create test version
    with open('bracket_test.scad', 'w') as f:
        content = open('bracket.scad').read().replace('N = 2', 'N = 3')
        f.write(content)
    
    ret1 = run_command("openscad -o out/bracket_n2.stl -D 'L=60' -D 'W=30' -D 'T=4' -D 'H1=40' -D 'H2=40' -D 'D=5' -D 'N=2' -D 'R=3' bracket.scad", "Generate N=2")
    ret2 = run_command("openscad -o out/bracket_n3.stl -D 'L=60' -D 'W=30' -D 'T=4' -D 'H1=40' -D 'H2=40' -D 'D=5' -D 'N=3' -D 'R=3' bracket_test.scad", "Generate N=3")
    
    print("Volume comparison (if OpenSCAD available):")
    run_command("python3 -c \"from stl import mesh; v2=mesh.Mesh.from_file('out/bracket_n2.stl').get_mass(); v3=mesh.Mesh.from_file('out/bracket_n3.stl').get_mass(); print(f'N=2: {v2:.1f} mm³'); print(f'N=3: {v3:.1f} mm³'); print(f'Reduced: {v3 < v2}')\" 2>/dev/null || echo 'Volume comparison requires numpy-stl'")
    
    # Step 5: Create zip
    print("\n" + "="*60)
    print("Creating ZIP Package")
    print("="*60)
    
    # Copy analysis results to out
    if os.path.exists('out/slice_analysis.json'):
        print("Slice analysis JSON found")
    
    run_command("rm -f bracket_test.scad out/bracket_n2.stl out/bracket_n3.stl 2>/dev/null; ls -la out/", "Clean up and list output")
    
    run_command("zip -j deliverable.zip bracket.scad render.sh check.py README.md out/check.json", "Creating deliverable.zip")
    
    print("\n" + "="*60)
    print("DELIVERABLES COMPLETE")
    print("="*60)
    
    print("\nBracket Task Files:")
    print("  - bracket.scad (OpenSCAD model)")
    print("  - render.sh (render script)")
    print("  - check.py (validation)")
    print("  - README.md (usage)")
    print("  - out/check.json (validation result)")
    print("  - deliverable.zip (package)")
    
    print("\nSlice Analysis:")
    print("  - out/slice_analysis.json (STL analysis)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
