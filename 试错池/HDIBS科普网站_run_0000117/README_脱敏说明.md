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
