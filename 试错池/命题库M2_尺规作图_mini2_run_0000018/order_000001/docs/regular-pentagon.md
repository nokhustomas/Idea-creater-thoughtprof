# 正五边形可尺规作图

## 经典作图步骤

任选圆周上两点 A、B：

1. 画弦 AB；
2. 作 AB 的中垂线得圆心 O；
3. 以 OA 为半径作圆（外接圆）；
4. 在圆周上依次截取等分点 C, D, E；
5. 连接 A, B, C, D, E 即得正五边形。

## 关键代数量：cos 36°

将圆周四等分对应的角是 90°，五等分对应的圆心角是 72°，于是等腰三角形顶角的一半就是 36°。由几何关系可得

$$\cos(36°) = \frac{\sqrt{5} + 1}{4} \approx 0.80901699\ldots$$

**数值验证**：(√5 + 1) / 4 = (2.2360679... + 1) / 4 = 3.2360679.../4 ≈ 0.80901699...
与计算器 `cos(36°)` = 0.8090169943749474 完全一致。

## 极小多项式

由五等分圆的几何关系可以推得：

$$4 \cos^2(36°) - 2 \cos(36°) - 1 = 0$$

设 x = cos(36°)，其极小多项式为 **4x² − 2x − 1 = 0**，次数为 **2**。

2 = 2¹ 是 2 的幂，根据 Gauss《Disquisitiones Arithmeticae》Section VII 的可构造数定理，cos(36°) 是可构造数 → 正五边形可尺规作图。

### 验证 4x² − 2x − 1 = 0

判别式 Δ = 4 + 16 = 20，根为

$$x = \frac{2 \pm \sqrt{20}}{8} = \frac{1 \pm \sqrt{5}}{4}$$

取正根即 x = (1 + √5) / 4 = (√5 + 1) / 4 ✓ 与 cos(36°) 数值一致。

## 历史小注

- 古希腊数学家已经掌握正五边形尺规作图（Euclid《几何原本》Book IV, Prop. 11）。
- 1796 年 Gauss 在日记中写道："…principia quibus innititur theoria, easdem esse quae circa aequationem 4x²−2x−1=0 obtinent…"，把 5 边形可作与该二次方程直接联系。
- 1509 年 Pacioli 画过五角星的黄金比例分割图，是数学与艺术的著名结合。

## 参考文献

- Euclid《几何原本》Book IV, Proposition 11 — https://mathcs.clarku.edu/~djoyce/elements/bookIV/propIV11.html
- Weisstein, Eric W. **"Trigonometry Constants"** from MathWorld — http://mathworld.wolfram.com/TrigonometryConstants.html
- Gauss《Disquisitiones Arithmeticae》Section VII.
- Honsberger, R. **Mathematical Gems II**, Chapter on Regular Polygons.