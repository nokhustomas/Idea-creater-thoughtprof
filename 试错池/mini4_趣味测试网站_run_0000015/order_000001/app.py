#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
怪问题研究所 - 极简 Flask 后端（可选）
- 启动: python3 app.py
- 端口: 8765
- 主页: http://localhost:8765/
- 静态: index.html 直接 serve 在 /

前端已经在 index.html 里完全跑起来了（无后端依赖）。
这个 app.py 只是顺手提供 Python3 一键起的选项，符合订单里
"app.py + templates, python3 app.py 在 8765 起" 的备用交付形态。
"""
import os
from flask import Flask, send_from_directory, render_template_string

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE)

INDEX_PATH = os.path.join(BASE, "index.html")
with open(INDEX_PATH, "r", encoding="utf-8") as f:
    INDEX_HTML = f.read()


@app.route("/")
def index():
    # 直接把内嵌好的 index.html 渲出来，零额外依赖
    return INDEX_HTML


@app.route("/health")
def health():
    return {"ok": True, "app": "guaiwenti", "port": 8765}


@app.route("/<path:filename>")
def static_files(filename):
    # 防止跳出工作目录
    safe = os.path.normpath(filename)
    if safe.startswith("..") or os.path.isabs(safe):
        return ("forbidden", 403)
    return send_from_directory(BASE, filename)


if __name__ == "__main__":
    port = 8765
    print(f"[guaiwenti] serving on http://0.0.0.0:{port}/")
    app.run(host="0.0.0.0", port=port, debug=False)