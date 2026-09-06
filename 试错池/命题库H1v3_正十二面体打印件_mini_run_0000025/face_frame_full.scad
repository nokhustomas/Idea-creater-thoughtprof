// face_frame_full.scad
// 1:1 正五边形面框，沿 90° 对称轴(y轴) 拆成 A/B 两半打印
// 客户原话：边长 220mm，外接圆直径 374mm，边框宽 25mm、厚 6mm
// 拼合：中央定位榫(5x20x3) + 2个M3通孔(Ø3.3，中心距分割线15mm、孔距30mm)
// 中央：Ø30 圆形插座凹位 + 5 个 Ø8x3 磁铁位(半径12mm、72°均布)
// 卡扣槽：5 个 8x15x3，外壁侧，72°均布
//
// 用法：
//   openscad -D 'is_left=1' -o face_frame_full_A.stl face_frame_full.scad
//   openscad -D 'is_left=0' -o face_frame_full_B.stl face_frame_full.scad

// ============ 参数（顶部可改） ============
a                = 220;   // 五边形边长 (mm) — 题面
border_width     = 25;    // 边框宽 (mm) — 题面
border_thickness = 6;     // 边框厚 (mm) — 题面

socket_d         = 30;    // 中央插座直径 (mm) — 题面
socket_depth     = 3;     // 中央插座凹位深 (mm) — 推导/常见结构
magnet_d         = 8;     // 磁铁位直径 (mm) — 题面
magnet_depth     = 3;     // 磁铁位深 (mm) — 题面
magnet_radius    = 12;    // 磁铁位环半径 (mm) — 题面

tenon_w          = 5;     // 定位榫宽（沿 X，越过分割线）— 常见结构
tenon_l          = 20;    // 定位榫长（沿 Y，分割线方向）— 常见结构
tenon_h          = 3;     // 定位榫高（沿 Z，框厚方向）— 常见结构

m3_hole_d        = 3.3;   // M3 通孔直径 (mm) — 常见结构
m3_offset        = 15;    // M3 孔中心距分割线 (mm) — 常见结构
m3_spacing       = 30;    // M3 两孔中心距 (mm) — 常见结构

slot_w           = 8;     // 卡扣槽宽 (mm) — 题面
slot_l           = 15;    // 卡扣槽长 (mm) — 题面
slot_d           = 3;     // 卡扣槽深 (mm) — 题面

// 派生：外接圆半径（题面 374/2 = 187）
R_circum = a / (2 * sin(36));

// 决定打印哪一半；render.sh 通过 -D 'is_left=1' 或 'is_left=0' 覆盖
is_left = 1;

$fn = 96;

// ============ 五边形几何 ============
// 顶点朝上（旋转 90° 使底边水平）；5 个顶点角 = 90 + i*72
function pentagon_verts(R) = [
    for (i = [0:4])
        let (a0 = 90 + i * 72)
        [ R * cos(a0), R * sin(a0) ]
];

// 沿法向向内偏移 d 后的五边形顶点（顶点处内角 108°，等距偏移后顶点
// 沿径向 -cos/sin 方向移动 d 即得到对应内五边形顶点）
function pentagon_verts_inward(R, d) = [
    for (i = [0:4])
        let (a0 = 90 + i * 72)
        [ (R * cos(a0)) - d * cos(a0),
          (R * sin(a0)) - d * sin(a0) ]
];

module pentagon_poly(verts) polygon(verts);

// 中空五边形面框 2D
module frame_2d() {
    difference() {
        pentagon_poly(pentagon_verts(R_circum));
        pentagon_poly(pentagon_verts_inward(R_circum, border_width));
    }
}

// ============ 完整面框（未切割） ============
module frame_full() {
    difference() {
        // 主体：中空五边形，厚 border_thickness
        linear_extrude(height = border_thickness)
            frame_2d();

        // 中央 Ø30 插座凹位：从顶面往下凹 socket_depth
        translate([0, 0, border_thickness - socket_depth])
            cylinder(d = socket_d, h = socket_depth + 0.1, $fn = 64);

        // 5 个磁铁位（Ø8x3，半径12mm，72°均布）
        for (i = [0:4]) {
            rotate([0, 0, i * 72])
                translate([magnet_radius, 0, border_thickness - magnet_depth])
                    cylinder(d = magnet_d, h = magnet_depth + 0.1, $fn = 32);
        }

        // 5 个卡扣槽（外壁侧，8x15x3）
        // 外五边形 5 条边的中点方向角 = 顶点角 + 36° = 126 + i*72
        // 边中点到圆心距 = R*cos(36°)
        // 槽沿径向朝中心凹入，长度沿边切向
        for (i = [0:4]) {
            edge_mid_angle = 126 + i * 72;
            edge_dist = R_circum * cos(36);
            rotate([0, 0, edge_mid_angle])
                translate([edge_dist - slot_d / 2, 0, border_thickness / 2])
                    cube([slot_d + 0.1, slot_w, slot_l], center = true);
        }
    }
}

// ============ M3 通孔（每个半件各 1 个） ============
// A 半孔心在 x=-m3_offset，B 半孔心在 x=+m3_offset
// 这样拼合后两孔相距 2*m3_offset = 30mm（= m3_spacing）
module m3_hole_half() {
    if (is_left)
        translate([-m3_offset, 0, -0.1])
            cylinder(d = m3_hole_d, h = border_thickness + 0.2, $fn = 32);
    else
        translate([m3_offset, 0, -0.1])
            cylinder(d = m3_hole_d, h = border_thickness + 0.2, $fn = 32);
}

// ============ 定位榫（A 半凸 / B 半凹） ============
// 都在分割线 x=0 附近、y∈[-10,+10] 居中
module tenon_features() {
    if (is_left) {
        // 凸榫：从 x=0 到 x=+tenon_w，跨入 B 半领地
        translate([tenon_w / 2, 0, border_thickness / 2])
            cube([tenon_w, tenon_l, tenon_h], center = true);
    } else {
        // 凹槽：从 x=0 到 x=+tenon_w，在 B 半内部挖空
        translate([tenon_w / 2, 0, border_thickness / 2])
            cube([tenon_w + 0.2, tenon_l + 0.2, tenon_h + 0.2], center = true);
    }
}

// ============ 半框（切割） ============
// A 半：x <= 0；B 半：x >= 0。切割盒尺寸足够大以覆盖整个框。
module half_model() {
    difference() {
        union() {
            frame_full();
            tenon_features();
            // 在 x=0 平面加一小薄片防止切割后底面缺料（无影响）
        }
        // 用大立方体切割
        if (is_left) {
            translate([0.05, -R_circum - 1, -0.1])
                cube([R_circum * 2 + 2, (R_circum + 1) * 2, border_thickness + 1]);
        } else {
            translate([-R_circum * 2 - 2 - 0.05, -R_circum - 1, -0.1])
                cube([R_circum * 2 + 2, (R_circum + 1) * 2, border_thickness + 1]);
        }
    }
    // M3 孔：在切割之后再打孔，保证孔完整存在于本半
    difference() {
        // 再加一点占位（差集用）
        m3_hole_half();
    }
}

// ============ 输出 ============
half_model();