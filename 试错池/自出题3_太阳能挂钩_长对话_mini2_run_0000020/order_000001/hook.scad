// ============================================================
// Parametric Solar Panel Hook for Eave Round Pipe
// For Li-shu: roof orchard small PV / camera mount
// ============================================================

// --- Tunable parameters ---
// angle: tilt angle of the hook arm, 0 ≤ angle ≤ 60 (degrees)
angle = 30;       // tilt angle in degrees, range 0-60

// clamp_d: inner diameter of the pipe clamp in mm, 25-50 default
clamp_d = 33;     // clamp inner diameter, range 20-100 mm

// plate_w: width of the top mounting plate (mm)
plate_w = 60;

// plate_l: length of the top mounting plate (mm)
plate_l = 80;

// plate_t: thickness of the top mounting plate (mm)
plate_t = 4;

// arm_w: width of the angled arm connecting clamp to plate (mm)
arm_w = 30;

// arm_t: thickness of the angled arm (mm)
arm_t = 4;

// clamp_width: width of the U-bolt / clamp band (mm)
clamp_width = 25;

// wall: clamp wall thickness (mm)
wall = 3;

// screw_r: bolt hole radius for clamp (mm)
screw_r = 2.5;

// mount_hole_r: bolt hole radius for panel/camera mount (mm)
mount_hole_r = 3;

// mount_hole_spacing: distance between two mounting holes (mm)
mount_hole_spacing = 40;

// $fn for smooth curves
$fn = 64;

// --- Derived values ---
clamp_r = clamp_d / 2;
arm_angle = angle; // alias for clarity

echo(str("angle=", angle, " deg (range 0..60)"));
echo(str("clamp_d=", clamp_d, " mm (range 20..100)"));

module clamp_half(side) {
    // side: +1 or -1 for the two halves of the clamp
    difference() {
        // Outer arc clamp band
        rotate([0, 0, 0])
        difference() {
            // outer cylinder shell
            translate([0, 0, -clamp_width/2])
                cylinder(r = clamp_r + wall, h = clamp_width, center = false);
            // inner pipe hole
            translate([0, 0, -clamp_width/2 - 1])
                cylinder(r = clamp_r, h = clamp_width + 2, center = false);
            // cut along x-axis to split into two halves (side dependent)
            if (side > 0) {
                translate([0, -clamp_r - wall - 1, -clamp_width/2 - 1])
                    cube([clamp_r + wall + 2, clamp_r + wall + 2, clamp_width + 2]);
            } else {
                translate([0, clamp_r + wall + 1, -clamp_width/2 - 1])
                    cube([clamp_r + wall + 2, clamp_r + wall + 2, clamp_width + 2]);
            }
        }
        // bolt holes through the flange
        for (i = [-1, 1]) {
            translate([i * (clamp_r + wall/2), side * (clamp_r + wall/2 + 1), 0])
                rotate([90, 0, 0])
                cylinder(r = screw_r, h = wall + 4, center = true);
        }
    }
}

module clamp() {
    // Full pipe clamp: two halves
    translate([0, 0, 0]) clamp_half(1);
    translate([0, 0, 0]) clamp_half(-1);
}

module angled_arm() {
    // The angled arm connecting clamp to top plate
    arm_length = clamp_r + wall + 40;
    difference() {
        // Box arm, rotated by angle around X-axis
        translate([0, clamp_r + wall, clamp_width/2])
            rotate([arm_angle, 0, 0])
            translate([0, 0, 0])
            cube([arm_w, arm_length, arm_t], center = true);
        // mounting holes in the arm (lightening optional)
    }
}

module mounting_plate() {
    // Top plate at the end of the angled arm
    arm_length = clamp_r + wall + 40;
    plate_offset = arm_length;
    translate([0, clamp_r + wall, clamp_width/2])
        rotate([arm_angle, 0, 0])
        translate([0, plate_offset, arm_t/2 + plate_t/2])
            difference() {
                cube([plate_w, plate_l, plate_t], center = true);
                // mounting holes for panel/camera
                for (i = [-1, 1]) {
                    translate([0, i * mount_hole_spacing/2, 0])
                        cylinder(r = mount_hole_r, h = plate_t + 2, center = true);
                }
            }
}

// --- Main assembly ---
union() {
    clamp();
    angled_arm();
    mounting_plate();
}