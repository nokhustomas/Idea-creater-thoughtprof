# 想法推进器（Idea-Pusher）客户用网页系统

一台叫「想法推进器」的机器，给客户一句话：先推敲、再制作、再机器验收、不达标自动重跑、最后出成品。这套网页就是它的门面——客户提交一句话之后，能在浏览器里走完全流程并拿到成品。

## 自己定的规则与理由

### 1. 流程分几步
1. **选题**：客户在首页一句话写下要做的事（不超 1000 字）。
2. **选档**：客户选一档套餐。
3. **提交**：写入 `TJ_ROOT/logs/queue.txt` 一行，线程后台启动流水线。
4. **推敲**：自动生成 `plan.md`（提问、方案蓝图）。
5. **制作**：按题面关键词分类，落到 `runs/run_XXXXXXX/out/` 真实文件里。
6. **机器验收**：本地自检脚本扫产出物，不达标自动重跑（按档位允许的轮数）。
7. **归档**：产出 `*_done.zip`、`reader.html` 导读，写 `verify.txt`、`ledger.txt`、`usage.json`。
8. **下载**：浏览器页面给出 zip 与 reader.html 链接。

### 2. 怎么定价 / 按什么收 / 分不分档
**分三档**，理由是让客户自由选颗粒度：

| 档位 | 价格  | 最大迭代轮 | 适用 |
|------|-------|------------|------|
| 基础档 | 免费 | 2 | 尝鲜、一次性小品 |
| 进阶档 | ¥29  | 4 | 个人 / 小团队常用 |
| 企业档 | ¥199 | 8 | 多次打磨、要 PDF 报告 |

价格档位保存在 `app.py` 的 `PRICING` 字典里，客户在浏览器点击就能切换。每次报价落到 `verify.txt` 与 `ledger.txt`，方便对账。

### 3. 客户看到什么
- 首页：一句话输入 + 档位选择 + 联系方式 + 进度日志 + 成品下载区。
- 后台接口：`/api/submit`、`/api/status/<run_id>`、`/api/download/<run_id>/<file>`。
- 全程中文页面，所有文案在 `app.py` 顶部常量里。

### 4. 要不要口令
**默认不要口令**。本机内部演示用，过度设计反而挡住真客户。若要外网暴露，可在 `app.py` 顶部加一行 `BASIC_AUTH = ("user", "pass")` 即可（详见源码 `do_AUTH` 分支预留）。

### 5. 成品怎么交
- 浏览器页面上有 `<a href="/api/download/...">` 直链 `*_done.zip` 与 `reader.html`。
- 归档目录：`$TJ_ROOT/runs/run_XXXXXXX/out/`（客户也可直接看）。
- 总账：`$TJ_ROOT/logs/ledger.txt`，逐行一条台账。

## 运行

```bash
python3 app.py            # 后台守护起站点，监听 8765（写 server.pid 后退出）
python3 app.py --fg       # 前台跑（不守护，调试用）
python3 app.py --selftest # 自检：起服务 -> 走完一单 -> 停服务 -> 退出 0
```

环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `TJ_ROOT` | `/opt/tuijinqi` | 根目录，无则自动建 |
| `TJ_PORT` | `8765` | 监听端口 |
| `TJ_DEMO` | `0` | 设为 `1` 自动在队列里塞演示单 |
| `TJ_NO_OPEN` | `0` | 设为 `1` 关闭自动开浏览器 |

## 自检命令（运行命令.txt 第一行）

```
TJ_DEMO=1 timeout 10 python3 app.py --selftest
```

## 文件清单

```
app.py                                # 主程序（守护模式 + 接口 + 流水线 + 自检）
README.md                             # 本文件
运行命令.txt                          # 第一行是上面的自检
user_research_plan.md                 # 用户调研方案
user_research_questions.md            # 调研问卷与访谈提纲
competitor_analysis_plan.md           # 竞品分析方案
competitor_analysis_criteria.md       # 竞品分析维度与标准
prototype_design.pdf                  # 原型设计（HTML 渲染为 PDF）
user_test_plan.md                     # 用户测试计划
user_feedback_form.md                 # 用户反馈表单
iteration_report.md                   # 迭代优化报告
iteration_log.md                      # 迭代过程记录
```

## 前提假设（按客户原话照搬）

- 用户群体的具体需求和偏好（待核实）
- 竞争对手网站的具体情况（待核实）
- 用户测试的参与人数和反馈收集方式（待核实）

这三条都是「先占位」内容，等真客户数据进来再回填。流程不变，模板已留好接口。