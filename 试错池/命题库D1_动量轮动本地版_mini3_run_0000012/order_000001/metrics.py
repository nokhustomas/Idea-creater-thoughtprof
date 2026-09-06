#!/usr/bin/env python3
"""
指标计算模块：
- 最大回撤（全局最大回撤，基于净值）
- 换手率（累计换手率/回测窗口，按净值归一化）
- 费用后收益（单边万三手续费，每次买入卖出各扣一次，即双边万六/轮动）
"""
import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('metrics')


def max_drawdown(nav: np.ndarray) -> float:
    """全局最大回撤（负数，例如 -0.15 表示回撤15%）"""
    nav = np.asarray(nav, dtype=float)
    if len(nav) == 0:
        return 0.0
    peak = -np.inf
    mdd = 0.0
    for x in nav:
        if x > peak:
            peak = x
        if peak > 0:
            dd = x / peak - 1.0
            if dd < mdd:
                mdd = dd
    return float(mdd)


def turnover_rate(turnover_per_day: np.ndarray) -> float:
    """累计换手率（按日累加），按净值归一化（即日均换手×天数/平均净值，单位化）"""
    turnover_per_day = np.asarray(turnover_per_day, dtype=float)
    if len(turnover_per_day) == 0:
        return 0.0
    # 累计换手率 = sum(每日换手率)，单位化（百分比形式：×100）
    return float(turnover_per_day.sum())


def apply_fee(nav_start: float, gross_return: float, turnover: float,
              fee_rate: float = 0.0003) -> float:
    """费用后收益：nav_start * (1+gross) - nav_start*fee_rate*turnover - nav_start = nav_start*gross - fee"""
    fee_cost = nav_start * fee_rate * turnover
    return gross_return - fee_cost


def fee_adjusted_return(nav: np.ndarray, turnover_per_day: np.ndarray,
                        fee_rate: float = 0.0003) -> dict:
    """
    费用后净值：每发生一次换手（turnover_per_day>0）扣双边万六。
    返回 {nav_fee, total_return_fee, fee_paid}
    """
    nav = np.asarray(nav, dtype=float)
    turnover = np.asarray(turnover_per_day, dtype=float)
    n = len(nav)
    if n == 0:
        return {'nav_fee': nav, 'total_return_fee': 0.0, 'fee_paid': 0.0}
    nav_fee = np.empty(n, dtype=float)
    nav_fee[0] = nav[0]
    fee_paid = 0.0
    for i in range(1, n):
        prev = nav_fee[i - 1]
        gross = nav[i] / nav[i - 1] - 1.0 if nav[i - 1] > 0 else 0.0
        to = turnover[i]
        # 单边万三，turnover 表示双边换手比例（0~2），一次双边收费 = 2*fee_rate*turnover
        # 但通常 turnover 已表示"换手比例"=卖出+买入/总资产，归一到双边各一次
        fee = prev * fee_rate * to * 2.0  # 双边万六/单位换手
        nav_fee[i] = prev * (1 + gross) - fee
        fee_paid += fee
    total_return_fee = nav_fee[-1] / nav_fee[0] - 1.0
    return {'nav_fee': nav_fee, 'total_return_fee': float(total_return_fee), 'fee_paid': float(fee_paid)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', action='store_true')
    args = ap.parse_args()

    # 演示：用一组合成数据计算三项指标
    nav = np.array([1.0, 1.02, 1.05, 1.03, 1.01, 1.06, 1.08, 1.04, 1.07, 1.10,
                    1.12, 1.09, 1.13, 1.15, 1.11, 1.14, 1.16, 1.18, 1.15, 1.20,
                    1.22, 1.19, 1.21, 1.24, 1.23, 1.26, 1.25, 1.28, 1.27, 1.30, 1.32])
    # 30 个交易日的换手：第 2、6、11、16、21、26 日发生轮动（双边），其余为 0
    turnover = np.zeros(31)
    for d in [2, 6, 11, 16, 21, 26]:
        turnover[d] = 1.0  # 全换手
    mdd = max_drawdown(nav)
    to = turnover_rate(turnover)
    fee_res = fee_adjusted_return(nav, turnover, fee_rate=0.0003)
    print(f'max_drawdown: {mdd:.6f}')
    print(f'turnover: {to:.6f}')
    print(f'return_after_fee: {fee_res["total_return_fee"]:.6f}')
    print(f'fee_paid: {fee_res["fee_paid"]:.6f}')


if __name__ == '__main__':
    main()