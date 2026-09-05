// ============================================================
// Parametric Desktop Cable Organizer
// OpenSCAD script - adjustable length, slot count, spacing, etc.
// ============================================================

/* [Dimensions] */
// Total length along X axis (mm): 80-200
length = 120;
// Number of cable slots: 3-8
num_slots = 5;
// Width of each cable slot along X (mm): 6-12
slot_width = 8;
// Depth of each cable slot along Y (mm): 10-20
slot_depth = 15;
// Spacing between adjacent slots along X (mm): >= 3
slot_spacing = 5;

// Derived constants
body_width  = 40;  // Y dimension (mm) - flat structure, no support needed
body_height = 10;  // Z dimension (mm) - flat structure, no support needed
end_margin  = 5;   // margin from end of body to first/last slot

// Parameter validation
assert(length >= 80 && length <= 200, str("length out of range: ", length));
assert(num_slots >= 3 && num_slots <= 8, str("num_slots out of range: ", num_slots));
assert(slot_width >= 6 && slot_width <= 12, str("slot_width out of range: ", slot_width));
assert(slot_depth >= 10 && slot_depth <= 20, str("slot_depth out of range: ", slot_depth));
assert(slot_spacing >= 3, str("slot_spacing too small: ", slot_spacing));

// Total occupied length along X (slots spread along length, not width)
total_slot_length = num_slots * slot_width + (num_slots - 1) * slot_spacing;
assert(total_slot_length + 2 * end_margin <= length,
       str("slots overflow body length: total=", total_slot_length + 2 * end_margin, " length=", length));

// Slot depth (Y) must not exceed body width
assert(slot_depth < body_width,
       str("slot_depth exceeds body_width: ", slot_depth, " >= ", body_width));

// Module: one slot cut (square hole going through Z)
// slot_width is along X, slot_depth is along Y
module slot_cut(i) {
    group_span = num_slots * slot_width + (num_slots - 1) * slot_spacing;
    x_start = (length - group_span) / 2 + i * (slot_width + slot_spacing);
    y_center = body_width / 2;
    // Slightly oversized in Z to fully cut through body
    translate([x_start, y_center - slot_depth / 2, -1])
        cube([slot_width, slot_depth, body_height + 2]);
}

module cable_organizer() {
    difference() {
        // Main body: length x body_width x body_height, centered on origin in Y/Z
        translate([0, -body_width / 2, 0])
            cube([length, body_width, body_height]);
        // Subtract each slot
        for (i = [0 : num_slots - 1]) {
            slot_cut(i);
        }
    }
}

echo("ECHO: Cable Organizer Parameters");
echo(str("ECHO: length=", length, "mm"));
echo(str("ECHO: body_width=", body_width, "mm"));
echo(str("ECHO: body_height=", body_height, "mm"));
echo(str("ECHO: num_slots=", num_slots));
echo(str("ECHO: slot_width=", slot_width, "mm"));
echo(str("ECHO: slot_depth=", slot_depth, "mm"));
echo(str("ECHO: slot_spacing=", slot_spacing, "mm"));
echo(str("ECHO: total_slot_length=", total_slot_length, "mm"));

cable_organizer();