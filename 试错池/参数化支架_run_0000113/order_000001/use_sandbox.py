#!/usr/bin/env python3
"""Try to use sandbox slicer for STL analysis"""
import subprocess
import os
import json

def try_sandbox_slicer():
    """Attempt to use sandbox slicer tool"""
    stl_files = [
        'info_000010/fbspool-hub-v1-inner.stl',
        'info_000010/dospool-hub-v1-outer.stl'
    ]
    
    results = {}
    
    for stl in stl_files:
        if not os.path.exists(stl):
            results[stl] = {'error': 'File not found'}
            continue
            
        try:
            # Try sandbox slicer
            result = subprocess.run(
                ['sandbox/slicer_run', '0', 'info', stl],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            results[stl] = {
                'sandbox_available': True,
                'output': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except FileNotFoundError:
            results[stl] = {
                'sandbox_available': False,
                'error': 'sandbox/slicer_run not found'
            }
        except Exception as e:
            results[stl] = {
                'sandbox_available': False,
                'error': str(e)
            }
    
    return results

if __name__ == '__main__':
    r = try_sandbox_slicer()
    print(json.dumps(r, indent=2))
