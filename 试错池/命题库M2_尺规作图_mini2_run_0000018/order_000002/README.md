# 尺规作图的可与不可 —— 交互式教学网页

> 为什么正五边形能尺规作图，而正七边形永远不能？—— 讲到高中生能懂，含可操作的作图模拟，数学上严格（域扩张的思路要正确但不堆符号）。

## 一、项目目标

- **交互式教学**：通过 SVG 画布上的"直尺 / 圆规"工具，让学生亲手体验尺规作图的三条基本规则。
- **正五边形案例**：自动演示完整作图流程（45 秒左右），并解释为什么 cos 36° = (√5+1)/4 满足二次方程 ⇒ 可构造。
- **正七边形案例**：演示"无论如何尝试都找不到 7 等分点"的根源 —— cos(2π/7) 满足三次方程 x³+x²−2x−1=0，次数 3 不是 2 的幂 ⇒ 不可构造。
- **数学原理**：从"可构造数 → 域扩张 → 高斯定理"的角度讲清楚，但不堆代数符号。

## 二、文件结构

```
.
├── index.html               # 主页面（SVG 画布 + 工具栏 + 文案）
├── style.css                # 样式
├── math.js                  # 基础几何计算（解析几何实现）
├── geometry.js              # 尺规作图专用工具函数（直线交点 / 圆交点 / 中点 / 多边形）
├── script.js                # 交互逻辑（工具切换、自动演示、撤销、交点选择）
├── verify.js                # 数学验证（cos36°、cos(2π/7) 极小多项式数值复算）
├── docs/                    # 数学原理详细文档
│   ├── constructible-number.md
│   ├── regular-pentagon.md
│   └── heptagon.md
├── ConstructibleNumber.html # 单文件讲义：可构造数
├── TrigonometryConstants.html# 单文件讲义：三角常数
├── README.md                # 本文件
└── 运行命令.txt              # 一行自检命令
```

## 三、快速运行

```bash
# 进入工作目录后启动静态服务器
python3 -m http.server 8000 --bind 127.0.0.1 > /dev/null 2>&1 & sleep 2 \
  && curl -s localhost:8000/index.html | grep -q canvas && echo PASS || echo FAIL
```

打开浏览器访问 <http://127.0.0.1:8000/> 即可。

## 四、数学原理（可直接复算）

### 4.1 可构造数（Constructible Number）

尺规作图允许的三类操作：
1. 过两个已知点画直线；
2. 以一个已知点为圆心、过另一个已知点画圆；
3. 取两条曲线（直线或圆）的交点。

从单位长度 1 出发，经过有限步上述操作能得到的所有长度，称为"可构造数"。它们恰好等于对 1 做有限次 **加、减、乘、除、开平方** 所得到的全部实数。

**高斯定理**：每一步尺规作图所对应的数域扩张次数 ≤ 2。因此一个数可构造 ⇔ 它在 ℚ 上的极小多项式次数是 **2 的幂**。

### 4.2 正五边形可作

由五等分圆的几何关系推出：

$$
\cos 36° = \frac{\sqrt{5}+1}{4} \approx 0.8090169943749474
$$

代入验证：

$$
4x^2 - 2x - 1 = 0 \quad (x = \cos 36°)
$$

判别式 Δ = 4 + 16 = 20 > 0，二次根式可开方 ⇒ 次数 2 = 2¹ ⇒ **可构造**。

### 4.3 正七边形不可作

$$
\cos\frac{2\pi}{7} \approx 0.6234898018587336
$$

满足三次方程：

$$
x^3 + x^2 - 2x - 1 = 0
$$

验证：方程 x³+x²−2x−1=0 的三个实根为 2cos(2π/7)、2cos(4π/7)、2cos(6π/7)，数值残差 < 1e-10。

但 3 不是 2 的幂（2⁰=1, 2¹=2, 2²=4, 2³=8 均不含 3），所以 **不可构造**。

### 4.4 历史

- 1593 年 Viète（韦达）研究过正七边形作图，只能给出近似解；
- 1801 年 Gauss《算术研究》(Disquisitiones Arithmeticae) 给出完整可构造数理论；
- Galois 理论从根式可解角度彻底证明这条边界。

## 五、验证方法

### 5.1 数学验证（Node.js）

```bash
# 验证基础几何函数存在
node -e "const g=require('./geometry.js');console.log(typeof g.intersectLines,typeof g.intersectCircles,typeof g.midpoint)"

# 验证 cos(36°) 与极小多项式
node -e "const v=require('./verify.js');console.log(JSON.stringify(v.verifyCos36(),null,2))"

# 验证 cos(2π/7) 与三次极小多项式
node -e "const v=require('./verify.js');console.log(JSON.stringify(v.verifyDegree3(),null,2))"

# 一次跑完
node -e "const v=require('./verify.js');console.log(v.runAll().ok?'PASS':'FAIL')"
```

### 5.2 浏览器端

打开 `index.html`，依次点击：

1. ▶ **演示：正五边形** —— 观看约 45 秒自动作图，验证出 5 个等分点。
2. ▶ **演示：正七边形尝试** —— 观察为何无论怎么取交点都凑不出 7 等分。

控制台输出：

```js
Verify.runAll()   // {ok:true, cos36:{ok:true,...}, heptagon:{ok:true,...}}
```

## 六、操作提示

- **直尺**：依次点击两个已有点画直线。
- **圆规**：单击确定圆心，再次单击另一处定半径画圆。
- **选中**：点击元素查看 / 删除。
- 当两个图形的交点多于一个时，系统弹出菜单让你选哪一个。
- <kbd>空格</kbd> 推进动画下一步；<kbd>Ctrl+Z</kbd> 撤销。

## 七、坐标系约定

SVG 原点在左上角，**y 轴向下为正**。所有几何计算需要在内部统一转换到标准笛卡尔坐标。

## 八、参考资料

- C. F. Gauss, *Disquisitiones Arithmeticae*, 1801, Section VII.
- 维基百科 [Constructible number](https://en.wikipedia.org/wiki/Constructible_number)
- 维基百科 [Heptagon](https://en.wikipedia.org/wiki/Heptagon)
- 维基百科 [Trigonometric constants expressed in real radicals](https://en.wikipedia.org/wiki/Trigonometric_constants_expressed_in_real_radicals)
- 《普通高中数学课程标准（2017 年版 2020 年修订）》人教 A 版必修第二册"复数的几何意义"章节。

## 九、版权与许可

MIT License，仅供教学使用。