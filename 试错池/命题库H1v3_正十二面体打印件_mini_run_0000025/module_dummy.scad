// module_dummy.scad
// 1:1 假模块（正五边形片，边长 208mm 留边隙、厚 8mm）
// 背面：30mm 圆形插头凸台、5 个磁铁位、5 个卡扣舌
// 沿 y 轴对称拆成 A/B 两半打印（与面框同缝）
//
// 用法：
//   openscad -D 'is_left=1' -o module_dummy_A.stl module_dummy.scad
//   openscad -D 'is_left=0' -o module_dummy_B.stl module_dummy.scad

// ============ 参数 ============
a              = 208;      // 五边形边长 (mm) — 比 220 小 12mm（每边 6mm 边隙）
thickness      = 8;        // 厚 (mm) — 题面

socket_d       = 30;       // 背面 30mm 圆形插头凸台直径
socket_h       = 6;        // 凸台高度（伸出背面）
magnet_d       = 8;        // 磁铁位直径
magnet_depth   = 3;        // 磁铁位凹位深
magnet_radius  = 12;       // 磁铁位环半径（与面框一致）

clip_w         = 8;        // 卡扣舌宽
clip_l         = 15;       // 卡扣舌长（径向伸出长度）
clip_t         = 3;        // 卡扣舌厚（高度，与面框卡扣槽深一致）

is_left = 1;

$fn = 96;

// ============ 五边形几何（与面框一致：顶点朝上） ============
function pentagon_verts(R) = [
    for (i = [0:4])
        let (a0 = 90 + i * 72)
        [ R * cos(a0), R * sin(a0) ]
];

R_circum = a / (2 * sin(36));

module dummy_plate_2d() {
    polygon(pentagon_verts(R_circum));
}

// ============ 假模块主体（未切割） ============
module dummy_full() {
    union() {
        // 主体：八边形片（实心）
        linear_extrude(height = thickness)
            dummy_plate_2d();

        // 背面插头凸台（位于背面 Z=0，前面向 +Z；凸台向 -Z 方向伸出）
        // 我们约定"背面"为 -Z 方向，凸台从底面向下伸
        translate([0, 0, -socket_h])
            cylinder(d = socket_d, h = socket_h, $fn = 64);

        // 5 个磁铁位（背面凹位）：Ø8×3，半径12mm，72°均布
        // 凹位在 Z ∈ [0, magnet_depth]（向 -Z 凹）
        for (i = [0:4]) {
            rotate([0, 0, i * 72])
                translate([magnet_radius, 0, -magnet_depth])
                    cylinder(d = magnet_d, h = magnet_depth + 0.1, $fn = 32);
        }

        // 5 个卡扣舌（径向伸出，从五边形外边缘向外伸 15mm × 厚 3mm × 宽 8mm）
        // 位于 5 条边的中点方向（126 + i*72），沿径向 +cos/sin 方向向外
        for (i = [0:4]) {
            edge_mid_angle = 126 + i * 72;
            edge_dist = R_circum * cos(36);   // 边中点到圆心距
            // 舌放在 dummy 厚度外侧（Z 方向），径向伸出
            rotate([0, 0, edge_mid_angle])
                translate([edge_dist + clip_l / 2, 0, thickness / 2])
                    cube([clip_l, clip_w, clip_t], center = true);
        }
    }
}

// ============ 半件切割 ============
module half_model() {
    difference() {
        dummy_full();
        if (is_left) {
            // 去掉右侧 (x > 0)
            translate([0.05, -R_circum - 1, -(socket_h + 1)])
                cube([R_circum * 2 + 2, (R_circum + 1) * 2, thickness + socket_h + 2]);
        } else {
            // 去掉左侧 (x < 0)
            translate([-R_circum * 2 - 2 - 0.05, -R_circum - 1, -(socket_h + 1)])
                cube([R_circum * 2 + 2, (R_circum + 1) * 2, thickness + socket_h + 2]);
        }
    }
}

half_model();