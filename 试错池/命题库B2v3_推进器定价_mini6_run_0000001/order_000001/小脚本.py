#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小脚本：把三档定价（1999 / 9999 / 39999）算成表格 + 漏斗收入预测 + 毛利估算。
输入定价来源：三档定价方案.md（人工维护），本脚本只读取内置常量以保证可离线运行。
输出：纯文本表格到 stdout，60 秒内退出 0。
"""
import sys

# 三档定价（人民币 / 项目）
TIERS = [
    {"name": "基础查证 (Light)",      "price": 1999,  "delivery_days": 3,
     "cost":  {"interview": 0,    "compute": 50,   "labor": 700},
     "target": "早期创始人 / 个人开发者"},
    {"name": "深度查证 (Pro)",        "price": 9999,  "delivery_days": 7,
     "cost":  {"interview": 1500, "compute": 200,  "labor": 2800},
     "target": "成长期科技公司 VP/CTO"},
    {"name": "战略路线图 (Strategic)", "price": 39999, "delivery_days": 14,
     "cost":  {"interview": 8000, "compute": 600,  "labor": 14000},
     "target": "CEO / 董事会"},
]

# 漏斗比例（低:中:高 = 5:3:1，即每 9 单里有 5/3/1）
FUNNEL = [5, 3, 1]

# 假设每月总订单数（可调整）
MONTHLY_ORDERS_TOTAL = 30  # 30 单/月 → 约低 16.7 / 中 10 / 高 3.3


def fmt_money(x: float) -> str:
    return f"¥{x:,.0f}"


def tier_row(t):
    cost_total = sum(t["cost"].values())
    gross = t["price"] - cost_total
    margin = gross / t["price"] * 100 if t["price"] else 0
    return t, cost_total, gross, margin


def print_tier_table():
    print("=" * 78)
    print("三档定价明细表")
    print("=" * 78)
    header = f"{'档位':<22}{'单价':>10}{'成本':>10}{'毛利':>10}{'毛利率':>8}{'交付(天)':>10}"
    print(header)
    print("-" * 78)
    for t in TIERS:
        _, cost_total, gross, margin = tier_row(t)
        print(f"{t['name']:<22}{fmt_money(t['price']):>10}"
              f"{fmt_money(cost_total):>10}{fmt_money(gross):>10}"
              f"{margin:>7.1f}%{t['delivery_days']:>10}")
    print("-" * 78)


def print_funnel_forecast():
    print()
    print("=" * 78)
    print("月度漏斗收入预测（总订单 %d 单 / 月，比例 低:中:高 = %d:%d:%d）"
          % (MONTHLY_ORDERS_TOTAL, *FUNNEL))
    print("=" * 78)
    total_units = sum(FUNNEL)
    total_rev = 0.0
    total_cost = 0.0
    print(f"{'档位':<22}{'订单数':>8}{'收入':>12}{'成本':>12}{'毛利':>12}")
    print("-" * 78)
    for t, share in zip(TIERS, FUNNEL):
        units = MONTHLY_ORDERS_TOTAL * share / total_units
        cost_total = sum(t["cost"].values())
        rev = units * t["price"]
        cost = units * cost_total
        gross = rev - cost
        total_rev += rev
        total_cost += cost
        print(f"{t['name']:<22}{units:>8.1f}{fmt_money(rev):>12}"
              f"{fmt_money(cost):>12}{fmt_money(gross):>12}")
    print("-" * 78)
    print(f"{'合计':<22}{MONTHLY_ORDERS_TOTAL:>8}{fmt_money(total_rev):>12}"
          f"{fmt_money(total_cost):>12}{fmt_money(total_rev - total_cost):>12}")
    print()


def print_target_audience():
    print("=" * 78)
    print("目标客户对照")
    print("=" * 78)
    for t in TIERS:
        print(f"• {t['name']} → {t['target']}")
    print()


def main():
    print_tier_table()
    print_funnel_forecast()
    print_target_audience()
    print("脚本运行完成。来源：三档定价方案.md；无需联网；60 秒内退出 0。")
    sys.exit(0)


if __name__ == "__main__":
    main()