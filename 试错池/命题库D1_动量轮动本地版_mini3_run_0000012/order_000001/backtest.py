#!/usr/bin/env python3
"""
回测引擎：从 2023-12-01 起 30 个交易日 T+1 回测，
每交易日末计算动量，次日开盘以前一日收盘价调仓。
支持 --start_date 参数覆盖起始日。
"""
import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd

from load_data import load_all, DEFAULT_DATA_DIR, DEFAULT_UNIVERSE
from momentum import compute_momentum
from rotator import select_top_with_fallback
from metrics import max_drawdown, turnover_rate, fee_adjusted_return

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('backtest')


def run_backtest(df: pd.DataFrame, dates: list[str], start_date: str,
                 days: int = 30, top_n: int = 5, window: int = 20,
                 fee_rate: float = 0.0003) -> dict:
    """
    T+1 回测：
    - 在 date_i 收盘后计算动量（基于 date_i 及之前数据）
    - 在 date_{i+1} 开盘时按 date_i 的动量选 TopN 等权调仓
    - 用 date_{i+1} 的 open 作为成交价（近似：此处数据未提供完整 open 在所有日，故以 preclose/close 近似）
    - 由于本数据每只股票每日有 open，本函数用 open 作为调仓价
    返回 {nav, nav_fee, turnover_per_day, dates, holdings}
    """
    # 计算动量
    mom = compute_momentum(df, window=window)
    # 索引加速
    by_date = {d: g for d, g in mom.groupby('date')}
    # 收盘价 / 开盘价 pivot
    close_pivot = df.pivot(index='date', columns='code', values='close').sort_index()
    open_pivot = df.pivot(index='date', columns='code', values='open').sort_index()

    # 选窗口
    if start_date not in dates:
        cand = [d for d in dates if d >= start_date]
        if not cand:
            raise ValueError(f'no date >= {start_date}')
        s = cand[0]
    else:
        s = start_date
    sidx = dates.index(s)
    eidx = min(sidx + days + 1, len(dates))  # 多取 1 日用于 T+1 调仓
    win = dates[sidx:eidx]
    if len(win) < 2:
        raise ValueError('window too short')

    # 资金：初始 1.0
    cash = 1.0
    holdings = {}  # code -> shares
    n_trade_days = len(win) - 1  # 实际收益日
    nav = np.empty(n_trade_days + 1, dtype=float)
    nav[0] = 1.0
    turnover_per_day = np.zeros(n_trade_days + 1, dtype=float)
    daily_records = []  # (date, nav)
    holding_records = []  # (date, code, weight)

    # 用 T+1 逻辑：day 0 (date=win[0]) 是起点；day i (date=win[i]) 的开盘用于 day i-1 的调仓
    # 第 i 日的收益：用 win[i] 收盘 / win[i-1] 收盘 - 1，应用到当前持仓
    for i in range(1, n_trade_days + 1):
        today = win[i]
        prev = win[i - 1]
        # 在 prev 日末计算动量
        if prev in by_date:
            sel = select_top_with_fallback(mom, prev, dates, top_n=top_n)
        else:
            sel = pd.DataFrame()
        target_codes = sel['code'].tolist() if len(sel) > 0 else []

        # 调仓：用 today 的 open 作为成交价
        if i == 1:
            # 首日建仓：cash=1.0
            if target_codes:
                per = cash / len(target_codes)
                new_holdings = {}
                for c in target_codes:
                    px = open_pivot.at[today, c] if (today in open_pivot.index and c in open_pivot.columns) else np.nan
                    if pd.notna(px) and px > 0:
                        sh = per / px
                        new_holdings[c] = sh
                # 卖出原 holdings（旧为空，turnover = 1.0 全换）
                turnover_per_day[i] = 1.0
                holdings = new_holdings
            else:
                holdings = {}
        else:
            # 调仓：先卖出不在 target 的，买入 target 中未持仓的，按等权再平衡
            old_codes = set(holdings.keys())
            tgt = set(target_codes)
            sell_codes = old_codes - tgt
            buy_codes = tgt - old_codes
            keep_codes = old_codes & tgt
            today_close_row = close_pivot.loc[prev]  # 卖出按昨收近似（更接近开盘）
            today_open_row = open_pivot.loc[today] if today in open_pivot.index else None
            # 卖出所得现金
            sell_cash = 0.0
            for c in sell_codes:
                sh = holdings.pop(c, 0)
                px = today_close_row[c] if c in today_close_row.index else np.nan
                if pd.notna(px) and px > 0:
                    sell_cash += sh * px
            # 当前持仓市值（按今日开盘估价）
            hold_value = sell_cash
            for c in keep_codes:
                sh = holdings.get(c, 0)
                px = today_open_row[c] if (today_open_row is not None and c in today_open_row.index) else np.nan
                if pd.notna(px) and px > 0:
                    hold_value += sh * px
                else:
                    px2 = today_close_row[c] if c in today_close_row.index else np.nan
                    if pd.notna(px2) and px2 > 0:
                        hold_value += sh * px2
            # 计算目标等权重
            n_target = len(target_codes)
            if n_target > 0 and hold_value > 0:
                per_target = hold_value / n_target
                for c in buy_codes:
                    px = today_open_row[c] if (today_open_row is not None and c in today_open_row.index) else np.nan
                    if pd.notna(px) and px > 0:
                        sh_buy = per_target / px
                        holdings[c] = holdings.get(c, 0) + sh_buy
                # 等权再平衡：keep 的也要调整到 per_target
                for c in keep_codes:
                    sh = holdings.get(c, 0)
                    px = today_open_row[c] if (today_open_row is not None and c in today_open_row.index) else np.nan
                    if pd.notna(px) and px > 0:
                        target_sh = per_target / px
                        holdings[c] = target_sh
                # turnover：调整量 / 总资产
                if hold_value > 0:
                    turnover_per_day[i] = min(1.0, (len(sell_codes) + len(buy_codes)) / max(1, n_target))
                else:
                    turnover_per_day[i] = 1.0

        # 计算今日末净值（用今日收盘）
        today_close_row = close_pivot.loc[today] if today in close_pivot.index else None
        port_value = 0.0
        for c, sh in holdings.items():
            if today_close_row is not None and c in today_close_row.index:
                px = today_close_row[c]
                if pd.notna(px) and px > 0:
                    port_value += sh * px
        if port_value <= 0:
            port_value = cash  # 兜底
        nav[i] = port_value
        cash = port_value
        daily_records.append((today, port_value))
        for c, sh in holdings.items():
            w = sh * (today_close_row[c] if (today_close_row is not None and c in today_close_row.index) else 0) / port_value if port_value > 0 else 0
            holding_records.append((today, c, float(w)))

    # 完整 30 日窗口（含起点）的净值序列
    full_dates = [win[0]] + [d for d, _ in daily_records]
    # 费用后
    fee_res = fee_adjusted_return(nav, turnover_per_day, fee_rate=fee_rate)
    return {
        'dates': full_dates,
        'nav': nav,
        'nav_fee': fee_res['nav_fee'],
        'turnover_per_day': turnover_per_day,
        'turnover_total': turnover_rate(turnover_per_day),
        'max_drawdown': max_drawdown(nav),
        'return_after_fee': fee_res['total_return_fee'],
        'fee_paid': fee_res['fee_paid'],
        'holdings': holding_records,
        'start_date': win[0],
        'end_date': win[-1],
        'n_days': len(full_dates) - 1,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--start_date', default='20231201')
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--top_n', type=int, default=5)
    ap.add_argument('--window', type=int, default=20)
    ap.add_argument('--fee_rate', type=float, default=0.0003)
    args = ap.parse_args()

    try:
        big, loaded, missing = load_all(args.data_dir, args.universe)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    dates = sorted(big['date'].unique())
    try:
        res = run_backtest(big, dates, args.start_date, days=args.days,
                           top_n=args.top_n, window=args.window, fee_rate=args.fee_rate)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    print(f'window: {res["start_date"]} ~ {res["end_date"]} n_days={res["n_days"]} codes={len(loaded)}')
    print(f'final_nav: {res["nav"][-1]:.6f}')
    print(f'return: {res["nav"][-1] - 1.0:.6f}')
    print(f'max_drawdown: {res["max_drawdown"]:.6f}')
    print(f'turnover: {res["turnover_total"]:.6f}')
    print(f'return_after_fee: {res["return_after_fee"]:.6f}')
    # 输出净值曲线（紧凑）
    print('nav_curve:')
    for d, v in zip(res['dates'], res['nav']):
        print(f'  {d}  {v:.6f}')


if __name__ == '__main__':
    main()