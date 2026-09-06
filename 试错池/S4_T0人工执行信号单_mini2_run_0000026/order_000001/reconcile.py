#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile.py - T+0 人工执行复盘对账脚本"""
import argparse, csv, re
from datetime import datetime
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parent
DISCLAIMER = "> ⚠️ 这不是投资建议，盈亏自负。"


def parse_signals_md(md_path):
    if not md_path.exists():
        return []
    text = md_path.read_text(encoding="utf-8")
    items = []
    for blk in re.split(r"\n(?=###\s)", text):
        m_code = re.search(r"股票代码[：:]\s*\**\s*([0-9]{6})", blk)
        if not m_code:
            continue
        m_side = re.search(r"信号方向[：:]\s*\**\s*(买入|卖出)\**", blk)
        m_rng = re.search(r"价格区间[：:]\s*\**\s*([0-9.]+)\s*[~\-]\s*([0-9.]+)", blk)
        m_qty = re.search(r"数量[（(]股[）)][：:]\s*\**\s*([0-9,]+)", blk)
        m_stop = re.search(r"止损价[：:]\s*\**\s*([0-9.]+)", blk)
        m_exp = re.search(r"失效时间[：:]\s*\**\s*([0-9:]+)", blk)
        m_trig = re.search(r"触发条件[：:]\s*([^\n]+)", blk)
        m_ord = re.search(r"下单时间[：:]\s*([^\n]+)", blk)
        items.append({
            "code": m_code.group(1),
            "side": m_side.group(1) if m_side else "?",
            "low": float(m_rng.group(1)) if m_rng else None,
            "high": float(m_rng.group(2)) if m_rng else None,
            "qty": int(m_qty.group(1).replace(",", "")) if m_qty else 0,
            "stop": float(m_stop.group(1)) if m_stop else None,
            "expire": m_exp.group(1) if m_exp else "15:00",
            "trigger": m_trig.group(1).strip() if m_trig else "",
            "order_time": m_ord.group(1).strip() if m_ord else "",
        })
    return items


def load_ledger(ledger_path):
    if not ledger_path.exists():
        return []
    with ledger_path.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        rows = []
        for r in rdr:
            try:
                rows.append({
                    "时间": (r.get("时间") or "").strip(),
                    "代码": (r.get("代码") or "").strip(),
                    "方向": (r.get("方向") or "").strip(),
                    "价": float(r.get("价") or 0),
                    "量": int(r.get("量") or 0),
                })
            except Exception:
                continue
        return rows


def match_fills(sig, fills):
    matched, rest = [], []
    used = 0
    for f in fills:
        if f["代码"] == sig["code"] and f["方向"] == sig["side"] and used < sig["qty"]:
            take = min(f["量"], sig["qty"] - used)
            mc = dict(f)
            mc["match_qty"] = take
            matched.append(mc)
            used += take
            if f["量"] > take:
                r = dict(f)
                r["量"] = f["量"] - take
                rest.append(r)
        else:
            rest.append(f)
    return matched, rest, used


def calc_slippage(sig, matched):
    if sig["low"] is None or sig["high"] is None or not matched:
        return None
    mid = (sig["low"] + sig["high"]) / 2.0
    total = sum(m["match_qty"] for m in matched)
    if total == 0:
        return None
    avg = sum(m["价"] * m["match_qty"] for m in matched) / total
    return (avg - mid) if sig["side"] == "买入" else (mid - avg)


def estimate_pnl(sig, matched):
    if sig["low"] is None or sig["high"] is None or not matched:
        return 0.0
    mid = (sig["low"] + sig["high"]) / 2.0
    pnl = 0.0
    for m in matched:
        pnl += ((mid - m["价"]) if sig["side"] == "买入" else (m["价"] - mid)) * m["match_qty"]
    return pnl


DEMO_FILLS = [
    {"时间": "09:35", "代码": "510300", "方向": "买入", "价": 3.842, "量": 5000},
    {"时间": "09:42", "代码": "510300", "方向": "买入", "价": 3.851, "量": 5000},
    {"时间": "11:08", "代码": "510300", "方向": "卖出", "价": 3.890, "量": 10000},
    {"时间": "10:15", "代码": "600519", "方向": "卖出", "价": 1678.00, "量": 100},
    {"时间": "14:32", "代码": "600519", "方向": "买入", "价": 1672.50, "量": 100},
]


