#!/usr/bin/env python3
import os
import json
import subprocess

def find_stl_files():
    """Find STL files in info_000010"""
    stl_dir = 'info_000010'
    if not os.path.exists(stl_dir):
        return []
    return [f for f in os.listdir(stl_dir) if f.endswith('.stl')]

def run_slicer_analysis():
    """Run slicer analysis using sandbox tool"""
    stl_files = find_stl_files()
    
    if not stl_files:
        print("No STL files found in info_000010")
        return
    
    results = {}
    
    for stl_file in stl_files:
        stl_path = os.path.join('info_000010', stl_file)
        print(f"Analyzing: {stl_file}")
        
        # Run slicer analysis
        try:
            result = subprocess.run(
                ['sandbox/slicer_run', '0', 'info', stl_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            results[stl_file] = {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except Exception as e:
            results[stl_file] = {'error': str(e)}
    
    return results

if __name__ == '__main__':
    results = run_slicer_analysis()
    print(json.dumps(results, indent=2))
