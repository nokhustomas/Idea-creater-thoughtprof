#!/usr/bin/env python3
"""
A 股个人交易规则回测工具
本工具不下单、不连接账户、不构成投资建议
"""

import sys
import os
import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# A股交易费用
BUY_COMMISSION_RATE = 0.0003  # 万分之三
SELL_COMMISSION_RATE = 0.0003
STAMP_TAX_RATE = 0.0005  # 千分之零点五 (印花税仅卖出收取)
UP_DOWN_LIMIT = 0.10  # 涨跌停10%

class StockData:
    """股票行情数据"""
    def __init__(self, symbol):
        self.symbol = symbol
        self.data = {}  # date -> {open, high, low, close, volume}
        self.dates = []
    
    def load_csv(self, filepath):
        """从CSV加载数据"""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row['date']
                self.data[date] = {
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                }
        self.dates = sorted(self.data.keys())
    
    def get_price(self, date):
        """获取指定日期的价格"""
        return self.data.get(date)

class BacktestEngine:
    """回测引擎"""
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0  # 持仓数量
        self.buy_date = None  # 买入日期(T+1用)
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值
        self.hold_days = 0  # 持仓天数
    
    def calculate_fee(self, amount, is_buy=True):
        """计算手续费"""
        if is_buy:
            return amount * BUY_COMMISSION_RATE
        else:
            return amount * (SELL_COMMISSION_RATE + STAMP_TAX_RATE)
    
    def can_sell(self, date, buy_date):
        """检查是否满足T+1条件"""
        if buy_date is None:
            return False
        buy_idx = self.dates.index(buy_date) if buy_date in self.dates else -1
        current_idx = self.dates.index(date) if date in self.dates else -1
        return current_idx > buy_idx
    
    def is_limit_up(self, stock, date, is_buy):
        """检查涨跌停"""
        if date not in stock.data:
            return True
        prev_date = self.get_prev_trading_date(stock, date)
        if prev_date and prev_date in stock.data:
            prev_close = stock.data[prev_date]['close']
            curr = stock.data[date]
            if is_buy:
                # 涨停价买入被限制
                if abs(curr['close'] - prev_close) / prev_close >= UP_DOWN_LIMIT - 0.001:
                    return True
            else:
                # 跌停价卖出被限制
                if abs(curr['close'] - prev_close) / prev_close <= -UP_DOWN_LIMIT + 0.001:
                    return True
        return False
    
    def get_prev_trading_date(self, stock, date):
        """获取前一交易日"""
        if date not in stock.dates:
            return None
        idx = stock.dates.index(date)
        if idx > 0:
            return stock.dates[idx - 1]
        return None
    
    def execute_buy(self, date, price, quantity):
        """执行买入"""
        cost = price * quantity
        fee = self.calculate_fee(cost, is_buy=True)
        total_cost = cost + fee
        
        if self.cash >= total_cost:
            self.cash -= total_cost
            self.position += quantity
            self.buy_date = date
            self.hold_days = 0
            self.trades.append({
                'date': date,
                'action': '买入',
                'price': price,
                'quantity': quantity,
                'amount': cost,
                'fee': fee,
                'balance': self.cash
            })
            return True
        return False
    
    def execute_sell(self, date, price, quantity):
        """执行卖出"""
        if self.position >= quantity:
            revenue = price * quantity
            fee = self.calculate_fee(revenue, is_buy=False)
            net_revenue = revenue - fee
            
            self.cash += net_revenue
            self.position -= quantity
            profit = net_revenue - (price * quantity - self.calculate_fee(price * quantity, True))
            
            self.trades.append({
                'date': date,
                'action': '卖出',
                'price': price,
                'quantity': quantity,
                'amount': revenue,
                'fee': fee,
                'balance': self.cash
            })
            return True
        return False
    
    def get_ma(self, stock, date, period):
        """计算N日均线"""
        if date not in stock.dates:
            return None
        idx = stock.dates.index(date)
        if idx < period - 1:
            return None
        
        prices = []
        for i in range(period):
            d = stock.dates[idx - i]
            if d in stock.data:
                prices.append(stock.data[d]['close'])
        
        if len(prices) >= period:
            return sum(prices[:period]) / period
        return None
    
    def get_high_low(self, stock, date, period):
        """获取N日高低点"""
        if date not in stock.dates:
            return None, None
        idx = stock.dates.index(date)
        if idx < period:
            return None, None
        
        highs = []
        lows = []
        for i in range(period):
            d = stock.dates[idx - i]
            if d in stock.data:
                highs.append(stock.data[d]['high'])
                lows.append(stock.data[d]['low'])
        
        if len(highs) >= period:
            return max(highs[:period]), min(lows[:period])
        return None, None
    
    def get_price_change(self, stock, date, days):
        """计算N日涨跌幅"""
        if date not in stock.dates:
            return None
        idx = stock.dates.index(date)
        if idx < days:
            return None
        
        curr_date = stock.dates[idx]
        prev_date = stock.dates[idx - days]
        
        if curr_date in stock.data and prev_date in stock.data:
            curr_close = stock.data[curr_date]['close']
            prev_close = stock.data[prev_date]['close']
            return (curr_close - prev_close) / prev_close
        return None

