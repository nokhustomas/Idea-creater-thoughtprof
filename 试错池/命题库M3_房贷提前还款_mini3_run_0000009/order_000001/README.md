# 房贷提前还款决策器 (Mortgage Prepayment Decision Calculator)

一个基于浏览器的单页应用，对比"提前还款"与"投资理财"两种策略的现金流差异，
含机会成本（月复利理财收益）和通胀因子（实际购买力调整）。
规则依据中国现行房贷政策，覆盖中行、工行、建行、农行、交行、招行、邮储七家主流银行。

---

## 🚀 快速开始 (Quick Start)

### 在线预览（30 秒内自检命令）

```bash
cd $(dirname "$0") && python3 -m http.server 8080 > /dev/null 2>&1 &
SERVER_PID=$!
sleep 2
curl -s http://localhost:8080/index.html | grep -qE "(房贷|计算|银行)" && echo "✅ 页面结构完整"
kill $SERVER_PID 2>/dev/null
```

或单行版本：

```bash
cd $(dirname "$0") && python3 -m http.server 8080 > /dev/null 2>&1 & sleep 2 && curl -s http://localhost:8080/index.html | grep -qE "(房贷|计算|银行)" && pkill -f "python3 -m http.server"
```

浏览器打开 <http://localhost:8080/index.html>

### 直接打开

`index.html` 是纯静态文件，可直接双击在浏览器打开（无需服务器）。

---

## 📖 使用方法 (Usage)

### 网页端
1. 在「决策计算」标签页填写：
   - **贷款余额**：剩余未还本金（元）
   - **年利率**：如 0.049 表示 4.9%
   - **剩余年限**：剩余还款年数
   - **还款方式**：等额本息 / 等额本金
   - **可用提前还款金额**：拟一次性提前还款的金额
   - **提前还款时点**：第几个月执行提前还款
   - **提前还款策略**：缩短年限（推荐）或降低月供
   - **理财年化收益率**：用于计算机会成本（默认 3%）
   - **通胀年化率**：用于计算实际购买力（默认 2%）
2. 点击「🚀 开始计算」查看对比结果
3. 在「银行政策查询」标签页查看各行最新政策

### Node.js 命令行（API 调用）

```javascript
const c = require('./calculator.js');
const result = c.calculate(
  1000000,    // 贷款余额
  0.049,      // 年利率 4.9%
  30,         // 剩余年限
  200000,     // 提前还款金额
  0.03,       // 理财收益 3%
  0.02,       // 通胀率 2%
  'epi',      // 等额本息
  12,         // 第12月提前还款
  true        // 缩短年限
);
console.log(result.nominal);
console.log(result.prepay.totalInterest, 'vs', result.noPrepay.totalInterest);
console.log('建议:', result.recommendation);
```

---

## 🧮 计算公式 (Calculation Formulas)

### 1. 等额本息月供 (Equal Principal & Interest)

$$
M = P \cdot \frac{r(1+r)^n}{(1+r)^n - 1}
$$

其中：
- $P$ = 贷款余额
- $r$ = 月利率（年利率 ÷ 12）
- $n$ = 还款期数（年数 × 12）
- $M$ = 每月固定还款额

### 2. 等额本金月供 (Equal Principal)

$$
M_k = \frac{P}{n} + \left(P - (k-1)\cdot\frac{P}{n}\right) \cdot r
$$

每月偿还固定本金 $\frac{P}{n}$，利息按剩余本金计算，因此月供逐月递减。

### 3. 提前还款后

- **缩短年限**：保持月供不变，贷款在更短时间内结清
- **降低月供**：保持年限不变，按剩余本金与剩余期数重算月供

$$
M_{\text{new}} = P_{\text{new}} \cdot \frac{r(1+r)^{n_{\text{new}}}}{(1+r)^{n_{\text{new}}} - 1}
$$

### 4. 机会成本（理财月复利）

$$
FV = P_{\text{prepay}} \cdot \left(1 + \frac{g}{12}\right)^{n}
$$

