#!/bin/bash
set -e
cd "$(dirname "$0")"
openscad -o cable_organizer.stl cable_organizer.scad 2>&1 | tee /tmp/scad.log
echo "---"
ls -la cable_organizer.stl
file cable_organizer.stl
SIZE=$(stat -c%s cable_organizer.stl)
echo "SIZE=$SIZE"
test "$SIZE" -gt 1000 && echo "STL file valid"