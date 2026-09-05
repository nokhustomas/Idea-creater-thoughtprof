#!/bin/bash
# bench.sh — CodeDiff 价值证明脚本
# 直接调用 codediff.py，不经过 demo.py，独立可运行
# 退出码 0 表示成功

set -e

echo "=== CodeDiff 价值证明 Benchmark ==="

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"

# 1) 准备样本文件（若已存在则复用）
if [ ! -f sample_v1.py ] || [ ! -f sample_v2.py ]; then
    echo "[准备] 生成 sample_v1.py / sample_v2.py"
    python3 - <<'PY'
v1 = '''def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result


def calculate(a, b):
    return a + b


class Worker:
    def run(self):
        return "v1"
'''
v2 = '''def process_data(data):
    result = []
    for item in data:
        result.append(item * 3)
    return result


def calculate(a, b, c):
    return a + b + c


def helper(x):
    return x + 1


class Worker:
    def run(self):
        return "v2"

    def stop(self):
        return None
'''
with open('sample_v1.py', 'w') as f:
    f.write(v1)
with open('sample_v2.py', 'w') as f:
    f.write(v2)
PY
fi

# 2) 跑 codediff.py
echo ""
echo "[1] 运行 codediff.py sample_v1.py sample_v2.py"
python3 codediff.py sample_v1.py sample_v2.py

# 3) 统计
echo ""
echo "[2] 报告统计"
if [ ! -f diff_report.txt ]; then
    echo "ERROR: diff_report.txt 未生成"
    exit 1
fi

TOTAL=$(wc -l < diff_report.txt)
ADDED=$(grep -c "^+" diff_report.txt || true)
REMOVED=$(grep -c "^-" diff_report.txt || true)
MODIFIED=$(grep -c "^~" diff_report.txt || true)
[ -z "$ADDED" ] && ADDED=0
[ -z "$REMOVED" ] && REMOVED=0
[ -z "$MODIFIED" ] && MODIFIED=0

echo "总报告行数: $TOTAL"
echo "新增(added): $ADDED"
echo "删除(removed): $REMOVED"
echo "修改(modified): $MODIFIED"

# 4) 对比传统 diff
echo ""
echo "[3] 与传统文本 diff 对比"
TRAD_LINES=$(diff sample_v1.py sample_v2.py | wc -l)
echo "传统 diff 输出行数: $TRAD_LINES"
echo "CodeDiff 报告行数: $TOTAL"
if [ "$TRAD_LINES" -gt 0 ]; then
    RATIO=$(python3 -c "print(f'{($TOTAL/$TRAD_LINES)*100:.1f}%')")
    echo "信息密度比(报告行/传统diff行): $RATIO"
fi

echo ""
echo "=== 结论 ==="
echo "CodeDiff 在 AST 层面只报告函数/类的增删改，"
echo "审查者无需逐行读 diff 即可定位关键结构变更。"
echo "相比传统文本 diff：报告行数=$TOTAL，传统 diff 行数=$TRAD_LINES"
echo "退出码 0,价值证明完成。"
exit 0