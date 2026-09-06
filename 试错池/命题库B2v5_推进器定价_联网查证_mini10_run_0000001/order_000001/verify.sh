#!/bin/bash
set -e
echo "=== 当前目录 ==="
pwd
ls -la *.md 运行命令.txt make_pricing_table.py

echo ""
echo "=== 条款 1: 竞品定价全景.md 含 http + Devin ==="
grep -q "http" 竞品定价全景.md && grep -q "Devin" 竞品定价全景.md && echo "PASS 1"

echo ""
echo "=== 条款 2: 付费意愿证据.md > 10 行 ==="
LINES=$(wc -l < 付费意愿证据.md)
if [ "$LINES" -gt 10 ]; then echo "PASS 2 (lines=$LINES)"; else echo "FAIL 2"; exit 1; fi

echo ""
echo "=== 条款 3: 三档定价方案.md 含 低 + 高 ==="
grep -q "低" 三档定价方案.md && grep -q "高" 三档定价方案.md && echo "PASS 3"

echo ""
echo "=== 条款 4: 前100用户获客.md >= 1500 行 ==="
LINES=$(wc -l < 前100用户获客.md)
if [ "$LINES" -ge 1500 ]; then echo "PASS 4 (lines=$LINES)"; else echo "FAIL 4"; exit 1; fi

echo ""
echo "=== 条款 5: 需核清单.md > 5 行 ==="
LINES=$(wc -l < 需核清单.md)
if [ "$LINES" -gt 5 ]; then echo "PASS 5 (lines=$LINES)"; else echo "FAIL 5"; exit 1; fi

echo ""
echo "=== 条款 6: 运行命令.txt 第一行 ==="
cat 运行命令.txt
echo "---"
head -1 运行命令.txt | xargs -I {} sh -c "timeout 60 {} && echo OK"
echo "=== ALL DONE ==="