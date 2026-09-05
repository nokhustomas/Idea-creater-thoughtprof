#!/usr/bin/env python3
"""
A 股个人交易规则回测工具 (只研究，不下单)
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# constants
COMMISSION_BUY = 0.0003
COMMISSION_SELL = 0.0003 + 0.0005  # 0.0008 (sell includes stamp duty)
INITIAL_CAPITAL = 1_000_000.0
TRADING_DAYS_PER_YEAR = 252


def parse_args():
    parser = argparse.ArgumentParser(
        description="A股个人交易规则回测工具 – 只研究，不下单"
    )
    parser.add_argument("--data", required=True, help="CSV 数据目录")
    parser.add_argument("--rules", required=True, help="规则 JSON 文件")
    parser.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    return parser.parse_args()


def load_stock_data(data_dir, start_date, end_date):
    """加载目录下所有 CSV 文件，返回 dict[stock] = list of dicts"""
    stocks = {}
    for fname in os.listdir(data_dir):
        if not fname.endswith(".csv"):
            continue
        symbol = fname.replace(".csv", "")
        rows = []
        filepath = os.path.join(data_dir, fname)
        with open(filepath, "r") as f:
            reader = csv.reader(f)
            for line in reader:
                if not line:
                    continue
                # skip comment lines (synthetic data note)
                if line[0].startswith("#"):
                    continue
                if len(line) < 6:
                    continue
                date_str = line[0].strip()
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if date < start_date or date > end_date:
                    continue
                try:
                    open_p = float(line[1])
                    high_p = float(line[2])
                    low_p = float(line[3])
                    close_p = float(line[4])
                    volume = float(line[5])
                except ValueError:
                    continue
                rows.append({
                    "date": date,
                    "open": open_p,
                    "high": high_p,
                    "low": low_p,
                    "close": close_p,
                    "volume": volume,
                })
        rows.sort(key=lambda x: x["date"])
        if rows:
            stocks[symbol] = rows
    return stocks


def generate_synthetic_data(target_dir, n_stocks=3, n_days=300, seed=42):
    """生成合成数据并写入 target_dir"""
    import random
    random.seed(seed)
    os.makedirs(target_dir, exist_ok=True)

    # start date for 300 trading days (weekdays only)
    cur = datetime(2024, 7, 1).date()
    dates = []
    while len(dates) < n_days:
        if cur.weekday() < 5:  # Mon-Fri
            dates.append(cur)
        cur += timedelta(days=1)

    for stock_idx in range(1, n_stocks + 1):
        symbol = f"stock_{chr(64 + stock_idx)}"  # A, B, C
        fpath = os.path.join(target_dir, f"{symbol}.csv")
        price = 20.0 + random.random() * 30  # initial price 20-50
        with open(fpath, "w") as f:
            # comment line to indicate synthetic data
            f.write("# Synthetic data for A-share backtest, not real\n")
            f.write("date,open,high,low,close,volume\n")
            for dt in dates:
                change = (random.random() - 0.48) * 0.04  # daily change ~ ±2%
                close = price * (1 + change)
                open_p = price * (1 + (random.random() - 0.5) * 0.01)
                high = max(open_p, close) * (1 + random.random() * 0.01)
                low = min(open_p, close) * (1 - random.random() * 0.01)
                volume = random.randint(1_000_000, 10_000_000)
                f.write(
                    f"{dt.strftime('%Y-%m-%d')},"
                    f"{open_p:.2f},{high:.2f},{low:.2f},{close:.2f},{volume}\n"
                )
                price = close
        print(f"  Generated {fpath}")


# ---------- indicator helpers ----------
def get_ma(prices, i, period):
    """simple moving average ending at index i (inclusive)"""
    if i + 1 < period:
        return None
    return sum(prices[i - period + 1 : i + 1]) / period


def get_highest_high(highs, i, period):
    """max of high over previous `period` days, ending at i-1"""
    if i < period:
        return None
    return max(highs[i - period : i])


def get_lowest_low(lows, i, period):
    """min of low over previous `period` days, ending at i-1"""
    if i < period:
        return None
    return min(lows[i - period : i])


# ---------- condition evaluation ----------
def evaluate_condition(cond, row, rows, i, close_list, high_list, low_list):
    typ = cond.get("type")
    if typ == "ma_cross":
        short = cond["short"]
        long_ = cond["long"]
        direction = cond.get("direction", "up")
        if i < long_:
            return False
        ma_short_prev = get_ma(close_list, i - 1, short)
        ma_long_prev = get_ma(close_list, i - 1, long_)
        ma_short_cur = get_ma(close_list, i, short)
        ma_long_cur = get_ma(close_list, i, long_)
        if None in (ma_short_prev, ma_long_prev, ma_short_cur, ma_long_cur):
            return False
        if direction == "up":
            return ma_short_prev <= ma_long_prev and ma_short_cur > ma_long_cur
        else:  # down
            return ma_short_prev >= ma_long_prev and ma_short_cur < ma_long_cur

    elif typ == "breakout":
        period = cond["period"]
        direction = cond.get("direction", "high")
        if direction == "high":
            highest = get_highest_high(high_list, i, period)
            if highest is None:
                return False
            return row["close"] > highest
        else:  # low
            lowest = get_lowest_low(low_list, i, period)
            if lowest is None:
                return False
            return row["close"] < lowest

    elif typ == "threshold":
        field = cond.get("field", "close")
        op = cond.get("operator", ">")
        value = cond["value"]
        if field == "close":
            actual = row["close"]
        elif field == "change":
            if i == 0:
                return False
            actual = (close_list[i] - close_list[i - 1]) / close_list[i - 1] * 100
        elif field == "open":
            actual = row["open"]
        elif field == "high":
            actual = row["high"]
        elif field == "low":
            actual = row["low"]
        else:
            return False
        if op == ">":
            return actual > value
        elif op == "<":
            return actual < value
        elif op == ">=":
            return actual >= value
        elif op == "<=":
            return actual <= value
        elif op == "==":
            return abs(actual - value) < 1e-9
        return False

    return False


def evaluate_entry(entry_conditions, row, rows, i, close_list, high_list, low_list):
    """all conditions must be true (AND)"""
    if not entry_conditions:
        return True  # always enter
    for cond in entry_conditions:
        if not evaluate_condition(cond, row, rows, i, close_list, high_list, low_list):
            return False
    return True


# ---------- backtest engine ----------
def run_backtest(stocks, rules, start_date, end_date):
    entry_conditions = rules.get("entry_conditions", [])
    exit_conf = rules.get("exit_conditions", {})
    stop_loss_pct = exit_conf.get("stop_loss_pct", None)  # negative, e.g. -5
    take_profit_pct = exit_conf.get("take_profit_pct", None)  # positive, e.g. 10
    max_holding_days = exit_conf.get("max_holding_days", 9999)

    # gather all trading dates across stocks
    all_dates = set()
    for rows in stocks.values():
        for r in rows:
            all_dates.add(r["date"])
    all_dates = sorted(all_dates)

    # state
    cash = INITIAL_CAPITAL
    positions = []  # list of (symbol, quantity, buy_price, buy_date, buy_index)
    trades = []  # list of dicts for each completed trade
    daily_net_values = []  # list of (date, net_value, cash, stock_value)

    # for each stock, keep index pointer
    stock_idx = {sym: 0 for sym in stocks}

    for date in all_dates:
        # current stock_value & net_value before trading
        stock_value = 0.0
        for sym, qty, buy_price, buy_date, _ in positions:
            # find today's close for that stock
            rows = stocks.get(sym, [])
            # find row for today
            row_today = None
            for r in rows:
                if r["date"] == date:
                    row_today = r
                    break
            if row_today:
                stock_value += qty * row_today["close"]
        net_value = cash + stock_value
        daily_net_values.append((date, net_value, cash, stock_value))

        # process each stock
        for sym, rows in stocks.items():
            # advance index to today
            while stock_idx[sym] < len(rows) and rows[stock_idx[sym]]["date"] < date:
                stock_idx[sym] += 1
            if stock_idx[sym] >= len(rows) or rows[stock_idx[sym]]["date"] != date:
                continue
            i = stock_idx[sym]
            row = rows[i]
            close = row["close"]
            open_ = row["open"]
            high = row["high"]
            low = row["low"]
            prev_close = rows[i - 1]["close"] if i > 0 else None

            # limit up/down
            limit_up = limit_down = None
            if prev_close is not None:
                limit_up = prev_close * 1.1
                limit_down = prev_close * 0.9

            # collect data for condition evaluation
            # close_list, high_list, low_list for this stock
            close_list = [r["close"] for r in rows]
            high_list = [r["high"] for r in rows]
            low_list = [r["low"] for r in rows]

            # check if we already have a position for this stock
            pos = None
            for p in positions:
                if p[0] == sym:
                    pos = p
                    break

            if pos is None:
                # ----- entry -----
                # check T+1 not applicable for buy
                # check limit up (cannot buy at limit up)
                if limit_up is not None and close >= limit_up:
                    continue
                # evaluate entry conditions
                if not evaluate_entry(entry_conditions, row, rows, i,
                                      close_list, high_list, low_list):
                    continue
                # buy
                cost_per_share = close * (1 + COMMISSION_BUY)
                max_shares = int(cash / cost_per_share)
                if max_shares <= 0:
                    continue
                # buy
                buy_cost = max_shares * cost_per_share
                cash -= buy_cost
                positions.append((sym, max_shares, close, date, i))
                # record buy in trades? we'll record on sell
            else:
                # ----- exit -----
                sym_pos, qty, buy_price, buy_date, buy_idx = pos
                # T+1: cannot sell same day
                if date == buy_date:
                    continue
                # limit down: cannot sell at limit down
                if limit_down is not None and close <= limit_down:
                    continue
                # check stop loss
                if stop_loss_pct is not None:
                    if close <= buy_price * (1 + stop_loss_pct / 100.0):
                        # sell
                        trigger = "stop_loss"
                        sell_now = True
                    else:
                        sell_now = False
                else:
                    sell_now = False
                # check take profit
                if not sell_now and take_profit_pct is not None:
                    if close >= buy_price * (1 + take_profit_pct / 100.0):
                        trigger = "take_profit"
                        sell_now = True
                # check max holding days
                if not sell_now:
                    days_held = i - buy_idx
                    if days_held >= max_holding_days:
                        trigger = "max_hold"
                        sell_now = True
                # if we have a sell signal from conditions, we could also have
                # an exit condition from entry_conditions? Not implemented.
                if not sell_now:
                    continue

                # sell
                sell_proceeds = qty * close * (1 - COMMISSION_SELL)
                gross_profit = sell_proceeds - (qty * buy_price * (1 + COMMISSION_BUY))
                cash += sell_proceeds
                # record trade
                trades.append({
                    "stock": sym,
                    "buy_date": buy_date.strftime("%Y-%m-%d"),
                    "sell_date": date.strftime("%Y-%m-%d"),
                    "quantity": qty,
                    "buy_price": buy_price,
                    "sell_price": close,
                    "gross_profit": round(gross_profit, 2),
                    "commission_buy": round(qty * buy_price * COMMISSION_BUY, 2),
                    "commission_sell": round(qty * close * COMMISSION_SELL, 2),
                })
                # remove position
                positions.remove(pos)

    # liquidate any remaining positions at last close
    # (use last date in each stock)
    for sym, qty, buy_price, buy_date, buy_idx in positions[:]:
        rows = stocks[sym]
        last_row = rows[-1]
        close = last_row["close"]
        # limit down not applied? we'll just sell
        sell_proceeds = qty * close * (1 - COMMISSION_SELL)
        gross_profit = sell_proceeds - (qty * buy_price * (1 + COMMISSION_BUY))
        cash += sell_proceeds
        trades.append({
            "stock": sym,
            "buy_date": buy_date.strftime("%Y-%m-%d"),
            "sell_date": last_row["date"].strftime("%Y-%m-%d"),
            "quantity": qty,
            "buy_price": buy_price,
            "sell_price": close,
            "gross_profit": round(gross_profit, 2),
            "commission_buy": round(qty * buy_price * COMMISSION_BUY, 2),
            "commission_sell": round(qty * close * COMMISSION_SELL, 2),
        })
        positions.remove((sym, qty, buy_price, buy_date, buy_idx))

    # final net value
    final_net_value = cash
    return trades, daily_net_values, final_net_value


# ---------- reporting ----------
def write_report(trades, daily_net_values, final_net_value, out_dir):
    # compute statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["gross_profit"] > 0]
    losing_trades = [t for t in trades if t["gross_profit"] <= 0]
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    total_profit = sum(t["gross_profit"] for t in trades)
    avg_profit_win = (sum(t["gross_profit"] for t in winning_trades) /
                      len(winning_trades)) if winning_trades else 0.0
    avg_loss_lose = (sum(t["gross_profit"] for t in losing_trades) /
                     len(losing_trades)) if losing_trades else 0.0
    profit_loss_ratio = abs(avg_profit_win / avg_loss_lose) if avg_loss_lose != 0 else 0.0

    # net value series
    net_values = [v[1] for v in daily_net_values]
    total_return = (final_net_value / INITIAL_CAPITAL - 1) * 100
    n_days = len(net_values)
    if n_days > 0:
        annual_return = (final_net_value / INITIAL_CAPITAL) ** (TRADING_DAYS_PER_YEAR / n_days) - 1
        annual_return *= 100
    else:
        annual_return = 0.0

    # max drawdown
    peak = net_values[0] if net_values else 0
    max_dd = 0.0
    for v in net_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak
        if dd > max_dd:
            max_dd = dd
    max_drawdown = max_dd * 100

    # monthly returns
    monthly = defaultdict(list)
    for date, nv, _, _ in daily_net_values:
        key = date.strftime("%Y-%m")
        monthly[key].append(nv)
    month_returns = []
    for month in sorted(monthly):
        vals = monthly[month]
        if len(vals) >= 2:
            ret = (vals[-1] / vals[0] - 1) * 100
        else:
            ret = 0.0
        month_returns.append((month, ret))

    # write report
    report_path = os.path.join(out_dir, "回测报告.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 回测报告\n\n")
        f.write(f"初始资金: {INITIAL_CAPITAL:,.2f}\n")
        f.write(f"最终资金: {final_net_value:,.2f}\n")
        f.write(f"总收益率: {total_return:.2f}%\n")
        f.write(f"年化收益率: {annual_return:.2f}%\n")
        f.write(f"最大回撤: {max_drawdown:.2f}%\n")
        f.write(f"胜率: {win_rate*100:.2f}%\n")
        f.write(f"盈亏比: {profit_loss_ratio:.2f}\n")
        f.write(f"交易次数: {total_trades}\n\n")
        f.write("## 每月收益表\n\n")
        f.write("| 月份 | 收益率(%) |\n")
        f.write("|------|-----------|\n")
        for month, ret in month_returns:
            f.write(f"| {month} | {ret:.2f} |\n")

    # write trade details
    trade_path = os.path.join(out_dir, "交易明细.csv")
    with open(trade_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["股票", "买入日期", "卖出日期", "数量", "买入价", "卖出价", "毛利润"])
        for t in trades:
            writer.writerow([
                t["stock"],
                t["buy_date"],
                t["sell_date"],
                t["quantity"],
                t["buy_price"],
                t["sell_price"],
                t["gross_profit"],
            ])

    # write equity curve
    equity_path = os.path.join(out_dir, "资金曲线.csv")
    with open(equity_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "净值", "现金", "持仓市值"])
        for date, nv, c, sv in daily_net_values:
            writer.writerow([date.strftime("%Y-%m-%d"), f"{nv:.2f}", f"{c:.2f}", f"{sv:.2f}"])

    print(f"Report written to {report_path}")
    print(f"Trades written to {trade_path}")
    print(f"Equity curve written to {equity_path}")


def main():
    args = parse_args()
    data_dir = args.data
    rules_file = args.rules
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    # auto‑generate sample data if directory missing
    if not os.path.isdir(data_dir):
        print(f"Data directory '{data_dir}' not found. Generating synthetic data...")
        generate_synthetic_data(data_dir)
        print("Synthetic data generated.")

    # load rules
    with open(rules_file, "r") as f:
        rules = json.load(f)

    # load stock data
    stocks = load_stock_data(data_dir, start_date, end_date)
    if not stocks:
        print("No stock data found in the given date range.", file=sys.stderr)
        sys.exit(1)

    # run backtest
    trades, daily_net_values, final_net_value = run_backtest(
        stocks, rules, start_date, end_date
    )

    # create output directory
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)

    # write reports
    write_report(trades, daily_net_values, final_net_value, out_dir)

    # exit code 0 on success
    sys.exit(0)


if __name__ == "__main__":
    main()
