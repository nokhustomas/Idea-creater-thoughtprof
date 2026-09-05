#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三维原创性验证工具 - verify_novelty.py

读取自创方案描述（--self）和现有方案列表（--others），
在"问题-方法-场景"三个维度上做关键词共现相似度粗筛，
输出带概率估计的 markdown 表格到 output/comparison.md，
供人工复核。

用法：
    python verify_novelty.py --self my_idea.txt --others existing_solutions.txt
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


# ---------- 维度关键词词典 ----------
DIMENSION_KEYWORDS = {
    "问题": [
        "问题", "痛点", "需求", "场景", "瓶颈", "难题", "挑战",
        "缺失", "空白", "缺口", "限制", "约束", "目标",
    ],
    "方法": [
        "方法", "算法", "模型", "架构", "框架", "流程", "机制",
        "策略", "技术", "协议", "原理", "思路", "实现", "方案",
    ],
    "场景": [
        "领域", "行业", "用户", "应用", "用例", "环境",
        "上下文", "条件", "情境", "受众", "市场", "客户", "人群",
    ],
}

# 中文停用词
STOPWORDS = set(
    "的 了 和 是 在 与 或 及 等 这 那 我 你 他 她 它 我们 你们 他们 "
    "一个 一些 这个 那个 这些 那些 以及 但是 因为 所以 如果 那么 "
    "通过 可以 能够 进行 实现 处理 使用 包括 包含 提供 支持 进行 "
    "为 于 上 下 中 内 外 前 后 之 以 来 所 由 从 把 被 让"
)


def tokenize(text):
    """简单分词：英文按空格/下划线切，中文做 2-gram 和连续片段切。"""
    text = text.lower()
    en_words = re.findall(r"[a-z_][a-z0-9_]+", text)
    cn_segs = re.findall(r"[\u4e00-\u9fa5]+", text)
    tokens = list(en_words)
    for seg in cn_segs:
        seg = seg.strip()
        if len(seg) <= 1:
            continue
        tokens.append(seg)
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i + 2])
    return [t for t in tokens if t not in STOPWORDS and len(t) >= 2]


def extract_dimension_keywords(text, dim):
    """提取与某个维度相关的关键词集合。"""
    base_kw = set(DIMENSION_KEYWORDS[dim])
    all_tokens = tokenize(text)
    matched = set()
    for tok in all_tokens:
        for kw in base_kw:
            if kw in tok or tok in kw:
                matched.add(kw)
                break
    return matched


def jaccard(a, b):
    """Jaccard 相似度，返回 [0, 1]。"""
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def classify(similarity):
    """根据相似度做三级判定。"""
    if similarity >= 0.5:
        return "表面修改"
    if similarity >= 0.2:
        return "无法判断"
    return "本质差异"


def parse_solutions(path):
    """读取现有方案列表文件。用 --- 或 === 或空行作为分隔符。"""
    content = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*(?:---|===)\s*\n", content)
    solutions = []
    for blk in blocks:
        blk = blk.strip()
        if not blk:
            continue
        lines = [l for l in blk.split("\n") if l.strip()]
        if not lines:
            continue
        name = lines[0].strip().lstrip("#").strip()
        desc = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if not desc:
            desc = name
        solutions.append({"name": name, "desc": desc})
    # 如果分隔符没起作用，按空行再分一次
    if len(solutions) <= 1:
        solutions = []
        content_blocks = re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8"))
        for blk in content_blocks:
            blk = blk.strip()
            if not blk:
                continue
            lines = [l for l in blk.split("\n") if l.strip()]
            if not lines:
                continue
            name = lines[0].strip().lstrip("#").strip()
            desc = "\n".join(lines[1:]).strip() if len(lines) > 1 else name
            solutions.append({"name": name, "desc": desc})
    return solutions


