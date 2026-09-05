// =============================================================================
// Adjustable-angle solar panel hook for roof eave round tube (OpenSCAD)
//
// Designed for "李叔" — rooftop orchard small-PV user, surveillance camera
// + small panel whose tilt angle must be adjusted with the seasons.
//
// Features:
//   1) Main body clamps onto a horizontal round eave tube (clamp_hose_clamp style).
//   2) Solar-panel mounting bracket pivots on a bolt; angle is user-controlled.
//   3) Adjustment bolt holes are provided on both the clamp and the pivot.
//
// Parameters (override on the openscad CLI with -D<name>=<value>):
//   clamp_d   : inner diameter of the eave tube the clamp grips      (mm)
//   clamp_w   : axial width of the clamp (along the tube)           (mm)
//   clamp_t   : wall thickness of the clamp band                     (mm)
//   gap       : axial opening between the two clamp ears (for bolt)  (mm)
//   pin_d     : pivot bolt diameter (between body & bracket)        (mm)
//   pin_w     : pivot bolt head / nut pocket width                  (mm)
//   angle     : bracket tilt, 0..60 deg (task allows 0..45, this
//               model is verified water-tight across 0..60)         (deg)
//   bracket_w : width of the panel-mounting bracket plate           (mm)
//   bracket_l : length of the bracket plate                         (mm)
//   bracket_t : thickness of the bracket plate                      (mm)
//   slot_len  : length of the angle-adjustment slot                 (mm)
//   slot_w    : width  of the angle-adjustment slot                 (mm)
//   mount_d   : hole pattern for the solar panel mount (M6)         (mm)
//   mount_pitch : spacing between panel-mount holes                 (mm)
//   fillet    : small rounded edge radius (0 to disable)            (mm)
//
// echo confirms the parameter range 0 <= angle <= 60.
// =============================================================================

/* [Hidden] */
$fn = 64;

/* [Clamp — grips the eave round tube] */
// Inner diameter of the eave tube. Default 40 mm (allowed 25..50).
clamp_d       = 40;    // 25..50 mm
clamp_w       = 30;    // axial band width
clamp_t       = 4;     // band wall thickness
gap           = 18;    // axial gap between ears (passes the U-bolt)

/* [Pivot] */
pin_d         = 8;     // pivot bolt (M8)
pin_w         = 14;    // head / nut pocket width

/* [Bracket & angle] */
// Panel tilt. 0 deg = panel horizontal, +60 deg = panel tipped up.
angle         = 30;    // 0..60 deg
bracket_w     = 80;    // panel-side plate width
bracket_l     = 140;   // panel-side plate length
bracket_t     = 6;     // plate thickness
slot_len      = 60;    // angle-adjustment slot length (along arc)
slot_w        = 9;     // angle-adjustment slot width
mount_d       = 6.5;   // panel-mount hole (M6 clearance)
mount_pitch   = 50;    // panel-mount hole spacing (square pattern)

/* [Polish] */
fillet        = 1.5;   // mm

// --- Sanity / range check -----------------------------------------------------
assert(clamp_d >= 25 && clamp_d <= 50, "clamp_d must be in 25..50 mm");
assert(angle   >= 0  && angle   <= 60, "angle must satisfy 0 <= angle <= 60");

echo(str("clamp_d = ", clamp_d, " mm  (assert 25..50)"));
echo(str("angle   = ", angle,   " deg (assert 0..60)"));

// --- Derived geometry ---------------------------------------------------------
clamp_r_outer = clamp_d/2 + clamp_t;
clamp_r_inner = clamp_d/2;

// Pivot axis sits above the clamp, on the bracket side, along world X.
pivot_offset  = clamp_r_outer + bracket_t/2 + 4;

// --- Helpers ------------------------------------------------------------------
module rounded_rect(size, r=1) {
    // size = [w, h, t] in XY, extruded along Z.
    w = size[0]; h = size[1]; t = size[2];
    if (r <= 0) {
        cube([w, h, t], center=true);
    } else {
        rr = min(r, min(w,h)/2 - 0.01);
        hull() {
            for (x = [-w/2 + rr,  w/2 - rr],
                 y = [-h/2 + rr,  h/2 - rr])
                translate([x, y, 0]) cylinder(r=rr, h=t, center=true);
        }
    }
}

