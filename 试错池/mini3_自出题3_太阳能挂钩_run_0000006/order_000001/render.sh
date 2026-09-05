#!/usr/bin/env bash
# =============================================================================
# render.sh — build the solar-panel eave-hook CAD model.
#
# Produces (in the current working directory):
#   * hook.stl  — printable mesh of hook.scad at the default parameters
#   * hook.png  — top-view render of the same model (for visual review)
#
# Usage:
#   ./render.sh              # build with default parameters
#   ./render.sh -Dangle=20   # override any hook.scad parameter
#
# Requires: openscad on PATH.  Image export also requires a working
# OpenSCAD GUI backend or xvfb-run on headless systems.
# =============================================================================

set -euo pipefail

SCAD="hook.scad"
STL="hook.stl"
PNG="hook.png"

if ! command -v openscad >/dev/null 2>&1; then
    echo "ERROR: openscad not found on PATH" >&2
    exit 1
fi

# Forward any extra -D overrides the user passes to render.sh.
OPTS=("$@")

echo "[render] building ${STL} from ${SCAD}..."
openscad -o "${STL}" "${OPTS[@]}" "${SCAD}"

# Hard-warnings / warnings check (acceptance criterion).
if openscad --enable=all -o /tmp/null.stl "${OPTS[@]}" "${SCAD}" 2>&1 \
        | grep -iE 'warning|error' ; then
    echo "ERROR: openscad produced warnings or errors" >&2
    exit 1
fi

if [[ ! -s "${STL}" ]] || [[ "$(stat -c %s "${STL}")" -le 1024 ]]; then
    echo "ERROR: ${STL} is missing or smaller than 1 KB" >&2
    exit 1
fi

echo "[render] ${STL} built ( $(stat -c %s "${STL}") bytes )"

echo "[render] rendering top-view ${PNG}..."
# Top view: camera positioned above the part looking straight down (-Y).
if command -v xvfb-run >/dev/null 2>&1; then
    xvfb-run -a openscad \
        --camera=0,0,0,0,0,0,180 \
        --imgsize=1024,1024 \
        --colorscheme=Tomorrow \
        -o "${PNG}" "${OPTS[@]}" "${SCAD}"
else
    openscad \
        --camera=0,0,0,0,0,0,180 \
        --imgsize=1024,1024 \
        --colorscheme=Tomorrow \
        -o "${PNG}" "${OPTS[@]}" "${SCAD}"
fi

if [[ ! -s "${PNG}" ]]; then
    echo "ERROR: ${PNG} was not produced" >&2
    exit 1
fi

echo "[render] ${PNG} built ( $(stat -c %s "${PNG}") bytes )"
echo "[render] done."