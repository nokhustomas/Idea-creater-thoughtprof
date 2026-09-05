#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A share backtest tool. Read-only, no order placement."""
import argparse, csv, json, os, sys, math
from datetime import datetime, date

LIMIT_PCT = 0.10
FEE_BUY = 0.0003
FEE_SELL = 0.0003
TAX_SELL = 0.0005
LOT_SIZE = 100


def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d').date()


def load_csv_data(data_dir):
    stocks = {}
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith('.csv'):
            continue
        sym = os.path.splitext(fname)[0]
        rows = []
        with open(os.path.join(data_dir, fname), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    rows.append((r['date'].strip(), float(r['open']), float(r['high']),
                                 float(r['low']), float(r['close']), float(r.get('volume', 0) or 0)))
                except (KeyError, ValueError):
                    pass
        rows.sort(key=lambda x: x[0])
        stocks[sym] = rows
    return stocks


def sma(values, n):
    out = [None] * len(values)
    if n <= 0 or len(values) < n:
        return out
    s = sum(values[:n])
    out[n - 1] = s / n
    for i in range(n, len(values)):
        s += values[i] - values[i - n]
        out[i] = s / n
    return out


def eval_condition(cond, idx, closes, highs, lows):
    t = cond.get('type')
    if t == 'never':
        return False
    if t == 'always':
        return True
    if t == 'ma_cross':
        sn, ln = int(cond['short']), int(cond['long'])
        direction = cond.get('direction', 'golden')
        if idx < max(sn, ln):
            return False
        ms = sma(closes[:idx + 1], sn)
        ml = sma(closes[:idx + 1], ln)
        if ms[-1] is None or ml[-1] is None:
            return False
        if direction == 'golden':
            return ms[-2] <= ml[-2] and ms[-1] > ml[-1]
        return ms[-2] >= ml[-2] and ms[-1] < ml[-1]
    if t == 'breakout':
        w = int(cond['window'])
        d = cond.get('direction', 'high')
        if idx < w:
            return False
        seg = highs[idx - w:idx] if d == 'high' else lows[idx - w:idx]
        if not seg:
            return False
        ref = max(seg) if d == 'high' else min(seg)
        return closes[idx] > ref if d == 'high' else closes[idx] < ref
    if t == 'change_threshold':
        th = float(cond.get('threshold_pct', 0))
        d = cond.get('direction', 'above')
        if idx < 1 or closes[idx - 1] <= 0:
            return False
        chg = closes[idx] / closes[idx - 1] - 1.0
        return chg > th if d == 'above' else chg < th
    return False


def all_conds(conds, idx, closes, highs, lows):
    if not conds:
        return False
    for c in conds:
        if not eval_condition(c, idx, closes, highs, lows):
            return False
    return True


def is_limit(prev_close, high, low, close):
    if prev_close <= 0:
        return None
    if close >= prev_close * (1 + LIMIT_PCT) - 1e-6:
        return 'up'
    if close <= prev_close * (1 - LIMIT_PCT) + 1e-6:
        return 'down'
    return None


def run_backtest(data_dir, rules, start_date, end_date):
    start = parse_date(start_date)
    end = parse_date(end_date)
    stocks = load_csv_data(data_dir)
    if not stocks:
        print('no csv in ' + data_dir, file=sys.stderr)
        return None
    si = {}
    for sym, rows in stocks.items():
        dates = [r[0] for r in rows]
        opens = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        closes = [r[4] for r in rows]
        vols = [r[5] for r in rows]
        si[sym] = {'dates': dates, 'opens': opens, 'highs': highs,
                   'lows': lows, 'closes': closes, 'vols': vols,
                   'dmap': {d: i for i, d in enumerate(dates)}}
    all_dates = sorted({parse_date(d) for s in si.values() for d in s['dates']
                        if start <= parse_date(d) <= end})
    if not all_dates:
        print('no data in range', file=sys.stderr)
        return None

    init_cap = float(rules.get('initial_capital', 1000000))
    pos_pct = float(rules.get('position_size_pct', 0.2))
    max_pos = int(rules.get('max_positions', 3))
    sl_pct = float(rules.get('stop_loss_pct', 0.08))
    tp_pct = float(rules.get('take_profit_pct', 0.15))
    max_hold = int(rules.get('max_hold_days', 20))
    buy_conds = rules.get('buy_conditions', [])
    sell_conds = rules.get('sell_conditions', [])

    cash = init_cap
    positions = {}  # sym -> {shares, cost_price, buy_date, accum_fee}
    trades = []
    daily = []
    pending_buys = []
    pending_sells = []

    def fees(price, shares, side):
        amt = price * shares
        if side == 'buy':
            return amt * FEE_BUY, 0.0
        return amt * FEE_SELL, amt * TAX_SELL

    for i, today in enumerate(all_dates):
        ts = today.isoformat()

        # Execute pending T+1 orders
        if i > 0:
            new_ps = []
            for sym, reason in pending_sells:
                s = si[sym]
                idx = s['dmap'].get(ts)
                if idx is None or sym not in positions:
                    continue
                p_prev = s['closes'][idx - 1] if idx > 0 else s['closes'][0]
                lim = is_limit(p_prev, s['highs'][idx], s['lows'][idx], s['closes'][idx])
                if lim == 'down':
                    new_ps.append((sym, reason))
                    continue
                pos = positions[sym]
                price = s['opens'][idx]
                shares = pos['shares']
                f, t = fees(price, shares, 'sell')
                proceeds = price * shares - f - t
                pnl = proceeds - pos['cost_price'] * shares - pos['accum_fee']
                cash += proceeds
                del positions[sym]
                trades.append({'symbol': sym, 'date': ts, 'side': 'sell',
                               'price': round(price, 4), 'shares': shares,
                               'amount': round(price * shares, 4),
                               'fee': round(f, 4), 'tax': round(t, 4),
                               'pnl': round(pnl, 4), 'reason': reason})
            pending_sells = new_ps

            new_pb = []
            for (sym,) in pending_buys:
                s = si[sym]
                idx = s['dmap'].get(ts)
                if idx is None or sym in positions or len(positions) >= max_pos:
                    continue
                p_prev = s['closes'][idx - 1] if idx > 0 else s['closes'][0]
                lim = is_limit(p_prev, s['highs'][idx], s['lows'][idx], s['closes'][idx])
                if lim == 'up':
                    new_pb.append((sym,))
                    continue
                price = s['opens'][idx]
                alloc = cash * pos_pct
                shares = int(alloc / price / LOT_SIZE) * LOT_SIZE
                if shares <= 0:
                    continue
                f, t = fees(price, shares, 'buy')
                cost = price * shares + f + t
                if cost > cash:
                    continue
                cash -= cost
                positions[sym] = {'shares': shares, 'cost_price': price,
                                  'buy_date': today, 'accum_fee': f + t}
                trades.append({'symbol': sym, 'date': ts, 'side': 'buy',
                               'price': round(price, 4), 'shares': shares,
                               'amount': round(price * shares, 4),
                               'fee': round(f, 4), 'tax': round(t, 4),
                               'pnl': 0.0, 'reason': 'signal'})
            pending_buys = new_pb

        # Intraday stop loss / take profit
        for sym in list(positions.keys()):
            s = si[sym]
            idx = s['dmap'].get(ts)
            if idx is None:
                continue
            pos = positions[sym]
            cost = pos['cost_price']
            if tp_pct > 0 and s['highs'][idx] >= cost * (1 + tp_pct):
                price = cost * (1 + tp_pct)
                shares = pos['shares']
                f, t = fees(price, shares, 'sell')
                proceeds = price * shares - f - t
                pnl = proceeds - cost * shares - pos['accum_fee']
                cash += proceeds
                del positions[sym]
                trades.append({'symbol': sym, 'date': ts, 'side': 'sell',
                               'price': round(price, 4), 'shares': shares,
                               'amount': round(price * shares, 4),
                               'fee': round(f, 4), 'tax': round(t, 4),
                               'pnl': round(pnl, 4), 'reason': 'take_profit'})
                continue
            if sl_pct > 0 and s['lows'][idx] <= cost * (1 - sl_pct):
                price = cost * (1 - sl_pct)
                shares = pos['shares']
                f, t = fees(price, shares, 'sell')
                proceeds = price * shares - f - t
                pnl = proceeds - cost * shares - pos['accum_fee']
                cash += proceeds
                del positions[sym]
                trades.append({'symbol': sym, 'date': ts, 'side': 'sell',
                               'price': round(price, 4), 'shares': shares,
                               'amount': round(price * shares, 4),
                               'fee': round(f, 4), 'tax': round(t, 4),
                               'pnl': round(pnl, 4), 'reason': 'stop_loss'})

        # Max hold
        if max_hold > 0:
            for sym in list(positions.keys()):
                if (today - positions[sym]['buy_date']).days >= max_hold:
                    pending_sells.append((sym, 'max_hold'))

        # Generate signals (end of day)
        for sym, s in si.items():
            idx = s['dmap'].get(ts)
            if idx is None:
                continue
            if sym not in positions:
                if all_conds(buy_conds, idx, s['closes'], s['highs'], s['lows']):
                    pending_buys.append((sym,))
            else:
                if all_conds(sell_conds, idx, s['closes'], s['highs'], s['lows']):
                    pending_sells.append((sym, 'signal'))

        # End of day mark-to-market
        equity = cash
        for sym, pos in positions.items():
            s = si[sym]
            idx = s['dmap'].get(ts)
            if idx is not None:
                equity += pos['shares'] * s['closes'][idx]
        daily.append((ts, round(equity, 4)))

    # Force close remaining at last day's close
    if all_dates:
        last = all_dates[-1].isoformat()
        for sym in list(positions.keys()):
            s = si[sym]
            idx = s['dmap'].get(last)
            if idx is None:
                continue
            pos = positions[sym]
            price = s['closes'][idx]
            shares = pos['shares']
            f, t = fees(price, shares, 'sell')
            proceeds = price * shares - f - t
            pnl = proceeds - pos['cost_price'] * shares - pos['accum_fee']
            cash += proceeds
            trades.append({'symbol': sym, 'date': last, 'side': 'sell',
                           'price': round(price, 4), 'shares': shares,
                           'amount': round(price * shares, 4),
                           'fee': round(f, 4), 'tax': round(t, 4),
                           'pnl': round(pnl, 4), 'reason': 'force_close'})
            del positions[sym]
        if positions:
            for sym, pos in positions.items():
                equity += pos['shares'] * pos['cost_price']
            daily[-1] = (daily[-1][0], round(equity, 4))

    return {'daily': daily, 'trades': trades, 'initial_capital': init_cap,
            'start_date': start_date, 'end_date': end_date}


def calc_stats(result):
    daily = result['daily']
    trades = result['trades']
    init_cap = result['initial_capital']
    if not daily:
        return {'total_return': 0, 'annual_return': 0, 'max_drawdown': 0,
                'win_rate': 0, 'profit_loss_ratio': 0, 'n_trades': 0,
                'avg_pnl': 0, 'monthly': {}}
    start_d = parse_date(daily[0][0])
    end_d = parse_date(daily[-1][0])
    days = (end_d - start_d).days or 1
    final_equity = daily[-1][1]
    total_ret = final_equity / init_cap - 1.0
    annual_ret = (1 + total_ret) ** (365.0 / days) - 1.0

    peak = daily[0][1]
    mdd = 0
    for d, eq in daily:
        if eq > peak:
            peak = eq
        dd = peak / eq - 1.0 if eq > 0 else 0
        if dd > mdd:
            mdd = dd

    # Pair buys with sells for pnl
    buy_map = {}
    pnls = []
    wins = 0
    losses = 0
    sum_win = 0
    sum_loss = 0
    for tr in trades:
        if tr['side'] == 'buy':
            buy_map.setdefault(tr['symbol'], []).append(tr)
        else:
            bs = buy_map.get(tr['symbol'], [])
            if bs:
                b = bs.pop(0)
                pnl = tr['pnl']
                pnls.append(pnl)
                if pnl > 0:
                    wins += 1
                    sum_win += pnl
                elif pnl < 0:
                    losses += 1
                    sum_loss += -pnl
    n_trades = len(pnls)
    win_rate = wins / n_trades if n_trades else 0
    avg_win = sum_win / wins if wins else 0
    avg_loss = sum_loss / losses if losses else 0
    pl_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    # Monthly
    monthly = {}
    for d, eq in daily:
        ym = d[:7]
        monthly[ym] = eq
    monthly_ret = {}
    prev = init_cap
    for ym in sorted(monthly.keys()):
        monthly_ret[ym] = monthly[ym] / prev - 1.0
        prev = monthly[ym]

    return {'total_return': total_ret, 'annual_return': annual_ret,
            'max_drawdown': mdd, 'win_rate': win_rate,
            'profit_loss_ratio': pl_ratio, 'n_trades': n_trades,
            'avg_pnl': sum(pnls) / n_trades if n_trades else 0,
            'final_equity': final_equity, 'monthly': monthly_ret}


def write_outputs(result, stats):
    out = 'out'
    os.makedirs(out, exist_ok=True)
    # report
    lines = []
    lines.append('# A 股回测报告')
    lines.append('')
    lines.append('本工具不下单、不连接账户、不构成投资建议。')
    lines.append('')
    lines.append('- 初始资金: %.2f' % result['initial_capital'])
    lines.append('- 区间: %s ~ %s' % (result['start_date'], result['end_date']))
    lines.append('- 最终净值: %.2f' % stats['final_equity'])
    lines.append('- 总收益: %.2f%%' % (stats['total_return'] * 100))
    lines.append('- 年化收益: %.2f%%' % (stats['annual_return'] * 100))
    lines.append('- 最大回撤: %.2f%%' % (stats['max_drawdown'] * 100))
    lines.append('- 胜率: %.2f%%' % (stats['win_rate'] * 100))
    lines.append('- 盈亏比: %.2f' % stats['profit_loss_ratio'])
    lines.append('- 交易次数: %d' % stats['n_trades'])
    lines.append('- 平均盈亏: %.2f' % stats['avg_pnl'])
    lines.append('')
    lines.append('## 每月收益')
    lines.append('')
    lines.append('| 月份 | 月收益 |')
    lines.append('| --- | --- |')
    for ym in sorted(stats['monthly'].keys()):
        lines.append('| %s | %.2f%% |' % (ym, stats['monthly'][ym] * 100))
    with open(os.path.join(out, '回测报告.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    # trades
    with open(os.path.join(out, '交易明细.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['symbol', 'date', 'side', 'price',
                                           'shares', 'amount', 'fee', 'tax',
                                           'pnl', 'reason'])
        w.writeheader()
        for tr in result['trades']:
            w.writerow(tr)

    # equity
    with open(os.path.join(out, '资金曲线.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'equity'])
        for d, eq in result['daily']:
            w.writerow([d, eq])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--rules', required=True)
    ap.add_argument('--start', required=True)
    ap.add_argument('--end', required=True)
    args = ap.parse_args()
    with open(args.rules, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    result = run_backtest(args.data, rules, args.start, args.end)
    if result is None:
        sys.exit(1)
    stats = calc_stats(result)
    write_outputs(result, stats)
    print('done: total=%.2f%% trades=%d' % (stats['total_return'] * 100, stats['n_trades']))
    sys.exit(0)


if __name__ == '__main__':
    main()