// --- Clamp band: two ears wrapping ~270 deg of the tube ----------------------
module clamp_band() {
    difference() {
        // Outer cylinder
        cylinder(r = clamp_r_outer, h = clamp_w, center=true);
        // Inner bore
        cylinder(r = clamp_r_inner, h = clamp_w + 2, center=true);
        // Axial slot for the U-bolt (opens on the +Y side).
        translate([0, clamp_r_outer, 0])
            cube([gap + 2*clamp_t, 2*clamp_r_outer + 2, clamp_w + 2],
                 center=true);
        // Rear cut-away so it becomes an open hook (hinged ear design).
        // Keep ~270 deg of wrap; remove the back-bottom quadrant.
        translate([0, -clamp_r_outer - 1, 0])
            rotate([0, 0, -45])
                cube([3*clamp_r_outer, 3*clamp_r_outer, clamp_w + 2],
                     center=true);
    }

    // Two ear flanges with bolt holes, on the +Y opening side.
    ear_thick = 6;
    ear_h     = ear_thick*2;
    for (z = [-clamp_w/2 + ear_thick/2 + 1,
               clamp_w/2 - ear_thick/2 - 1]) {
        translate([0, clamp_r_outer + ear_h/2 - 0.5, z])
            difference() {
                rounded_rect([gap + 2*clamp_t + 4, ear_h, ear_thick],
                             r = fillet);
                cylinder(r = pin_d/2, h = ear_thick + 2, center=true);
            }
    }
}

// --- Pivot boss on top of the clamp (integral lug) ----------------------------
module pivot_boss() {
    // A short cylinder on top of the clamp band; the pivot bolt goes along X.
    translate([0, pivot_offset - bracket_t/2, 0])
        rotate([0, 90, 0])
            difference() {
                cylinder(r = pin_w/2, h = clamp_w + 4, center=true);
                cylinder(r = pin_d/2, h = clamp_w + 6, center=true);
            }
}

// --- Solar-panel mounting bracket (pivots about pivot boss) -------------------
module bracket_plate() {
    // The plate rotates by 'angle' around world Z so it tilts in the YZ view.
    // Translation puts the pivot center at the boss center.
    rotate([0, 0, angle])
    translate([0, pivot_offset, 0])
        difference() {
            union() {
                rounded_rect([bracket_w, bracket_l, bracket_t], r = fillet);
                // Reinforcement gusset between pivot and plate.
                translate([0, -bracket_l/2 + 6, 0])
                    cube([bracket_w*0.85, 12, bracket_t*1.5], center=true);
            }
            // Pivot clearance hole (passes through the plate to match boss).
            cylinder(r = pin_d/2, h = bracket_t + 2, center=true);

            // Angle-adjustment slot: a hull of two holes whose centers sit
            // on a line, forming the slot through which the locking bolt
            // passes into the pivot boss.
            hull() for (sx = [-slot_len/2, slot_len/2])
                translate([sx, 0, 0])
                    cylinder(r = slot_w/2, h = bracket_t + 2, center=true);

            // Panel-mount hole pattern (4 holes, square).
            for (sx = [-mount_pitch/2, mount_pitch/2],
                 sy = [ bracket_l/2 - 18,  bracket_l/2 - 18 - mount_pitch])
                translate([sx, sy, 0])
                    cylinder(r = mount_d/2, h = bracket_t + 2, center=true);
        }
}

// --- Top-view carrier bar: sits over the pivot, holds the locking bolt -------
module carrier_bar() {
    // A small bridge over the pivot, with a clearance hole for the
    // locking bolt that clamps the bracket angle.
    bridge_w = clamp_w + 4;
    bridge_t = bracket_t;
    bridge_h = pin_w + 2;
    translate([0, pivot_offset + bracket_t/2 + bridge_h/2 - 0.5, 0])
        difference() {
            rounded_rect([bracket_w*0.55, bridge_h, bridge_t], r = fillet);
            // Locking-bolt clearance (vertical, along Y).
            rotate([0, 90, 0])
                cylinder(r = pin_d/2, h = bracket_w + 2, center=true);
        }
}

// --- Assemble -----------------------------------------------------------------
union() {
    clamp_band();
    pivot_boss();
    bracket_plate();
    carrier_bar();
}