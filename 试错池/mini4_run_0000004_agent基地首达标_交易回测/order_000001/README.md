本工具不下单、不连接账户、不构成投资建议。
用法：`python3 backtest.py --data sample_data --rules rules_example.json --start 2025-01-01 --end 2026-08-31`
内置 A 股 T+1、涨跌停 10%、手续费万三+卖出印花税千分之零点五。
规则支持均线交叉、N 日高低点突破、涨跌幅阈值、止损止盈、持有上限；输出 out/ 报告。
sample_data/ 内为合成数据，仅供验收。