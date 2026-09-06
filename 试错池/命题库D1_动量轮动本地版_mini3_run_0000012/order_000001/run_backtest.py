#!/usr/bin/env python3
"""
主脚本：整合以上模块，输出完整回测报告（净值曲线、四项指标、基准对比）。
支持 --days / --start_date / --top_n 参数。

用法：
    python3 run_backtest.py --days 30
    python3 run_backtest.py --days 30 --start_date 20231201 --top_n 5
"""
import os
import sys
import argparse
import logging
import json
import numpy as np
import pandas as pd

from load_data import load_all, DEFAULT_DATA_DIR, DEFAULT_UNIVERSE
from backtest import run_backtest
from benchmark import build_equal_weight_benchmark
from metrics import max_drawdown, turnover_rate, fee_adjusted_return

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('run_backtest')


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', default=DEFAULT_DATA_DIR)
    ap.add_argument('--universe', default=DEFAULT_UNIVERSE)
    ap.add_argument('--days', type=int, default=30)
    ap.add_argument('--start_date', default='20231201')
    ap.add_argument('--top_n', type=int, default=5)
    ap.add_argument('--window', type=int, default=20)
    ap.add_argument('--fee_rate', type=float, default=0.0003)
    ap.add_argument('--out_dir', default='./output')
    return ap.parse_args()


def save_nav_curve(res: dict, bench: dict, out_path: str):
    n = min(len(res['dates']), len(res['nav']))
    rows = []
    for i in range(n):
        rows.append({
            'date': res['dates'][i],
            'nav': float(res['nav'][i]),
            'nav_fee': float(res['nav_fee'][i]),
        })
    df = pd.DataFrame(rows)
    # 基准对齐日期
    bm_rows = []
    for i, d in enumerate(bench['dates']):
        bm_rows.append({
            'date': d,
            'benchmark_nav': float(bench['nav'][i]),
        })
    bm_df = pd.DataFrame(bm_rows)
    merged = df.merge(bm_df, on='date', how='outer').sort_values('date').reset_index(drop=True)
    merged.to_csv(out_path, index=False, encoding='utf-8-sig')
    return merged


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    # 1. 加载数据
    big, loaded, missing = load_all(args.data_dir, args.universe)
    dates = sorted(big['date'].unique())
    print(f'[load] loaded={len(loaded)} missing={len(missing)} dates={len(dates)}')

    # 2. 动量策略回测
    res = run_backtest(big, dates, args.start_date, days=args.days,
                       top_n=args.top_n, window=args.window, fee_rate=args.fee_rate)

    # 3. 基准
    # 用回测窗口的日期做基准窗口
    win_dates = res['dates']
    bench = build_equal_weight_benchmark(big, win_dates, fee_rate=args.fee_rate)

    # 4. 保存净值曲线
    nav_csv = os.path.join(args.out_dir, 'nav_curve.csv')
    nav_df = save_nav_curve(res, bench, nav_csv)
    print(f'[save] nav_curve -> {nav_csv} ({len(nav_df)} rows)')

    # 5. 输出报告
    report = {
        'strategy': {
            'name': 'momentum_rotation_topN',
            'window': args.window,
            'top_n': args.top_n,
            'start_date': res['start_date'],
            'end_date': res['end_date'],
            'n_days': res['n_days'],
            'final_nav': float(res['nav'][-1]),
            'final_nav_fee': float(res['nav_fee'][-1]),
            'max_drawdown': float(res['max_drawdown']),
            'turnover': float(res['turnover_total']),
            'return_after_fee': float(res['return_after_fee']),
            'fee_paid': float(res['fee_paid']),
        },
        'benchmark': {
            'name': 'equal_weight_50',
            'start_date': bench['dates'][0],
            'end_date': bench['dates'][-1],
            'n_days': len(bench['dates']) - 1,
            'final_nav': float(bench['nav'][-1]),
            'final_nav_fee': float(bench['nav'][-1] - bench['fee_paid']),  # 占位：下面用真实
            'max_drawdown': float(bench['mdd']),
            'turnover': float(bench['turnover']),
            'return_after_fee': float(bench['return_fee']),
            'fee_paid': float(bench['fee_paid']),
        },
        'alpha': {
            'final_nav_diff': float(res['nav'][-1] - bench['nav'][-1]),
            'return_after_fee_diff': float(res['return_after_fee'] - bench['return_fee']),
        },
        'params': {
            'data_dir': args.data_dir,
            'universe': args.universe,
            'fee_rate': args.fee_rate,
        },
    }
    # 修正 final_nav_fee(benchmark)
    report['benchmark']['final_nav_fee'] = float(report['benchmark']['final_nav'] - bench['fee_paid'])

    rp = os.path.join(args.out_dir, 'report.json')
    with open(rp, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'[save] report -> {rp}')

    # 6. 打印关键指标
    s = report['strategy']
    b = report['benchmark']
    print('=' * 60)
    print(f'【动量策略】 start={s["start_date"]} end={s["end_date"]} days={s["n_days"]} top_n={s["top_n"]}')
    print(f'  final_nav           : {s["final_nav"]:.6f}')
    print(f'  max_drawdown        : {s["max_drawdown"]:.6f}')
    print(f'  turnover            : {s["turnover"]:.6f}')
    print(f'  return_after_fee    : {s["return_after_fee"]:.6f}')
    print(f'  fee_paid            : {s["fee_paid"]:.6f}')
    print(f'【等权基准】 {b["name"]}')
    print(f'  benchmark_final_nav          : {b["final_nav"]:.6f}')
    print(f'  benchmark_max_drawdown       : {b["max_drawdown"]:.6f}')
    print(f'  benchmark_turnover           : {b["turnover"]:.6f}')
    print(f'  benchmark_return_after_fee   : {b["return_after_fee"]:.6f}')
    print(f'  benchmark_fee_paid           : {b["fee_paid"]:.6f}')
    print('=' * 60)


if __name__ == '__main__':
    main()