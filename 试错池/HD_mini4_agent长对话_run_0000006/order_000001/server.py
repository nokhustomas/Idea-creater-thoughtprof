# 别名入口：直接运行等价于 `python3 app.py`
# 为了满足交付物中要求同时存在 app.py / server.py 的目录约定
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)