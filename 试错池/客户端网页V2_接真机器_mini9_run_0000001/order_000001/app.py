#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
想法推进器 V2 客户端网页系统
接真机器，读取真实队列、档案、总账。题面池目录不存在时自动创建。

使用：
    python3 app.py                    # 默认 8080 端口启动
    python3 app.py --port 9000        # 指定端口
    python3 app.py --check            # 检查模式：验证能读到 TJ_ROOT 下三个真文件
    TJ_DEMO=1 python3 app.py          # 演示模式：自动创建目录
"""
import argparse
import json
import os
import sys
import time
import uuid
import zipfile
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ----------------------------- 路径与目录 -----------------------------
DEFAULT_TJ_ROOT = "/opt/tuijinqi"

def get_tj_root():
    return os.environ.get("TJ_ROOT", DEFAULT_TJ_ROOT)


def ensure_dirs(tj_root):
    """确保题面池、logs 等目录存在（演示模式或首次启动时）。"""
    dirs = [
        os.path.join(tj_root, "题面池"),
        os.path.join(tj_root, "logs"),
        os.path.join(tj_root, "命题库"),
        os.path.join(tj_root, "runs"),
    ]
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass


# ----------------------------- 定价 -----------------------------
PRICING = {
    "basic":    {"name": "基础档", "price": 0,    "rounds": 2, "desc": "免费体验：2 轮自愈，适合先尝鲜"},
    "pro":      {"name": "进阶档", "price": 29,   "rounds": 4, "desc": "企业版低价锚点：4 轮自愈，性价比首选"},
    "enterprise": {"name": "企业档", "price": 199, "rounds": 8, "desc": "高端深度服务：8 轮自愈，结果更稳"},
}

DEFAULT_PASSWORD = "admin123"


# ----------------------------- 业务逻辑 -----------------------------
def read_queue(tj_root):
    p = os.path.join(tj_root, "logs", "队列.txt")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    except FileNotFoundError:
        return []


def read_ledger(tj_root):
    p = os.path.join(tj_root, "logs", "自愈总账.txt")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    except FileNotFoundError:
        return []


def read_topic_bank_ledger(tj_root):
    p = os.path.join(tj_root, "命题库", "命题库总账.txt")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    except FileNotFoundError:
        return []


def list_runs(tj_root):
    runs_dir = os.path.join(tj_root, "runs")
    runs = []
    if not os.path.isdir(runs_dir):
        return runs
    for name in sorted(os.listdir(runs_dir)):
        rd = os.path.join(runs_dir, name)
        if os.path.isdir(rd):
            runs.append(name)
    return runs


def infer_run_status(tj_root, run_name):
    """按 验收.txt / llm_usage.jsonl 真实推断状态。"""
    rd = os.path.join(tj_root, "runs", run_name)
    verify = os.path.join(rd, "验收.txt")
    usage = os.path.join(rd, "llm_usage.jsonl")
    status = "排队中"
    calls = 0
    last_line = ""
    if os.path.exists(verify):
        try:
            with open(verify, "r", encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f if l.strip()]
            if lines:
                last_line = lines[-1]
                if last_line.startswith("结果 达标"):
                    status = "达标"
                elif last_line.startswith("结果 未达标"):
                    status = "未达标·重跑中"
                else:
                    status = "在跑"
        except OSError:
            status = "在跑"
    if os.path.exists(usage):
        try:
            with open(usage, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            json.loads(line)
                            calls += 1
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass
    if status == "在跑" and calls > 0:
        status = f"在跑·已调用 {calls} 次"
    return {"run": run_name, "status": status, "calls": calls, "verify_last": last_line}


def next_order_no(tj_root):
    """自增单号：取 logs/队列.txt 中已出现的最大 客户<单号> +1。"""
    max_n = 0
    try:
        with open(os.path.join(tj_root, "logs", "队列.txt"), "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split("|")
                if len(parts) >= 2:
                    tag = parts[1].strip()
                    if tag.startswith("客户"):
                        rest = tag[2:]
                        try:
                            max_n = max(max_n, int(rest))
                        except ValueError:
                            pass
    except FileNotFoundError:
        pass
    return max_n + 1


def submit_order(tj_root, text, tier):
    """提交一单：写题面文件 + 队列追加一行。"""
    ensure_dirs(tj_root)
    order_no = next_order_no(tj_root)
    filename = f"客户_{order_no}.txt"
    problem_path = os.path.join(tj_root, "题面池", filename)
    with open(problem_path, "w", encoding="utf-8") as f:
        f.write(text or "")
    queue_path = os.path.join(tj_root, "logs", "队列.txt")
    line = f"{problem_path}|客户{order_no}|{tier}|0\n"
    with open(queue_path, "a", encoding="utf-8") as f:
        f.write(line)
    return {"order_no": order_no, "file": problem_path, "tier": tier}


def safe_out_path(tj_root, requested):
    """下载路径校验：必须落在 $TJ_ROOT/runs/.../out/ 内，否则返回 None。"""
    runs_dir = os.path.realpath(os.path.join(tj_root, "runs"))
    requested = requested.lstrip("/").replace("..", "").strip()
    target = os.path.realpath(os.path.join(runs_dir, requested))
    if not target.startswith(runs_dir + os.sep):
        return None
    out_marker = os.sep + "out" + os.sep
    if out_marker not in target:
        return None
    if not os.path.isfile(target):
        return None
    return target


# ----------------------------- HTTP -----------------------------
HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>想法推进器 V2</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:920px;margin:24px auto;padding:0 16px;color:#222}
h1{margin-bottom:4px}
.nav a{margin-right:12px;text-decoration:none;color:#06c}
.card{border:1px solid #ddd;border-radius:8px;padding:14px;margin:12px 0;background:#fafafa}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;background:#eef;font-size:12px;margin-left:6px}
table{border-collapse:collapse;width:100%;margin-top:8px}
th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:14px}
th{background:#f0f0f0}
.passed{color:#0a7d2c}.failed{color:#b00020}.running{color:#a05a00}.queued{color:#666}
textarea{width:100%;min-height:120px;padding:8px;border:1px solid #ccc;border-radius:6px}
select,button{padding:6px 12px;border:1px solid #ccc;border-radius:6px;background:#fff}
button{background:#06c;color:#fff;border-color:#06c;cursor:pointer}
button:hover{background:#055ab3}
</style></head><body>"""
HTML_FOOT = "</body></html>"


