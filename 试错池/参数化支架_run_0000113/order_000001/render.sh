#!/bin/bash
set -e
mkdir -p out
if ! command -v openscad &> /dev/null; then
    echo "OpenSCAD not found" >&2
    exit 2
fi
openscad -o out/bracket.stl -D "L=60" -D "W=30" -D "T=4" -D "H1=40" -D "H2=40" -D "D=5" -D "N=2" -D "R=3" bracket.scad
echo "Render complete"
