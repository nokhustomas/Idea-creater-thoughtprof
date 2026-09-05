#!/bin/bash
# build.sh - 大字版每日用药提醒卡构建脚本
# 用法: sh build.sh
# 产物: card.html (源文件), card.pdf (A4 打印版，可贴冰箱)
# 适用: 王奶奶, 78 岁, 独居, 早中晚睡前 4 个时段共 4 种药

set -e

cd "$(dirname "$0")"

HTML_FILE="card.html"
PDF_FILE="card.pdf"

# ---------- 前置检查 ----------
[ -f "$HTML_FILE" ] || { echo "❌ 缺少源文件 $HTML_FILE"; exit 1; }

echo "🔨 构建大字版用药提醒卡..."

# ---------- 选择 PDF 工具 ----------
PDF_TOOL=""

if command -v wkhtmltopdf >/dev/null 2>&1; then
    PDF_TOOL="wkhtmltopdf"
elif command -v weasyprint >/dev/null 2>&1; then
    PDF_TOOL="weasyprint"
elif command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1; then
    PDF_TOOL="chrome"
fi

# 都没有就尝试装一个 weasyprint (纯 Python, 跨平台)
if [ -z "$PDF_TOOL" ]; then
    echo "⚙️  未检测到 PDF 工具，尝试 pip 安装 weasyprint ..."
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install --quiet weasyprint 2>/dev/null && PDF_TOOL="weasyprint" || true
    fi
    if [ -z "$PDF_TOOL" ] && command -v pip >/dev/null 2>&1; then
        pip install --quiet weasyprint 2>/dev/null && PDF_TOOL="weasyprint" || true
    fi
fi

[ -n "$PDF_TOOL" ] || { echo "❌ 找不到 PDF 工具 (wkhtmltopdf / weasyprint / chromium)"; exit 1; }

echo " 使用 $PDF_TOOL 生成 A4 PDF ..."

# ---------- 生成 PDF ----------
case "$PDF_TOOL" in
    wkhtmltopdf)
        wkhtmltopdf \
            --page-size A4 \
            --margin 8mm \
            --encoding UTF-8 \
            --enable-local-file-access \
            --print-media-type \
            --no-background \
            "$HTML_FILE" "$PDF_FILE"
        ;;
    weasyprint)
        weasyprint \
            --presentational-hints \
            "$HTML_FILE" "$PDF_FILE"
        ;;
    chrome)
        CHROME_BIN="$(command -v chromium || command -v chromium-browser || command -v google-chrome)"
        "$CHROME_BIN" \
            --headless=new \
            --disable-gpu \
            --no-sandbox \
            --hide-scrollbars \
            --no-pdf-header-footer \
            --print-to-pdf="$PDF_FILE" \
            --virtual-time-budget=2000 \
            "file://$(pwd)/$HTML_FILE"
        ;;
esac

# ---------- 验证 ----------
if [ ! -s "$PDF_FILE" ]; then
    echo "❌ $PDF_FILE 生成失败或为空文件"
    exit 1
fi

# 刷新 mtime 保险一下
touch "$PDF_FILE"

HTML_BYTES=$(wc -c < "$HTML_FILE" | tr -d ' ')
PDF_BYTES=$(wc -c < "$PDF_FILE" | tr -d ' ')

echo ""
echo "✅ 构建完成!"
echo "   📄  $HTML_FILE : $HTML_BYTES bytes"
echo "     $PDF_FILE  : $PDF_BYTES bytes"
echo "   🖨️   浏览器打开 $HTML_FILE 或直接打印 $PDF_FILE 即可贴冰箱"