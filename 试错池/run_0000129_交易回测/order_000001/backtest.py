#!/usr/bin/env python3
"""
A股个人交易规则回测工具
只研究，不下单
"""

import sys
import os
import csv
import json
import argparse
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 常量
COMMISSION_RATE = 0.0003  # 手续费万分之三
STAMP_TAX_RATE = 0.0005   # 印花税千分之零点五
PRICE_LIMIT = 0.10        # 涨跌停10%

class StockData:
    """单只股票数据"""
    def __init__(self, symbol: str, data: List[Dict]):
        self.symbol = symbol
        self.data = sorted(data, key=lambda x: x['date'])
        self.dates = [d['date'] for d in self.data]
        self.prices = {d['date']: d for d in self.data}
    
    def get_price(self, date: str) -> Optional[Dict]:
        return self.prices.get(date)
    
    def get_date_index(self, date: str) -> int:
        return self.dates.index(date) if date in self.dates else -1

class Position:
    """持仓"""
    def __init__(self, symbol: str, buy_date: str, buy_price: float, quantity: int):
        self.symbol = symbol
        self.buy_date = buy_date
        self.buy_price = buy_price
        self.quantity = quantity
        self.hold_days = 0

class BacktestEngine:
    """回测引擎"""
    def __init__(self, rules: Dict, start_date: str, end_date: str):
        self.rules = rules
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = 100000  # 初始资金10万
        self.cash = self.initial_capital
        self.positions: List[Position] = []
        self.trades: List[Dict] = []  # 交易明细
        self.equity_curve: List[Dict] = []  # 资金曲线
        self.holding_days_limit = rules.get('holding_days_limit', 10)
    
    def load_stock_data(self, data_dir: str) -> Dict[str, StockData]:
        """加载股票数据"""
        stocks = {}
        data_path = Path(data_dir)
        for csv_file in data_path.glob('*.csv'):
            symbol = csv_file.stem
            data = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        data.append({
                            'date': row['date'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['volume'])
                        })
                    except (ValueError, KeyError):
                        continue
            if data:
                stocks[symbol] = StockData(symbol, data)
        return stocks
    
    def get_trading_dates(self, stocks: Dict[str, StockData]) -> List[str]:
        """获取所有股票的交易日期并合并排序"""
        all_dates = set()
        for stock in stocks.values():
            for date in stock.dates:
                if self.start_date <= date <= self.end_date:
                    all_dates.add(date)
        return sorted(all_dates)
    
    def check_ma_cross(self, stock: StockData, date: str, rule: Dict) -> bool:
        """检查均线交叉条件"""
        if 'short_ma' not in rule or 'long_ma' not in rule:
            return False
        
        idx = stock.get_date_index(date)
        if idx < rule['long_ma']:
            return False
        
        def calc_ma(days):
            prices = [stock.data[idx - i]['close'] for i in range(days)]
            return sum(prices) / days
        
        short_ma = calc_ma(rule['short_ma'])
        long_ma = calc_ma(rule['long_ma'])
        
        # 前一天均线
        idx_prev = idx - 1
        if idx_prev < rule['long_ma']:
            return False
        
        def calc_ma_prev(days):
            prices = [stock.data[idx_prev - i]['close'] for i in range(days)]
            return sum(prices) / days
        
        short_ma_prev = calc_ma_prev(rule['short_ma'])
        long_ma_prev = calc_ma_prev(rule['long_ma'])
        
        if rule.get('type') == 'ma_cross':
            # 金叉：短均线上穿长均线
            return short_ma_prev <= long_ma_prev and short_ma > long_ma
        return False
    
    def check_breakout(self, stock: StockData, date: str, rule: Dict) -> bool:
        """检查突破N日高点/低点"""
        if 'period' not in rule:
            return False
        
        idx = stock.get_date_index(date)
        if idx < rule['period']:
            return False
        
        period_prices = [stock.data[idx - i]['close'] for i in range(rule['period'])]
        highest = max(period_prices[:-1])  # 不包含当天
        lowest = min(period_prices[:-1])
        
        current_close = stock.data[idx]['close']
        
        if rule.get('type') == 'breakout_high':
            return current_close > highest
        elif rule.get('type') == 'breakout_low':
            return current_close < lowest
        return False
    
    def check_price_change(self, stock: StockData, date: str, rule: Dict) -> bool:
        """检查涨跌幅阈值"""
        if 'change_percent' not in rule:
            return False
        
        idx = stock.get_date_index(date)
        if idx < 1:
            return False
        
        current_close = stock.data[idx]['close']
        prev_close = stock.data[idx - 1]['close']
        change_pct = (current_close - prev_close) / prev_close
        
        threshold = rule['change_percent'] / 100.0
        condition = rule.get('condition', 'above')
        
        if condition == 'above':
            return change_pct > threshold
        elif condition == 'below':
            return change_pct < -threshold
        elif condition == 'abs_above':
            return abs(change_pct) > threshold
        return False
    
    def check_buy_conditions(self, stock: StockData, date: str) -> bool:
        """检查买入条件"""
        if 'buy_conditions' not in self.rules:
            return False
        
        for condition in self.rules['buy_conditions']:
            cond_type = condition.get('type')
            result = False
            if cond_type == 'ma_cross':
                result = self.check_ma_cross(stock, date, condition)
            elif cond_type == 'breakout_high' or cond_type == 'breakout_low':
                result = self.check_breakout(stock, date, condition)
            elif cond_type == 'price_change':
                result = self.check_price_change(stock, date, condition)
            
            if not result:
                return False
        
        return True
    
    def check_sell_conditions(self, position: Position, stock: StockData, date: str, current_price: float) -> Tuple[bool, str]:
        """检查卖出条件，返回(是否卖出, 原因)"""
        # 止损
        stop_loss = self.rules.get('stop_loss_percent', 0)
        if stop_loss > 0:
            loss_pct = (current_price - position.buy_price) / position.buy_price
            if loss_pct <= -stop_loss / 100:
                return True, 'stop_loss'
        
        # 止盈
        take_profit = self.rules.get('take_profit_percent', 0)
        if take_profit > 0:
            profit_pct = (current_price - position.buy_price) / position.buy_price
            if profit_pct >= take_profit / 100:
                return True, 'take_profit'
        
        # 持有上限
        position.hold_days += 1
        if position.hold_days >= self.holding_days_limit:
            return True, 'holding_limit'
        
        # 其他卖出条件
        if 'sell_conditions' in self.rules:
            for condition in self.rules['sell_conditions']:
                cond_type = condition.get('type')
                result = False
                if cond_type == 'ma_cross':
                    result = self.check_ma_cross(stock, date, condition)
                elif cond_type == 'breakout_high' or cond_type == 'breakout_low':
                    result = self.check_breakout(stock, date, condition)
                elif cond_type == 'price_change':
                    result = self.check_price_change(stock, date, condition)
                
                if result:
                    return True, cond_type
        
        return False, ''
    
    def simulate_buy(self, symbol: str, date: str, price: float) -> bool:
        """模拟买入"""
        price = round(price, 2)
        
        # 用500股整数倍
        quantity = 500
        
        # 资金不足则调整数量
        max_quantity = int(self.cash / (price * (1 + COMMISSION_RATE)))
        if max_quantity < 500:
            return False
        
        quantity = min(quantity, (max_quantity // 500) * 500)
        if quantity < 500:
            return False
        
        cost = price * quantity
        commission = cost * COMMISSION_RATE
        total_cost = cost + commission
        
        if total_cost > self.cash:
            return False
        
        self.cash -= total_cost
        self.positions.append(Position(symbol, date, price, quantity))
        
        self.trades.append({
            'symbol': symbol,
            'buy_date': date,
            'buy_price': price,
            'buy_quantity': quantity,
            'buy_commission': round(commission, 2),
            'sell_date': '',
            'sell_price': 0,
            'sell_quantity': 0,
            'sell_commission': 0,
            'profit': 0,
            'reason': ''
        })
        return True
    
    def simulate_sell(self, position: Position, date: str, price: float, reason: str) -> bool:
        """模拟卖出"""
        price = round(price, 2)
        
        sell_value = price * position.quantity
        commission = sell_value * COMMISSION_RATE
        stamp_tax = sell_value * STAMP_TAX_RATE
        total_cost = commission + stamp_tax
        
        net_value = sell_value - total_cost
        buy_cost = position.buy_price * position.quantity + self.trades[-1]['buy_commission']
        profit = net_value - buy_cost
        
        self.cash += net_value
        self.trades[-1]['sell_date'] = date
        self.trades[-1]['sell_price'] = price
        self.trades[-1]['sell_quantity'] = position.quantity
        self.trades[-1]['sell_commission'] = round(commission + stamp_tax, 2)
        self.trades[-1]['profit'] = round(profit, 2)
        self.trades[-1]['reason'] = reason
        
        self.positions.remove(position)
        return True
    
    def can_buy(self, date: str, price: float, prev_close: float) -> bool:
        """检查能否买入（涨停不能买）"""
        if prev_close <= 0:
            return True
        limit_up_price = prev_close * (1 + PRICE_LIMIT)
        return price < limit_up_price - 0.01
    
    def can_sell(self, date: str, price: float, prev_close: float) -> bool:
        """检查能否卖出（跌停不能卖）"""
        if prev_close <= 0:
            return True
        limit_down_price = prev_close * (1 - PRICE_LIMIT)
        return price > limit_down_price + 0.01
    
    def run(self, stocks: Dict[str, StockData]) -> Dict:
        """运行回测"""
        trading_dates = self.get_trading_dates(stocks)
        
        # 初始化资金曲线
        if trading_dates:
            self.equity_curve.append({
                'date': trading_dates[0],
                'equity': self.cash,
                'cash': self.cash
            })
        
        for i, date in enumerate(trading_dates):
            # 计算当前总权益
            current_equity = self.cash
            
            # 处理现有持仓
            positions_to_close = []
            for position in self.positions[:]:
                stock = stocks.get(position.symbol)
                if not stock:
                    continue
                
                price_data = stock.get_price(date)
                if not price_data:
                    continue
                
                current_price = price_data['close']
                
                # 检查卖出条件
                should_sell, reason = self.check_sell_conditions(position, stock, date, current_price)
                
                if should_sell:
                    # 检查是否能卖出（不是跌停）
                    if i > 0:
                        prev_date = trading_dates[i - 1]
                        prev_price_data = stock.get_price(prev_date)
                        if prev_price_data:
                            if not self.can_sell(date, current_price, prev_price_data['close']):
                                continue  # 跌停卖不出，跳过
                    
                    if self.simulate_sell(position, date, current_price, reason):
                        positions_to_close.append(position)
            
            # 买入信号
            buy_candidates = []
            for symbol, stock in stocks.items():
                price_data = stock.get_price(date)
                if not price_data:
                    continue
                
                # 检查是否涨停不能买
                if i > 0:
                    prev_date = trading_dates[i - 1]
                    prev_price_data = stock.get_price(prev_date)
                    if prev_price_data:
                        if not self.can_buy(date, price_data['close'], prev_price_data['close']):
                            continue
                
                if self.check_buy_conditions(stock, date):
                    # 检查是否已持有该股票（T+1限制：当天买的不能当天卖）
                    has_position = any(p.symbol == symbol for p in self.positions)
                    if not has_position:
                        buy_candidates.append((symbol, stock, price_data['close']))
            
            # 按价格排序，优先买低价的（简单策略）
            buy_candidates.sort(key=lambda x: x[2])
            
            for symbol, stock, price in buy_candidates:
                if self.simulate_buy(symbol, date, price):
                    pass  # 资金已更新
            
            # 更新资金曲线
            if self.positions:
                for pos in self.positions:
                    stock = stocks.get(pos.symbol)
                    if stock:
                        price_data = stock.get_price(date)
                        if price_data:
                            current_equity += pos.quantity * price_data['close']
            
            self.equity_curve.append({
                'date': date,
                'equity': round(current_equity, 2),
                'cash': round(self.cash, 2)
            })
        
        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'final_equity': self.cash,
            'initial_capital': self.initial_capital
        }
    
    def generate_report(self) -> str:
        """生成回测报告"""
        completed_trades = [t for t in self.trades if t['sell_date']]
        
        if not completed_trades:
            total_return = 0
            annual_return = 0
            max_drawdown = 0
            win_rate = 0
            profit_loss_ratio = 0
            total_trades = 0
            monthly_returns = {}
        else:
            # 总收益
            total_profit = sum(t['profit'] for t in completed_trades)
            total_return = (total_profit / self.initial_capital) * 100
            
            # 年化收益
            if len(self.equity_curve) > 1:
                days = len(self.equity_curve)
                years = days / 250
                annual_return = ((1 + total_profit / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
            else:
                annual_return = 0
            
            # 最大回撤
            equity_values = [e['equity'] for e in self.equity_curve]
            peak = equity_values[0] if equity_values else self.initial_capital
            max_drawdown = 0
            for eq in equity_values:
                if eq > peak:
                    peak = eq
                drawdown = (peak - eq) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            # 胜率
            winning_trades = sum(1 for t in completed_trades if t['profit'] > 0)
            total_trades = len(completed_trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # 盈亏比
            wins = [t['profit'] for t in completed_trades if t['profit'] > 0]
            losses = [t['profit'] for t in completed_trades if t['profit'] < 0]
            avg_win = statistics.mean(wins) if wins else 0
            avg_loss = abs(statistics.mean(losses)) if losses else 0
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            
            # 每月收益
            monthly_returns = {}
            for trade in completed_trades:
                month = trade['sell_date'][:7]
                if month not in monthly_returns:
                    monthly_returns[month] = 0
                monthly_returns[month] += trade['profit']
        
        report = f"""# 回测报告

## 总体统计
- 总收益: {total_return:.2f}%
- 年化收益: {annual_return:.2f}%
- 最大回撤: {max_drawdown:.2f}%
- 胜率: {win_rate:.2f}%
- 盈亏比: {profit_loss_ratio:.2f}
- 交易次数: {total_trades}
- 初始资金: {self.initial_capital:.2f} 元
- 最终资金: {self.cash:.2f} 元

## 规则配置
"""
        report += f"- 止损: {self.rules.get('stop_loss_percent', 0)}%\n"
        report += f"- 止盈: {self.rules.get('take_profit_percent', 0)}%\n"
        report += f"- 持有上限: {self.rules.get('holding_days_limit', 10)}天\n"
        
        if monthly_returns:
            report += "\n## 每月收益\n"
            report += "| 月份 | 收益 |\n|------|------|\n"
            for month in sorted(monthly_returns.keys()):
                report += f"| {month} | {monthly_returns[month]:.2f} |\n"
        
        return report

def main():
    parser = argparse.ArgumentParser(description='A股回测工具')
    parser.add_argument('--data', required=True, help='CSV数据目录')
    parser.add_argument('--rules', required=True, help='规则JSON文件')
    parser.add_argument('--start', required=True, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='结束日期 YYYY-MM-DD')
    
    args = parser.parse_args()
    
    # 加载规则
    with open(args.rules, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    
    # 创建回测引擎
    engine = BacktestEngine(rules, args.start, args.end)
    
    # 加载数据
    stocks = engine.load_stock_data(args.data)
    if not stocks:
        print("错误: 未找到股票数据")
        sys.exit(1)
    
    print(f"已加载 {len(stocks)} 只股票")
    
    # 运行回测
    result = engine.run(stocks)
    
    # 创建输出目录
    os.makedirs('out', exist_ok=True)
    
    # 输出报告
    report = engine.generate_report()
    with open('out/回测报告.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 输出交易明细
    with open('out/交易明细.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'buy_date', 'buy_price', 'buy_quantity', 
                                                'buy_commission', 'sell_date', 'sell_price', 
                                                'sell_quantity', 'sell_commission', 'profit', 'reason'])
        writer.writeheader()
        writer.writerows(engine.trades)
    
    # 输出资金曲线
    with open('out/资金曲线.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'equity', 'cash'])
        writer.writeheader()
        writer.writerows(engine.equity_curve)
    
    completed = len([t for t in engine.trades if t['sell_date']])
    print(f"回测完成，共完成交易 {completed} 笔")
    print("输出文件已保存到 out/ 目录")

if __name__ == '__main__':
    main()
