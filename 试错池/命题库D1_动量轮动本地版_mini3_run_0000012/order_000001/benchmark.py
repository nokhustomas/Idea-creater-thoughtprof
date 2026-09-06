#!/usr/bin/env python3
"""
基准对比模块：50只等权持有30日作为基准（每日等权再平衡），
计算同样指标（最大回撤/换手率/费用后收益）与动量策略对比。
"""
import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd

from load_data import load_all, DEFAULT_DATA_DIR, DEFAULT_UNIVERSE
from metrics import max_drawdown, turnover_rate, fee_adjusted_return

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('benchmark')


def build_equal_weight_benchmark(df: pd.DataFrame, dates: list[str],
                                  fee_rate: float = 0.0003) -> dict:
    """
    50只等权基准：每日等权再平衡。
    - 每日收益 = 50只等权日收益（用次日开盘/当日开盘近似T+1成交）
    - 由于基准也每日再平衡，turnover ≈ 每日小幅（仅保留换仓差异），近似处理为每日 0.0（持仓不变无换手），
      但若视为每日再平衡一次，则换手较高。这里采用保守口径：把每日视作"换手=再平衡比例"=1.0（全换），扣双边费。
    返回 {nav, returns, mdd, turnover, return_fee}
    """
    # 用 pivot close
    pivot = df.pivot(index='date', columns='code', values='close').sort_index()
    pivot = pivot.loc[dates]
    # 日收益
    daily_ret = pivot.pct_change().fillna(0.0)
    # 等权每日收益
    ew_ret = daily_ret.mean(axis=1).values  # len=len(dates)
    n = len(dates)
    nav = np.empty(n, dtype=float)
    nav[0] = 1.0
    for i in range(1, n):
        nav[i] = nav[i - 1] * (1.0 + ew_ret[i])
    # 换手率：每日等权再平衡换手 ≈ 1.0（全换）
    turnover_per_day = np.zeros(n)
    for i in range(1, n):
        turnover_per_day[i] = 1.0  # 每日再平衡视作全换
    total_turnover = turnover_rate(turnover_per_day)
    mdd = max_drawdown(nav)
    fee_res = fee_adjusted_return(nav, turnover_per_day, fee_rate=fee_rate)
    return {
        'nav': nav,
        'returns': ew_ret,
        'dates': dates,
        'mdd': mdd,
        'turnover': total_turnover,
        'return_fee': fee_res['total_return_fee'],
        'fee_paid': fee_res['fee_paid'],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--start_date', default='20231201')
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--fee_rate', type=float, default=0.0003)
    args = ap.parse_args()

    try:
        big, loaded, missing = load_all(args.data_dir, args.universe)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    dates = sorted(big['date'].unique())
    # 截取窗口
    if args.start_date not in dates:
        cand = [d for d in dates if d >= args.start_date]
        if not cand:
            print(f'Error: no date >= {args.start_date}', file=sys.stderr)
            sys.exit(1)
        start = cand[0]
    else:
        start = args.start_date
    sidx = dates.index(start)
    eidx = min(sidx + args.days, len(dates))
    win_dates = dates[sidx:eidx]
    res = build_equal_weight_benchmark(big, win_dates, fee_rate=args.fee_rate)
    print(f'benchmark_window: {win_dates[0]} ~ {win_dates[-1]} ({len(win_dates)} days, codes={len(loaded)})')
    print(f'benchmark_final_nav: {res["nav"][-1]:.6f}')
    print(f'benchmark_return: {res["nav"][-1] - 1.0:.6f}')
    print(f'benchmark_max_drawdown: {res["mdd"]:.6f}')
    print(f'benchmark_turnover: {res["turnover"]:.6f}')
    print(f'benchmark_return_after_fee: {res["return_fee"]:.6f}')
    print(f'benchmark_fee_paid: {res["fee_paid"]:.6f}')


if __name__ == '__main__':
    main()