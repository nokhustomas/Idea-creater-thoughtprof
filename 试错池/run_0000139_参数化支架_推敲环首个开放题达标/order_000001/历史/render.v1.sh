#!/usr/bin/env bash
# Render the parametric L-bracket to STL (+ PNG).
# Uses OpenSCAD if available; otherwise falls back to a pure-Python generator.
set -e

OUT_DIR="${OUT_DIR:-out}"
mkdir -p "$OUT_DIR"

if command -v openscad >/dev/null 2>&1; then
    echo "Using openscad"
    openscad -o "$OUT_DIR/bracket.stl" bracket.scad
    openscad -o "$OUT_DIR/bracket.png" --imgsize=800,600 bracket.scad
else
    echo "openscad not available; using Python fallback"
    python3 fallback_render.py
fi

test -s "$OUT_DIR/bracket.stl" || { echo "ERROR: bracket.stl not produced"; exit 1; }
echo "Render OK: $OUT_DIR/bracket.stl ($(wc -c < "$OUT_DIR/bracket.stl") bytes)"
ls -la "$OUT_DIR"
