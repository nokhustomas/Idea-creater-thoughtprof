#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for 具身智能数据瓶颈机会地图 delivery.

Checks:
  1) all required files exist
  2) JSON files parse cleanly
  3) arXiv paper IDs match YYMM.NNNNN format
  4) Markdown files contain key section headers and source markers
Exits 0 on success, non-zero on failure. Designed to run < 30s.
"""
import json
import os
import re
import sys

REQUIRED_FILES = [
    "arxiv_papers.json",
    "检索日志.json",
    "瓶颈观点.md",
    "机会地图.md",
    "公司动态.md",
    "运行命令.txt",
    "README.md",
]

ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")

failures = []


def check_files():
    missing = [f for f in REQUIRED_FILES if not os.path.isfile(f)]
    if missing:
        failures.append(f"missing files: {missing}")
    else:
        print(f"[OK] all {len(REQUIRED_FILES)} files present")


def check_json():
    for fp in ("arxiv_papers.json", "检索日志.json"):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            failures.append(f"json parse fail {fp}: {e}")
            continue
        print(f"[OK] {fp} parseable, top-level type={type(data).__name__}")


def check_arxiv_ids():
    try:
        papers = json.load(open("arxiv_papers.json", encoding="utf-8"))
    except Exception as e:
        failures.append(f"cannot read arxiv_papers.json: {e}")
        return
    if not isinstance(papers, list) or len(papers) == 0:
        failures.append("arxiv_papers.json must be a non-empty list")
        return
    bad = []
    for p in papers:
        aid = p.get("id", "")
        if not ID_RE.match(aid):
            bad.append(aid)
    if bad:
        failures.append(f"bad arxiv ids: {bad}")
    else:
        print(f"[OK] all {len(papers)} arxiv ids match YYMM.NNNNN")


def check_markdown():
    rules = {
        "瓶颈观点.md": [
            r"已验证|合理推断|待验证",
            r"arXiv:\d{4}\.\d{4,5}",
        ],
        "机会地图.md": [
            r"缝隙|切入点|小团队",
            r"依据",
        ],
        "公司动态.md": [
            r"(来源[：:]\s*https?://|存档[：:]|来源[：:][^\n]+——)",
        ],
    }
    for fp, patterns in rules.items():
        try:
            content = open(fp, encoding="utf-8").read()
        except Exception as e:
            failures.append(f"cannot read {fp}: {e}")
            continue
        for pat in patterns:
            if not re.search(pat, content):
                failures.append(f"{fp} missing pattern: {pat}")
    dyn = open("公司动态.md", encoding="utf-8").read()
    n_src = len(re.findall(r"(来源[：:]\s*https?://|存档[：:]|来源[：:][^\n]+——)", dyn))
    if n_src < 3:
        failures.append(f"公司动态.md source/存档 count {n_src} < 3")
    else:
        print(f"[OK] 公司动态.md has {n_src} source/存档 entries (>=3)")
    print("[OK] markdown key sections checked")


def check_run_command():
    txt = open("运行命令.txt", encoding="utf-8").read().strip().splitlines()
    first = txt[0] if txt else ""
    if "python3" not in first:
        failures.append(f"运行命令.txt first line missing self-check command: {first!r}")
    else:
        print(f"[OK] 运行命令.txt first line: {first}")


def main():
    check_files()
    check_json()
    check_arxiv_ids()
    check_markdown()
    check_run_command()
    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()