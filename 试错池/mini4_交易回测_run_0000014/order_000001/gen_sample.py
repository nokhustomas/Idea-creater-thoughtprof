#!/usr/bin/env python3
"""生成 sample_data/ 三只股票各 350 个交易日的合成数据（覆盖 2025 全年）。"""
import csv
import math
import os
import random
from datetime import date, timedelta

random.seed(42)

STOCKS = [
    ("STOCK_A", 10.0),
    ("STOCK_B", 25.0),
    ("STOCK_C", 50.0),
]

os.makedirs("sample_data", exist_ok=True)

START = date(2024, 1, 1)
N = 350


def nxt(d):
    d = d + timedelta(days=1)
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    return d


for sym, base in STOCKS:
    p = base
    d = START
    rows = []
    for i in range(N):
        drift = 0.0002 + 0.0001 * math.sin(i / 30.0)
        vol = 0.015 + 0.005 * math.cos(i / 20.0)
        ret = random.gauss(drift, vol)
        gap = random.gauss(0, 0.005)
        o = p * (1 + gap)
        ir = abs(random.gauss(0, vol)) * p
        c = o * (1 + ret)
        h = max(o, c) + random.uniform(0, ir)
        l = min(o, c) - random.uniform(0, ir)
        if l < 0.01:
            l = 0.01
        v = int(random.uniform(500000, 3000000))
        rows.append((d.isoformat(), round(o, 2), round(h, 2), round(l, 2), round(c, 2), v))
        p = c
        d = nxt(d)
    path = f"sample_data/{sym}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for r in rows:
            w.writerow(r)
    print(f"{sym}: {len(rows)} rows, last={rows[-1][0]}")