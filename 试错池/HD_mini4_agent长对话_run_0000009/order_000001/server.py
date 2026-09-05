#!/usr/bin/env python3
# server.py - 备用启动入口（与 app.py 同等服务）
# 用法：python3 server.py
# 端口：8765
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)