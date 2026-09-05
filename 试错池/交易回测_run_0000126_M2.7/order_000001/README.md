本工具不下单、不连接账户、不构成投资建议。

用法: python3 backtest.py --data <csv目录> --rules rules.json --start 2025-01-01 --end 2025-12-31

输入: 本地CSV文件(列:date,open,high,low,close,volume)，自带sample_data/合成示例数据
输出: out/回测报告.md, 交易明细.csv, 资金曲线.csv
