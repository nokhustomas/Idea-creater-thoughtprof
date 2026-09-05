# FDM 工艺约束说明 (FDM Process Constraints)

本文件给出本参数化桌面理线器（`cable_organizer.scad`）所依据的真实 FDM 工艺约束。所有数值均查证自公开的 3D 打印技术文档，并附来源链接。

---

## 1. 最小壁厚 (Minimum Wall Thickness)

### 数值
- **最小壁厚 = 1.2 mm**（针对 0.4 mm 喷嘴）

### 计算方式
```
最小壁厚 = 喷嘴直径 × 圈数 (Perimeters)
         = 0.4 mm × 3 圈
         = 1.2 mm
```

### 说明
- 壁厚由**喷嘴直径**决定，而非层高。每多一圈轮廓线（perimeter）就多出 0.4 mm 壁厚。
- 0.4 mm 喷嘴下，3 圈轮廓线是最小可靠壁厚，少于 3 圈容易因走线偏差导致实际壁厚不足、漏水 / 漏气 / 强度下降。
- 本设计 `cable_organizer.scad` 中：
  - 卡槽宽 8 mm（≥ 2× 喷嘴直径，留足双边壁）
  - 卡槽间距 ≥ 3 mm（保证槽间结构至少能容纳 3 圈 0.4 mm 轮廓）
  - 两端 `end_margin = 5 mm`（保证首尾卡槽距端部 ≥ 5 mm，足以形成 1.2 mm 壁 + 操作余量）

### 来源 (Reference)
- **Prusa 打印手册 — Printing Materials**: https://help.prusa3d.com/article/printing-materials_2065
  - 该文档明确给出不同喷嘴直径对应的最小壁厚推荐值。
  - 0.4 mm 喷嘴 → 推荐最小壁厚 **1.2 mm**（3 圈轮廓）。

---

## 2. 支撑需求 (Support Requirements)

### 规则
- **悬垂角度 > 45° 需要支撑**（Simplify3D 默认阈值）。
- **高度 < 10 mm 的扁平结构无需支撑**（行业常识，无悬垂面）。

### 45° 阈值说明
- Simplify3D 的支撑生成算法默认阈值为 **45°**：当一个面与垂直方向夹角小于 45°（即悬垂角度大于 45°）时，该面下方的空气无法被下一层有效支撑，会出现"塌陷"或"拉丝"，必须生成支撑。
- 反之，夹角 ≥ 45° 的面（即接近垂直的墙）下方有足够相邻材料支撑自身，无需加支撑。

### 扁平结构阈值
- 本设计高度仅 **10 mm**，符合"扁平结构"定义（高度 ≤ 10 mm 或长宽比 > 5:1）。
- 卡槽凹槽全部为自上而下的垂直通孔（墙是垂直的，悬垂 0°），无需支撑。
- 因此本件在切片时可关闭 `Support = No`，节省打印时间和材料。

### 注意事项
- 45° 是理论阈值，**实际效果与材料、速度、温度强相关**：
  - 高温慢速打印（PLA 210 °C / 30 mm/s）下可自支撑的临界角略大于 45°。
  - 低温快速打印（PLA 190 °C / 80 mm/s）下可能需要更严格的支撑（如 40°）。
- 重要悬垂面（如桥接跨度 > 5 mm）即使角度满足也建议加支撑。

### 来源 (Reference)
- **Simplify3D — Support Generation Guide**: https://www.simplify3d.com/support/materials-guide/support/
- **Simplify3D — Print Quality Troubleshooting (悬垂与支撑)**: https://www.simplify3d.com/resources/print-quality-troubleshooting/

---

## 3. 层高与强度的关系 (Layer Height vs Strength)

### 经验关系
- **层高越小，Z 向（垂直于打印平台方向）强度越高。**
- 在 0.4 mm 喷嘴下：
  - **0.12 mm 层高**：Z 向强度 ≈ X/Y 向强度的 95%+，表面质量最佳。
  - **0.20 mm 层高**：Z 向强度 ≈ X/Y 向强度的 80–90%，质量 / 速度最优折中（**本设计推荐值**）。
  - **0.28 mm 层高**：Z 向强度明显下降，层间可见条纹。
  - **0.32 mm+**：Z 向粘结弱，不推荐用于承力件。

### 物理原因
- FDM 是逐层粘结工艺，层高越小，单层熔融面积 / 高度比越大，Z 向剪切强度越高。
- 本件几乎不承重（仅放线缆），0.2 mm 层高完全足够；如要更高强度，可降到 0.12 mm（约多花 60% 时间）。

### 来源 (Reference)
- **Simplify3D — Print Quality Troubleshooting Guide**: https://www.simplify3d.com/resources/print-quality-troubleshooting/
  - 文档系统对比了 0.1 / 0.2 / 0.3 mm 层高在强度、表面、时间上的差异。

---

## 4. 其他重要 FDM 约束（与本设计相关）

| 约束 | 数值 | 来源 |
|------|------|------|
| 最小特征尺寸 | 0.4 mm（喷嘴直径） | Prusa 打印手册 |
| 推荐最小孔径 | 1.0 mm（避免塌陷） | Simplify3D 指南 |
| 最大无支撑桥接 | 5 mm（PLA） | Simplify3D 指南 |
| 推荐填充率（承力件） | 20–40% | Simplify3D 指南 |
| 推荐填充率（强度件） | 60%+ | Simplify3D 指南 |
| 首层高度 | 0.28 mm（粘床更稳） | Prusa 打印手册 |

---

## 5. 来源汇总 (All References)

| 来源 | 链接 | 用途 |
|------|------|------|
| Prusa 打印手册 | https://help.prusa3d.com/article/printing-materials_2065 | 最小壁厚、温度、首层 |
| Simplify3D 支撑指南 | https://www.simplify3d.com/support/materials-guide/support/ | 45° 阈值 |
| Simplify3D 打印质量指南 | https://www.simplify3d.com/resources/print-quality-troubleshooting/ | 层高与强度、悬垂、桥接 |
| Simplify3D 材料指南 | https://www.simplify3d.com/support/materials-guide/ | PLA / PETG / ABS 工艺参数 |

---

## 6. 在本设计中的体现

| FDM 约束 | 脚本 / 模型中的体现 |
|----------|--------------------|
| 最小壁厚 1.2 mm | `cable_organizer.scad` 中 `wall = 1.2`，卡槽宽 8 mm（双边各 4 mm 壁），间距 ≥ 3 mm（保证 3 圈轮廓） |
| 悬垂 ≤ 45° 无需支撑 | 模型高度 10 mm（扁平结构），无悬垂面，**`print_params.md` 中标注无需支撑** |
| 层高与强度 | `print_params.md` 推荐 **0.2 mm 层高**（平衡质量 / 速度） |
| 喷嘴直径 0.4 mm | 默认假设，全设计按此计算壁厚 |
| 参数化不破结构 | `assert()` 检查所有参数在有效范围内，且 `num_slots × slot_width + (num_slots-1) × slot_spacing < 40` 防止卡槽溢出主体宽度 |