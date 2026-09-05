#!/usr/bin/env python3
"""
A股个人交易规则回测工具（只研究，不下单）
本工具绝不连接任何券商账户、绝不下单、绝不给出买卖建议；只做历史回测与统计。
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# A股手续费率
BUY_FEE_RATE = 0.0003  # 万分之三
SELL_FEE_RATE = 0.0003  # 万分之三
SELL_STAMP_TAX_RATE = 0.0005  # 千分之零点五 (印花税只在卖出时收取)
PRICE_LIMIT_RATE = 0.10  # 涨跌停10%


def parse_args():
    parser = argparse.ArgumentParser(
        description='A股回测工具 - 只研究，不下单'
    )
    parser.add_argument('--data', required=True, help='CSV数据目录')
    parser.add_argument('--rules', required=True, help='规则JSON文件')
    parser.add_argument('--start', required=True, help='回测开始日期 YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='回测结束日期 YYYY-MM-DD')
    return parser.parse_args()


def load_csv_data(data_dir, start_date, end_date):
    """加载CSV数据文件"""
    stocks = {}
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        sys.exit(1)
    
    for csv_file in data_path.glob('*.csv'):
        stock_code = csv_file.stem
        stock_data = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = row['date']
                    if start_date <= date_str <= end_date:
                        stock_data.append({
                            'date': date_str,
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['volume'])
                        })
            
            if stock_data:
                # 按日期排序
                stock_data.sort(key=lambda x: x['date'])
                stocks[stock_code] = stock_data
                
        except Exception as e:
            print(f"警告: 读取 {csv_file} 时出错: {e}")
            continue
    
    return stocks


def load_rules(rules_file):
    """加载交易规则"""
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        return rules
    except Exception as e:
        print(f"错误: 读取规则文件失败: {e}")
        sys.exit(1)


def calculate_ma(prices, period):
    """计算简单移动平均线"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def check_ma_crossover(current_ma, prev_ma, short_period, long_period):
    """检查均线金叉/死叉"""
    if current_ma is None or prev_ma is None:
        return None
    
    # 金叉：短期均线从下方穿过长期均线
    if prev_ma < long_period and current_ma >= long_period:
        return 'golden_cross'  # 买入信号
    # 死叉：短期均线从上方穿过长期均线
    elif prev_ma > long_period and current_ma <= long_period:
        return 'death_cross'  # 卖出信号
    return None


def check_breakout(data, period, breakout_type='high'):
    """检查是否突破N日高点/低点"""
    if len(data) < period:
        return False
    
    prices = [d['close'] for d in data[-period:]]
    current_close = data[-1]['close']
    
    if breakout_type == 'high':
        high = max(prices)
        return current_close >= high
    else:  # low
        low = min(prices)
        return current_close <= low


def check_price_change(data, threshold):
    """检查涨跌幅是否超过阈值"""
    if len(data) < 2:
        return False
    
    prev_close = data[-2]['close']
    current_close = data[-1]['close']
    change_pct = (current_close - prev_close) / prev_close
    
    return abs(change_pct) >= threshold


def check_stop_loss_take_profit(entry_price, current_price, stop_loss, take_profit):
    """检查是否触发止损/止盈"""
    if stop_loss:
        loss_pct = (current_price - entry_price) / entry_price
        if loss_pct <= -stop_loss:
            return 'stop_loss'
    if take_profit:
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct >= take_profit:
            return 'take_profit'
    return None


def is_price_limit_blocked(open_price, prev_close, limit_type='up'):
    """检查涨跌停是否阻止交易"""
    if limit_type == 'up':
        limit_price = prev_close * (1 + PRICE_LIMIT_RATE)
        return open_price >= limit_price
    else:
        limit_price = prev_close * (1 - PRICE_LIMIT_RATE)
        return open_price <= limit_price


