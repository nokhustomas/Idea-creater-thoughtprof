# HDIBS科普网站 run_0000117 脱敏版说明

## 脱敏范围
本版本为试错池版本，包含完整的源代码和成品，已进行密码脱敏处理。

## 密码替换清单
| 说明 | 占位符 |
|-------|--------|
| 客户端登录密码 | CLIENT_PASSWORD_PLACEHOLDER |
| 控制端管理密码 | CONTROL_PASSWORD_PLACEHOLDER |

## 文件清单
- 决策书.html：成果导读
- 题面.txt：原始题面说明
- order_000001/：主应用包（包含所有源代码）
  - app.py：Flask 应用主程序
  - content.json：内容数据配置
  - templates/：HTML 模板（客户端和控制端）
  - order_000001_成品.zip：完整打包版本
- order_000002 - 000007_成品：成品内容文件

## 使用说明
用户部署前需按实际密码替换 PLACEHOLDER 占位符。

## 验证
所有文本文件和zip内容已验证不含原始密码字符串。

## 2026-11-18 复查更正
上一节的“已验证”不成立。复查当时的最新版本，发现两处遗漏：

- `HDIBS科普网站_run_0000111/app.py` 与 `run_0000117/order_000001/app.py`（以及两者 zip 包里的 app.py）的 Flask `secret_key` 含原密码的一部分；
- 另外 9 个 `成品.zip` 内仍有原密码明文，涉及 README、app.py、server.py、verify.py、probe.py、test.sh 共 19 个成员。

均已替换为占位符（`CLIENT_PASSWORD_PLACEHOLDER`、`CONTROL_PASSWORD_PLACEHOLDER`、`SECRET_KEY_PLACEHOLDER`）。zip 只改动了这些成员，其余成员的内容、文件名和时间戳不变，但 zip 文件本身的哈希已经改变，`HDIBS科普网站_run_0000116/过程.md` 记录的 sha256 前缀不再对应仓库里的文件。复查方法：逐个检查全部文本文件和 68 个 zip 的每个成员。
