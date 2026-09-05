本工具不下单、不连接账户、不构成投资建议

A股个人交易规则回测工具，使用历史 CSV 数据检验交易规则有效性。

用法：python3 backtest.py --data sample_data --rules rules_example.json --start 2025-01-01 --end 2025-12-31

输出放在 out/ 目录，包含回测报告、交易明细、资金曲线。

sample_data 为合成数据（自动生成），仅用于验证。