def render_index():
    cards = ""
    for k, v in PRICING.items():
        price_text = "免费" if v["price"] == 0 else f"¥{v['price']}"
        cards += f"""<div class="card">
<strong>{v['name']}</strong><span class="tag">{price_text} · {v['rounds']} 轮</span>
<p>{v['desc']}</p></div>"""
    body = f"""<h1>想法推进器 V2</h1>
<p>把您的一句话想法交给我们，开盘、推敲、制作、自检、出成品，全流程服务。</p>
<div class="nav"><a href="/">提交</a><a href="/progress">进度</a><a href="/download">成品</a></div>
<h2>定价</h2>
{cards}
<h2>提交题目</h2>
<form method="POST" action="/submit">
<label>档位：<select name="tier">
<option value="basic">基础档（免费，2 轮）</option>
<option value="pro">进阶档（¥29，4 轮）</option>
<option value="enterprise">企业档（¥199，8 轮）</option>
</select></label><br><br>
<label>客户原话：</label><br>
<textarea name="text" placeholder="把您的一句话想法写在这里…" required></textarea><br><br>
<button type="submit">提交</button>
</form>"""
    return HTML_HEAD + body + HTML_FOOT


def render_progress(tj_root):
    runs = list_runs(tj_root)
    rows = ""
    for r in runs:
        info = infer_run_status(tj_root, r)
        cls = "queued"
        s = info["status"]
        if s == "达标":
            cls = "passed"
        elif s == "未达标·重跑中":
            cls = "failed"
        elif s.startswith("在跑"):
            cls = "running"
        rows += f"<tr><td>{info['run']}</td><td class='{cls}'>{s}</td><td>{info['calls']}</td><td><a href='/download?run={info['run']}'>查看成品</a></td></tr>"
    body = f"""<h1>进度</h1>
<div class="nav"><a href="/">提交</a><a href="/progress">进度</a><a href="/download">成品</a></div>
<p>共 {len(runs)} 个 run。</p>
<table><tr><th>run</th><th>状态</th><th>模型调用次数</th><th>操作</th></tr>
{rows or '<tr><td colspan=4>暂无 run</td></tr>'}
</table>"""
    return HTML_HEAD + body + HTML_FOOT