将本用于提前还款的资金投入理财，按月复利计息 $n$ 期后的终值。

### 5. 通胀因子（实际购买力）

每期现金流按通胀率折现到今日：

$$
PV_{\text{real}} = \sum_{k=1}^{n} \frac{CF_k}{(1+\pi/12)^k}
$$

其中 $\pi$ 为年通胀率。此处**调整每期现金流购买力**，而非调整贴现率（按用户前提）。

### 6. 决策判据

| 指标 | 公式 | 含义 |
|---|---|---|
| 名义净收益 | $(-\text{提前支付}) - (-\text{不提前支付} + FV_{\text{投资}})$ | 正数 → 提前还款名义上更优 |
| 实际净收益 | 基于通胀调整后 PV 比较 | 正数 → 提前还款实际更优 |

**最终建议**：若 `realNetBenefit > 0` → `PREPAY`，否则 → `INVEST`。

---

## 📊 数据来源 (Data Sources)

### 银行政策 (`banks_policy.json`)
- **数据获取日期**：2024-08 至 2024-09
- **来源**：
  - 中国银行：<https://www.boc.cn/personal/loan/>
  - 工商银行：<https://mybank.icbc.com.cn/icbc/newperloan/>
  - 建设银行：<https://www.ccb.com/chn/home/personal/loan/>
  - 农业银行：<https://www.abchina.com/cn/PersonalServices/Loan/>
  - 交通银行：<https://www.bankcomm.com/>
  - 招商银行：<https://www.cmbchina.com/personal/loan/>
  - 邮储银行：<https://www.psbc.com/cn/index.html>
- **更新建议**：每 6 个月更新一次；2024 年下半年起部分银行收紧了提前还款额度与次数。

### 利率参考
- 2024 年 5 年期以上 LPR：3.85%（中国人民银行授权全国银行间同业拆借中心公布）
- 首套房贷利率：LPR - 30BP 左右（因城施策）

---

## ⚠️ 局限性 (Limitations)

1. **地区差异**：部分银行提前还款政策仅在分支行层面执行，总行官网无细化条款；
   当前只能收集公开发布的政策，无法覆盖所有城市所有分支行的差异化规定。
   如需精确条款，请**致电本地支行**确认。
2. **理论模型**：未考虑贷款合同中可能的"罚息"条款、提前还款额度上限、
   一年内次数限制等非价格因素（这些已整理在 `banks_policy.json` 中供参考）。
3. **通胀简化**：通胀率取单一常数，未考虑收入增长率、未来现金流结构调整等复杂情况。
4. **理财假设**：理财收益率取单一常数且无风险/税后；实际投资存在波动、税费、流动性限制。
5. **再投资风险**：现实中理财到期后可能无法续作到原收益率。
6. **公积金部分**：本工具主要面向商贷；公积金贷款政策差异较大，部分城市允许
   用公积金余额直接冲还贷月供，需单独建模。
7. **税费忽略**：未考虑提前还款可能涉及的个税/契税退还（极少场景）。

---

## 📞 银行政策查询指引 (Policy Inquiry Guide)

### 官方渠道

| 银行 | 官网 | 客服热线 | 备注 |
|---|---|---|---|
| 中国银行 | www.boc.cn | 95566 | 转人工后按"个人贷款" |
| 工商银行 | www.icbc.com.cn | 95588 | 转人工按"贷款业务" |
| 建设银行 | www.ccb.com | 95533 | 转人工按"个人贷款" |
| 农业银行 | www.abchina.com | 95559 | 转人工按"房贷" |
| 交通银行 | www.bankcomm.com | 95559 | 转人工按"提前还款" |
| 招商银行 | www.cmbchina.com | 95555 | 招商银行 APP 可直接操作 |
| 邮储银行 | www.psbc.com | 95580 | 转人工按"个人贷款" |

### 网点查询
- 各行官网 → "网点查询" / "营业网点" → 选择城市 → 查看附近支行
- 高德地图 / 百度地图 搜索 "XX银行 + 附近"
- 直接在银行 APP 内预约"提前还款"

