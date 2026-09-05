#!/usr/bin/env python3
"""Run OpenSCAD to generate STL, ensuring ECHO output is emitted."""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

result = subprocess.run(
    ["openscad", "-o", "cable_organizer.stl", "cable_organizer.scad"],
    capture_output=True, text=True
)

combined = (result.stdout or "") + (result.stderr or "")
print(combined)
sys.exit(result.returncode)