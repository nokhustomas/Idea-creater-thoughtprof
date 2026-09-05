#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 A 股回测工具的合成样本数据。

本脚本仅用于本仓库的验收与示例，数据为程序随机生成的合成数据，
并非真实行情，不构成任何投资参考。
"""
import os
import csv
import random
from datetime import date, timedelta

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data")
os.makedirs(OUT_DIR, exist_ok=True)

START_DATE = date(2024, 1, 2)  # 第一个交易日的日期
N_DAYS = 300                    # 每只股票 300 个交易日

# 三只示例股票：代码, 显示名, 起始价（A 股常见量级）
STOCKS = [
    ("600000", "浦发银行_合成", 8.50),
    ("600519", "贵州茅台_合成", 1500.00),
    ("000001", "平安银行_合成", 12.00),
]


def trading_days(start, n):
    """从 start 开始返回 n 个交易日的日期列表（跳过周末）。"""
    days = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:  # 周一~周五
            days.append(d)
        d += timedelta(days=1)
    return days


def gen_one(start_price, n, seed):
    """为单只股票生成 n 个交易日的 OHLCV 数据，并遵守 A 股涨跌停 10%。"""
    rng = random.Random(seed)

    days = trading_days(START_DATE, n)

    # 先生成收盘价序列（带漂移的高斯随机游走，单日涨跌幅限制 ±10%）
    closes = [start_price]
    for _ in range(n - 1):
        r = rng.gauss(0.0006, 0.018)
        if r > 0.10:
            r = 0.10
        if r < -0.10:
            r = -0.10
        new_close = closes[-1] * (1.0 + r)
        if new_close < 0.10:
            new_close = 0.10
        closes.append(new_close)

    rows = []
    for i, d in enumerate(days):
        # 开盘价：基于昨日收盘小幅跳空，并受涨跌停限制
        if i == 0:
            o = closes[0]
        else:
            gap = rng.uniform(-0.004, 0.004)
            o = closes[i - 1] * (1.0 + gap)
            upper = closes[i - 1] * 1.10
            lower = closes[i - 1] * 0.90
            if o > upper:
                o = upper
            if o < lower:
                o = lower
        c = closes[i]

        # 当日振幅：随机在 0.2%~2.5% 之间，再围绕 (o,c) 给出最高最低
        amp_pct = rng.uniform(0.002, 0.025)
        base_high = max(o, c)
        base_low = min(o, c)
        up_extra = amp_pct * rng.random() * c
        dn_extra = amp_pct * rng.random() * c
        h = base_high + up_extra
        l = base_low - dn_extra

        # 涨跌停限制：相对昨日收盘 ±10%
        if i > 0:
            upper = closes[i - 1] * 1.10
            lower = closes[i - 1] * 0.90
            if h > upper:
                h = upper
            if l < lower:
                l = lower
            if h < max(o, c):
                h = max(o, c)
            if l > min(o, c):
                l = min(o, c)

        # A 股报价最小变动 0.01 元
        o = round(o + 1e-9, 2)
        h = round(h + 1e-9, 2)
        l = round(l + 1e-9, 2)
        c = round(c + 1e-9, 2)

        # 成交量：50 万 ~ 3000 万股的随机整数
        v = rng.randint(500_000, 30_000_000)

        rows.append([d.isoformat(), o, h, l, c, v])
    return rows


def main():
    for code, name, base in STOCKS:
        rows = gen_one(base, N_DAYS, (hash(code) & 0xFFFF))
        path = os.path.join(OUT_DIR, f"{code}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "open", "high", "low", "close", "volume"])
            w.writerows(rows)
        print(f"已写入 {path}（{len(rows)} 行，合成数据，仅供示例）")

    # 写一个 README 说明这是合成数据
    readme_path = os.path.join(OUT_DIR, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "本目录下三只股票 CSV 均为程序随机生成的合成数据，"
            "仅用于 backtest.py 的功能演示与验收，不构成真实行情或投资参考。\n"
        )
    print(f"已写入 {readme_path}")


if __name__ == "__main__":
    main()