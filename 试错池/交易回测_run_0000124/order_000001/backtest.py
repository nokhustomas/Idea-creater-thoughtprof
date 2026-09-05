#!/usr/bin/env python3
"""
A股个人交易规则回测工具（只研究，不下单）
本工具不下单、不连接账户、不构成投资建议
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 常量
COMMISSION_RATE = 0.0003  # 万分之三
STAMP_TAX_RATE = 0.0005   # 千分之零点五
PRICE_LIMIT = 0.10        # 涨跌停10%
MAX_POSITION_DAYS = 30    # 默认最大持仓天数


class StockData:
    """单只股票数据"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.data: Dict[str, dict] = {}  # date -> {open, high, low, close, volume}
    
    def add_bar(self, date: str, open_p: float, high: float, low: float, close: float, volume: int):
        self.data[date] = {
            'open': float(open_p),
            'high': float(high),
            'low': float(low),
            'close': float(close),
            'volume': int(volume)
        }
    
    def get_bar(self, date: str) -> Optional[dict]:
        return self.data.get(date)
    
    def get_dates(self) -> List[str]:
        return sorted(self.data.keys())
    
    def get_price_on_date(self, date: str) -> Optional[float]:
        bar = self.data.get(date)
        return bar['close'] if bar else None


class Portfolio:
    """投资组合"""
    def __init__(self, initial_cash: float = 1000000.0):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.position: Optional[dict] = None  # {symbol, buy_date, buy_price, quantity, buy_commission}
        self.trades: List[dict] = []
        self.daily_value: List[dict] = []  # 每日净值
        self.hold_days: int = 0
    
    def can_buy(self, symbol: str) -> bool:
        """检查是否可以买入（不在持仓中）"""
        return self.position is None or self.position['symbol'] != symbol
    
    def buy(self, date: str, symbol: str, price: float, commission: float):
        """买入股票"""
        quantity = self.cash / (price * (1 + COMMISSION_RATE))
        quantity = int(quantity / 100) * 100  # 100股整数倍
        
        if quantity < 100:
            return False
        
        cost = quantity * price
        total_cost = cost + commission
        
        if total_cost > self.cash:
            return False
        
        self.cash -= total_cost
        self.position = {
            'symbol': symbol,
            'buy_date': date,
            'buy_price': price,
            'quantity': quantity,
            'buy_commission': commission
        }
        self.hold_days = 0
        return True
    
    def sell(self, date: str, price: float, commission: float, stamp_tax: float) -> Tuple[float, float]:
        """卖出股票"""
        if not self.position:
            return 0.0, 0.0
        
        quantity = self.position['quantity']
        proceeds = quantity * price
        total_fees = commission + stamp_tax
        net_proceeds = proceeds - total_fees
        
        # 计算盈亏
        buy_cost = quantity * self.position['buy_price'] + self.position['buy_commission']
        profit = net_proceeds - buy_cost
        
        # 记录交易
        self.trades.append({
            'symbol': self.position['symbol'],
            'buy_date': self.position['buy_date'],
            'sell_date': date,
            'buy_price': self.position['buy_price'],
            'sell_price': price,
            'quantity': quantity,
            'profit': profit,
            'commission': self.position['buy_commission'] + commission + stamp_tax
        })
        
        self.cash += net_proceeds
        self.position = None
        self.hold_days = 0
        
        return profit, proceeds
    
    def get_value(self, date: str, stocks: Dict[str, StockData]) -> float:
        """计算当日总价值"""
        total = self.cash
        if self.position:
            stock = stocks.get(self.position['symbol'])
            if stock:
                price = stock.get_price_on_date(date)
                if price:
                    total += self.position['quantity'] * price
        return total
    
    def check_limit_up(self, stock: StockData, date: str, is_buy: bool) -> bool:
        """检查涨跌停限制"""
        bar = stock.get_bar(date)
        if not bar:
            return True
        
        prev_date = self._get_prev_trading_date(stock, date)
        if not prev_date:
            return False
        
        prev_bar = stock.get_bar(prev_date)
        if not prev_bar:
            return False
        
        prev_close = prev_bar['close']
        limit_price = prev_close * (1 + PRICE_LIMIT if is_buy else 1 - PRICE_LIMIT)
        
        if is_buy:
            # 涨停板不能买入
            return bar['high'] < limit_price - 0.001
        else:
            # 跌停板不能卖出
            return bar['low'] > limit_price + 0.001
    
    def _get_prev_trading_date(self, stock: StockData, date: str) -> Optional[str]:
        """获取前一交易日"""
        dates = stock.get_dates()
        for i, d in enumerate(dates):
            if d == date and i > 0:
                return dates[i - 1]
        return None
    
    def can_sell_t1(self, date: str) -> bool:
        """检查T+1限制"""
        if not self.position:
            return True
        return self.position['buy_date'] < date