def evaluate_buy_signal(data, rules, stock_code):
    """评估是否产生买入信号"""
    conditions = rules.get('buy_conditions', [])
    if not conditions:
        return False
    
    all_passed = True
    for condition in conditions:
        cond_type = condition.get('type')
        
        if cond_type == 'ma_crossover':
            short_ma = condition.get('short_ma', 5)
            long_ma = condition.get('long_ma', 20)
            
            if len(data) < long_ma + 1:
                all_passed = False
                break
            
            prices = [d['close'] for d in data]
            current_ma_short = calculate_ma(prices, short_ma)
            prev_prices = prices[:-1]
            prev_ma_short = calculate_ma(prev_prices, short_ma)
            current_ma_long = calculate_ma(prices, long_ma)
            prev_ma_long = calculate_ma(prev_prices, long_ma)
            
            signal = check_ma_crossover(current_ma_short, prev_ma_short, short_ma, current_ma_long)
            prev_signal = check_ma_crossover(prev_ma_short, calculate_ma(prev_prices[:-1] if len(prev_prices) > 1 else prev_prices, short_ma), short_ma, prev_ma_long)
            
            if signal != 'golden_cross':
                all_passed = False
                break
                
        elif cond_type == 'breakout':
            period = condition.get('period', 20)
            breakout_type = condition.get('breakout_type', 'high')
            
            if not check_breakout(data, period, breakout_type):
                all_passed = False
                break
                
        elif cond_type == 'price_change':
            threshold = condition.get('threshold', 0.05)
            
            if not check_price_change(data, threshold):
                all_passed = False
                break
    
    return all_passed


def evaluate_sell_signal(data, rules, entry_price):
    """评估是否产生卖出信号"""
    conditions = rules.get('sell_conditions', [])
    if not conditions:
        return False
    
    for condition in conditions:
        cond_type = condition.get('type')
        
        if cond_type == 'ma_crossover':
            short_ma = condition.get('short_ma', 5)
            long_ma = condition.get('long_ma', 20)
            
            if len(data) < long_ma + 1:
                return False
            
            prices = [d['close'] for d in data]
            current_ma_short = calculate_ma(prices, short_ma)
            prev_prices = prices[:-1]
            prev_ma_short = calculate_ma(prev_prices, short_ma)
            current_ma_long = calculate_ma(prices, long_ma)
            prev_ma_long = calculate_ma(prev_prices, long_ma)
            
            signal = check_ma_crossover(current_ma_short, prev_ma_short, short_ma, current_ma_long)
            if signal == 'death_cross':
                return True
                
        elif cond_type == 'stop_loss':
            stop_loss = condition.get('stop_loss')
            if stop_loss:
                current_price = data[-1]['close']
                result = check_stop_loss_take_profit(entry_price, current_price, stop_loss, None)
                if result == 'stop_loss':
                    return True
                    
        elif cond_type == 'take_profit':
            take_profit = condition.get('take_profit')
            if take_profit:
                current_price = data[-1]['close']
                result = check_stop_loss_take_profit(entry_price, current_price, None, take_profit)
                if result == 'take_profit':
                    return True
    
    return False


