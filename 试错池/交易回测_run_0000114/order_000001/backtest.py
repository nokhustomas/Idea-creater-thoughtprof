#!/usr/bin/env python3
"""
A-Share Personal Trading Rules Backtesting Tool
For research only - no trading, no account connection, no investment advice.
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Constants for A-share trading
TICKER_FEE_RATE = 0.0003  # 0.03%
STAMP_TAX_RATE = 0.0005   # 0.05% sell stamp tax
LIMIT_UP_DOWN = 0.10      # 10% limit up/down


def calculate_fee(amount: float, is_sell: bool = False) -> float:
    """Calculate trading fee. Buy: 0.03%, Sell: 0.03% + 0.05% stamp tax."""
    fee = amount * TICKER_FEE_RATE
    if is_sell:
        fee += amount * STAMP_TAX_RATE
    return round(fee, 2)


class StockData:
    """Container for single stock data."""
    def __init__(self, symbol: str, data: List[Dict]):
        self.symbol = symbol
        self.data = sorted(data, key=lambda x: x['date'])
        self.dates = [d['date'] for d in self.data]
        self.close_prices = {d['date']: d['close'] for d in self.data}
        self.high_prices = {d['date']: d['high'] for d in self.data}
        self.low_prices = {d['date']: d['low'] for d in self.data}
        self.open_prices = {d['date']: d['open'] for d in self.data}
        self.volumes = {d['date']: d['volume'] for d in self.data}
    
    def get_price(self, date: str) -> Optional[float]:
        return self.close_prices.get(date)
    
    def get_high(self, date: str) -> Optional[float]:
        return self.high_prices.get(date)
    
    def get_low(self, date: str) -> Optional[float]:
        return self.low_prices.get(date)
    
    def get_open(self, date: str) -> Optional[float]:
        return self.open_prices.get(date)


class Backtester:
    """Main backtesting class with A-share constraints."""
    
    def __init__(self, data_dir: str, rules: Dict, start_date: str, end_date: str):
        self.data_dir = Path(data_dir)
        self.rules = rules
        self.start_date = start_date
        self.end_date = end_date
        self.stocks: Dict[str, StockData] = {}
        self.trading_dates: List[str] = []
        
        # Trading state
        self.position = 0
        self.buy_price = 0.0
        self.buy_date = None
        self.hold_days = 0
        
        # Results
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.total_fees = 0.0
        self.initial_capital = 100000.0
        self.cash = self.initial_capital
        
        self.load_data()
        self.build_trading_calendar()
    
    def load_data(self):
        """Load stock data from CSV files."""
        for csv_file in self.data_dir.glob('*.csv'):
            symbol = csv_file.stem
            data = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row['date']
                    if self.start_date <= date <= self.end_date:
                        data.append({
                            'date': date,
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['volume'])
                        })
            if data:
                self.stocks[symbol] = StockData(symbol, data)
    
    def build_trading_calendar(self):
        """Build unified trading calendar from all stocks."""
        all_dates = set()
        for stock in self.stocks.values():
            all_dates.update(stock.dates)
        self.trading_dates = sorted([d for d in all_dates 
                                      if self.start_date <= d <= self.end_date])
    
    def get_prev_date(self, stock: StockData, date: str, days: int = 1) -> Optional[str]:
        """Get previous trading day."""
        try:
            idx = stock.dates.index(date)
            if idx >= days:
                return stock.dates[idx - days]
        except ValueError:
            pass
        return None
    
    def calculate_ma(self, stock: StockData, date: str, period: int) -> Optional[float]:
        """Calculate moving average."""
        try:
            idx = stock.dates.index(date)
        except ValueError:
            return None
        
        if idx < period:
            return None
        
        prices = [stock.close_prices[stock.dates[i]] for i in range(idx - period, idx)]
        return sum(prices) / period
    
    def calculate_highest(self, stock: StockData, date: str, period: int) -> Optional[float]:
        """Calculate highest price in last N days."""
        if date is None:
            return None
        try:
            idx = stock.dates.index(date)
        except ValueError:
            return None
        
        if idx < period:
            return None
        
        highs = [stock.high_prices[stock.dates[i]] for i in range(idx - period, idx)]
        return max(highs)
    
    def check_buy_allowed(self, date: str, stock: StockData, price: float) -> Tuple[bool, str]:
        """Check if buy is allowed under A-share rules."""
        if price is None:
            return False, "No price"
        
        if self.position > 0:
            return False, "Already holding"
        
        # Check limit up
        prev_close = stock.get_price(self.get_prev_date(stock, date, 1))
        if prev_close:
            limit_up_price = prev_close * (1 + LIMIT_UP_DOWN)
            if price >= limit_up_price - 0.001:
                return False, "Limit up"
        
        return True, ""
    
    def check_sell_allowed(self, date: str, stock: StockData, price: float) -> Tuple[bool, str]:
        """Check if sell is allowed under A-share T+1 rules."""
        if self.position == 0:
            return False, "No position"
        
        # T+1: cannot sell on same day as buy
        if self.buy_date and date == self.buy_date:
            return False, "T+1"
        
        # Check limit down
        prev_close = stock.get_price(self.get_prev_date(stock, date, 1))
        if prev_close:
            limit_down_price = prev_close * (1 - LIMIT_UP_DOWN)
            if price <= limit_down_price + 0.001:
                return False, "Limit down"
        
        return True, ""
    
    def check_buy_signals(self, date: str, stock: StockData) -> List[str]:
        """Check all buy signal conditions."""
        signals = []
        price = stock.get_price(date)
        if price is None:
            return signals
        
        prev_date = self.get_prev_date(stock, date, 1)
        prev_price = stock.get_price(prev_date) if prev_date else None
        
        # 1. MA Crossover
        ma_rules = self.rules.get('ma_crossover', {})
        if ma_rules.get('enabled'):
            short_period = ma_rules.get('short_period', 5)
            long_period = ma_rules.get('long_period', 20)
            
            short_ma = self.calculate_ma(stock, date, short_period)
            long_ma = self.calculate_ma(stock, date, long_period)
            prev_short_ma = self.calculate_ma(stock, prev_date, short_period) if prev_date else None
            prev_long_ma = self.calculate_ma(stock, prev_date, long_period) if prev_date else None
            
            if all(x is not None for x in [short_ma, long_ma, prev_short_ma, prev_long_ma]):
                if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                    signals.append(f"MA({short_period}/{long_period})")
        
        # 2. Breakout N-day high
        breakout_rules = self.rules.get('breakout', {})
        if breakout_rules.get('enabled'):
            high_period = breakout_rules.get('high_period', 20)
            prev_date_high = self.get_prev_date(stock, date, 1)
            if prev_date_high:
                highest = self.calculate_highest(stock, prev_date_high, high_period)
                if highest is not None and price > highest:
                    signals.append(f"Break{high_period}dHigh")
        
        # 3. Price change threshold
        price_change_rules = self.rules.get('price_change', {})
        if price_change_rules.get('enabled') and prev_price:
            change_pct = (price - prev_price) / prev_price * 100
            min_change = price_change_rules.get('min_change_pct', -100)
            max_change = price_change_rules.get('max_change_pct', 100)
            if min_change <= change_pct <= max_change:
                signals.append(f"Change{change_pct:.1f}%")
        
        return signals
    
    def check_sell_signals(self, date: str, stock: StockData) -> Tuple[bool, str]:
        """Check all sell signal conditions."""
        price = stock.get_price(date)
        if price is None or self.position == 0:
            return False, ""
        
        profit_pct = (price - self.buy_price) / self.buy_price * 100 if self.buy_price > 0 else 0
        
        # 1. Stop loss
        stop_loss = self.rules.get('stop_loss_pct', 100)
        if profit_pct <= -stop_loss:
            return True, f"StopLoss({profit_pct:.2f}%)"
        
        # 2. Take profit
        take_profit = self.rules.get('take_profit_pct', 1000)
        if profit_pct >= take_profit:
            return True, f"TakeProfit({profit_pct:.2f}%)"
        
        # 3. Max hold days
        max_hold = self.rules.get('max_hold_days', 1000)
        if self.hold_days >= max_hold:
            return True, f"MaxHold{max_hold}d"
        
        # 4. MA death cross
        ma_rules = self.rules.get('ma_crossover', {})
        if ma_rules.get('enabled') and ma_rules.get('sell_on_death_cross'):
            short_period = ma_rules.get('short_period', 5)
            long_period = ma_rules.get('long_period', 20)
            
            short_ma = self.calculate_ma(stock, date, short_period)
            long_ma = self.calculate_ma(stock, date, long_period)
            prev_date = self.get_prev_date(stock, date, 1)
            prev_short_ma = self.calculate_ma(stock, prev_date, short_period) if prev_date else None
            prev_long_ma = self.calculate_ma(stock, prev_date, long_period) if prev_date else None
            
            if all(x is not None for x in [short_ma, long_ma, prev_short_ma, prev_long_ma]):
                if prev_short_ma >= prev_long_ma and short_ma < long_ma:
                    return True, "DeathCross"
        
        return False, ""
    
    def execute_buy(self, date: str, stock: StockData, price: float, reason: str):
        """Execute buy order."""
        shares = int(self.cash / (price * 100)) * 100  # A-share: 100 shares per lot
        if shares == 0:
            return False
        
        actual_cost = shares * price
        fee = calculate_fee(actual_cost, is_sell=False)
        
        if actual_cost + fee > self.cash:
            available = self.cash / (1 + TICKER_FEE_RATE)
            shares = int(available / (price * 100)) * 100
            if shares == 0:
                return False
            actual_cost = shares * price
            fee = calculate_fee(actual_cost, is_sell=False)
        
        self.cash -= (actual_cost + fee)
        self.position = shares
        self.buy_price = price
        self.buy_date = date
        self.hold_days = 0
        self.total_fees += fee
        
        self.trades.append({
            'date': date,
            'action': 'BUY',
            'symbol': stock.symbol,
            'price': round(price, 2),
            'shares': shares,
            'amount': round(actual_cost, 2),
            'fee': fee,
            'reason': reason,
            'cash_after': round(self.cash, 2)
        })
        return True
    
    def execute_sell(self, date: str, stock: StockData, price: float, reason: str):
        """Execute sell order."""
        if self.position == 0:
            return False
        
        sell_value = self.position * price
        fee = calculate_fee(sell_value, is_sell=True)
        profit = sell_value - fee - (self.position * self.buy_price)
        
        self.cash += sell_value - fee
        self.total_fees += fee
        
        self.trades.append({
            'date': date,
            'action': 'SELL',
            'symbol': stock.symbol,
            'price': round(price, 2),
            'shares': self.position,
            'amount': round(sell_value, 2),
            'fee': fee,
            'profit': round(profit, 2),
            'reason': reason,
            'cash_after': round(self.cash, 2)
        })
        
        self.position = 0
        self.buy_price = 0.0
        self.buy_date = None
        self.hold_days = 0
        return True
    
    def run(self) -> 'Backtester':
        """Run backtest simulation."""
        for date in self.trading_dates:
            # Find stock with data for this date
            current_stock = None
            for symbol, stock in self.stocks.items():
                if date in stock.dates:
                    current_stock = stock
                    break
            
            if current_stock is None:
                continue
            
            price = current_stock.get_price(date)
            
            # Check sell first
            if self.position > 0:
                self.hold_days += 1
                sell_signal, reason = self.check_sell_signals(date, current_stock)
                
                if sell_signal:
                    can_sell, block_reason = self.check_sell_allowed(date, current_stock, price)
                    if can_sell:
                        self.execute_sell(date, current_stock, price, reason)
            
            # Check buy if no position
            if self.position == 0:
                buy_signals = self.check_buy_signals(date, current_stock)
                if buy_signals:
                    can_buy, block_reason = self.check_buy_allowed(date, current_stock, price)
                    if can_buy:
                        self.execute_buy(date, current_stock, price, buy_signals[0])
            
            # Record equity
            equity = self.cash
            if self.position > 0:
                equity += self.position * price
            
            self.equity_curve.append({
                'date': date,
                'equity': round(equity, 2),
                'position': self.position
            })
        
        return self
    
    def generate_report(self) -> str:
        """Generate backtest report in markdown."""
        trades = self.trades
        equity_curve = self.equity_curve
        
        final_equity = equity_curve[-1]['equity'] if equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        # Calculate holding days in backtest period
        days = (datetime.strptime(self.end_date, '%Y-%m-%d') - datetime.strptime(self.start_date, '%Y-%m-%d')).days
        years = max(days / 365, 1/365)
        annual_return = ((final_equity / self.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Max drawdown
        peak = self.initial_capital
        max_drawdown = 0
        for entry in equity_curve:
            if entry['equity'] > peak:
                peak = entry['equity']
            dd = (peak - entry['equity']) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd
        
        # Win rate and profit/loss
        sell_trades = [t for t in trades if t['action'] == 'SELL']
        wins = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(wins) / len(sell_trades) * 100 if sell_trades else 0
        
        total_profit = sum(t.get('profit', 0) for t in sell_trades if t.get('profit', 0) > 0)
        total_loss = abs(sum(t.get('profit', 0) for t in sell_trades if t.get('profit', 0) < 0))
        profit_loss_ratio = total_profit / total_loss if total_loss > 0 else (float('inf') if total_profit > 0 else 0)
        
        # Monthly returns
        monthly_returns = {}
        for entry in equity_curve:
            month = entry['date'][:7]
            if month not in monthly_returns:
                monthly_returns[month] = {'start_equity': entry['equity'], 'end_equity': entry['equity']}
            monthly_returns[month]['end_equity'] = entry['equity']
        
        # Build report
        report = f"""# 回测报告

