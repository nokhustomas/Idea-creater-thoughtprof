#!/usr/bin/env python3
"""
demo.py - CodeDiff 的价值证明脚本。

自动生成两个示例 Python 文件（sample_v1.py 和 sample_v2.py），
调用 codediff.py 对比它们的 AST 结构，输出结构差异摘要，
证明用户无需逐行读 diff 即可知道核心变更。

运行: python demo.py
预期: 退出码 0，并在当前目录生成 diff_report.txt
"""

import os
import subprocess
import sys


# 示例 v1：原始版本，含 process_data、calculate、legacy_func、DataProcessor
SAMPLE_V1 = '''"""Sample file version 1 - original version."""


def process_data(data):
    """Process the input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result


def calculate(a, b):
    """Calculate something."""
    return a + b


class DataProcessor:
    """Process data class."""

    def __init__(self):
        self.cache = {}

    def run(self, data):
        return process_data(data)


def legacy_func(x):
    """Legacy function that will be removed in v2."""
    return x - 1
'''


# 示例 v2：修改版本
#   - process_data 未变
#   - calculate 参数从 2 个 (a,b) 变为 3 个 (a,b,c=0)
#   - 新增 helper(data)
#   - DataProcessor 类新增 helper 方法
#   - legacy_func 被移除
SAMPLE_V2 = '''"""Sample file version 2 - modified version."""


def process_data(data):
    """Process the input data."""
    result = []
    for item in data:
        result.append(item * 2)
    return result


def calculate(a, b, c=0):
    """Calculate something with extra param."""
    return a + b + c


def helper(data):
    """Helper function - newly added."""
    return [x for x in data if x > 0]


class DataProcessor:
    """Process data class."""

    def __init__(self):
        self.cache = {}

    def run(self, data):
        return process_data(data)

    def helper(self, x):
        return helper(x)
'''


def create_samples():
    """Create sample_v1.py and sample_v2.py in current directory."""
    with open('sample_v1.py', 'w', encoding='utf-8') as f:
        f.write(SAMPLE_V1)
    with open('sample_v2.py', 'w', encoding='utf-8') as f:
        f.write(SAMPLE_V2)
    print(f"[demo] 创建 sample_v1.py ({len(SAMPLE_V1)} bytes)")
    print(f"[demo] 创建 sample_v2.py ({len(SAMPLE_V2)} bytes)")


def run_codediff():
    """Invoke codediff.py on the two samples and capture output."""
    print("\n[demo] 运行 CodeDiff 分析 sample_v1.py vs sample_v2.py ...")
    if not os.path.exists('codediff.py'):
        print("[demo] 错误: 当前目录找不到 codediff.py")
        return None, -1
    result = subprocess.run(
        [sys.executable, 'codediff.py', 'sample_v1.py', 'sample_v2.py'],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    print("--- codediff.py 输出 ---")
    print(result.stdout)
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr)
    if result.returncode != 0:
        print(f"[demo] 错误: codediff.py 退出码 {result.returncode}")
        return None, result.returncode
    return result.stdout, result.returncode


def parse_diff_output(output):
    """Parse codediff output into (added, removed, modified) lists of raw lines."""
    added, removed, modified = [], [], []
    for line in output.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('+ '):
            added.append(s)
        elif s.startswith('- '):
            removed.append(s)
        elif s.startswith('~ '):
            modified.append(s)
    return added, removed, modified


def extract_name(line):
    """Extract entity name from a diff line like '+ 函数: foo (args...)'."""
    if ':' in line:
        rest = line.split(':', 1)[1].strip()
        name = rest.split('(')[0].strip()
        return name
    return line.strip()


def extract_modified_detail(line):
    """For a modified line, return the bracketed detail like '(参数从2个变为3个)'."""
    if '(' in line:
        start = line.find('(')
        end = line.find(')', start)
        if end != -1:
            return line[start:end + 1]
    return ''


def build_summary(added, removed, modified):
    """Build a one-line summary string from parsed lists."""
    parts = []
    if added:
        names = [extract_name(l) for l in added]
        parts.append("新增: " + ", ".join(names))
    if removed:
        names = [extract_name(l) for l in removed]
        parts.append("删除: " + ", ".join(names))
    if modified:
        bits = []
        for l in modified:
            name = extract_name(l)
            detail = extract_modified_detail(l)
            bits.append(f"{name} {detail}".strip())
        parts.append("修改: " + "; ".join(bits))
    if not parts:
        return "无结构差异"
    return " | ".join(parts)


def main():
    print("=" * 64)
    print(" CodeDiff 价值证明 Demo ")
    print("=" * 64)

    # 1. 创建示例文件
    create_samples()

    # 2. 调用 codediff.py（命令行方式，模拟真实使用场景）
    output, rc = run_codediff()
    if output is None:
        sys.exit(1)

    # 3. 解析输出，打印一行摘要
    added, removed, modified = parse_diff_output(output)
    summary = build_summary(added, removed, modified)
    print("\n[demo] 结构差异摘要:")
    print(f"  {summary}")

    # 4. 验收 diff_report.txt 是否生成
    report_path = 'diff_report.txt'
    if os.path.exists(report_path):
        size = os.path.getsize(report_path)
        print(f"\n[demo] 验证: {report_path} 已生成 ({size} bytes)  [OK]")
    else:
        print(f"\n[demo] 验证失败: {report_path} 未生成  [FAIL]")
        sys.exit(1)

    # 5. 打印价值证明数据（机器可读的"至少一组数字"）
    print("\n" + "=" * 64)
    print(" 价值证明 / Value Proof ")
    print("=" * 64)
    print(f"  自动生成的代码文件数:       2")
    print(f"  检测到的结构变更 (新增):    {len(added)}")
    print(f"  检测到的结构变更 (删除):    {len(removed)}")
    print(f"  检测到的结构变更 (修改):    {len(modified)}")
    print(f"  diff_report.txt 大小:       {os.path.getsize(report_path)} bytes")
    print(f"  摘要输出:")
    print(f"    {summary}")
    print(f"  关键点: 用户无需逐行读 diff，从上面一行即可知道核心变更")

    print("\n[demo] 完成. ✓")


if __name__ == '__main__':
    main()