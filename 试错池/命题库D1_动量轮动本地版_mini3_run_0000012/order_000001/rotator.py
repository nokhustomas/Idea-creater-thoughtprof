#!/usr/bin/env python3
"""
轮动选股模块：按20日动量排序选取Top N只（默认5只，参数可覆盖），等权持仓，排除动量值为NaN的股票。
学术依据：Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers"
业界依据：A股动量/反转实证见王永宏、赵学军(2001)《中国股市"惯性策略"和"反转策略"的实证分析》
"""
import os
import sys
import argparse
import logging
import pandas as pd
import numpy as np

from load_data import load_all, DEFAULT_DATA_DIR, DEFAULT_UNIVERSE
from momentum import compute_momentum

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('rotator')


def select_top(df_mom: pd.DataFrame, asof_date: str, top_n: int = 5) -> pd.DataFrame:
    """按 asof_date 当日动量选 Top N；排除 NaN。"""
    sub = df_mom[df_mom['date'] == asof_date].copy()
    sub = sub[sub['momentum'].notna()]
    sub = sub.sort_values('momentum', ascending=False)
    selected = sub.head(top_n)
    return selected.reset_index(drop=True)


def select_top_with_fallback(df_mom: pd.DataFrame, asof_date: str,
                              available_dates: list[str], top_n: int = 5) -> pd.DataFrame:
    """若当日无有效动量（例如前20日不足），回溯到最近一个有≥top_n个非NaN的交易日"""
    sub = select_top(df_mom, asof_date, top_n)
    if len(sub) >= top_n:
        return sub
    # 回溯
    for d in available_dates:
        if d > asof_date:
            break
        sub2 = select_top(df_mom, d, top_n)
        if len(sub2) >= top_n:
            log.warning('rotator fallback: asof=%s -> use %s', asof_date, d)
            return sub2
    # 退而求其次，返回能拿到的全部
    log.warning('rotator fallback partial: asof=%s got=%d', asof_date, len(sub))
    return sub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--window', type=int, default=20)
    ap.add_argument('--top_n', type=int, default=5)
    ap.add_argument('--date', default='20231201')
    args = ap.parse_args()

    try:
        big, loaded, missing = load_all(args.data_dir, args.universe)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    mom = compute_momentum(big, args.window)
    dates = sorted(mom['date'].unique())
    if args.date not in dates:
        # 取 ≤ date 的最近一天
        cand = [d for d in dates if d <= args.date]
        if not cand:
            print(f'Error: no date <= {args.date}', file=sys.stderr)
            sys.exit(1)
        actual = cand[-1]
        log.warning('date %s not in trading days, use %s', args.date, actual)
    else:
        actual = args.date
    sel = select_top_with_fallback(mom, actual, dates, args.top_n)
    print(f'--- rotation @ {actual} top_n={args.top_n} ---')
    print(f'selected count: {len(sel)}')
    if len(sel) == 0:
        print('0 holding')
        return
    print('holding:')
    for _, r in sel.iterrows():
        print(f"  {r['code']}  momentum={r['momentum']:.6f}  close={r['close']}")


if __name__ == '__main__':
    main()