def render_download(tj_root):
    runs = list_runs(tj_root)
    items = ""
    for r in runs:
        out_dir = os.path.join(tj_root, "runs", r, "out")
        if os.path.isdir(out_dir):
            for f in sorted(os.listdir(out_dir)):
                items += f"<li><a href='/download?file={r}/{f}'>{r}/{f}</a></li>"
    body = f"""<h1>成品下载</h1>
<div class="nav"><a href="/">提交</a><a href="/progress">进度</a><a href="/download">成品</a></div>
<ul>{items or '<li>暂无成品</li>'}</ul>"""
    return HTML_HEAD + body + HTML_FOOT


def render_submitted(order):
    body = f"""<h1>已提交</h1>
<div class="nav"><a href="/">提交</a><a href="/progress">进度</a><a href="/download">成品</a></div>
<div class="card">
<p>单号：客户{order['order_no']}</p>
<p>档位：{PRICING.get(order['tier'], {}).get('name', order['tier'])}</p>
<p>题面文件：<code>{order['file']}</code></p>
<p>已写入题面池目录，并追加到 logs/队列.txt。守护进程开盘后会到进度页更新状态。</p>
<p><a href="/progress">查看进度</a></p>
</div>"""
    return HTML_HEAD + body + HTML_FOOT


def render_login():
    body = f"""<h1>需要口令</h1>
<div class="card"><p>请用 Authorization 头传口令，或在下方输入。</p>
<form method="POST" action="/login">
<label>口令：</label><input type="password" name="pwd">
<button type="submit">进入</button>
</form></div>"""
    return HTML_HEAD + body + HTML_FOOT


