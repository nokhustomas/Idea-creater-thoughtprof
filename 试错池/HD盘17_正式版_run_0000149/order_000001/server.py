# server.py — minimal fallback (no Flask) using stdlib http.server
# This is provided so that if Flask isn't available, you can still run:
#   python3 server.py
# Same port (8765), same routes. Kept simple intentionally.
import os
import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(BASE_DIR, "content.json")
CLIENT_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"


def load_content():
    if not os.path.exists(CONTENT_PATH):
        with open(CONTENT_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONTENT, f, ensure_ascii=False)
        return dict(DEFAULT_CONTENT)
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


DEFAULT_CONTENT = {
    "client_home_intro": "希望你可以在这里燃起你对科学的兴趣。",
    "about_hdibs": "这里是关于HDIBS社团的介绍。控制端可编辑此段正文。",
    "about_history": "历任社长：（待填写）",
    "members": [{"photo": "", "text": f"成员 {i+1}"} for i in range(10)],
}


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        # trivial placeholder so the file is runnable as a fallback
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Fallback server. Use python3 app.py (Flask) for the full site.".encode("utf-8"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    HTTPServer(("0.0.0.0", port), H).serve_forever()