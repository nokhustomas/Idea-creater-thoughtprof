#!/usr/bin/env python3
"""Try sandbox slicer for STL analysis"""
import subprocess
import os
import json

def try_sandbox_slicer():
    """Use sandbox/slicer_run if available"""
    stl_dir = 'info_000010'
    files = ['fbspool-hub-v1-inner.stl', 'dospool-hub-v1-outer.stl']
    
    results = {}
    
    for fname in files:
        fpath = os.path.join(stl_dir, fname)
        if not os.path.exists(fpath):
            fpath = fname
        
        if not os.path.exists(fpath):
            results[fname] = {'status': 'file_not_found'}
            continue
        
        try:
            result = subprocess.run(
                ['sandbox/slicer_run', '0', 'info', fpath],
                capture_output=True,
                text=True,
                timeout=120
            )
            results[fname] = {
                'status': 'success',
                'output': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except FileNotFoundError:
            results[fname] = {'status': 'sandbox_not_available'}
        except Exception as e:
            results[fname] = {'status': 'error', 'message': str(e)}
    
    return results

if __name__ == '__main__':
    r = try_sandbox_slicer()
    print(json.dumps(r, indent=2))
