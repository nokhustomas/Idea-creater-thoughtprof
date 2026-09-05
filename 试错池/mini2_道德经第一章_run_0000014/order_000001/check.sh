#!/bin/bash
# 验收脚本：检查 读后感.md 与 对照.md 是否全部达标
# 退出码：0=全部通过，1=存在失败
cd "$(dirname "$0")"

PASS=0
FAIL=0
report() {
    if [ "$1" = "ok" ]; then
        echo "  ✅ $2"
        PASS=$((PASS+1))
    else
        echo "  ❌ $2"
        FAIL=$((FAIL+1))
    fi
}

echo "【1】两个文件都存在"
[ -e 读后感.md ] && report ok "读后感.md 存在" || report no "读后感.md 不存在"
[ -e 对照.md ]   && report ok "对照.md 存在"   || report no "对照.md 不存在"

echo "【2】两个文件都非空"
[ -s 读后感.md ] && report ok "读后感.md 非空" || report no "读后感.md 为空"
[ -s 对照.md ]   && report ok "对照.md 非空"   || report no "对照.md 为空"

echo "【3】读后感.md 含「道可道」四字"
grep -q "道可道" 读后感.md && report ok "读后感.md 含「道可道」" || report no "读后感.md 缺「道可道」"

echo "【4】读后感.md 正文不少于八百汉字"
HZ=$(awk '{gsub(/[^\x00-\x7F]/,"U"); h+=length($0)} END{print h+0}' 读后感.md)
if [ "$HZ" -ge 800 ]; then
    report ok "读后感.md 汉字数=$HZ ≥800"
else
    report no "读后感.md 汉字数=$HZ <800"
fi

echo "【5】读后感.md 段数 3-5 段"
SEG=$(awk 'NF==0{blank++} blank==0 && NR>1{lines++} END{print lines+0}' 读后感.md)
if [ "$SEG" -ge 3 ] && [ "$SEG" -le 5 ]; then
    report ok "读后感.md 段数=$SEG (3-5 段)"
else
    report no "读后感.md 段数=$SEG (期望 3-5)"
fi

echo "【6】对照.md 至少 8 行"
ROWS=$(awk 'END{print NR}' 对照.md)
if [ "$ROWS" -ge 8 ]; then
    report ok "对照.md 行数=$ROWS ≥8"
else
    report no "对照.md 行数=$ROWS <8"
fi

echo "【7】对照.md 含全部八句原文"
for s in "道可道，非常道" "名可名，非常名" "无名天地之始" "有名万物之母" "故常无欲以观其妙" "常有欲以观其徼" "此两者同出而异名" "同谓之玄"; do
    if grep -q "$s" 对照.md; then
        report ok "对照.md 含「$s」"
    else
        report no "对照.md 缺「$s」"
    fi
done

echo ""
echo "=== 汇总：通过 $PASS 项 / 失败 $FAIL 项 ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1