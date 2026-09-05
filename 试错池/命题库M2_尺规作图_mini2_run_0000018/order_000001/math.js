/* math.js
 * 几何计算模块（解析几何）。
 *
 * 约定：
 *   - 内部使用标准笛卡尔坐标：x 向右为正，y 向上为正。
 *   - SVG 默认 y 轴向下为正，因此所有从屏幕点 (sx, sy) 进入的坐标都应先
 *     转成 (x = sx, y = -sy)（或者维持 SVG 坐标但牢记 y 轴方向），
 *     index.html 已注明 "y 轴向下为正"，此处函数全部用 SVG 坐标系的 (x, y)
 *     （即 y 向下为正）以避免来回转换，但调用方需要注意。
 *   - 点的表示：{ x, y, id?, kind? }。
 *
 * 直线方程：两点式 L: (y2 - y1)(x - x1) = (x2 - x1)(y - y1)
 * 圆方程：(x - cx)^2 + (y - cy)^2 = r^2
 *
 * 直线-圆交点：联立后得到关于 x（或 y）的一元二次方程，
 *              判别式 Δ = b^2 - 4ac。
 *              Δ < 0 无交点；Δ = 0 相切（单交点）；Δ > 0 两交点。
 *
 * 圆-圆交点：两圆方程相减得一条直线，再求该直线与任一圆的交点。
 */

// ---------- 基础对象 ----------

class Point {
  constructor(x, y, id = null, kind = 'point') {
    this.x = x;
    this.y = y;
    this.id = id;
    this.kind = kind; // 'point' | 'center' | 'intersection'
  }
}

class Line {
  constructor(p1, p2) {
    this.p1 = p1;
    this.p2 = p2;
    // 一般式 ax + by + c = 0
    this.a = p2.y - p1.y;
    this.b = p1.x - p2.x;
    this.c = -(this.a * p1.x + this.b * p1.y);
  }
  // 直线方向向量
  direction() {
    return { x: this.p2.x - this.p1.x, y: this.p2.y - this.p1.y };
  }
}

class Circle {
  constructor(center, radius) {
    this.center = center;
    this.radius = radius;
  }
}

// ---------- 数值常量 ----------

const Math2 = window.Math;

// cos(36°) = (√5 + 1) / 4
function cos36() {
  return (Math2.sqrt(5) + 1) / 4;
}

// cos(72°) = (√5 - 1) / 4
function cos72() {
  return (Math2.sqrt(5) - 1) / 4;
}

// cos(2π/7)，数值约 0.6234898...
function cos2pi7() {
  return Math2.cos((2 * Math.PI) / 7);
}

// cos(2π/5) = cos(72°)
function cos2pi5() {
  return Math2.cos((2 * Math.PI) / 5);
}

// 三角函数 → 度
function radToDeg(rad) {
  return (rad * 180) / Math.PI;
}

// 度 → 弧度
function degToRad(deg) {
  return (deg * Math.PI) / 180;
}

// 两点距离
function distance(p1, p2) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  return Math2.sqrt(dx * dx + dy * dy);
}

// ---------- 直线 / 圆 交点 ----------

/**
 * 判别式 Δ = b^2 - 4ac 用于判断一元二次方程根的情况，
 * 这里同时给出返回值：< 0 无实根（无交点），
 * = 0 单根（相切），
 * > 0 两根（两个交点）。
 */
function discriminantOfQuadratic(a, b, c) {
  return b * b - 4 * a * c;
}

/**
 * 直线与圆的交点。返回 0 / 1 / 2 个交点。
 * 圆方程 (x-cx)^2 + (y-cy)^2 = r^2；
 * 直线方程 ax + by + c = 0；
 * 把 y = -(ax + c)/b 代入圆方程，整理后得到一元二次方程：
 *    (a^2 + b^2) x^2 + 2(a c + b c2 + a cx b) x + ... = 0
 * 这里直接用参数化直线 + 投影方法避免手算错误。
 *
 * 实现要点（参考《解析几何》教材通用方法）：
 *   1) 直线方向 d = (p2 - p1)；
 *   2) 圆心 c 到直线 p1 的投影 t = (c - p1) · d / (d · d)；
 *   3) 投影点 q = p1 + t d；
 *   4) 距离 h = |c - q|；
 *   5) 判别式 Δ = r^2 - h^2；
 *   6) 偏移 u = √Δ / |d|；
 *   7) 交点 = q ± u d。
 */