class Handler(BaseHTTPRequestHandler):
    tj_root = get_tj_root()
    password = os.environ.get("TJ_PASSWORD", DEFAULT_PASSWORD)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))

    def _authorized(self):
        auth = self.headers.get("Authorization", "")
        if auth == self.password or auth == f"Bearer {self.password}":
            return True
        return False

    def _send_html(self, code, body):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path, display_name=None):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            self._send_html(404, f"<h1>404</h1><p>{e}</p>")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        disp = display_name or os.path.basename(path)
        self.send_header("Content-Disposition", f'attachment; filename="{disp}"')
        self.end_headers()
        self.wfile.write(data)

    def _send_zip(self, files, zip_name="download.zip"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                if os.path.isfile(p):
                    zf.write(p, arcname=os.path.basename(p))
        data = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{zip_name}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._authorized():
            self._send_html(401, render_login())
            return
        u = urlparse(self.path)
        path = u.path
        qs = parse_qs(u.query)
        if path in ("/", "/index"):
            self._send_html(200, render_index())
        elif path == "/progress":
            self._send_html(200, render_progress(self.tj_root))
        elif path == "/download":
            # 单文件下载
            if "file" in qs:
                req = qs["file"][0]
                safe = safe_out_path(self.tj_root, req)
                if safe is None:
                    self._send_html(404, HTML_HEAD + "<h1>404</h1><p>路径越界或文件不存在</p>" + HTML_FOOT)
                    return
                self._send_file(safe)
                return
            # 整个 run 打包下载
            if "run" in qs:
                run_name = qs["run"][0]
                out_dir = os.path.join(self.tj_root, "runs", run_name, "out")
                if not os.path.isdir(out_dir):
                    self._send_html(404, HTML_HEAD + "<h1>404</h1><p>无成品</p>" + HTML_FOOT)
                    return
                files = [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
                files = [f for f in files if os.path.isfile(f)]
                if not files:
                    self._send_html(404, HTML_HEAD + "<h1>404</h1><p>空目录</p>" + HTML_FOOT)
                    return
                self._send_zip(files, zip_name=f"{run_name}_成品.zip")
                return
            self._send_html(200, render_download(self.tj_root))
        elif path == "/healthz":
            data = json.dumps({"ok": True, "tj_root": self.tj_root, "demo": bool(os.environ.get("TJ_DEMO"))}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send_html(404, HTML_HEAD + "<h1>404</h1>" + HTML_FOOT)

    def do_POST(self):
        if not self._authorized():
            self._send_html(401, render_login())
            return
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in ctype:
            from urllib.parse import parse_qs as _pq
            params = _pq(raw.decode("utf-8"))
        elif "multipart/form-data" in ctype:
            # 极简解析：取 boundary
            params = {}
            try:
                boundary = ctype.split("boundary=")[1].split(";")[0].strip().strip('"').encode()
                parts = raw.split(b"--" + boundary)
                for part in parts:
                    if not part or part.strip() == b"--" or part.strip() == b"":
                        continue
                    if b"\r\n\r\n" in part:
                        head, body = part.split(b"\r\n\r\n", 1)
                        body = body.rstrip(b"\r\n")
                        # 取 name
                        name = ""
                        for h in head.split(b"\r\n"):
                            if h.lower().startswith(b"content-disposition"):
                                for kv in h.decode("utf-8", "ignore").split(";"):
                                    kv = kv.strip()
                                    if kv.startswith("name="):
                                        name = kv.split("=", 1)[1].strip('"')
                                        break
                                break
                        if name:
                            params[name] = [body.decode("utf-8", "ignore")]
            except Exception:
                params = {}
        else:
            params = {}
        if u.path == "/submit":
            text = (params.get("text", [""])[0] or "").strip()
            tier = (params.get("tier", ["basic"])[0] or "basic").strip()
            if tier not in PRICING:
                tier = "basic"
            if not text:
                self._send_html(400, HTML_HEAD + "<h1>题面不能为空</h1>" + HTML_FOOT)
                return
            order = submit_order(self.tj_root, text, tier)
            self._send_html(200, render_submitted(order))
        elif u.path == "/login":
            pwd = (params.get("pwd", [""])[0] or "").strip()
            if pwd == self.password:
                self._send_html(200, HTML_HEAD + "<h1>已登录</h1><p><a href='/'>进入主页</a></p>" + HTML_FOOT)
            else:
                self._send_html(401, render_login())
        else:
            self._send_html(404, HTML_HEAD + "<h1>404</h1>" + HTML_FOOT)


# ----------------------------- 入口 -----------------------------
def do_check(tj_root):
    """检查模式：验证能读到三个真文件。"""
    targets = [
        os.path.join(tj_root, "logs", "队列.txt"),
        os.path.join(tj_root, "logs", "自愈总账.txt"),
        os.path.join(tj_root, "命题库", "命题库总账.txt"),
    ]
    missing = [p for p in targets if not os.path.exists(p)]
    if missing:
        print(f"[check] 缺少文件：{missing}", file=sys.stderr)
        return 1
    for p in targets:
        try:
            with open(p, "r", encoding="utf-8") as f:
                _ = f.read(1)
        except OSError as e:
            print(f"[check] 读取失败：{p}: {e}", file=sys.stderr)
            return 1
    print(f"[check] OK TJ_ROOT={tj_root}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="想法推进器 V2 客户端网页")
    parser.add_argument("--port", type=int, default=8080, help="HTTP 端口（默认 8080）")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--check", action="store_true", help="只校验 TJ_ROOT 下三个真文件可读")
    args = parser.parse_args()

    tj_root = get_tj_root()
    Handler.tj_root = tj_root

    if args.check:
        sys.exit(do_check(tj_root))

    demo = bool(os.environ.get("TJ_DEMO"))
    if demo:
        ensure_dirs(tj_root)
        print(f"[demo] TJ_DEMO=1，已确保 TJ_ROOT={tj_root} 下目录存在", file=sys.stderr)
    else:
        ensure_dirs(tj_root)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"想法推进器 V2 监听 http://{args.host}:{args.port}/  TJ_ROOT={tj_root}  demo={demo}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()