# 可构造数（Constructible Number）

## 定义

在平面几何中，给定两个点（从而确定一个"单位长度"），只用以下三类操作可以得到的任何长度所对应的实数，称为**可构造数**：

1. 过两个已知点画**直线**；
2. 以一个已知点为圆心、过另一个已知点画**圆**；
3. 取两条直线 / 两圆 / 直线与圆的**交点**。

从代数角度看，可构造数恰好是：从 1 出发，经过有限次加、减、乘、除、开平方运算能够得到的全部实数。

## 历史背景

- 古典尺规作图三大难题（化圆为方、三等分角、倍立方）数千年来悬而未决。
- 1796 年 Gauss 19 岁时给出正十七边形可作图的构造方法，并在《Disquisitiones Arithmeticae》（《算术研究》，1801 年出版）中给出系统的代数刻画。
- 1837 年 Pierre Wantzel 给出尺规可作图的完整判定（[Wantzel 1837](https://en.wikipedia.org/wiki/Pierre_Wantzel)）。
- 后续 Galois 理论将这一结果推广到更高次根。

## 核心定理（Gauss《Disquisitiones Arithmeticae》Section VII, Article 365）

> 设初始域为 ℚ（即"单位长度 1"所对应的有理数域）。每一步尺规作图：
> - 作直线 / 圆：等价于一次至多 **2 次扩张**；
> - 取交点：等价于一次至多 **2 次扩张**。
>
> 因此，经过有限步后所能达到的数域是 ℚ 的 **2 的幂次** 塔式扩张。
>
> **推论**：实数 α 是可构造数当且仅当它在 ℚ 上的极小多项式次数为 **2 的幂**。

## 等价表述（常用于课本）

正 *n* 边形能尺规作图  ⇔  cos(2π/*n*) 是可构造数
                       ⇔  φ(*n*) 是 2 的幂
                       （φ 为 Euler totient 函数）

详见 Stewart《Galois Theory》第四章（Constructible Numbers and Regular Polygons）。

## 参考文献与可查证来源

- Weisstein, Eric W. **"Constructible Number"** from MathWorld — http://mathworld.wolfram.com/ConstructibleNumber.html
- Gauss, C. F. **Disquisitiones Arithmeticae** (1801), Section VII "De aequationibus circuli et sectionum"; English translation available at https://archive.org/details/disquisitionesa00gausrich
- Stewart, I. **Galois Theory** (3rd ed.), Chapter 4.
- Wikipedia 词条 [Constructible number](https://en.wikipedia.org/wiki/Constructible_number)

## 在本课件中的角色

正五边形 vs 正七边形这一节，使用了上述定理的直接推论：

- cos(36°) 的极小多项式 4x² − 2x − 1 = 0 次数为 2 = 2¹，是 2 的幂 → 可作；
- cos(2π/7) 的最小多项式 x³ + x² − 2x − 1 = 0 次数为 3，不是 2 的幂 → 永远不可作。