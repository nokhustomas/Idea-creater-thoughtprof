#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
想法推进器 V2 自检脚本

TJ_DEMO=1 时：
  - 创建临时目录模拟 $TJ_ROOT 结构
  - 自动造 3 条演示 run（含 验收.txt 末行'结果 达标'、llm_usage.jsonl、out/*_成品.zip）
  - 后台启动 app.py，sleep 30 秒模拟客户走通全流程
  - 验证生成的目录和文件
  - 停止服务并退出 0（全程 60 秒内）

真模式：
  - 验证 logs/队列.txt、logs/自愈总账.txt、命题库/命题库总账.txt 三个文件存在
  - 通过则退出 0，否则退出 1
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import http.client
import urllib.parse

DEFAULT_TJ_ROOT = "/opt/tuijinqi"
DEMO_RUNS = 3
SLEEP_AFTER_START = 30
TOTAL_LIMIT = 60
DEFAULT_PASSWORD = "admin123"


def get_tj_root():
    return os.environ.get("TJ_ROOT", DEFAULT_TJ_ROOT)


def is_demo():
    return os.environ.get("TJ_DEMO") == "1"


def get_password():
    return os.environ.get("TJ_PASSWORD", DEFAULT_PASSWORD)


def log(msg):
    print(f"[selfcheck] {msg}", flush=True)


def make_demo_run(tj_root, idx):
    """造一条演示 run：run_XXXXXXX，含 验收.txt / llm_usage.jsonl / out/*_成品.zip。"""
    run_name = f"run_{idx:07d}"
    rd = os.path.join(tj_root, "runs", run_name)
    out_dir = os.path.join(rd, "out")
    os.makedirs(out_dir, exist_ok=True)

    verify_path = os.path.join(rd, "验收.txt")
    with open(verify_path, "w", encoding="utf-8") as f:
        f.write(f"run: {run_name}\n")
        f.write("步骤: 推敲+制作+自检\n")
        f.write("耗时: 12.3s\n")
        f.write("结果 达标\n")

    usage_path = os.path.join(rd, "llm_usage.jsonl")
    with open(usage_path, "w", encoding="utf-8") as f:
        for i in range(2 + idx):
            row = {
                "ts": time.time(),
                "model": "demo-model",
                "prompt_tokens": 100 + i * 10,
                "completion_tokens": 50 + i * 5,
                "call_no": i + 1,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    intro = os.path.join(out_dir, "成果导读.html")
    with open(intro, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><title>{run_name}</title>"
                f"<h1>{run_name} 成果导读</h1><p>这是演示 run {idx}。</p>")

    zip_path = os.path.join(out_dir, f"{run_name}_成品.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", f"demo run {idx} artifact\n")

    return run_name


def http_get(host, port, path, auth=None, timeout=5):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    headers = {}
    if auth:
        headers["Authorization"] = auth
    conn.request("GET", path, headers=headers)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r.status, body


def http_post(host, port, path, data, auth=None, headers=None, timeout=5):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    h = dict(headers or {})
    h["Content-Type"] = "application/x-www-form-urlencoded"
    if auth:
        h["Authorization"] = auth
    conn.request("POST", path, body=data, headers=h)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r.status, body


def wait_for_http(host, port, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=1.5)
            conn.request("GET", "/")
            r = conn.getresponse()
            r.read()
            conn.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def demo_selfcheck():
    """演示模式自检：造数据、起服务、走流程、停服务、验证。"""
    log("演示模式启动")
    started = time.time()

    tmp_root = tempfile.mkdtemp(prefix="tj_selfcheck_")
    tj_root = os.path.join(tmp_root, "tuijinqi")
    os.makedirs(tj_root, exist_ok=True)
    for sub in ["题面池", "logs", "命题库", "runs"]:
        os.makedirs(os.path.join(tj_root, sub), exist_ok=True)
    log(f"演示 TJ_ROOT = {tj_root}")

    env = os.environ.copy()
    env["TJ_ROOT"] = tj_root
    env["TJ_DEMO"] = "1"
    env["TJ_PASSWORD"] = DEFAULT_PASSWORD

    created_runs = []
    for i in range(1, DEMO_RUNS + 1):
        rn = make_demo_run(tj_root, i)
        created_runs.append(rn)
        log(f"造演示 run: {rn}")

    port = 18080
    app_log = os.path.join(tmp_root, "app.log")
    log_file = open(app_log, "w")
    proc = subprocess.Popen(
        [sys.executable, "app.py", "--port", str(port)],
        env=env, stdout=log_file, stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__)) or ".",
    )
    log(f"已启 app.py，pid={proc.pid}, port={port}")

    if not wait_for_http("127.0.0.1", port, timeout=15.0):
        log("ERROR: 服务没起来")
        try:
            proc.terminate(); proc.wait(timeout=3)
        except Exception:
            pass
        log_file.close()
        shutil.rmtree(tmp_root, ignore_errors=True)
        return 1
    log("服务起来了")

    time.sleep(SLEEP_AFTER_START)

    ok = True

    # 文件结构校验
    for rn in created_runs:
        rd = os.path.join(tj_root, "runs", rn)
        verify = os.path.join(rd, "验收.txt")
        usage = os.path.join(rd, "llm_usage.jsonl")
        out_dir = os.path.join(rd, "out")
        if not (os.path.isfile(verify) and os.path.isfile(usage) and os.path.isdir(out_dir)):
            log(f"ERROR: run {rn} 缺文件")
            ok = False
            continue
        try:
            with open(verify, "r", encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f if l.strip()]
            if not lines or not lines[-1].startswith("结果 达标"):
                log(f"ERROR: run {rn} 验收末行不是 '结果 达标'")
                ok = False
        except OSError:
            ok = False
        try:
            with open(usage, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        json.loads(line)
        except (OSError, json.JSONDecodeError):
            log(f"ERROR: run {rn} llm_usage.jsonl 不合法")
            ok = False
        zips = [n for n in os.listdir(out_dir) if n.endswith(".zip")]
        if not zips:
            log(f"ERROR: run {rn} out/ 下没 zip")
            ok = False

    # HTTP 走流程（带 Authorization）
    auth = f"Bearer {DEFAULT_PASSWORD}"
    try:
        st, _ = http_get("127.0.0.1", port, "/", auth=auth)
        if st != 200:
            log(f"ERROR: GET / 状态 {st}"); ok = False

        body = urllib.parse.urlencode({
            "tier": "pro",
            "text": "演示客户原话：给我做一个能跑的网页。",
        }).encode()
        st, _ = http_post("127.0.0.1", port, "/submit", body, auth=auth)
        if st != 200:
            log(f"ERROR: POST /submit 状态 {st}"); ok = False

        st, _ = http_get("127.0.0.1", port, "/progress", auth=auth)
        if st != 200:
            log(f"ERROR: GET /progress 状态 {st}"); ok = False

        st, _ = http_get("127.0.0.1", port, "/download", auth=auth)
        if st != 200:
            log(f"ERROR: GET /download 状态 {st}"); ok = False
    except Exception as e:
        log(f"ERROR: HTTP 走流程异常 {e}")
        ok = False

    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    log_file.close()
    log(f"服务已停，pid={proc.pid}")

    elapsed = time.time() - started
    log(f"耗时 {elapsed:.1f}s")

    shutil.rmtree(tmp_root, ignore_errors=True)

    if elapsed > TOTAL_LIMIT:
        log(f"ERROR: 超过 {TOTAL_LIMIT}s 限制")
        return 1
    if not ok:
        log("ERROR: 验证未通过")
        return 1
    log("演示模式自检通过")
    return 0


def real_selfcheck():
    """真模式自检：验证三个文件存在。"""
    log("真模式启动")
    tj_root = get_tj_root()
    log(f"TJ_ROOT = {tj_root}")

    required = [
        os.path.join(tj_root, "logs", "队列.txt"),
        os.path.join(tj_root, "logs", "自愈总账.txt"),
        os.path.join(tj_root, "命题库", "命题库总账.txt"),
    ]
    ok = True
    for p in required:
        if not os.path.exists(p):
            log(f"ERROR: 缺文件 {p}")
            ok = False
        else:
            log(f"OK: {p}")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="想法推进器 V2 自检")
    parser.add_argument("--check-real", action="store_true",
                        help="强制走真模式（忽略 TJ_DEMO）")
    args = parser.parse_args()

    if args.check_real or not is_demo():
        return real_selfcheck()
    return demo_selfcheck()


if __name__ == "__main__":
    sys.exit(main())