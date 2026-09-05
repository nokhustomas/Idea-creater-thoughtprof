// Parametric L-bracket
L = 60; W = 30; T = 4; H1 = 40; H2 = 40; D = 5; N = 2; R = 3;

module rounded_cube(dim, r) {
    hull() {
        for (x = [r, dim[0]-r], y = [r, dim[1]-r], z = [r, dim[2]-r]) {
            translate([x, y, z]) sphere(r=r);
        }
    }
}

module l_bracket() {
    difference() {
        union() {
            rounded_cube([T, W, H1], R);
            rounded_cube([L, T, H2], R);
        }
        spacing = (L - T - 2*R) / (N + 1);
        for (i = [1:N]) {
            x_pos = T + R + i * spacing;
            translate([x_pos, T/2, H1/2])
                rotate([90, 0, 0]) cylinder(d=D, h=W+2, center=true);
        }
    }
}

l_bracket();