def reconcile(date_str, demo, ledger_name="ledger.csv"):
    if demo:
        signals_path = WORK_DIR / "signals_sample.md"
        fills = DEMO_FILLS
        out_path = WORK_DIR / "reconcile_sample.md"
        ledger_used = "(演示内置样例成交)"
    else:
        signals_path = WORK_DIR / f"signals_{date_str}.md"
        fills = load_ledger(WORK_DIR / ledger_name)
        out_path = WORK_DIR / f"reconcile_{date_str}.md"
        ledger_used = ledger_name
    signals = parse_signals_md(signals_path)
    L = [f"# 复盘对账报告（{date_str}）", "",
         f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ·  对账脚本：reconcile.py",
         f"> 信号单：{signals_path.name}  ·  账本：{ledger_used}",
         "", DISCLAIMER, ""]
    if not signals:
        L.append("⚠️ 未解析到任何信号。")
        out_path.write_text("\n".join(L), encoding="utf-8")
        print(f"[reconcile] 已生成：{out_path}")
        return out_path
    total_n = len(signals)
    executed_n = 0
    slip_sum = 0.0
    slip_cnt = 0
    pnl_sum = 0.0
    L.append("## 一、信号执行总览")
    L.append("")
    L.append("| # | 股票代码 | 方向 | 计划量 | 实际成交 | 执行率 | 滑点(元/股) | 当日盈亏(元) |")
    L.append("|---|---------|------|-------|---------|-------|------------|-------------|")
    for idx, sig in enumerate(signals, 1):
        matched, _, used = match_fills(sig, fills)
        rate = (used / sig["qty"] * 100.0) if sig["qty"] else 0.0
        slip = calc_slippage(sig, matched)
        pnl = estimate_pnl(sig, matched)
        if used > 0:
            executed_n += 1
        if slip is not None:
            slip_sum += slip
            slip_cnt += 1
        pnl_sum += pnl
        slip_str = f"{slip:+.4f}" if slip is not None else "—"
        L.append(f"| {idx} | {sig['code']} | {sig['side']} | {sig['qty']} | {used} | "
                 f"{rate:.1f}% | {slip_str} | {pnl:+.2f} |")
    L.append("")
    exec_rate = (executed_n / total_n * 100.0) if total_n else 0.0
    avg_slip = (slip_sum / slip_cnt) if slip_cnt else 0.0
    L.append(f"- 信号总数：**{total_n}** 条")
    L.append(f"- 实际执行：**{executed_n}** 条（**执行率 {exec_rate:.1f}%**）")
    if slip_cnt:
        L.append(f"- 平均**滑点**：{avg_slip:+.4f} 元/股（正=不利滑点：买贵/卖贱）")
    L.append(f"- 当日估算盈亏：**{pnl_sum:+.2f} 元**（以信号区间中点为目标价粗算）")
    L.append("")
    L.append("## 二、逐笔对照")
    L.append("")
    for idx, sig in enumerate(signals, 1):
        matched, _, used = match_fills(sig, fills)
        L.append(f"### 信号 #{idx}：{sig['code']} {sig['side']}")
        L.append("")
        L.append(f"- 触发条件：{sig['trigger']}")
        L.append(f"- 下单时间：{sig['order_time']}")
        L.append(f"- 价格区间：{sig['low']} ~ {sig['high']}  ·  计划量：{sig['qty']} 股")
        L.append(f"- 止损价：{sig['stop']}  ·  失效时间：{sig['expire']}")
        if matched:
            L.append(f"- 实际成交 {len(matched)} 笔，合计 {used} 股：")
            L.append("")
            L.append("  | 时间 | 价 | 量 |")
            L.append("  |------|-----|-----|")
            for m in matched:
                L.append(f"  | {m['时间']} | {m['价']} | {m['match_qty']} |")
            slip = calc_slippage(sig, matched)
            pnl = estimate_pnl(sig, matched)
            slip_str = f"{slip:+.4f}" if slip is not None else "—"
            L.append("")
            L.append(f"- 滑点：**{slip_str}** 元/股")
            L.append(f"- 当日盈亏：**{pnl:+.2f}** 元")
        else:
            L.append("- 实际成交：**无**（未执行）")
        L.append("")
    L.append("## 三、未匹配成交（可选检查）")
    L.append("")
    matched_codes = {s["code"] for s in signals}
    unmatched = [f for f in fills if f["代码"] not in matched_codes]
    if unmatched:
        L.append("以下成交未对应任何当日信号单，请确认是否为计划外操作：")
        L.append("")
        L.append("| 时间 | 代码 | 方向 | 价 | 量 |")
        L.append("|------|------|------|-----|-----|")
        for f in unmatched:
            L.append(f"| {f['时间']} | {f['代码']} | {f['方向']} | {f['价']} | {f['量']} |")
    else:
        L.append("无计划外成交，纪律良好。")
    L.append("")
    L.append("---")
    L.append("")
    L.append(DISCLAIMER)
    L.append("")
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"[reconcile] 已生成：{out_path}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="T+0 人工执行复盘对账")
    ap.add_argument("--date", default="2024-06-03", help="对账日期 YYYY-MM-DD")
    ap.add_argument("--demo", action="store_true", help="演示模式")
    ap.add_argument("--ledger", default="ledger.csv", help="账本文件名")
    args = ap.parse_args()
    date_str = args.date.replace("-", "")
    reconcile(date_str, args.demo, args.ledger)


if __name__ == "__main__":
    main()