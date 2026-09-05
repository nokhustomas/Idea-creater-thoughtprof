#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股个人交易规则回测工具（只研究，不下单）。
仅使用 Python 标准库。
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict


# ======================== A 股内置约束 ========================
T_PLUS_ONE = True          # T+1：当日买次日才能卖
PRICE_LIMIT_PCT = 0.10     # 涨跌停 10%（A股主板默认）
COMMISSION_RATE = 0.0003   # 手续费 万分之三
STAMP_TAX_RATE = 0.0005    # 印花税 千分之零点五（仅卖出）
INITIAL_CASH = 1_000_000.0 # 初始资金 100 万


# ======================== 数据加载 ========================
def load_csv_dir(data_dir, start_date, end_date):
    """
    读取 data_dir 下所有 .csv；每个文件包含 date,open,high,low,close,volume。
    返回 {symbol: [(date, open, high, low, close, volume), ...]}，
    按日期升序，按 start/end 过滤。
    """
    data = {}
    for fname in sorted(os.listdir(data_dir)):
        if not fname.lower().endswith(".csv"):
            continue
        symbol = os.path.splitext(fname)[0]
        path = os.path.join(data_dir, fname)
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    d = datetime.strptime(r["date"].strip(), "%Y-%m-%d").date()
                    o = float(r["open"]); h = float(r["high"])
                    lo = float(r["low"]); c = float(r["close"])
                    v = float(r.get("volume", 0) or 0)
                except Exception:
                    continue
                if d < start_date or d > end_date:
                    continue
                rows.append((d, o, h, lo, c, v))
        rows.sort(key=lambda x: x[0])
        if rows:
            data[symbol] = rows
    return data


def all_trading_dates(data_by_symbol):
    """汇总所有出现过的交易日并排序。"""
    s = set()
    for rows in data_by_symbol.values():
        for r in rows:
            s.add(r[0])
    return sorted(s)


# ======================== 工具：指标计算 ========================
def sma(values, n):
    """返回与 values 等长的 SMA 序列（不足 n 时为 None）。"""
    out = [None] * len(values)
    if n <= 0:
        return out
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def rolling_high(values, n):
    out = [None] * len(values)
    for i in range(len(values)):
        if i + 1 >= n:
            out[i] = max(values[i + 1 - n: i + 1])
    return out


def rolling_low(values, n):
    out = [None] * len(values)
    for i in range(len(values)):
        if i + 1 >= n:
            out[i] = min(values[i + 1 - n: i + 1])
    return out


def pct_change(values, lookback):
    out = [None] * len(values)
    for i in range(len(values)):
        if i >= lookback:
            prev = values[i - lookback]
            if prev != 0:
                out[i] = (values[i] - prev) / prev
            else:
                out[i] = 0.0
    return out


# ======================== 信号与下单 ========================
def is_limit_up_or_down(prev_close, cur_open, cur_high, cur_low, cur_close):
    """
    涨停：今日收盘 ≥ 昨收 × (1+10%) 且 不曾低于昨收×(1+10%) 的下边界近似处理。
    跌停：今日收盘 ≤ 昨收 × (1-10%)。
    更宽松：只要 收盘 触及涨跌停封板（±10%），就视为不可成交；
    我们以"收盘价相对昨收的涨跌幅是否触及 ±10%（含四舍五入误差）"判定。
    """
    if prev_close <= 0:
        return False, False
    up = prev_close * (1 + PRICE_LIMIT_PCT)
    dn = prev_close * (1 - PRICE_LIMIT_PCT)
    # 允许 0.5% 容差识别一字板
    hit_up = cur_high >= up * (1 - 0.005) and cur_close >= up * (1 - 0.005)
    hit_dn = cur_low <= dn * (1 + 0.005) and cur_close <= dn * (1 + 0.005)
    return hit_up, hit_dn


def passes_price_limit_for_buy(prev_close, o, h, lo, c):
    """涨停日买入通常无法成交（封板）；跌停不影响买入。"""
    up, _dn = is_limit_up_or_down(prev_close, o, h, lo, c)
    return not up