def run_backtest(stocks, rules, start_date, end_date):
    """运行回测"""
    initial_capital = 100000  # 初始资金10万
    capital = initial_capital
    position = None  # 当前持仓
    position_code = None  # 持仓股票代码
    position_date = None  # 买入日期(T+1限制)
    trades = []  # 交易记录
    equity_curve = []  # 每日净值
    
    # 获取所有交易日
    all_dates = set()
    for stock_data in stocks.values():
        for d in stock_data:
            all_dates.add(d['date'])
    all_dates = sorted(list(all_dates))
    
    start_idx = 0
    for i, date in enumerate(all_dates):
        if date >= start_date:
            start_idx = i
            break
    
    # 按日期遍历
    for i in range(start_idx, len(all_dates)):
        date = all_dates[i]
        
        # 计算当日账户价值
        if position:
            # 找到持仓股票的当日收盘价
            stock_data = stocks.get(position_code, [])
            for d in stock_data:
                if d['date'] == date:
                    current_value = position['shares'] * d['close']
                    break
            else:
                current_value = position['shares'] * position['price']  # 使用买入价
        else:
            current_value = capital
        
        equity_curve.append({
            'date': date,
            'capital': capital,
            'position_value': current_value if position else 0,
            'total_value': capital + (current_value if position else 0)
        })
        
        # 收集每只股票当日的bar数据
        for stock_code, stock_data in stocks.items():
            for j, d in enumerate(stock_data):
                if d['date'] == date:
                    # 更新历史数据用于计算指标
                    idx = j
                    # 检查是否可以卖出( T+1 限制)
                    if position and position_code == stock_code:
                        can_sell = True
                        # 卖出信号检查
                        history_data = stock_data[:idx+1]
                        if evaluate_sell_signal(history_data, rules, position['price']):
                            sell_price = d['close']
                            # 检查涨跌停
                            prev_close = stock_data[idx-1]['close'] if idx > 0 else d['close']
                            if is_price_limit_blocked(sell_price, prev_close, 'down'):
                                continue  # 涨跌停，无法卖出
                            
                            # 执行卖出
                            sell_value = position['shares'] * sell_price
                            sell_fee = sell_value * (SELL_FEE_RATE + SELL_STAMP_TAX_RATE)
                            net_value = sell_value - sell_fee
                            
                            profit = net_value - position['cost']
                            trades.append({
                                'buy_date': position['date'],
                                'buy_price': position['price'],
                                'buy_shares': position['shares'],
                                'buy_fee': position['fee'],
                                'sell_date': date,
                                'sell_price': sell_price,
                                'sell_shares': position['shares'],
                                'sell_fee': sell_fee,
                                'profit': profit,
                                'stock': stock_code
                            })
                            
                            capital += net_value
                            position = None
                            position_code = None
                            position_date = None
                    
                    # 买入信号检查
                    if not position:
                        history_data = stock_data[:idx+1]
                        if evaluate_buy_signal(history_data, rules, stock_code):
                            buy_price = d['close']
                            # 检查涨跌停
                            prev_close = stock_data[idx-1]['close'] if idx > 0 else d['close']
                            if is_price_limit_blocked(buy_price, prev_close, 'up'):
                                continue  # 涨跌停，无法买入
                            
                            # 计算可买入数量(100股整数倍)
                            buy_fee = capital * BUY_FEE_RATE
                            available = capital - buy_fee
                            shares = int(available / buy_price / 100) * 100
                            
                            if shares > 0:
                                cost = shares * buy_price + buy_fee
                                position = {
                                    'date': date,
                                    'price': buy_price,
                                    'shares': shares,
                                    'cost': cost,
                                    'fee': buy_fee
                                }
                                position_code = stock_code
                                position_date = date
                                capital = capital - cost
                    break
    
    return trades, equity_curve, initial_capital