def load_rules(filepath):
    """加载交易规则"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_stock_data(data_dir):
    """加载所有股票数据"""
    stocks = {}
    data_path = Path(data_dir)
    
    for csv_file in data_path.glob('*.csv'):
        symbol = csv_file.stem
        stock = StockData(symbol)
        stock.load_csv(csv_file)
        stocks[symbol] = stock
    
    return stocks

def get_trading_dates(stocks, start_date, end_date):
    """获取所有股票共同的交易日"""
    if not stocks:
        return []
    
    all_dates = set()
    for stock in stocks.values():
        all_dates.update(stock.dates)
    
    trading_dates = sorted([d for d in all_dates if start_date <= d <= end_date])
    
    # 找出所有股票都有的交易日
    common_dates = set(trading_dates)
    for stock in stocks.values():
        common_dates &= set(stock.dates)
    
    return sorted(common_dates)

def check_conditions(engine, stock, date, rules, position):
    """检查是否满足交易条件"""
    conditions = rules.get('conditions', [])
    must_all = rules.get('must_all', True)
    
    satisfied = []
    for cond in conditions:
        cond_type = cond.get('type')
        result = False
        
        if cond_type == 'ma_cross':
            # 均线交叉
            short_ma = engine.get_ma(stock, date, cond['short_period'])
            long_ma = engine.get_ma(stock, date, cond['long_period'])
            
            if short_ma is not None and long_ma is not None:
                if cond.get('direction') == 'short_above_long':
                    result = short_ma > long_ma
                else:
                    result = short_ma < long_ma
        
        elif cond_type == 'breakout':
            # 突破N日高低点
            high, low = engine.get_high_low(stock, date, cond['period'])
            price = stock.data[date]['close'] if date in stock.data else None
            
            if high is not None and low is not None and price is not None:
                if cond.get('breakout_type') == 'high':
                    result = price > high
                else:
                    result = price < low
        
        elif cond_type == 'price_change':
            # 涨跌幅阈值
            change = engine.get_price_change(stock, date, cond.get('days', 1))
            if change is not None:
                threshold = cond.get('threshold', 0) / 100.0
                if cond.get('direction') == 'up':
                    result = change > threshold
                else:
                    result = change < -threshold
        
        satisfied.append(result)
    
    if must_all:
        return all(satisfied)
    else:
        return any(satisfied)

def run_backtest(stocks, trading_dates, rules, initial_capital=1000000):
    """运行回测"""
    engine = BacktestEngine(initial_capital)
    engine.dates = trading_dates
    
    current_stock = None
    position = 0
    buy_price = 0
    
    # 止损止盈配置
    stop_loss = rules.get('stop_loss', 0) / 100.0
    take_profit = rules.get('take_profit', 0) / 100.0
    max_hold_days = rules.get('max_hold_days', 0)
    
    for i, date in enumerate(trading_dates):
        # 更新每日净值
        total_value = engine.cash
        if position > 0 and current_stock:
            price = current_stock.data[date]['close'] if date in current_stock.data else 0
            total_value += position * price
        
        engine.daily_values.append({
            'date': date,
            'cash': engine.cash,
            'position_value': total_value - engine.cash,
            'total_value': total_value
        })
        
        # 检查止损止盈
        if position > 0 and current_stock:
            current_price = current_stock.data[date]['close']
            price_change = (current_price - buy_price) / buy_price
            
            # 止损
            if stop_loss > 0 and price_change <= -stop_loss:
                if engine.can_sell(date, engine.buy_date):
                    engine.execute_sell(date, current_price, position)
                    current_stock = None
                    position = 0
            
            # 止盈
            elif take_profit > 0 and price_change >= take_profit:
                if engine.can_sell(date, engine.buy_date):
                    engine.execute_sell(date, current_price, position)
                    current_stock = None
                    position = 0
            
            # 最大持仓天数
            elif max_hold_days > 0 and engine.hold_days >= max_hold_days:
                if engine.can_sell(date, engine.buy_date):
                    engine.execute_sell(date, current_price, position)
                    current_stock = None
                    position = 0
    
    # 期末平仓
    if position > 0 and current_stock and trading_dates:
        last_date = trading_dates[-1]
        if last_date in current_stock.data:
            last_price = current_stock.data[last_date]['close']
            if engine.can_sell(last_date, engine.buy_date):
                engine.execute_sell(last_date, last_price, position)
    
    return engine

def generate_report(engine, trading_dates):
    """生成回测报告"""
    total_return = engine.cash - engine.initial_capital
    total_return_pct = (total_return / engine.initial_capital) * 100
    
    # 计算年化收益
    if trading_dates:
        days = len(trading_dates)
        years = days / 244  # A股一年约244个交易日
        annualized = ((engine.cash / engine.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    else:
        annualized = 0
    
    # 计算最大回撤
    peak = engine.initial_capital
    max_drawdown = 0
    for dv in engine.daily_values:
        if dv['total_value'] > peak:
            peak = dv['total_value']
        drawdown = (peak - dv['total_value']) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # 统计交易
    trades = engine.trades
    buy_trades = [t for t in trades if t['action'] == '买入']
    sell_trades = [t for t in trades if t['action'] == '卖出']
    trade_count = min(len(buy_trades), len(sell_trades))
    
    # 计算胜率盈亏比
    wins = 0
    losses = 0
    win_amount = 0
    loss_amount = 0
    
    buy_idx = 0
    for t in trades:
        if t['action'] == '买入':
            buy_idx = trades.index(t)
        elif t['action'] == '卖出' and buy_idx < len(trades):
            buy_trade = trades[buy_idx]
            buy_cost = buy_trade['price'] * buy_trade['quantity'] + buy_trade['fee']
            sell_revenue = t['price'] * t['quantity'] - t['fee']
            pnl = sell_revenue - buy_cost
            
            if pnl > 0:
                wins += 1
                win_amount += pnl
            else:
                losses += 1
                loss_amount += abs(pnl)
    
    win_rate = (wins / trade_count * 100) if trade_count > 0 else 0
    avg_win = win_amount / wins if wins > 0 else 0
    avg_loss = loss_amount / losses if losses > 0 else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 月度收益
    monthly_returns = defaultdict(float)
    for dv in engine.daily_values:
        month = dv['date'][:7]
        monthly_returns[month] = dv['total_value']
    
    report = f"""# A股回测报告