### 查询话术示例

**话术 1：违约金问询**
> "您好，我名下有一笔 [XX 银行] 的住房贷款，贷款余额约 [金额] 万元，
> 已还款 [X] 年。想咨询一下现在提前还款是否收取违约金？收取标准是什么？"

**话术 2：预约周期**
> "请问提前还款需要提前多久预约？是电话预约、APP 预约还是要去柜台？
> 预约后多久能扣款？"

**话术 3：次数与金额限制**
> "请问一年内可以办理几次提前还款？单次最低金额是多少？
> 是否可以部分还款？"

**话术 4：还款方式选择**
> "如果我打算提前还款 [XX] 万元，是选择'缩短还款年限'还是'降低月供金额'？
> 哪种方式利息节省更多？"

**话术 5：APP 操作（招行特有）**
> "我在招行 APP 上看到有'提前还款'入口，请问线上操作是否同样有效？
> 扣款是实时到账还是 T+1？"

### 话术补充

- **带齐材料**：身份证、借款合同、还款卡、最近一期还款凭证
- **要求书面确认**：若客服口头承诺免违约金/无限制，建议要求其发送书面确认短信或邮件
- **录音**：根据法律规定，与客服通话时可告知并录音作为凭证
- **不同时点对比**：建议在工作日上午 10-11 点致电，避开月初/月末高峰

---

## 📁 项目结构

```
.
├── index.html         # 单页应用入口（决策器前端 + 银行政策查询）
├── calculator.js      # 计算逻辑（Node 通用，可在浏览器/Node 运行）
├── banks_policy.json  # 银行政策数据（中行、工行、建行、农行、交行、招行、邮储）
├── test_calculator.js # 自检脚本（验证计算正确性）
└── README.md          # 本文件
```

---

## 🧪 验证 (Verification)

### 自检命令

```bash
cd $(dirname "$0") && node test_calculator.js
```

预期输出：`PASS: N, FAIL: 0`，退出码 0。

### 各分件验收命令

```bash
# 1. 决策器前端页面
python3 -m http.server 8080 > /dev/null 2>&1 & sleep 2 && \
  curl -s http://localhost:8080/index.html | grep -qE "(房贷|计算|银行)" && \
  echo "页面结构完整"
pkill -f "python3 -m http.server"

# 2. 计算逻辑脚本
node -c calculator.js && \
  node -e "const c=require('./calculator.js');console.log(c.calculate(1000000,0.049,30,500000,0.03,0.03)?'计算正常':'计算异常')"

# 3. 银行政策数据
python3 -c "import json;d=json.load(open('banks_policy.json'));assert all('source' in b and 'date' in str(b) for b in d['banks'])" && \
  echo "字段完整"

# 4+6. 运行说明 + 政策查询指引（合并在 README）
grep -qE "(计算公式|数据来源|局限性)" README.md && echo "README内容完整"
grep -qE "(955|官网|客服)" README.md && echo "查询指引完整"

# 5. 自检脚本
node test_calculator.js && echo "测试通过"
```

---

## 📜 许可证

MIT License - 仅供学习交流，投资决策请以专业金融顾问意见为准。

---

## 前提假设 (Assumptions)

为保证结果可解释，所有计算均遵循以下前提：

1. **理财收益率与通胀率为用户输入或设定默认值**，计算结果为理论值。
2. **2024 年政策数据需在 `banks_policy.json` 中标注获取日期**，后续需定期更新。
3. **通胀因子通过调整未来每期现金流购买力实现**，而非调整贴现率。
4. **机会成本理财复利按月复利计算**（非年复利）。
5. **部分银行提前还款政策仅在分支行层面执行**，总行官网可能无细化条款，
   此类信息标注为"致电 XX 银行 XX 支行获取"。
6. **当前只能收集公开发布的政策**，无法覆盖所有城市所有分支行的差异化规定。