def calculate_metrics(trades, equity_curve, initial_capital):
    """计算回测指标"""
    if not trades:
        return {
            'total_profit': 0,
            'total_return': 0,
            'annual_return': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'total_trades': 0,
            'monthly_returns': {}
        }
    
    total_profit = sum(t['profit'] for t in trades)
    final_value = initial_capital + total_profit
    total_return = (final_value - initial_capital) / initial_capital
    
    # 计算年化收益
    if equity_curve:
        start_date = equity_curve[0]['date']
        end_date = equity_curve[-1]['date']
        days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        years = days / 365 if days > 0 else 1
        annual_return = (final_value / initial_capital) ** (1/years) - 1 if years > 0 else 0
    else:
        annual_return = 0
    
    # 计算最大回撤
    max_value = initial_capital
    max_drawdown = 0
    for entry in equity_curve:
        if entry['total_value'] > max_value:
            max_value = entry['total_value']
        drawdown = (max_value - entry['total_value']) / max_value if max_value > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # 计算胜率
    winning_trades = [t for t in trades if t['profit'] > 0]
    total_trades = len(trades)
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    
    # 计算盈亏比
    avg_profit = sum(t['profit'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    losing_trades = [t for t in trades if t['profit'] < 0]
    avg_loss = abs(sum(t['profit'] for t in losing_trades) / len(losing_trades)) if losing_trades else 1
    profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
    
    # 计算月度收益
    monthly_returns = {}
    for entry in equity_curve:
        month = entry['date'][:7]
        if month not in monthly_returns:
            monthly_returns[month] = []
        monthly_returns[month].append(entry['total_value'])
    
    monthly_pnl = {}
    for month, values in monthly_returns.items():
        if len(values) >= 2:
            monthly_pnl[month] = values[-1] - values[0]
    
    return {
        'total_profit': total_profit,
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'total_trades': total_trades,
        'monthly_returns': monthly_pnl
    }


def generate_report(metrics, trades, equity_curve, output_dir):
    """生成回测报告"""
    report_path = os.path.join(output_dir, '回测报告.md')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# A股回测报告\n\n")
        f.write("**注意：本工具不下单、不连接账户、不构成投资建议**\n\n")
        f.write("## 总体指标\n\n")
        f.write(f"- 总收益: {metrics['total_profit']:.2f} 元\n")
        f.write(f"- 总收益率: {metrics['total_return']*100:.2f}%\n")
        f.write(f"- 年化收益率: {metrics['annual_return']*100:.2f}%\n")
        f.write(f"- 最大回撤: {metrics['max_drawdown']*100:.2f}%\n")
        f.write(f"- 胜率: {metrics['win_rate']*100:.2f}%\n")
        f.write(f"- 盈亏比: {metrics['profit_loss_ratio']:.2f}\n")
        f.write(f"- 交易次数: {metrics['total_trades']}\n\n")
        
        f.write("## 每月收益\n\n")
        f.write("| 月份 | 收益 |\n")
        f.write("|------|------|\n")
        for month in sorted(metrics['monthly_returns'].keys()):
            pnl = metrics['monthly_returns'][month]
            f.write(f"| {month} | {pnl:.2f} |\n")
    
    # 生成交易明细CSV
    trades_path = os.path.join(output_dir, '交易明细.csv')
    with open(trades_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['买入日期', '买入价格', '买入数量', '买入费用', '卖出日期', '卖出价格', '卖出数量', '卖出费用', '盈亏', '股票代码'])
        for t in trades:
            writer.writerow([
                t['buy_date'], t['buy_price'], t['buy_shares'], t['buy_fee'],
                t['sell_date'], t['sell_price'], t['sell_shares'], t['sell_fee'],
                t['profit'], t['stock']
            ])
    
    # 生成资金曲线CSV
    curve_path = os.path.join(output_dir, '资金曲线.csv')
    with open(curve_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['日期', '可用资金', '持仓市值', '总资产'])
        for entry in equity_curve:
            writer.writerow([entry['date'], entry['capital'], entry['position_value'], entry['total_value']])


def main():
    args = parse_args()
    
    # 确保输出目录存在
    os.makedirs('out', exist_ok=True)
    
    # 加载数据
    print(f"正在加载数据目录: {args.data}")
    stocks = load_csv_data(args.data, '2024-01-01', args.end)
    print(f"加载了 {len(stocks)} 只股票的数据")
    
    if not stocks:
        print("错误: 没有找到任何股票数据")
        sys.exit(1)
    
    # 加载规则
    print(f"正在加载规则: {args.rules}")
    rules = load_rules(args.rules)
    
    # 运行回测
    print(f"正在运行回测: {args.start} 至 {args.end}")
    trades, equity_curve, initial_capital = run_backtest(stocks, rules, args.start, args.end)
    
    # 计算指标
    print("正在计算指标...")
    metrics = calculate_metrics(trades, equity_curve, initial_capital)
    
    # 生成报告
    print("正在生成报告...")
    generate_report(metrics, trades, equity_curve, 'out')
    
    print("\n" + "="*50)
    print("回测完成!")
    print("="*50)
    print(f"总收益: {metrics['total_profit']:.2f} 元")
    print(f"总收益率: {metrics['total_return']*100:.2f}%")
    print(f"交易次数: {metrics['total_trades']}")
    print(f"\n报告已保存到 out/ 目录")


if __name__ == '__main__':
    main()