## 总体统计
- 总收益: {total_return:.2f} 元 ({total_return_pct:.2f}%)
- 年化收益: {annualized:.2f}%
- 最大回撤: {max_drawdown:.2f}%
- 交易次数: {trade_count}
- 胜率: {win_rate:.2f}%
- 盈亏比: {profit_loss_ratio:.2f}

## 期末资金
- 最终资金: {engine.cash:.2f} 元
- 期末持仓: {engine.position} 股

## 交易统计
- 买入次数: {len(buy_trades)}
- 卖出次数: {len(sell_trades)}

## 月度收益表
| 月份 | 净值 |
|------|------|
"""
    
    sorted_months = sorted(monthly_returns.keys())
    if sorted_months:
        base_value = monthly_returns[sorted_months[0]]
        for month in sorted_months:
            value = monthly_returns[month]
            ret = ((value / base_value) - 1) * 100 if base_value > 0 else 0
            report += f"| {month} | {value:.2f} ({ret:+.2f}%) |\n"
    
    return report

def main():
    parser = argparse.ArgumentParser(description='A股回测工具')
    parser.add_argument('--data', required=True, help='CSV数据目录')
    parser.add_argument('--rules', required=True, help='规则JSON文件')
    parser.add_argument('--start', required=True, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--capital', type=float, default=1000000, help='初始资金')
    
    args = parser.parse_args()
    
    # 加载数据
    print(f"加载数据目录: {args.data}")
    stocks = load_stock_data(args.data)
    print(f"加载股票数量: {len(stocks)}")
    
    # 加载规则
    print(f"加载规则: {args.rules}")
    rules = load_rules(args.rules)
    
    # 获取交易日
    trading_dates = get_trading_dates(stocks, args.start, args.end)
    print(f"交易日数量: {len(trading_dates)}")
    
    if not trading_dates:
        print("错误: 没有找到交易日")
        sys.exit(1)
    
    # 运行回测
    print("运行回测...")
    engine = run_backtest(stocks, trading_dates, rules, args.capital)
    
    # 创建输出目录
    os.makedirs('out', exist_ok=True)
    
    # 生成回测报告
    report = generate_report(engine, trading_dates)
    with open('out/回测报告.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print("生成报告: out/回测报告.md")
    
    # 生成交易明细
    with open('out/交易明细.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'action', 'symbol', 'price', 'quantity', 'amount', 'fee', 'balance'])
        writer.writeheader()
        for t in engine.trades:
            row = t.copy()
            row['symbol'] = 'STOCK'
            writer.writerow(row)
    print(f"生成交易明细: out/交易明细.csv ({len(engine.trades)}条记录)")
    
    # 生成资金曲线
    with open('out/资金曲线.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'cash', 'position_value', 'total_value'])
        writer.writeheader()
        for dv in engine.daily_values:
            writer.writerow(dv)
    print(f"生成资金曲线: out/资金曲线.csv ({len(engine.daily_values)}条记录)")
    
    print("回测完成!")
    sys.exit(0)

if __name__ == '__main__':
    main()
