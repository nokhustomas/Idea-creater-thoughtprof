// clip.scad
// 卡扣舌单独零件（可换、可试不同厚度）
// 尺寸：8mm 宽 × 20mm 长 × 3mm 厚，末端有 1.5mm 凸点做卡扣
// 一版打 10 个（render.sh 输出 clip.stl 是 10 个并排版，方便一次性打印）

// ============ 参数 ============
clip_w   = 8;     // 宽 (mm) — 与面框卡扣槽宽一致
clip_l   = 20;    // 长 (mm) — 略长于槽长 15，留 5mm 做卡扣头
clip_t   = 3;     // 厚 (mm) — 与面框卡扣槽深一致
hook_l   = 5;     // 卡扣头长（在末端）
hook_h   = 1.5;   // 卡扣头凸出高（在 clip_t 方向之外）

copies   = 10;    // 一版打 10 个
gap_x    = 2;     // 个体间隔
gap_y    = 2;

$fn = 32;

module clip_single() {
    union() {
        // 主体
        translate([0, 0, clip_t / 2])
            cube([clip_l, clip_w, clip_t], center = true);

        // 末端卡扣凸点（位于 +X 末端，向 +Z 凸 hook_h）
        translate([clip_l / 2 - hook_l / 2, 0, clip_t + hook_h / 2])
            cube([hook_l, clip_w, hook_h], center = true);
    }
}

// 把单个旋转 90°，让它"短边 20 沿 X、长边 8 沿 Y"（bbox 20×8）
module clip_single_rot() {
    rotate([0, 0, 90]) clip_single();
}

// 排列 10 个：2 列（沿 X，pitch=clip_l+gap=22） × 5 行（沿 Y，pitch=clip_w+gap=10）
// bbox ≈ 42 × 48 × 4.5 → 最长边 48mm
module clip_batch() {
    pitch_x = clip_l + gap_x;   // 22
    pitch_y = clip_w + gap_y;   // 10
    for (i = [0:copies - 1]) {
        cx = (i % 2) * pitch_x;
        cy = floor(i / 2) * pitch_y;
        translate([cx, cy, 0]) clip_single_rot();
    }
}

clip_batch();