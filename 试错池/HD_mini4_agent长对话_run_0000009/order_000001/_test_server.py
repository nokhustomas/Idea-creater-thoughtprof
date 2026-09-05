"""临时测试入口，使用 18765 端口避免与占用 8765 的进程冲突"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=18765, debug=False, use_reloader=False)