def load_stock_data(data_dir: str) -> Dict[str, StockData]:
    """加载股票数据"""
    stocks = {}
    data_path = Path(data_dir)
    
    for csv_file in data_path.glob('*.csv'):
        symbol = csv_file.stem
        stock = StockData(symbol)
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stock.add_bar(
                        row['date'],
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume']
                    )
                except (KeyError, ValueError):
                    continue
        
        if stock.data:
            stocks[symbol] = stock
    
    return stocks


def load_rules(rules_file: str) -> dict:
    """加载交易规则"""
    with open(rules_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_ma(prices: List[float], period: int) -> List[float]:
    """计算移动平均线"""
    if len(prices) < period:
        return []
    return prices[period - 1:]


def evaluate_rules(stock: StockData, date: str, rules: dict, all_dates: List[str]) -> dict:
    """评估交易规则"""
    results = {
        'ma_cross': False,
        'breakout_high': False,
        'breakout_low': False,
        'price_change_up': False,
        'price_change_down': False
    }
    
    # 获取历史数据（到date为止）
    hist_dates = [d for d in all_dates if d <= date]
    if len(hist_dates) < 60:  # 至少需要60天数据
        return results
    
    # 计算价格序列
    prices = [stock.data[d]['close'] for d in hist_dates]
    
    # 均线交叉
    if 'ma_cross' in rules:
        ma_rule = rules['ma_cross']
        short_period = ma_rule.get('short', 5)
        long_period = ma_rule.get('long', 20)
        
        if len(prices) >= long_period + 1:
            short_ma_prev = sum(prices[-(long_period + 1):-(long_period + 1 - short_period)]) / short_period
            long_ma_prev = sum(prices[-(long_period + 1):]) / long_period
            short_ma_curr = sum(prices[-short_period:]) / short_period
            long_ma_curr = sum(prices[-long_period:]) / long_period
            
            if ma_rule.get('type') == 'golden':
                results['ma_cross'] = short_ma_prev <= long_ma_prev and short_ma_curr > long_ma_curr
            elif ma_rule.get('type') == 'death':
                results['ma_cross'] = short_ma_prev >= long_ma_prev and short_ma_curr < long_ma_curr
    
    # 突破N日高点
    if 'breakout' in rules:
        bk_rule = rules['breakout']
        n = bk_rule.get('n', 20)
        curr_price = prices[-1]
        
        if len(prices) > n:
            high_prices = prices[-n:-1]
            if bk_rule.get('type') == 'high':
                results['breakout_high'] = curr_price > max(high_prices)
            elif bk_rule.get('type') == 'low':
                results['breakout_low'] = curr_price < min(high_prices)
    
    # 涨跌幅阈值
    if 'price_change' in rules:
        pc_rule = rules['price_change']
        pct = pc_rule.get('percent', 5) / 100.0
        n = pc_rule.get('n', 1)
        
        if len(prices) > n:
            prev_price = prices[-(n + 1)]
            change = (prices[-1] - prev_price) / prev_price
            
            if 'direction' in pc_rule:
                if pc_rule['direction'] == 'up':
                    results['price_change_up'] = change >= pct
                elif pc_rule['direction'] == 'down':
                    results['price_change_down'] = change <= -pct
    
    return results


def check_buy_conditions(stock: StockData, date: str, rules: dict, all_dates: List[str]) -> bool:
    """检查买入条件"""
    eval_results = evaluate_rules(stock, date, rules, all_dates)
    
    if 'conditions' not in rules or 'buy' not in rules['conditions']:
        return False
    
    conditions = rules['conditions']['buy']
    
    for cond in conditions:
        if cond == 'ma_cross' and not eval_results['ma_cross']:
            return False
        if cond == 'breakout_high' and not eval_results['breakout_high']:
            return False
        if cond == 'price_change_up' and not eval_results['price_change_up']:
            return False
    
    return True


def check_sell_conditions(portfolio: Portfolio, stock: StockData, date: str, rules: dict, all_dates: List[str]) -> Tuple[bool, str]:
    """检查卖出条件，返回(是否卖出, 原因)"""
    if not portfolio.position:
        return False, ''
    
    eval_results = evaluate_rules(stock, date, rules, all_dates)
    
    # 持有上限天数检查
    max_days = rules.get('max_position_days', MAX_POSITION_DAYS)
    portfolio.hold_days += 1
    if portfolio.hold_days >= max_days:
        return True, f'持有超限({portfolio.hold_days}天)'
    
    # 止损检查
    if 'stop_loss' in rules:
        buy_price = portfolio.position['buy_price']
        curr_price = stock.get_price_on_date(date)
        if curr_price:
            loss_pct = (curr_price - buy_price) / buy_price
            if loss_pct <= -rules['stop_loss'] / 100:
                return True, f'止损({loss_pct*100:.2f}%)'
    
    # 止盈检查
    if 'take_profit' in rules:
        buy_price = portfolio.position['buy_price']
        curr_price = stock.get_price_on_date(date)
        if curr_price:
            profit_pct = (curr_price - buy_price) / buy_price
            if profit_pct >= rules['take_profit'] / 100:
                return True, f'止盈({profit_pct*100:.2f}%)'
    
    # 均线死叉
    if 'conditions' in rules and 'sell' in rules['conditions']:
        conditions = rules['conditions']['sell']
        for cond in conditions:
            if cond == 'ma_cross' and eval_results['ma_cross']:
                return True, '均线死叉'
            if cond == 'breakout_low' and eval_results['breakout_low']:
                return True, '突破低点'
            if cond == 'price_change_down' and eval_results['price_change_down']:
                return True, '下跌突破'
    
    return False, ''


def run_backtest(stocks: Dict[str, StockData], rules: dict, start_date: str, end_date: str) -> Portfolio:
    """运行回测"""
    portfolio = Portfolio()
    
    # 获取所有交易日期（所有股票的并集）
    all_dates_set = set()
    for stock in stocks.values():
        all_dates_set.update(stock.get_dates())
    all_dates = sorted([d for d in all_dates_set if start_date <= d <= end_date])
    
    if not all_dates:
        return portfolio
    
    # 获取每个股票的历史数据
    stock_history: Dict[str, List[str]] = {}
    for symbol, stock in stocks.items():
        stock_history[symbol] = stock.get_dates()
    
    # 逐日回测
    for date in all_dates:
        # 获取当前日期有数据的股票
        available_stocks = {s: stocks[s] for s in stocks if date in stocks[s].data}
        
        if not available_stocks:
            continue
        
        # 检查卖出
        if portfolio.position:
            symbol = portfolio.position['symbol']
            if symbol in available_stocks:
                stock = available_stocks[symbol]
                should_sell, reason = check_sell_conditions(portfolio, stock, date, rules, stock_history[symbol])
                
                if should_sell and portfolio.can_sell_t1(date):
                    curr_price = stock.get_price_on_date(date)
                    if curr_price and not portfolio.check_limit_up(stock, date, False):
                        # 不能卖出（跌停），跳过
                        pass
                    else:
                        commission = curr_price * portfolio.position['quantity'] * COMMISSION_RATE
                        stamp_tax = curr_price * portfolio.position['quantity'] * STAMP_TAX_RATE
                        profit, proceeds = portfolio.sell(date, curr_price, commission, stamp_tax)
                        print(f"[{date}] 卖出 {symbol}: {portfolio.position['quantity']}股 @{curr_price:.2f}, 盈亏:{profit:.2f}, 原因:{reason}")
        
        # 检查买入
        if portfolio.can_buy(''):
            for symbol, stock in available_stocks.items():
                # 检查涨跌停
                if portfolio.check_limit_up(stock, date, True):
                    if check_buy_conditions(stock, date, rules, stock_history[symbol]):
                        curr_price = stock.get_price_on_date(date)
                        commission = curr_price * 100 * COMMISSION_RATE
                        if portfolio.buy(date, symbol, curr_price, commission):
                            print(f"[{date}] 买入 {symbol}: 100股 @{curr_price:.2f}")
                            break  # 一次只买一只
        
        # 记录每日净值
        total_value = portfolio.get_value(date, stocks)
        portfolio.daily_value.append({
            'date': date,
            'cash': portfolio.cash,
            'position_value': total_value - portfolio.cash,
            'total_value': total_value
        })
    
    return portfolio


def calculate_metrics(portfolio: Portfolio) -> dict:
    """计算回测指标"""
    trades = portfolio.trades
    daily_values = portfolio.daily_value
    
    if not trades:
        return {
            'total_return': 0,
            'annual_return': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'profit_loss_ratio': 0,
            'total_trades': 0
        }
    
    # 总收益
    total_profit = sum(t['profit'] for t in trades)
    initial = portfolio.initial_cash
    total_return = (total_profit / initial) * 100
    
    # 年化收益
    if daily_values:
        start_date = daily_values[0]['date']
        end_date = daily_values[-1]['date']
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        years = (end_dt - start_dt).days / 365.0
        if years > 0:
            annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
        else:
            annual_return = 0
    else:
        annual_return = 0
    
    # 最大回撤
    max_value = 0
    max_drawdown = 0
    peak = 0
    for dv in daily_values:
        if dv['total_value'] > peak:
            peak = dv['total_value']
        drawdown = (peak - dv['total_value']) / peak * 100 if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # 胜率
    winning_trades = [t for t in trades if t['profit'] > 0]
    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    
    # 盈亏比
    avg_win = sum(t['profit'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    losing_trades = [t for t in trades if t['profit'] <= 0]
    avg_loss = sum(abs(t['profit']) for t in losing_trades) / len(losing_trades) if losing_trades else 1
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'profit_loss_ratio': profit_loss_ratio,
        'total_trades': len(trades)
    }


def generate_report(portfolio: Portfolio, metrics: dict, output_dir: str):
    """生成报告"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 回测报告
    report_path = os.path.join(output_dir, '回测报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# 回测报告\n\n')
        f.write(f'## 整体指标\n\n')
        f.write(f'- 总收益率: {metrics["total_return"]:.2f}%\n')
        f.write(f'- 年化收益率: {metrics["annual_return"]:.2f}%\n')
        f.write(f'- 最大回撤: {metrics["max_drawdown"]:.2f}%\n')
        f.write(f'- 胜率: {metrics["win_rate"]:.2f}%\n')
        f.write(f'- 盈亏比: {metrics["profit_loss_ratio"]:.2f}\n')
        f.write(f'- 交易次数: {metrics["total_trades"]}\n')
        f.write(f'- 总盈亏: {sum(t["profit"] for t in portfolio.trades):.2f}元\n\n')
        
        # 每月收益
        monthly_data: Dict[str, float] = {}
        for dv in portfolio.daily_value:
            month = dv['date'][:7]
            if month not in monthly_data:
                monthly_data[month] = dv['total_value']
        
        if len(monthly_data) > 1:
            f.write('## 每月净值\n\n')
            f.write('| 月份 | 净值 |\n')
            f.write('|------|------|\n')
            months = sorted(monthly_data.keys())
            for month in months:
                f.write(f'| {month} | {monthly_data[month]:.2f} |\n')
    
    # 交易明细
    trades_path = os.path.join(output_dir, '交易明细.csv')
    with open(trades_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'buy_date', 'sell_date', 'buy_price', 'sell_price', 'quantity', 'profit', 'commission'])
        writer.writeheader()
        for t in portfolio.trades:
            writer.writerow(t)
    
    # 资金曲线
    equity_path = os.path.join(output_dir, '资金曲线.csv')
    with open(equity_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'cash', 'position_value', 'total_value'])
        writer.writeheader()
        for dv in portfolio.daily_value:
            writer.writerow(dv)


def main():
    parser = argparse.ArgumentParser(description='A股个人交易规则回测工具（只研究，不下单）')
    parser.add_argument('--data', required=True, help='CSV数据目录')
    parser.add_argument('--rules', required=True, help='规则JSON文件')
    parser.add_argument('--start', required=True, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='结束日期 YYYY-MM-DD')
    
    args = parser.parse_args()
    
    # 加载数据
    print(f'加载数据目录: {args.data}')
    stocks = load_stock_data(args.data)
    print(f'加载股票数量: {len(stocks)}')
    
    if not stocks:
        print('错误: 未找到股票数据')
        sys.exit(1)
    
    # 加载规则
    print(f'加载规则: {args.rules}')
    rules = load_rules(args.rules)
    
    # 运行回测
    print(f'运行回测: {args.start} 至 {args.end}')
    portfolio = run_backtest(stocks, rules, args.start, args.end)
    
    # 计算指标
    metrics = calculate_metrics(portfolio)
    
    # 生成报告
    output_dir = 'out'
    generate_report(portfolio, metrics, output_dir)
    
    print(f'\n回测完成!')
    print(f'交易次数: {metrics["total_trades"]}')
    print(f'总收益率: {metrics["total_return"]:.2f}%')
    print(f'输出目录: {output_dir}/')


if __name__ == '__main__':
    main()
