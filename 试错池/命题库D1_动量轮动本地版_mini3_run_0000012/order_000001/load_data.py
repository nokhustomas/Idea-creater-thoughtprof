#!/usr/bin/env python3
"""
数据加载模块：读取本地50只A股2023年日线csv和universe.json，
构建日线DataFrame，处理停牌日向前回溯收盘价，缺失文件时仅加载存在的文件并记录日志。
"""
import os
import sys
import json
import argparse
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('load_data')

DEFAULT_DATA_DIR = '/opt/tuijinqi/sandbox/data/bars'
DEFAULT_UNIVERSE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'universe.json')


def load_universe(universe_path: str) -> list:
    with open(universe_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    codes = cfg['codes'] if isinstance(cfg, dict) and 'codes' in cfg else cfg
    return list(codes)


def load_one(code: str, data_dir: str) -> pd.DataFrame | None:
    fp = os.path.join(data_dir, f'{code}.csv')
    if not os.path.exists(fp):
        log.warning('缺失文件: %s (code=%s)', fp, code)
        return None
    try:
        df = pd.read_csv(fp)
    except Exception as e:
        log.error('读取失败: %s err=%s', fp, e)
        return None
    # 列名规范化
    rename = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ('date', '日期'):
            rename[c] = 'date'
        elif cl in ('code', '代码', '股票代码'):
            rename[c] = 'code'
        elif cl in ('open', '开盘'):
            rename[c] = 'open'
        elif cl in ('high', '最高'):
            rename[c] = 'high'
        elif cl in ('low', '最低'):
            rename[c] = 'low'
        elif cl in ('close', '收盘', '收盘价'):
            rename[c] = 'close'
        elif cl in ('preclose', '昨收', '前收'):
            rename[c] = 'preclose'
        elif cl in ('volume', '成交量'):
            rename[c] = 'volume'
        elif cl in ('amount', '成交额'):
            rename[c] = 'amount'
        elif cl in ('pctchg', '涨跌幅'):
            rename[c] = 'pctChg'
    df = df.rename(columns=rename)
    need = ['date', 'open', 'high', 'low', 'close']
    for col in need:
        if col not in df.columns:
            log.error('列缺失: %s in %s', col, fp)
            return None
    if 'preclose' not in df.columns:
        df['preclose'] = df['close'].shift(1)
    if 'volume' not in df.columns:
        df['volume'] = 0
    if 'amount' not in df.columns:
        df['amount'] = 0.0
    if 'pctChg' not in df.columns:
        df['pctChg'] = df['close'].pct_change() * 100
    df['code'] = code
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
    df = df[['date', 'code', 'open', 'high', 'low', 'close', 'preclose', 'volume', 'amount', 'pctChg']]
    df = df.sort_values('date').reset_index(drop=True)
    return df


def forward_fill_suspend(df: pd.DataFrame) -> pd.DataFrame:
    """停牌日用前一日收盘价向前回溯：close/preclose 用前值填充，open/high/low 同步"""
    df = df.copy()
    for col in ['close', 'preclose', 'open', 'high', 'low']:
        df[col] = df[col].ffill()
    df['volume'] = df['volume'].fillna(0)
    df['amount'] = df['amount'].fillna(0.0)
    df['pctChg'] = df['pctChg'].fillna(0.0)
    return df


def load_all(data_dir: str = DEFAULT_DATA_DIR,
             universe_path: str = DEFAULT_UNIVERSE) -> tuple[pd.DataFrame, list, list]:
    codes = load_universe(universe_path)
    log.info('universe size=%d', len(codes))
    frames = []
    loaded = []
    missing = []
    for code in codes:
        df = load_one(code, data_dir)
        if df is None:
            missing.append(code)
            continue
        df = forward_fill_suspend(df)
        frames.append(df)
        loaded.append(code)
    if not frames:
        raise RuntimeError('未加载到任何股票数据，请检查数据目录')
    big = pd.concat(frames, ignore_index=True).sort_values(['date', 'code']).reset_index(drop=True)
    return big, loaded, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    try:
        big, loaded, missing = load_all(args.data_dir, args.universe)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    dates = sorted(big['date'].unique())
    print(f'shape: {big.shape}')
    print(f'dates: {len(dates)} from {dates[0]} to {dates[-1]}')
    print(f'loaded: {len(loaded)} codes')
    if missing:
        print(f'missing: {len(missing)} codes -> {missing[:10]}{"..." if len(missing)>10 else ""}')


if __name__ == '__main__':
    main()