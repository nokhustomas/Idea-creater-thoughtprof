#!/usr/bin/env bash
# render.sh - Build hook.stl and a top-view render.png from hook.scad
# Uses xvfb-run so OpenSCAD can render offscreen without an X server.
set -euo pipefail

cd "$(dirname "$0")"

OPENSCAD_RUN="openscad"
if ! openscad -o /dev/null /dev/null 2>/dev/null </dev/null; then
    : # fallback below
fi

# We always wrap with xvfb-run for headless compatibility.
if command -v xvfb-run >/dev/null 2>&1; then
    OPENSCAD_RUN="xvfb-run -a openscad"
fi

echo "[render.sh] Generating hook.stl ..."
${OPENSCAD_RUN} -o hook.stl hook.scad

echo "[render.sh] Generating top-view render.png ..."
# Top-view orthographic: camera looking straight down (Z axis) at the assembly.
# eye_x,eye_y,eye_z,center_x,center_y,center_z
${OPENSCAD_RUN} \
    --imgsize=800,600 \
    --camera=0,0,120,0,0,0 \
    --projection=ortho \
    --autocenter \
    --viewall \
    --colorscheme=Tomorrow \
    -o render.png \
    hook.scad

echo "[render.sh] Done."
echo "  STL : $(stat -c '%s bytes' hook.stl)  hook.stl"
echo "  PNG : $(stat -c '%s bytes' render.png)  render.png"