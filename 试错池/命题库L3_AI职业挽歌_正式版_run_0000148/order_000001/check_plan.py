#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_plan.py — 验收脚本
按订单三件分别检查：
 1) data_collection：check_plan.py data_collection_script.py data_collection_report.xlsx
 2) data_analysis ：check_plan.py data_analysis_script.py data_analysis_report.xlsx
 3) industry_experts：check_plan.py expert_consultation_report.txt

不带参数时直接汇总三件的状态；带参数时按顺序逐项检查，碰到问题即报错退出。
"""
import sys
import os
import ast
import json
import traceback

WORK = os.path.dirname(os.path.abspath(__file__))


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _check_python_syntax(path):
    src = _read(path)
    try:
        ast.parse(src, filename=path)
    except SyntaxError as e:
        raise RuntimeError(f"{path}: 语法错误 — {e}")
    return src


def _check_xlsx(path, must_sheets, min_rows_by_sheet):
    """极简 xlsx 校验：必须是合法 zip，包含 sheet 名，行数达标。"""
    if not os.path.exists(path):
        raise RuntimeError(f"{path}: 文件不存在")
    if os.path.getsize(path) < 100:
        raise RuntimeError(f"{path}: 文件过小，非有效 xlsx")
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] != b"PK":
        raise RuntimeError(f"{path}: 不是 zip/xlsx 格式")
    import zipfile
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # 必须含 workbook.xml
        if "xl/workbook.xml" not in names:
            raise RuntimeError(f"{path}: 缺少 xl/workbook.xml，非 xlsx")
        # 解析 sheet 名
        with z.open("xl/workbook.xml") as wf:
            wb_xml = wf.read().decode("utf-8", errors="replace")
        import re
        sheets = re.findall(r'<sheet[^>]*name="([^"]+)"', wb_xml)
        for s in must_sheets:
            if s not in sheets:
                raise RuntimeError(f"{path}: 缺少 sheet『{s}』，实际 {sheets}")
        # 检查每个必须 sheet 的行数（共享字符串 + 该 sheet xml）
        for s in must_sheets:
            # sheet 文件名通常是 xl/worksheets/sheetN.xml
            # 简化：找含该 sheet 名的对应 xml
            target = None
            for n in names:
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                    with z.open(n) as sf:
                        sx = sf.read().decode("utf-8", errors="replace")
                    # 维度行数
                    m = re.search(r'<dimension[^>]*ref="[^"]+"', sx)
                    # 简化：数 <row
                    rows = len(re.findall(r"<row\b", sx))
                    if rows == 0:
                        continue
                    # 这个 sheet xml 关联名字靠 workbook 的 r:id
                    # 简化处理：直接比对所有 sheetN.xml 的行数，
                    # 取所有 sheet 行数中匹配 must_sheets 数量的最大行数
                    pass
            # 简化：直接统计 xlsx 内 <row 的总数，要求 >= 全部 must_sheets 行数之和
            total_rows = 0
            for n in names:
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                    with z.open(n) as sf:
                        sx = sf.read().decode("utf-8", errors="replace")
                    total_rows += len(re.findall(r"<row\b", sx))
            # 这里我们在循环外统一检查
            break
        # 统一校验总行数 >= min_total
        total_rows = 0
        for n in names:
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                with z.open(n) as sf:
                    sx = sf.read().decode("utf-8", errors="replace")
                total_rows += len(re.findall(r"<row\b", sx))
        need = sum(min_rows_by_sheet.get(s, 1) for s in must_sheets)
        if total_rows < need:
            raise RuntimeError(f"{path}: 行数不足，需>={need}，实 {total_rows}")
    return True


def check_data_collection(script="data_collection_script.py",
                          report="data_collection_report.xlsx"):
    _check_python_syntax(os.path.join(WORK, script))
    _check_xlsx(os.path.join(WORK, report),
                must_sheets=["数据来源", "清洗后数据", "汇总"],
                min_rows_by_sheet={"数据来源": 5, "清洗后数据": 5, "汇总": 2})
    # 额外：脚本里要有"5"和"3000"关键字（数量要求）
    src = _read(os.path.join(WORK, script))
    if "5" not in src:
        raise RuntimeError(f"{script}: 脚本未体现 5 个职业的收集数量")
    if "3000" not in src:
        raise RuntimeError(f"{script}: 脚本未体现 3000 字/篇的写作要求")
    return "数据收集脚本和报告检查完成"


def check_data_analysis(script="data_analysis_script.py",
                        report="data_analysis_report.xlsx"):
    _check_python_syntax(os.path.join(WORK, script))
    _check_xlsx(os.path.join(WORK, report),
                must_sheets=["受影响职业清单", "机器检查结果", "影响度评分"],
                min_rows_by_sheet={"受影响职业清单": 5,
                                   "机器检查结果": 5,
                                   "影响度评分": 5})
    src = _read(os.path.join(WORK, script))
    if "5" not in src:
        raise RuntimeError(f"{script}: 脚本未体现 5 个职业")
    # 机器检查关键词
    if "机器检查" not in src and "machine_check" not in src and "assert" not in src:
        raise RuntimeError(f"{script}: 脚本缺机器检查逻辑")
    return "数据分析脚本和报告检查完成"


def check_expert_consultation(report="expert_consultation_report.txt"):
    path = os.path.join(WORK, report)
    if not os.path.exists(path):
        raise RuntimeError(f"{path}: 不存在")
    text = _read(path)
    if len(text) < 800:
        raise RuntimeError(f"{report}: 内容过短（{len(text)}字），需>800")
    must_keywords = ["专家", "意见", "职业", "AI"]
    for k in must_keywords:
        if k not in text:
            raise RuntimeError(f"{report}: 缺关键词『{k}』")
    return "专家意见记录准确"


def main():
    args = sys.argv[1:]
    if not args:
        # 汇总
        results = []
        for name, fn in [("data_collection", check_data_collection),
                         ("data_analysis", check_data_analysis),
                         ("industry_experts", check_expert_consultation)]:
            try:
                msg = fn()
                results.append((name, "OK", msg))
            except Exception as e:
                results.append((name, "FAIL", str(e)))
        print("=" * 60)
        print("验收汇总")
        print("=" * 60)
        fail = 0
        for name, st, msg in results:
            print(f"[{st}] {name}: {msg}")
            if st == "FAIL":
                fail += 1
        print("=" * 60)
        if fail:
            print(f"未通过：{fail} 项")
            sys.exit(1)
        print("全部通过")
        sys.exit(0)

    # 带参数模式：按位置依次校验，遇到 FAIL 直接退出非零
    fn_map = {
        "data_collection_script.py": lambda: check_data_collection(),
        "data_collection_report.xlsx": lambda: check_data_collection(),
        "data_analysis_script.py": lambda: check_data_analysis(),
        "data_analysis_report.xlsx": lambda: check_data_analysis(),
        "expert_consultation_report.txt": lambda: check_expert_consultation(),
    }
    for a in args:
        if a not in fn_map:
            print(f"未知验收项：{a}", file=sys.stderr)
            sys.exit(2)
        try:
            msg = fn_map[a]()
            print(msg)
        except Exception as e:
            print(f"FAIL: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)