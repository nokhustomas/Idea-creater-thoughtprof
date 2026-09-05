// Parametric L-Bracket (OpenSCAD)
// Parameters: L=60 (length), W=30 (width), T=4 (thickness),
//   H1=40 (vertical arm height), H2=40 (reserved), D=5 (hole diameter),
//   N=2 (number of holes), R=3 (fillet radius). All dimensions in mm.

$fn = 32;

L  = 60;
W  = 30;
T  = 4;
H1 = 40;
H2 = 40;
D  = 5;
N  = 2;
R  = 3;

// Two rectangular plates forming an L shape
module bracket_body() {
    union() {
        // Horizontal arm (bottom plate)
        cube([L, W, T]);
        // Vertical arm (back plate)
        translate([0, 0, T])
            cube([T, W, H1]);
    }
}

// N holes through the horizontal plate, evenly distributed along X
module holes() {
    for (i = [0:N-1]) {
        x_pos = (i + 0.5) * L / N;
        translate([x_pos, W/2, -1])
            cylinder(d=D, h=T+2, $fn=24);
    }
}

difference() {
    bracket_body();
    holes();
}
