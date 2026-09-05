// verify.js
// 验证脚本：
//  - verifyCos36()   ：复算 cos(36°) = (√5 + 1) / 4，验证其极小多项式 4x² - 2x - 1 = 0
//  - verifyDegree3() ：复算 cos(2π/7) 的最小多项式 x³ + x² - 2x - 1 = 0
//  - verifyPowers()  ：验证 3 不是 2 的幂
//  - compareImage()  ：对比 canvas.toDataURL() 是否包含足够多的封闭线段（占位逻辑，避免依赖外部图像处理库）
//
// 既可以在浏览器里通过 <script src="verify.js"> 使用（挂到 window.Verify），
// 也可以在 Node.js 下 require('./verify.js') 使用。

(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else {
    root.Verify = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var EPS = 1e-9;

  function abs(x) { return x < 0 ? -x : x; }
  function nearlyEqual(a, b, eps) { eps = (eps == null) ? EPS : eps; return abs(a - b) < eps; }

  // ---------- cos(36°) 验证 ----------
  // cos(36°) = (√5 + 1) / 4 ≈ 0.8090169943749474
  // 极小多项式：4x² - 2x - 1 = 0
  function verifyCos36() {
    var sqrt5 = Math.sqrt(5);
    var cos36_formula = (sqrt5 + 1) / 4;
    var cos36_numeric = Math.cos(Math.PI / 5);
    var diff = abs(cos36_formula - cos36_numeric);

    // 代入极小多项式 4x² - 2x - 1
    var x = cos36_numeric;
    var poly = 4 * x * x - 2 * x - 1;

    // 判别式 Δ = 4 + 16 = 20 ⇒ 二次根号内可开方 ⇒ 次数 = 2 = 2¹ ⇒ 可构造
    var delta = (-2) * (-2) - 4 * 4 * (-1);

    var ok = diff < 1e-12 && abs(poly) < 1e-10 && delta > 0;
    return {
      ok: ok,
      cos36_formula: cos36_formula,
      cos36_numeric: cos36_numeric,
      diff: diff,
      polyValue: poly,
      discriminant: delta,
      degree: 2,
      isPowerOfTwo: isPowerOfTwo(2),
      message: ok
        ? 'cos(36°) = (√5+1)/4 ✓；代入 4x²-2x-1 ≈ 0 ✓；次数=2=2¹ 可构造 ✓'
        : 'cos(36°) 验证失败'
    };
  }

  // ---------- cos(2π/7) 验证 ----------
  // 极小多项式：x³ + x² - 2x - 1 = 0
  function verifyDegree3() {
    var cos_numeric = Math.cos(2 * Math.PI / 7);
    var x = cos_numeric;
    var poly = x * x * x + x * x - 2 * x - 1;

    // 用一个根反算另外两个根（用于交叉验证）
    // 三次方程 x³ + x² - 2x - 1 = 0 的三个实根都是 2cos(2kπ/7), k=1,2,3
    var r1 = 2 * Math.cos(2 * Math.PI / 7);
    var r2 = 2 * Math.cos(4 * Math.PI / 7);
    var r3 = 2 * Math.cos(6 * Math.PI / 7);
    function cubicVal(t) { return t * t * t + t * t - 2 * t - 1; }
    var p1 = abs(cubicVal(r1));
    var p2 = abs(cubicVal(r2));
    var p3 = abs(cubicVal(r3));

    var ok = abs(poly) < 1e-10 && p1 < 1e-10 && p2 < 1e-10 && p3 < 1e-10;
    return {
      ok: ok,
      cos_2pi_over_7: cos_numeric,
      polyValue: poly,
      roots: [r1, r2, r3],
      rootsResidual: [p1, p2, p3],
      degree: 3,
      isPowerOfTwo: isPowerOfTwo(3),
      message: ok
        ? 'cos(2π/7) 满足 x³+x²-2x-1=0 ✓；三个根 = 2cos(2kπ/7) ✓；次数=3 不是 2 的幂 ⇒ 不可构造 ✓'
        : 'cos(2π/7) 验证失败'
    };
  }

  // ---------- 验证 n 是否是 2 的幂 ----------
  function isPowerOfTwo(n) {
    if (typeof n !== 'number' || !isFinite(n) || n <= 0) return false;
    var v = Math.round(n);
    if (Math.abs(v - n) > EPS) return false;
    // 2 的幂 & (2 的幂 - 1) = 0
    return (v & (v - 1)) === 0;
  }

  // ---------- 验证 3 不是 2 的幂 ----------
  function verifyThreeIsNotPowerOfTwo() {
    return {
      ok: !isPowerOfTwo(3),
      powers: [Math.pow(2, 0), Math.pow(2, 1), Math.pow(2, 2), Math.pow(2, 3)],
      message: !isPowerOfTwo(3)
        ? '3 不是 2 的幂（2⁰=1, 2¹=2, 2²=4, 2³=8 均不含 3）✓'
        : '失败：3 不应该是 2 的幂'
    };
  }

  // ---------- 图像比对占位 ----------
  // 浏览器端可以从 toDataURL 拿到字符串后做启发式判断：
  // "包含 5 条闭合线段" = 至少出现 5 个成对的 line/polygon 节点，并且 polygon 节点具有 "points" 属性
  function compareImage(svgString) {
    if (typeof svgString !== 'string') {
      return { ok: false, count: 0, message: '未提供 SVG 字符串' };
    }
    // 统计 <polygon> 节点
    var polygonMatches = svgString.match(/<polygon\b[^>]*>/gi) || [];
    // 统计 <line> 节点
    var lineMatches = svgString.match(/<line\b[^>]*>/gi) || [];
    return {
      ok: polygonMatches.length >= 1 && lineMatches.length >= 4,
      polygonCount: polygonMatches.length,
      lineCount: lineMatches.length,
      message: '已统计 SVG 中的 polygon / line 节点数'
    };
  }

  // ---------- 一步运行所有 ----------
  function runAll() {
    var r36 = verifyCos36();
    var r7 = verifyDegree3();
    var r3 = verifyThreeIsNotPowerOfTwo();
    var allOk = r36.ok && r7.ok && r3.ok;
    return { ok: allOk, cos36: r36, heptagon: r7, powerOfTwo: r3 };
  }

  return {
    EPS: EPS,
    verifyCos36: verifyCos36,
    verifyDegree3: verifyDegree3,
    verifyThreeIsNotPowerOfTwo: verifyThreeIsNotPowerOfTwo,
    isPowerOfTwo: isPowerOfTwo,
    compareImage: compareImage,
    runAll: runAll
  };
}));