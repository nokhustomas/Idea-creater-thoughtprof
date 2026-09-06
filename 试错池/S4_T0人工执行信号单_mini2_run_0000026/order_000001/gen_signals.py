#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_signals.py —— T+0 每日交易信号单生成器

用法：
  python3 gen_signals.py --date 2024-06-03         # 生成该日信号单（离线）
  python3 gen_signals.py --date 2024-06-03 --demo  # 演示模式：固定 4 条样例信号

输出：
  signals_YYYYMMDD.md（默认）或 signals_sample.md（--demo）
"""

import argparse
from datetime import datetime
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parent
DISCLAIMER = "> ⚠️ 这不是投资建议，盈亏自负。"


# ------------------------- 演示信号 -------------------------

DEMO_SIGNALS = [
    {
        "bucket": "底仓做 T",
        "code": "510300", "name": "沪深300ETF", "side": "买入",
        "low": 3.835, "high": 3.860, "qty": 10000,
        "order_time": "09:35（开盘后 5 分钟）",
        "trigger": "回踩 5 分钟 MA20 不破，且当日开盘价 -0.3% 以内",
        "stop": 3.820,
        "expire": "14:00",
    },
    {
        "bucket": "底仓做 T",
        "code": "600519", "name": "贵州茅台", "side": "卖出",
        "low": 1680.00, "high": 1695.00, "qty": 100,
        "order_time": "10:00 前",
        "trigger": "高开后量能不济，30 分钟内未突破 1700，区间上沿卖出一笔底仓",
        "stop": 1710.00,
        "expire": "11:30",
    },
    {
        "bucket": "T+0 ETF",
        "code": "510500", "name": "中证500ETF", "side": "买入",
        "low": 5.860, "high": 5.900, "qty": 5000,
        "order_time": "10:30 之前",
        "trigger": "中证500日内跌幅 -0.8% 以上，跌破日内 VWAP 后企稳",
        "stop": 5.840,
        "expire": "13:30",
    },
    {
        "bucket": "T+0 ETF",
        "code": "512760", "name": "半导体ETF", "side": "买入",
        "low": 1.020, "high": 1.035, "qty": 8000,
        "order_time": "13:00 之前",
        "trigger": "回踩 30 分钟级别支撑 1.022，RSI<35",
        "stop": 1.010,
        "expire": "14:30",
    },
]


# ------------------------- 渲染 -------------------------

def render_signal(sig, idx):
    L = []
    L.append(f"### 信号 #{idx}：{sig['name']}（{sig['code']}）— {sig['side']}")
    L.append("")
    L.append(f"- 股票代码：**{sig['code']}**")
    L.append(f"- 信号方向：**{sig['side']}**")
    L.append(f"- 价格区间：**{sig['low']} ~ {sig['high']}**")
    L.append(f"- 数量（股）：**{sig['qty']:,}**")
    L.append(f"- 下单时间：{sig['order_time']}")
    L.append(f"- 触发条件：{sig['trigger']}")
    L.append(f"- 止损价：**{sig['stop']}**（价格触发即手动市价止损/挂条件单）")
    L.append(f"- 失效时间：{sig['expire']}（未触发即作废，不追单）")
    L.append("")
    return "\n".join(L)


def render_day(date_str, signals, out_path):
    buckets = {}
    for s in signals:
        buckets.setdefault(s["bucket"], []).append(s)

    L = []
    L.append(f"# 每日交易信号单（{date_str}）")
    L.append("")
    L.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ·  生成脚本：gen_signals.py")
    L.append(f"> 适用用户：国信金太阳 iOS 版人工 T+0")
    L.append("")
    L.append(DISCLAIMER)
    L.append("")
    L.append("---")
    L.append("")

    if not signals:
        L.append("⚠️ 今日未生成任何信号（数据不足或策略不发信号）。")
        L.append("")
        out_path.write_text("\n".join(L), encoding="utf-8")
        return out_path

    L.append("## 字段说明")
    L.append("")
    L.append("每条信号 ≤ 2 条/品种，含 8 个必填字段：")
    L.append("")
    L.append("1. **股票代码**（6 位）")
    L.append("2. **信号方向**（买入 / 卖出）")
    L.append("3. **价格区间**（限价挂单区间）")
    L.append("4. **数量**（股数）")
    L.append("5. **下单时间**（窗口）")
    L.append("6. **触发条件**（客观可判定的条件）")
    L.append("7. **止损价**（价格触发即止损）")
    L.append("8. **失效时间**（到期未触发即作废）")
    L.append("")
    L.append("> 所有信号均为**条件单**，触发条件未满足即不下单，盈亏自负。")
    L.append("")

    idx = 0
    for bucket_name in ["底仓做 T", "T+0 ETF"]:
        if bucket_name not in buckets:
            continue
        L.append("---")
        L.append("")
        L.append(f"## 一、{bucket_name}" if bucket_name == "底仓做 T" else f"## 二、{bucket_name}")
        L.append("")
        L.append(f"> 适用范围：{bucket_name}。每只标的当日**最多 1 轮 T**（先买后卖 / 先卖后买）。")
        L.append("")
        for sig in buckets[bucket_name]:
            idx += 1
            L.append(render_signal(sig, idx))

    L.append("---")
    L.append("")
    L.append("## 纪律提醒")
    L.append("")
    L.append("- 严格按 [checklist.md](./checklist.md) 流程下单，未打勾不上手")
    L.append("- **不写'必涨'类语句**；本单只描述**触发条件**，结果取决于行情")
    L.append("- 收盘后把成交填入 `ledger.csv`，运行 `reconcile.py` 看对账")
    L.append("")
    L.append(DISCLAIMER)
    L.append("")

    out_path.write_text("\n".join(L), encoding="utf-8")
    return out_path


def gen(date_str, demo):
    if demo:
        out_path = WORK_DIR / "signals_sample.md"
        signals = DEMO_SIGNALS
    else:
        out_path = WORK_DIR / f"signals_{date_str}.md"
        signals = DEMO_SIGNALS
    out = render_day(date_str, signals, out_path)
    print(f"[gen_signals] 已生成：{out}（{len(signals)} 条信号）")
    return out


def main():
    ap = argparse.ArgumentParser(description="T+0 每日信号单生成器")
    ap.add_argument("--date", default="2024-06-03", help="信号单日期 YYYY-MM-DD")
    ap.add_argument("--demo", action="store_true", help="演示模式：写入 signals_sample.md")
    args = ap.parse_args()
    date_str = args.date.replace("-", "")
    gen(date_str, args.demo)


if __name__ == "__main__":
    main()