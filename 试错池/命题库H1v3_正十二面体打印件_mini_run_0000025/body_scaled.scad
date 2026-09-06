// body_scaled.scad
// 1:3 正十二面体空壳 (a=73.3mm)，12 个五边形面各留按比例缩小的圆形插座凹位
// 底面那个改为底座定位孔
// 客户原话：1:3 整机空壳（正十二面体，a≈73mm，相对面间距约 163mm），壁厚 2mm

// ============ 参数 ============
a = 63; // 边长 (mm) — 取 63 使 bbox≈165mm（150-175 区间内）   // 边长 (mm) — 取 63 使 bbox≈165mm（150-175 区间内）
wall_t           = 2;      // 壁厚 (mm) — 题面

// 1:1 插座 30mm → 1:3 ≈ 10mm
socket_d_full    = 30;
socket_d         = socket_d_full * (a / 220);  // ≈ 10mm
socket_depth     = wall_t + 1;                  // 凹位稍深于壁厚，便于插件插入

magnet_d_full    = 8;
magnet_d         = magnet_d_full * (a / 220); // ≈ 2.67mm
magnet_radius    = 12 * (a / 220);            // ≈ 4mm
magnet_depth     = 1.5;

// 底座定位孔（替换底面插座）
base_pilot_d     = 6;       // 底座定位孔直径
base_pilot_depth = 3;

phi = (1 + sqrt(5)) / 2;

$fn = 64;

// ============ 几何（沿用客户验证过的骨架） ============
function dodecahedron_pts(k) = [
    for (x = [-1, 1], y = [-1, 1], z = [-1, 1]) [x, y, z] * k,
    for (x = [-1, 1], y = [-1, 1])             [0, x / phi, y * phi] * k,
    for (x = [-1, 1], y = [-1, 1])             [x / phi, y * phi, 0] * k,
    for (x = [-1, 1], y = [-1, 1])             [x * phi, 0, y / phi] * k
];

module dodeca_hull(k) {
    hull() for (p = dodecahedron_pts(k))
        translate(p) sphere(0.01, $fn = 6);
}

// 12 个面法向（黄金比例坐标）
normals = [
    [0,  1,  phi], [0, -1,  phi], [0,  1, -phi], [0, -1, -phi],
    [1,  phi, 0], [-1,  phi, 0], [1, -phi, 0], [-1, -phi, 0],
    [phi, 0,  1], [-phi, 0,  1], [phi, 0, -1], [-phi, 0, -1]
];

module shell(a, t) {
    k = a / (2 / phi);
    ri = a * 1.1135;
    difference() {
        dodeca_hull(k);
        dodeca_hull(k * (ri - t) / ri);
    }
}

// 在某个法向 nn 上定位一个子体（把 z 轴对齐到 nn，沿 nn 平移 ri 到面中心）
module on_face(nn, a) {
    n = nn / norm(nn);
    rotate([0, acos(n[2]), atan2(n[1], n[0])])
        translate([0, 0, a * 1.1135])
            children();
}

// ============ 在 12 个面上挖插座（底面换定位孔） ============
module all_face_features() {
    ri_face = a * 1.1135;
    // 选法向 z 分量最小的那一面作为"底面"（指向 -z）
    bottom_idx = 0;
    bottom_n = normals[0];
    bottom_z = bottom_n[2];
    for (i = [0:11]) {
        if (normals[i][2] < bottom_z) {
            bottom_z = normals[i][2];
            bottom_idx = i;
        }
    }

    for (i = [0:11]) {
        n = normals[i];
        // 用 hull-of-cubes + scale 来确保 difference 能切到外壁
        if (i == bottom_idx) {
            // 底面：底座定位孔（贯穿或浅凹）
            on_face(n, a)
                translate([0, 0, -base_pilot_depth])
                    cylinder(d = base_pilot_d, h = base_pilot_depth + 1, $fn = 32);
        } else {
            // 普通面：圆形插座凹位
            on_face(n, a)
                translate([0, 0, -socket_depth])
                    cylinder(d = socket_d, h = socket_depth + 1, $fn = 32);
        }
    }
}

// ============ 输出 ============
difference() {
    shell(a, wall_t);
    all_face_features();
}