function intersectLineCircle(line, circle) {
  const d = line.direction();
  const denom = d.x * d.x + d.y * d.y;
  if (denom === 0) return [];
  const fx = circle.center.x - line.p1.x;
  const fy = circle.center.y - line.p1.y;
  const t = (fx * d.x + fy * d.y) / denom;
  const qx = line.p1.x + t * d.x;
  const qy = line.p1.y + t * d.y;
  const h2 = (circle.center.x - qx) ** 2 + (circle.center.y - qy) ** 2;
  const delta = circle.radius * circle.radius - h2;
  if (delta < -1e-9) return [];
  if (Math.abs(delta) < 1e-9) {
    return [new Point(qx, qy)];
  }
  const u = Math2.sqrt(delta) / Math2.sqrt(denom);
  return [
    new Point(qx + u * d.x, qy + u * d.y),
    new Point(qx - u * d.x, qy - u * d.y),
  ];
}

/**
 * 圆与圆的交点。
 * 两圆方程相减得到一条直线（公共弦所在直线），
 * 再求该直线与其中任一圆的交点。
 */
function intersectCircleCircle(c1, c2) {
  const dx = c2.center.x - c1.center.x;
  const dy = c2.center.y - c1.center.y;
  const d = Math2.sqrt(dx * dx + dy * dy);
  if (d === 0) return [];                  // 同心
  if (d > c1.radius + c2.radius + 1e-9) return [];  // 相离
  if (d + Math.min(c1.radius, c2.radius) < Math.max(c1.radius, c2.radius) - 1e-9) return []; // 内含

  // 圆心连线上的两个交点相对于 c1 的偏移
  const a = (c1.radius * c1.radius - c2.radius * c2.radius + d * d) / (2 * d);
  const h2 = c1.radius * c1.radius - a * a;
  if (h2 < 0) h2 = 0;
  const h = Math2.sqrt(h2);

  const baseX = c1.center.x + (a * dx) / d;
  const baseY = c1.center.y + (a * dy) / d;

  // 垂直方向（旋转 90°）
  const rx = -dy / d;
  const ry = dx / d;

  if (h < 1e-9) {
    return [new Point(baseX, baseY)];
  }
  return [
    new Point(baseX + h * rx, baseY + h * ry),
    new Point(baseX - h * rx, baseY - h * ry),
  ];
}

/**
 * 两条直线的交点。直线平行时返回空数组。
 */
function intersectLineLine(l1, l2) {
  const det = l1.a * l2.b - l2.a * l1.b;
  if (Math.abs(det) < 1e-9) return [];
  const x = (l1.b * l2.c - l2.b * l1.c) / det;
  const y = (l2.a * l1.c - l1.a * l2.c) / det;
  return [new Point(x, y)];
}

/**
 * 给定圆心与起点，沿指定角度方向确定圆上的点。
 */
function pointOnCircle(circle, angleRad) {
  return new Point(
    circle.center.x + circle.radius * Math2.cos(angleRad),
    circle.center.y + circle.radius * Math2.sin(angleRad)
  );
}

/**
 * 把多边形顶点环绕角度均分。n 等分圆，从 startAngle 起。
 */
function divideCirclePoints(circle, n, startAngle = 0) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = startAngle + (2 * Math.PI * i) / n;
    pts.push(pointOnCircle(circle, a));
  }
  return pts;
}

/**
 * 在两点之间插入等分点（共 n 段则 n-1 个内点）。
 */
function divideSegmentPoints(p1, p2, n) {
  const pts = [];
  for (let i = 1; i < n; i++) {
    pts.push(new Point(
      p1.x + (p2.x - p1.x) * (i / n),
      p1.y + (p2.y - p1.y) * (i / n)
    ));
  }
  return pts;
}

// ---------- 数值验证（小工具） ----------

/**
 * 极小多项式求值：4x^2 - 2x - 1。理论上应为零。
 */
function polyMinPentagon(x) {
  return 4 * x * x - 2 * x - 1;
}

/**
 * 最小多项式求值：x^3 + x^2 - 2x - 1。理论上应为零。
 */
function polyMinHeptagon(x) {
  return x * x * x + x * x - 2 * x - 1;
}

// 暴露到 window
window.Math2 = Math2;
window.Point = Point;
window.Line = Line;
window.Circle = Circle;
window.cos36 = cos36;
window.cos72 = cos72;
window.cos2pi7 = cos2pi7;
window.cos2pi5 = cos2pi5;
window.radToDeg = radToDeg;
window.degToRad = degToRad;
window.distance = distance;
window.discriminantOfQuadratic = discriminantOfQuadratic;
window.intersectLineCircle = intersectLineCircle;
window.intersectCircleCircle = intersectCircleCircle;
window.intersectLineLine = intersectLineLine;
window.pointOnCircle = pointOnCircle;
window.divideCirclePoints = divideCirclePoints;
window.divideSegmentPoints = divideSegmentPoints;
window.polyMinPentagon = polyMinPentagon;
window.polyMinHeptagon = polyMinHeptagon;