#!/usr/bin/env python3
"""
生成合成样本数据 - 每只股票300个交易日
注：此为合成数据，仅用于回测验证
"""

import csv
import random
import os
from datetime import datetime, timedelta

def generate_stock_data(symbol, start_price, volatility, start_date, output_file):
    """生成股票数据"""
    dates = []
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    
    # 生成300个交易日
    while len(dates) < 300:
        # 跳过周末
        if current_date.weekday() < 5:
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    prices = {'open': [], 'high': [], 'low': [], 'close': []}
    current_price = start_price
    
    for date in dates:
        # 随机波动
        change = random.gauss(0, volatility)
        open_price = round(current_price * (1 + change * 0.5), 2)
        high_price = round(open_price * (1 + abs(change) * 0.3), 2)
        low_price = round(open_price * (1 - abs(change) * 0.3), 2)
        close_price = round(open_price * (1 + change), 2)
        
        # 确保价格合理
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        prices['open'].append(open_price)
        prices['high'].append(high_price)
        prices['low'].append(low_price)
        prices['close'].append(close_price)
        
        current_price = close_price
    
    # 写入CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'open', 'high', 'low', 'close', 'volume'])
        
        for i, date in enumerate(dates):
            volume = int(800000 + random.randint(-200000, 400000))
            writer.writerow([
                date,
                prices['open'][i],
                prices['high'][i],
                prices['low'][i],
                prices['close'][i],
                volume
            ])

if __name__ == '__main__':
    os.makedirs('sample_data', exist_ok=True)
    
    # 设置随机种子以保证可重现性
    random.seed(42)
    
    # 生成三只股票的合成数据（注明是合成数据）
    # 000001: 从10元开始，中等波动
    generate_stock_data('000001', 10.0, 0.015, '2024-01-02', 'sample_data/000001.csv')
    print("生成 sample_data/000001.csv 完成 (合成数据)")
    
    # 000002: 从20元开始，较低波动
    generate_stock_data('000002', 20.0, 0.012, '2024-01-02', 'sample_data/000002.csv')
    print("生成 sample_data/000002.csv 完成 (合成数据)")
    
    # 600000: 从8元开始，较高波动
    generate_stock_data('600000', 8.0, 0.018, '2024-01-02', 'sample_data/600000.csv')
    print("生成 sample_data/600000.csv 完成 (合成数据)")
    
    print("\n所有样本数据已生成（合成数据，仅用于回测验证）！")
