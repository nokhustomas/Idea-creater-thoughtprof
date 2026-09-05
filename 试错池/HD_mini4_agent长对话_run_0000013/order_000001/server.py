#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py - 与 app.py 等价的启动入口。
可直接运行: python3 server.py
默认监听 0.0.0.0:8765
"""
from app import app, load_content

if __name__ == "__main__":
    load_content()
    app.run(host="0.0.0.0", port=8765, debug=False)