def main():
    parser = argparse.ArgumentParser(
        description="三维原创性验证工具（问题-方法-场景）",
    )
    parser.add_argument("--self", required=True, help="自创方案描述文件路径")
    parser.add_argument("--others", required=True, help="现有方案列表文件路径")
    parser.add_argument(
        "--output",
        default="output/comparison.md",
        help="输出 markdown 路径（默认 output/comparison.md）",
    )
    args = parser.parse_args()

    self_path = Path(args.self)
    others_path = Path(args.others)
    if not self_path.exists():
        print(f"[错误] 自创方案文件不存在: {self_path}", file=sys.stderr)
        sys.exit(1)
    if not others_path.exists():
        print(f"[错误] 现有方案文件不存在: {others_path}", file=sys.stderr)
        sys.exit(1)

    self_text = self_path.read_text(encoding="utf-8")
    solutions = parse_solutions(others_path)

    if not solutions:
        print("[错误] 未从现有方案文件中解析出任何方案", file=sys.stderr)
        sys.exit(1)

    # 计算自创方案在三个维度上的关键词集合
    self_dims = {
        d: extract_dimension_keywords(self_text, d) for d in DIMENSION_KEYWORDS
    }

    rows = []
    rows.append("# 三维对比报告（问题-方法-场景）")
    rows.append("")
    rows.append(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rows.append(f"- 自创方案: {self_path}")
    rows.append(f"- 现有方案文件: {others_path}")
    rows.append(f"- 对比方案数: {len(solutions)}")
    rows.append("")
    rows.append("> ⚠️ 本脚本只做关键词共现率粗筛，所有判定需人工复核。")
    rows.append("> 判定标签: **本质差异**(Jaccard<0.2) / **无法判断**(0.2~0.5) / **表面修改**(>=0.5)")
    rows.append("")
    rows.append("## 自创方案原文")
    rows.append("")
    rows.append("```")
    rows.append(self_text.strip())
    rows.append("```")
    rows.append("")
    rows.append("## 三维对比表格")
    rows.append("")
    rows.append(
        "| # | 现有方案 | 问题维度 | 方法维度 | 场景维度 | 综合判定 | 备注 |"
    )
    rows.append(
        "| --- | --- | --- | --- | --- | --- | --- |"
    )

    new_count = 0
    variant_count = 0
    unsure_count = 0

    for i, sol in enumerate(solutions, 1):
        sol_dims = {
            d: extract_dimension_keywords(sol["desc"], d)
            for d in DIMENSION_KEYWORDS
        }
        sims = {}
        labels = {}
        for d in DIMENSION_KEYWORDS:
            sim = jaccard(self_dims[d], sol_dims[d])
            sims[d] = sim
            labels[d] = classify(sim)

        essential = sum(1 for v in labels.values() if v == "本质差异")
        surface = sum(1 for v in labels.values() if v == "表面修改")
        unknown = sum(1 for v in labels.values() if v == "无法判断")

        if essential >= 2:
            verdict = "新创造"
            new_count += 1
        elif surface >= 2:
            verdict = "变种"
            variant_count += 1
        else:
            verdict = "需进一步调研"
            unsure_count += 1

        sim_str = {
            d: f"{labels[d]}({sims[d]:.2f})" for d in DIMENSION_KEYWORDS
        }
        if unknown > 0:
            note = "需人工确认"
        else:
            note = "粗筛结果"

        rows.append(
            f"| {i} | {sol['name']} | {sim_str['问题']} | "
            f"{sim_str['方法']} | {sim_str['场景']} | "
            f"{verdict} | {note} |"
        )

    rows.append("")
    rows.append("## 三级判定规则")
    rows.append("")
    rows.append("- **本质差异**：Jaccard 相似度 < 0.2，关键词几乎不共享")
    rows.append("- **表面修改**：Jaccard 相似度 >= 0.5，关键词大量共享")
    rows.append("- **无法判断**：Jaccard 相似度介于 0.2 ~ 0.5，需人工分析")
    rows.append("")
    rows.append("## 综合判定逻辑")
    rows.append("")
    rows.append("- 至少 **2 个维度本质差异** → **新创造**")
    rows.append("- 至少 **2 个维度表面修改** → **变种**")
    rows.append("- 其他情况 → **需进一步调研**（存在无法判断的维度时尤其需要补料）")
    rows.append("")
    rows.append("## 人工复核清单")
    rows.append("")
    rows.append("- [ ] 是否对比了『问题定义』『算法核心』『数据流』三件事？")
    rows.append("- [ ] 每个维度是否都看了本质差异而不是只看了表面特征（界面/参数/输出格式）？")
    rows.append("- [ ] 对于『无法判断』的维度，是否补充了调研资料？")
    rows.append("- [ ] 综合判定是否与三维分布一致？")
    rows.append("- [ ] 是否核实了每个现有方案的出处链接与核心原理描述？")
    rows.append("")
    rows.append("## 统计")
    rows.append("")
    rows.append(f"- 对比方案数: {len(solutions)}")
    rows.append(f"- 判定为新创造的方案数: {new_count}")
    rows.append(f"- 判定为变种的方案数: {variant_count}")
    rows.append(f"- 需进一步调研的方案数: {unsure_count}")
    rows.append("")
    rows.append("---")
    rows.append("")
    rows.append("⚠️ 本报告由 verify_novelty.py 自动生成，仅基于关键词共现率，必须人工复核后再下结论。")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(rows), encoding="utf-8")
    print(f"[完成] 已生成 {out_path}")
    print(f"[统计] 对比方案: {len(solutions)} | 新创造: {new_count} | 变种: {variant_count} | 待调研: {unsure_count}")


if __name__ == "__main__":
    main()