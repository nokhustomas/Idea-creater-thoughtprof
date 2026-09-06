#!/usr/bin/env python3
"""
动量计算模块：计算20日动量（收益率）= 当前收盘价/20日前收盘价 - 1
停牌日用前一日收盘价向前回溯；不足20日返回NaN
"""
import os
import sys
import argparse
import logging
import pandas as pd
import numpy as np

from load_data import load_all, DEFAULT_DATA_DIR, DEFAULT_UNIVERSE

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('momentum')


def compute_momentum(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """对每只股票计算 window 日动量。返回带列 momentum 的 DataFrame。"""
    out = df.copy().sort_values(['code', 'date']).reset_index(drop=True)
    out['momentum'] = np.nan
    for code, g in out.groupby('code', sort=False):
        idx = g.index
        close = g['close'].astype(float)
        # 20 日动量：close[t]/close[t-20] - 1
        m = close / close.shift(window) - 1.0
        out.loc[idx, 'momentum'] = m.values
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--window', type=int, default=20)
    ap.add_argument('--date', default=None, help='指定查询某日动量摘要')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    try:
        big, loaded, missing = load_all(args.data_dir, args.universe)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    mom = compute_momentum(big, args.window)
    print(f'loaded: {len(loaded)} codes, missing: {len(missing)}')
    print(f'momentum: rows={len(mom)}, non_nan={mom["momentum"].notna().sum()}, nan={mom["momentum"].isna().sum()}')
    if args.date:
        sub = mom[mom['date'] == args.date][['code', 'close', 'momentum']].sort_values('momentum', ascending=False)
        print(f'--- momentum @ {args.date} ---')
        print(sub.to_string(index=False))


if __name__ == '__main__':
    main()