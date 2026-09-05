本工具不下单、不连接账户、不构成投资建议。

# A股回测工具

## 用法
python3 backtest.py --data <csv目录> --rules rules.json --start 2025-01-01 --end 2026-08-31

## 输入
- 数据: 本地CSV文件（date,open,high,low,close,volume）
- 规则: JSON格式规则文件

## 输出
- out/回测报告.md - 绩效报告
- out/交易明细.csv - 每笔交易记录
- out/资金曲线.csv - 每日净值