def passes_price_limit_for_sell(prev_close, o, h, lo, c):
    """跌停日卖出通常无法成交；涨停不影响卖出。"""
    _up, dn = is_limit_up_or_down(prev_close, o, h, lo, c)
    return not dn


def buyable_lots(cash, price, lot_size=100):
    """A股 100 股一手。可用现金能买几手。"""
    if price <= 0:
        return 0
    max_shares = int(cash // (price * (1 + COMMISSION_RATE)))
    lots = max_shares // lot_size
    return lots * lot_size


def calc_buy_cost(price, shares):
    return price * shares + price * shares * COMMISSION_RATE


def calc_sell_proceeds(price, shares):
    fee = price * shares * COMMISSION_RATE + price * shares * STAMP_TAX_RATE
    return price * shares - fee, fee


# ======================== 主回测 ========================
class Position:
    __slots__ = ("symbol", "shares", "cost_price", "buy_date")
    def __init__(self, symbol, shares, cost_price, buy_date):
        self.symbol = symbol
        self.shares = shares
        self.cost_price = cost_price
        self.buy_date = buy_date


def run_backtest(data_by_symbol, rules, start_date, end_date):
    """
    多标的、多仓位的简单回测框架。
    每只股票独立处理信号；同时维护一个总资金账户。
    """
    cash = INITIAL_CASH
    positions = {}      # symbol -> Position
    trade_log = []      # 每笔交易明细
    equity_curve = []   # [(date, equity)]

    # 规则参数
    ma_short = int(rules.get("ma_short", 5))
    ma_long = int(rules.get("ma_long", 20))
    breakout_high_n = int(rules.get("breakout_high_n", 20))
    breakout_low_n = int(rules.get("breakout_low_n", 20))
    change_threshold = float(rules.get("change_threshold", 0.0))
    change_lookback = int(rules.get("change_lookback", 1))
    stop_loss_pct = float(rules.get("stop_loss_pct", 0.0))
    take_profit_pct = float(rules.get("take_profit_pct", 0.0))
    max_hold_days = int(rules.get("max_hold_days", 0))  # 0 表示不限制
    position_pct = float(rules.get("position_pct", 1.0))  # 每次买入用多少比例的可用资金
    if position_pct <= 0:
        position_pct = 1.0
    if position_pct > 1.0:
        position_pct = 1.0

    # 每日：先处理卖出（止损/止盈/最大持有/卖点信号），再处理买入
    # 用每个 symbol 自己的交易日序列做局部索引推进
    indices = {sym: 0 for sym in data_by_symbol}
    sorted_dates = all_trading_dates(data_by_symbol)

    for di, today in enumerate(sorted_dates):
        # —— 先按当日数据做信号判断与成交 —— #
        # 收集当日每只股票的行情 & 前一日收盘
        today_quotes = {}
        for sym, rows in data_by_symbol.items():
            if indices[sym] < len(rows) and rows[indices[sym]][0] == today:
                idx = indices[sym]
                today_quotes[sym] = rows[idx]
            else:
                # 该股票今天没数据
                pass

        # 取每只股票截至今日（含）的历史序列（用于指标计算）
        hist = {}
        for sym, rows in data_by_symbol.items():
            if indices.get(sym, 0) < len(rows) and rows[indices[sym]][0] == today:
                hist[sym] = rows[: indices[sym] + 1]
            else:
                # 取截至今日为止的所有行（多数情况与上一交易日相同）
                # 我们以最后一行日期 ≤ today 为准
                cut = 0
                for i, r in enumerate(rows):
                    if r[0] <= today:
                        cut = i + 1
                    else:
                        break
                hist[sym] = rows[:cut]

        # —— 1) 卖出逻辑 —— #
        for sym in list(positions.keys()):
            pos = positions[sym]
            if sym not in hist or len(hist[sym]) < 2:
                continue
            rows = hist[sym]
            # 当前 K 线
            d, o, h, lo, c, v = rows[-1]
            # 昨收
            prev_close = rows[-2][4]
            # T+1 校验
            if T_PLUS_ONE and pos.buy_date >= d:
                continue  # 当日买入次日才能卖

            # 计算买入后是否触发止损/止盈/最大持有日
            closes = [r[4] for r in rows]
            ret = (c - pos.cost_price) / pos.cost_price if pos.cost_price > 0 else 0.0
            do_sell = False
            sell_reason = ""

            # 止盈/止损：以收盘价判定
            if stop_loss_pct > 0 and ret <= -stop_loss_pct:
                do_sell = True; sell_reason = "止损"
            elif take_profit_pct > 0 and ret >= take_profit_pct:
                do_sell = True; sell_reason = "止盈"
            elif max_hold_days > 0 and (d - pos.buy_date).days >= max_hold_days:
                do_sell = True; sell_reason = "持有上限"

            # 卖点信号：MA 死叉 / 跌破 N 日低点 / 跌幅阈值
            if not do_sell:
                short_ma = sma(closes, ma_short)[-1]
                long_ma = sma(closes, ma_long)[-1]
                prev_short_ma = sma(closes[:-1], ma_short)[-1] if len(closes) >= 2 else None
                prev_long_ma = sma(closes[:-1], ma_long)[-1] if len(closes) >= 2 else None
                if short_ma is not None and long_ma is not None \
                   and prev_short_ma is not None and prev_long_ma is not None:
                    if prev_short_ma >= prev_long_ma and short_ma < long_ma:
                        do_sell = True; sell_reason = "均线死叉"

                if not do_sell and breakout_low_n > 0:
                    lows_series = [r[3] for r in rows]
                    if len(lows_series) >= breakout_low_n:
                        recent_low = min(lows_series[-breakout_low_n:])
                        if c < recent_low:
                            do_sell = True; sell_reason = f"跌破{breakout_low_n}日低点"

                if not do_sell and change_threshold > 0:
                    pc = pct_change(closes, change_lookback)[-1]
                    if pc is not None and pc <= -change_threshold:
                        do_sell = True; sell_reason = "跌幅阈值"

            if not do_sell:
                continue

            # 涨跌停卖出检查
            if not passes_price_limit_for_sell(prev_close, o, h, lo, c):
                # 当日无法卖出，跳过
                continue

            # 以开盘价成交（次日开盘模型在 T+1 已体现）
            px = o
            if px <= 0:
                continue
            shares = pos.shares
            proceeds, fee = calc_sell_proceeds(px, shares)
            cash += proceeds
            trade_log.append({
                "symbol": sym,
                "buy_date": pos.buy_date.isoformat(),
                "sell_date": d.isoformat(),
                "buy_price": round(pos.cost_price, 4),
                "sell_price": round(px, 4),
                "shares": shares,
                "amount": round(px * shares, 2),
                "fee": round(fee, 4),
                "pnl": round(proceeds - px * shares * COMMISSION_RATE - pos.cost_price * shares * COMMISSION_RATE, 2),
                "pnl_net": round(proceeds - (pos.cost_price * shares + pos.cost_price * shares * COMMISSION_RATE), 2),
                "reason": sell_reason,
            })
            del positions[sym]

        # —— 2) 买入逻辑 —— #
        for sym, rows in hist.items():
            if len(rows) < 2:
                continue
            if sym in positions:
                continue  # 已持仓不重复买
            d, o, h, lo, c, v = rows[-1]
            prev_close = rows[-2][4]

            closes = [r[4] for r in rows]
            buy_signal = False

            # 买点信号：MA 金叉 / 突破 N 日新高 / 涨幅阈值
            short_ma = sma(closes, ma_short)[-1]
            long_ma = sma(closes, ma_long)[-1]
            prev_short_ma = sma(closes[:-1], ma_short)[-1] if len(closes) >= 2 else None
            prev_long_ma = sma(closes[:-1], ma_long)[-1] if len(closes) >= 2 else None
            if short_ma is not None and long_ma is not None \
               and prev_short_ma is not None and prev_long_ma is not None:
                if prev_short_ma <= prev_long_ma and short_ma > long_ma:
                    buy_signal = True

            if not buy_signal and breakout_high_n > 0:
                highs_series = [r[2] for r in rows]
                if len(highs_series) >= breakout_high_n:
                    recent_high = max(highs_series[-breakout_high_n:])
                    if c > recent_high:
                        buy_signal = True

            if not buy_signal and change_threshold > 0:
                pc = pct_change(closes, change_lookback)[-1]
                if pc is not None and pc >= change_threshold:
                    buy_signal = True

            if not buy_signal:
                continue

            # 涨跌停买入检查
            if not passes_price_limit_for_buy(prev_close, o, h, lo, c):
                continue

            px = o
            if px <= 0:
                continue
            budget = cash * position_pct
            shares = buyable_lots(budget, px)
            if shares <= 0:
                continue
            cost = calc_buy_cost(px, shares)
            if cost > cash:
                continue
            cash -= cost
            positions[sym] = Position(sym, shares, px, d)

        # —— 3) 当日净值 —— #
        market_value = 0.0
        for sym, pos in positions.items():
            if sym in hist and hist[sym]:
                market_value += hist[sym][-1][4] * pos.shares
        equity_curve.append((today, round(cash + market_value, 2)))

        # 推进每个 symbol 的索引：如果今天有数据则 +1
        for sym in list(indices.keys()):
            if sym in today_quotes:
                indices[sym] += 1

    # 回测结束：按收盘价强制平仓（仅用于会计记账，不计入交易明细；如有持仓则以市价清算并写一条平仓记录便于统计）
    # 这里选择在回测期末不再追加额外交易记录，直接以最后一日的市值结算作为终值。
    return {
        "initial_cash": INITIAL_CASH,
        "trades": trade_log,
        "equity": equity_curve,
        "end_cash": cash,
        "open_market_value": sum(
            (hist.get(sym, [[None, 0, 0, 0, 0, 0]])[-1][4]) * pos.shares
            for sym, pos in positions.items()
            if sym in hist and hist[sym]
        ),
    }


# ======================== 统计 & 输出 ========================
def compute_stats(result):
    equity = result["equity"]
    trades = result["trades"]
    init = result["initial_cash"]
    end_value = result["end_cash"] + result["open_market_value"]

    if not equity:
        return {
            "total_return": 0.0, "annualized": 0.0, "max_drawdown": 0.0,
            "win_rate": 0.0, "profit_loss_ratio": 0.0, "trade_count": 0,
            "monthly": {}, "end_value": end_value,
        }

    total_return = (end_value - init) / init if init > 0 else 0.0
    days = (equity[-1][0] - equity[0][0]).days
    years = days / 365.25 if days > 0 else (len(equity) / 252.0 if equity else 0.0)
    if years <= 0:
        annualized = 0.0
    else:
        try:
            annualized = (end_value / init) ** (1 / years) - 1
        except Exception:
            annualized = 0.0

    # 最大回撤
    peak = -float("inf")
    max_dd = 0.0
    for _, v in equity:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

    # 胜率 & 盈亏比（按 pnl_net 算）
    pnls = [t["pnl_net"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    pl_ratio = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if wins else 0.0)

    # 每月收益表（按月末净值对比月初）
    monthly = {}
    # 按月初第一日净值与月末最后一日净值估算
    first_of_month = {}
    last_of_month = {}
    for d, v in equity:
        key = (d.year, d.month)
        if key not in first_of_month:
            first_of_month[key] = (d, v)
        last_of_month[key] = (d, v)
    last_val = None
    months_sorted = sorted(set(list(first_of_month.keys()) + list(last_of_month.keys())))
    # 以月末净值环比
    prev_end_val = init
    for key in months_sorted:
        if key not in last_of_month:
            continue
        ed, ev = last_of_month[key]
        ret = (ev - prev_end_val) / prev_end_val if prev_end_val > 0 else 0.0
        monthly[f"{key[0]:04d}-{key[1]:02d}"] = ret
        prev_end_val = ev

    return {
        "total_return": total_return,
        "annualized": annualized,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "profit_loss_ratio": pl_ratio,
        "trade_count": len(trades),
        "monthly": monthly,
        "end_value": end_value,
    }


def write_outputs(result, stats, out_dir, start_date, end_date):
    os.makedirs(out_dir, exist_ok=True)

    # 1) 交易明细.csv
    trades_path = os.path.join(out_dir, "交易明细.csv")
    with open(trades_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "buy_date", "sell_date", "buy_price", "sell_price",
                    "shares", "amount", "fee", "pnl", "pnl_net", "reason"])
        for t in result["trades"]:
            w.writerow([t["symbol"], t["buy_date"], t["sell_date"],
                        t["buy_price"], t["sell_price"], t["shares"],
                        t["amount"], t["fee"], t["pnl"], t["pnl_net"], t["reason"]])

    # 2) 资金曲线.csv
    eq_path = os.path.join(out_dir, "资金曲线.csv")
    with open(eq_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "equity"])
        for d, v in result["equity"]:
            w.writerow([d.isoformat(), v])

    # 3) 回测报告.md
    rep_path = os.path.join(out_dir, "回测报告.md")
    plr = stats["profit_loss_ratio"]
    plr_s = "inf" if plr == float("inf") else f"{plr:.2f}"
    lines = []
    lines.append("# A 股规则回测报告\n")
    lines.append(f"- 回测区间：{start_date.isoformat()} ~ {end_date.isoformat()}")
    lines.append(f"- 初始资金：{result['initial_cash']:.2f}")
    lines.append(f"- 终值（含未平仓市值）：{stats['end_value']:.2f}")
    lines.append("")
    lines.append("## 核心指标")
    lines.append(f"- 总收益：{stats['total_return']*100:.2f}%")
    lines.append(f"- 年化收益：{stats['annualized']*100:.2f}%")
    lines.append(f"- 最大回撤：{stats['max_drawdown']*100:.2f}%")
    lines.append(f"- 胜率：{stats['win_rate']*100:.2f}%")
    lines.append(f"- 盈亏比：{plr_s}")
    lines.append(f"- 交易次数：{stats['trade_count']}")
    lines.append("")
    lines.append("## 每月收益")
    lines.append("| 月份 | 收益率 |")
    lines.append("| --- | --- |")
    for k in sorted(stats["monthly"].keys()):
        lines.append(f"| {k} | {stats['monthly'][k]*100:.2f}% |")
    lines.append("")
    lines.append("## A 股约束说明")
    lines.append("- T+1：当日买入次日才能卖出。")
    lines.append("- 涨跌停 ±10%：触及当日买入/卖出不成交。")
    lines.append(f"- 手续费：买入 {COMMISSION_RATE*10000:.1f}‱ / 卖出 {COMMISSION_RATE*10000:.1f}‱ + 印花税 {STAMP_TAX_RATE*10000:.1f}‱。")
    lines.append("")
    lines.append("> 本工具仅做历史回测，不下单、不连接账户、不构成投资建议。")
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return trades_path, eq_path, rep_path


# ======================== 入口 ========================
def main():
    ap = argparse.ArgumentParser(description="A股个人交易规则回测工具（只研究，不下单）")
    ap.add_argument("--data", required=True, help="行情 CSV 目录")
    ap.add_argument("--rules", required=True, help="规则 JSON 文件路径")
    ap.add_argument("--start", required=True, help="起始日期 YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")
    ap.add_argument("--out", default="out", help="输出目录，默认 out")
    args = ap.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    with open(args.rules, "r", encoding="utf-8") as f:
        rules = json.load(f)

    data_by_symbol = load_csv_dir(args.data, start_date, end_date)
    if not data_by_symbol:
        print(f"[错误] 在 {args.data} 下未读取到任何 CSV 数据。", file=sys.stderr)
        return 2

    result = run_backtest(data_by_symbol, rules, start_date, end_date)
    stats = compute_stats(result)
    t_path, e_path, r_path = write_outputs(result, stats, args.out, start_date, end_date)

    print("== 回测完成 ==")
    print(f"交易次数: {stats['trade_count']}")
    print(f"总收益:   {stats['total_return']*100:.2f}%")
    print(f"最大回撤: {stats['max_drawdown']*100:.2f}%")
    print(f"输出:     {t_path} | {e_path} | {r_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())