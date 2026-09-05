#!/usr/bin/env python3
"""生成A股合成测试数据 - 仅用于回测验证"""
import csv
import os
from datetime import datetime, timedelta

def generate_trading_dates(start_date, count):
    """生成300个交易日的日期（排除周末）"""
    dates = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    while len(dates) < count:
        # 跳过周末
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def generate_stock_data(symbol, start_price, volatility, trend, dates):
    """生成单只股票的数据"""
    data = []
    price = start_price
    
    for i, date in enumerate(dates):
        # 加入趋势和随机波动
        daily_return = trend + (hash(f"{symbol}{date}") % 100 - 50) / 500 * volatility
        price = price * (1 + daily_return)
        price = max(1.0, price)  # 确保价格不为负
        
        # OHLC生成
        open_price = price * (1 + (hash(f"{symbol}o{date}") % 100 - 50) / 1000)
        high_price = max(price, open_price) * (1 + abs(hash(f"{symbol}h{date}") % 50) / 1000)
        low_price = min(price, open_price) * (1 - abs(hash(f"{symbol}l{date}") % 50) / 1000)
        close_price = price
        
        volume = 1000000 + (hash(f"{symbol}v{date}") % 500000)
        
        data.append({
            'date': date,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': int(volume)
        })
    
    return data

def save_csv(filepath, data):
    """保存为CSV"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'open', 'high', 'low', 'close', 'volume'])
        writer.writeheader()
        writer.writerows(data)

# 生成3只股票的数据
trading_dates = generate_trading_dates("2024-01-02", 300)

# 股票1：震荡上行
data1 = generate_stock_data("stock_001", 10.0, 0.02, 0.001, trading_dates)
save_csv("sample_data/stock_001.csv", data1)

# 股票2：持续上涨
data2 = generate_stock_data("stock_002", 20.0, 0.015, 0.002, trading_dates)
save_csv("sample_data/stock_002.csv", data2)

# 股票3：震荡下行
data3 = generate_stock_data("stock_003", 15.0, 0.025, -0.001, trading_dates)
save_csv("sample_data/stock_003.csv", data3)

print("生成合成测试数据完成！")
print("- sample_data/stock_001.csv: 300条记录")
print("- sample_data/stock_002.csv: 300条记录")
print("- sample_data/stock_003.csv: 300条记录")
print("")
print("【注意】以上数据均为合成数据，仅用于回测验证，不构成任何投资建议")
