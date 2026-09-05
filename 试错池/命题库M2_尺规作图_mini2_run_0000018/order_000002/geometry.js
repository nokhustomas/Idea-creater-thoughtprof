// geometry.js
// 几何工具函数：求直线交点、圆交点、线段中点、垂直平分线等
// 既可以在浏览器通过 <script src="geometry.js"> 使用（挂到 window.Geometry），
// 也可以在 Node.js 下通过 require('./geometry.js') 使用（兼容 CommonJS）。

(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.Geometry = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var EPS = 1e-9;

  // ---------------- 基础工具 ----------------

  function nearlyEqual(a, b, eps) {
    eps = (eps == null) ? EPS : eps;
    return Math.abs(a - b) < eps;
  }

  function distance(p1, p2) {
    var dx = p2.x - p1.x, dy = p2.y - p1.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function midpoint(p1, p2) {
    return { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
  }

  // ---------------- 直线 ----------------
  // 直线用一般式 Ax + By + C = 0 表示，对应方向向量 (B, -A)。

  function lineFromTwoPoints(p1, p2) {
    var A = p2.y - p1.y;
    var B = p1.x - p2.x;
    var C = -(A * p1.x + B * p1.y);
    return { A: A, B: B, C: C };
  }

  function lineIntersect(l1, l2) {
    var det = l1.A * l2.B - l2.A * l1.B;
    if (Math.abs(det) < EPS) return null; // 平行或重合
    var x = (l1.B * l2.C - l2.B * l1.C) / det;
    var y = (l2.A * l1.C - l1.A * l2.C) / det;
    return { x: x, y: y };
  }

  // 给定直线和其上一点，求垂足
  function perpendicularFoot(line, p) {
    var A = line.A, B = line.B, C = line.C;
    var denom = A * A + B * B;
    if (denom < EPS) return null;
    var x = (B * (B * p.x - A * p.y) - A * C) / denom;
    var y = (A * (-B * p.x + A * p.y) - B * C) / denom;
    return { x: x, y: y };
  }

  // 给定两个点，求垂直平分线
  function perpendicularBisector(p1, p2) {
    var mid = midpoint(p1, p2);
    // 方向与 (p2-p1) 垂直：原方向 (p2.x-p1.x, p2.y-p1.y)
    // 垂直方向 (-(p2.y-p1.y), p2.x-p1.x)
    var dx = p2.x - p1.x, dy = p2.y - p1.y;
    // 一般式：dx * (x - mid.x) + dy * (y - mid.y) = 0  即 dx*x + dy*y - (dx*mid.x + dy*mid.y) = 0
    return {
      A: dx,
      B: dy,
      C: -(dx * mid.x + dy * mid.y)
    };
  }

  // ---------------- 圆 ----------------
  // 圆用 {cx, cy, r} 表示。

  function circleLineIntersect(circle, line) {
    // 代入一般式 A x + B y + C = 0
    // 把直线方程化为 y = (-A x - C) / B（B ≠ 0）或 x = (-B y - C) / A（A ≠ 0）
    // 这里用更通用的"投影"做法：先求圆心到直线的距离，再沿直线方向偏移。
    var A = line.A, B = line.B, C = line.C;
    var denom = Math.sqrt(A * A + B * B);
    if (denom < EPS) return [];
    var signed = (A * circle.cx + B * circle.cy + C) / denom;
    var d2 = (A * circle.cx + B * circle.cy + C) * (A * circle.cx + B * circle.cy + C) / (A * A + B * B);
    var r2 = circle.r * circle.r;
    if (d2 > r2 + EPS) return [];
    if (Math.abs(d2 - r2) < EPS) {
      // 一个切点
      var t = - (A * circle.cx + B * circle.cy + C) / (A * A + B * B);
      return [{ x: circle.cx + A * t, y: circle.cy + B * t }];
    }
    // 两个交点
    var t = - (A * circle.cx + B * circle.cy + C) / (A * A + B * B);
    var foot = { x: circle.cx + A * t, y: circle.cy + B * t };
    var h = Math.sqrt(r2 - d2);
    var ux = -B / denom, uy = A / denom;
    return [
      { x: foot.x + ux * h, y: foot.y + uy * h },
      { x: foot.x - ux * h, y: foot.y - uy * h }
    ];
  }

  function circleCircleIntersect(c1, c2) {
    var d = distance({ x: c1.cx, y: c1.cy }, { x: c2.cx, y: c2.cy });
    if (d < EPS) return []; // 同心
    if (d > c1.r + c2.r + EPS) return []; // 外离
    if (d < Math.abs(c1.r - c2.r) - EPS) return []; // 内含
    var a = (c1.r * c1.r - c2.r * c2.r + d * d) / (2 * d);
    var h2 = c1.r * c1.r - a * a;
    var h = (h2 < 0) ? 0 : Math.sqrt(h2);
    var px = c1.cx + a * (c2.cx - c1.cx) / d;
    var py = c1.cy + a * (c2.cy - c1.cy) / d;
    if (h < EPS) return [{ x: px, y: py }];
    return [
      { x: px + h * (c2.cy - c1.cy) / d, y: py - h * (c2.cx - c1.cx) / d },
      { x: px - h * (c2.cy - c1.cy) / d, y: py + h * (c2.cx - c1.cx) / d }
    ];
  }

  // ---------------- 弧上取点 ----------------

  function pointOnCircle(circle, angleRad) {
    return {
      x: circle.cx + circle.r * Math.cos(angleRad),
      y: circle.cy + circle.r * Math.sin(angleRad)
    };
  }

  // 给定圆心和一个起点（圆上点），按指定方向（顺时针 -1 / 逆时针 +1）截取等分
  function circleDivide(circle, startPoint, count, direction) {
    direction = direction || 1; // 默认逆时针
    var startAngle = Math.an2(startPoint.y - circle.cy, startPoint.x - circle.cx);
    var step = (2 * Math.PI) / count;
    var pts = [];
    for (var i = 0; i < count; i++) {
      var a = startAngle + direction * i * step;
      pts.push(pointOnCircle(circle, a));
    }
    return pts;
  }

  // 兼容 atan2 的小补丁（避免极个别环境缺函数）
  if (typeof Math.atan2 === 'function') {
    Math.an2 = Math.atan2;
  }

  // ---------------- 多边形周长 / 面积 ----------------

  function polygonArea(pts) {
    var s = 0;
    for (var i = 0; i < pts.length; i++) {
      var a = pts[i], b = pts[(i + 1) % pts.length];
      s += a.x * b.y - b.x * a.y;
    }
    return Math.abs(s) / 2;
  }

  function polygonPerimeter(pts) {
    var s = 0;
    for (var i = 0; i < pts.length; i++) {
      var a = pts[i], b = pts[(i + 1) % pts.length];
      s += distance(a, b);
    }
    return s;
  }

  return {
    EPS: EPS,
    distance: distance,
    midpoint: midpoint,
    lineFromTwoPoints: lineFromTwoPoints,
    lineIntersect: lineIntersect,
    perpendicularFoot: perpendicularFoot,
    perpendicularBisector: perpendicularBisector,
    circleLineIntersect: circleLineIntersect,
    circleCircleIntersect: circleCircleIntersect,
    pointOnCircle: pointOnCircle,
    circleDivide: circleDivide,
    polygonArea: polygonArea,
    polygonPerimeter: polygonPerimeter,
    nearlyEqual: nearlyEqual
  };
}));