## 基本信息
- 回测期间: {self.start_date} 至 {self.end_date}
- 初始资金: {self.initial_capital:,.2f} 元
- 最终净值: {final_equity:,.2f} 元

## 收益统计
- 总收益率: {total_return:+.2f}%
- 年化收益率: {annual_return:+.2f}%
- 最大回撤: {max_drawdown:.2f}%
- 交易次数: {len(sell_trades)} 笔

## 交易统计
- 胜率: {win_rate:.2f}%
- 盈亏比: {profit_loss_ratio:.2f}
- 总手续费: {self.total_fees:,.2f} 元

## 月度收益表
| 月份 | 收益率 |
|------|--------|
"""
        for month in sorted(monthly_returns.keys()):
            start_eq = monthly_returns[month]['start_equity']
            end_eq = monthly_returns[month]['end_equity']
            monthly_ret = (end_eq - start_eq) / start_eq * 100 if start_eq > 0 else 0
            report += f"| {month} | {monthly_ret:+.2f}% |\n"
        
        return report
    
    def save_results(self, output_dir: str):
        """Save all results to output directory."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate and save report
        report = self.generate_report()
        with open(os.path.join(output_dir, '回测报告.md'), 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Save trades detail
        with open(os.path.join(output_dir, '交易明细.csv'), 'w', encoding='utf-8', newline='') as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].keys())
                writer.writeheader()
                writer.writerows(self.trades)
        
        # Save equity curve
        with open(os.path.join(output_dir, '资金曲线.csv'), 'w', encoding='utf-8', newline='') as f:
            if self.equity_curve:
                writer = csv.DictWriter(f, fieldnames=self.equity_curve[0].keys())
                writer.writeheader()
                writer.writerows(self.equity_curve)


def main():
    parser = argparse.ArgumentParser(description='A-Share Backtesting Tool')
    parser.add_argument('--data', required=True, help='CSV data directory')
    parser.add_argument('--rules', required=True, help='Rules JSON file')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Load rules
    with open(args.rules, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    
    # Run backtest
    backtester = Backtester(args.data, rules, args.start, args.end)
    backtester.run()
    
    # Save results
    backtester.save_results('out')
    
    print(f"Backtest completed. Results saved to out/")
    print(f"Total sell trades: {len([t for t in backtester.trades if t['action'] == 'SELL'])}")
    print(f"Final equity: {backtester.equity_curve[-1]['equity'] if backtester.equity_curve else 100000:.2f}")


if __name__ == '__main__':
    main()
