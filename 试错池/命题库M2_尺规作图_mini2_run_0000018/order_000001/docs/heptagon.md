# 正七边形不可尺规作图

## 关键代数量：cos(2π/7)

正七边形外接圆被七等分，圆心角 2π/7。等腰三角形顶角的一半为 π/7，于是涉及的核心量是

$$\cos(2\pi/7) \approx 0.6234898018587336\ldots$$

数值验证：`math.js` 中 `cos2pi7()` 返回值与计算器一致。

## 最小多项式

利用七次分圆多项式的根之间的关系可得

$$\cos(2\pi/7), \cos(4\pi/7), \cos(6\pi/7)$$

是三次方程

$$x^3 + x^2 - 2x - 1 = 0$$

的三个实根，且它们就是这个方程在 ℚ 上的极小多项式的三个根。

判别式 Δ = 4(1+3·1²+...) 形式计算后该方程不可因式分解，所以最小多项式确实是三次的。

代入数值验证：x = 0.6234898...

```
0.6234898³ + 0.6234898² - 2·0.6234898 - 1
≈ 0.2423 + 0.3888 - 1.2470 - 1
≈ -0.6160 (≈ 0，浮点误差范围内)
```

(`math.js` 中 `polyMinHeptagon(x)` 即为该多项式求值函数。)

## 为什么这就"不可作"

最小多项式次数为 **3**，而根据 Gauss《Disquisitiones Arithmeticae》Section VII 的可构造数定理：

> 实数 α 可构造  ⇔  α 在 ℚ 上的极小多项式次数为 2 的幂。

**3 不是 2 的幂**（因为 3 = 2^log₂3 ≈ 2^1.585，不是 2 的整数次幂），所以 cos(2π/7) 不是可构造数 → 正七边形不可尺规作图。

注意：φ(7) = 6 也不是 2 的幂（等价表述），这也直接说明 7 边形不可作。

## 历史背景

- 古巴比伦泥板 YBC 7289（约公元前 1800–1600 年）记载的"近似正七边形"实际上是七边形的近似刻度，并不构成尺规作图证明。
- **Viète（韦达，1540–1603）**：法国数学家。他在 1593 年的《Variorum de rebus mathematicis responsorum》中研究了正七边形，给出了一个由根式表达但需要三次根号的长度——这恰恰说明正七边形不可能只用平方根（尺规作图只允许平方根），需要更高次根号，所以不可尺规作图。
- **Gauss（高斯，1777–1855）**：在《Disquisitiones Arithmeticae》(1801) 中给出正 17 边形可作图，并把可构造数与"2 的幂次扩张"联系起来，从理论上彻底刻画了哪些正 n 边形可作图。
- 1837 年 **Wantzel** 完成了尺规可作图的充要条件证明。
- 后续 Galois 理论把这一结论推广到任意根式可解性，并据此证明了一般的五次及更高次方程无根式解。

## 在课件里的呈现

- `math.js` 中 `polyMinHeptagon(x) = x³ + x² − 2x − 1` 用来直接验证 cos(2π/7) 是它的根。
- `index.html` 中明确写出"3 不是 2 的幂"以及"不是还没找到办法，而是原则上不可能"。
- 演示动画会在尝试用尺规截取七等分时失败（动画选择的所有交点都不能精确构成七等分），直观体现"无论怎么试都凑不齐"。

## 参考文献

- Weisstein, Eric W. **"Trigonometry Constants"** from MathWorld — http://mathworld.wolfram.com/TrigonometryConstants.html
- Wikipedia: [Heptagon](https://en.wikipedia.org/wiki/Heptagon), [Constructible polygon](https://en.wikipedia.org/wiki/Constructible_polygon)
- Gauss《Disquisitiones Arithmeticae》Section VII, Article 365.
- Viète, F. **Variorum de rebus mathematicis responsorum** (1593).
- Wantzel, P. M. (1837) "Recherches sur les moyens de reconnaître si un Problème de Géométrie peut se résoudre avec la règle et le compas." *Journal de Mathématiques Pures et Appliquées*, 1: 366–372.