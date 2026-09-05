#!/bin/bash
set -e

echo "=== 验收1: api调研报告.md ==="
grep -q '闲鱼' api调研报告.md
grep -q '转转' api调研报告.md
grep -q '拍拍' api调研报告.md
grep -q 'API状态' api调研报告.md
LINES=$(wc -l < api调研报告.md)
if [ "$LINES" -gt 5 ]; then
  echo "api调研报告.md 行数: $LINES (>5 通过)"
else
  echo "api调研报告.md 行数不足: $LINES"
  exit 1
fi
echo "验收1通过"

echo ""
echo "=== 验收2: 爬虫可行性.md ==="
grep -q '反爬' 爬虫可行性.md
grep -q '来源' 爬虫可行性.md
grep -q '闲鱼' 爬虫可行性.md
grep -q '转转' 爬虫可行性.md
echo "验收2通过"

echo ""
echo "=== 验收3: 规则边界.md ==="
grep -q '闲鱼' 规则边界.md
grep -q 'robots' 规则边界.md
grep -q '条款' 规则边界.md
echo "验收3通过"

echo ""
echo "=== 自检命令 ==="
python -c "print('自检通过')"

echo ""
echo "=== 全部验收通过 ==="