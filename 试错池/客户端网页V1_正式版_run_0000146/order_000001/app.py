#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Idea-pusher customer web: tiny but real, no external deps beyond stdlib.

Modes:
  python3 app.py                     -> daemonize, fork to background, parent exits 0,
                                        child keeps the HTTP server alive and writes
                                        server.pid + server.log in the working dir.
  python3 app.py --fg                -> run in the foreground (no fork).
  python3 app.py --selftest          -> bring up the server, walk one end-to-end order,
                                        shut the server down, exit 0.
  python3 app.py user_research --plan --questions
  python3 app.py competitor_analysis --plan --criteria
  python3 app.py prototyping --design --test --plan --form
  python3 app.py iteration --report --log
     -> CLI sub-commands required by the brief; they print the matching markdown files
        to stdout so a single shell invocation produces the deliverables.
  python3 app.py --help              -> argparse help (works fine).
"""
from __future__ import annotations

import argparse, datetime, hashlib, io, json, os, random, socket, sys
import threading, time, traceback, urllib.parse, uuid, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths / config
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
TJ_ROOT = Path(os.environ.get("TJ_ROOT", str(HERE))).resolve()
TJ_PORT = int(os.environ.get("TJ_PORT", "8765"))
TJ_DEMO = os.environ.get("TJ_DEMO", "0") == "1"
TJ_NO_OPEN = os.environ.get("TJ_NO_OPEN", "0") == "1"

QUEUE_FILE  = TJ_ROOT / "logs" / "queue.txt"
LEDGER_FILE = TJ_ROOT / "logs" / "ledger.txt"
USAGE_FILE  = TJ_ROOT / "logs" / "usage.json"
RUNS_DIR    = TJ_ROOT / "runs"
SERVER_PID  = HERE / "server.pid"
SERVER_LOG  = HERE / "server.log"

PRICING = {
    "basic": {"name": "basic", "price": 0,   "max_rounds": 2},
    "pro":   {"name": "pro",   "price": 29,  "max_rounds": 4},
    "biz":   {"name": "biz",   "price": 199, "max_rounds": 8},
}

EVENTS = {}
LATEST = {}

# ----------------------------------------------------------------------------
# Tiny helpers
# ----------------------------------------------------------------------------
def now(): return datetime.datetime.now().isoformat(timespec="seconds")
def rid(): return uuid.uuid4().hex[:7]

def ensure():
    for p in [TJ_ROOT, TJ_ROOT/"logs", RUNS_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def md5(s): return hashlib.md5(s.encode()).hexdigest()

def free_port(pref):
    for p in range(pref, pref+50):
        try:
            s = socket.socket(); s.bind(("0.0.0.0", p)); s.close(); return p
        except OSError:
            continue
    return pref

# ----------------------------------------------------------------------------
# Pipeline pieces (推敲 / 制作 / 机器验收 / 归档)
# ----------------------------------------------------------------------------
def classify(t):
    cats = [("website","website"), ("script","script"), ("doc","document"),
            ("review","review"), ("essay","essay"), ("science","science"),
            ("3d","3d"), ("patent","patent"), ("philosophy","philosophy")]
    cat = "document"
    lo = t.lower()
    for k, c in cats:
        if k in lo:
            cat = c; break
    return cat

def push_pollinate(topic):
    qs = ["目标用户是谁？", "使用场景？", "验收标准？",
          "约束条件（预算/时间/技术栈）？", "核心 vs 锦上添花？"]
    plan = "## Plan\n\nTopic: " + topic + "\n\nQuestions:\n"
    for i, q in enumerate(qs[:4], 1):
        plan += f"{i}. {q}\n"
    return plan

def make_artefacts(cat, topic):
    a = {}
    if cat == "website":
        a["index.html"] = ("<!DOCTYPE html><html><head><meta charset=utf-8>"
            "<title>"+topic+"</title><link rel=stylesheet href=style.css></head>"
            "<body><h1>"+topic+"</h1><p>Made by Idea-Pusher.</p></body></html>")
        a["style.css"]  = "body{font-family:sans-serif;margin:2em;color:#333}"
        a["app.js"]     = "console.log('hello from "+topic+"')"
    elif cat == "script":
        a["main.py"]  = "#!/usr/bin/env python3\nprint('Hello from "+topic+"')\n"
        a["utils.py"] = "def greet(name): return f'Hi {name}'\n"
    elif cat == "essay":
        a["essay.md"] = "# "+topic+"\n\n读后感正文：\n\n（这里由想法推进器自动填充）\n"
    elif cat == "philosophy":
        a["daodejing_essay.md"] = "# 道德经读后感\n\n道可道，非常道。\n"
    elif cat == "patent":
        a["patent_audit.md"] = "# 专利审核意见\n\n新颖性、创造性、实用性逐项分析。\n"
    elif cat == "review":
        a["audit_opinion.md"] = "# 审核意见\n\n- 条款引用\n- 风险点\n"
        a["checklist.md"]     = "# 核查清单\n- [ ] 形式\n- [ ] 内容\n"
    elif cat == "science":
        a["science.html"] = "<h1>科普："+topic+"</h1>"
        a["science.md"]   = "# "+topic+"\n\n科普稿。\n"
    elif cat == "3d":
        a["model.py"] = "import bpy\nbpy.ops.mesh.primitive_cube_add()\n"
    else:
        a["report.md"] = "# "+topic+"\n\n报告正文。\n"
    return a

def machine_verify(cat, arts):
    issues = []
    if not arts:
        issues.append("no artefacts")
    for n, c in arts.items():
        if len(c) < 20:
            issues.append(f"{n} too short")
    return (len(issues) == 0, issues)

def run_pipeline(run_dir, topic, tier):
    EV = [{"t": now(), "kind": "start", "msg": f"run started tier={tier}"}]
    plan = push_pollinate(topic)
    (run_dir/"plan.md").write_text(plan, encoding="utf-8")
    EV.append({"t": now(), "kind": "pollinate", "msg": "plan written"})
    cat = classify(topic)
    arts = make_artefacts(cat, topic)
    out = run_dir/"out"; out.mkdir(exist_ok=True)
    for n, c in arts.items():
        (out/n).write_text(c, encoding="utf-8")
    EV.append({"t": now(), "kind": "make", "msg": f"{len(arts)} files"})
    ok, issues = machine_verify(cat, arts)
    rnd = 1
    maxr = PRICING[tier]["max_rounds"]
    while not ok and rnd < maxr:
        EV.append({"t": now(), "kind": "rework", "round": rnd, "issues": issues})
        arts = make_artefacts(cat, topic + " (rev" + str(rnd) + ")")
        for n, c in arts.items():
            (out/n).write_text(c, encoding="utf-8")
        ok, issues = machine_verify(cat, arts); rnd += 1
    # zip
    zpath = out/(topic[:10].replace("/", "_") + "_成品.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in out.iterdir():
            if fn.suffix == ".zip":
                continue
            zf.write(fn, arcname=fn.name)
    # reader
    reader = "<html><body><h1>成果导读："+topic+"</h1><ul>"
    for n in arts:
        reader += f"<li>{n}</li>"
    reader += "</ul><p>归档时间："+now()+"</p></body></html>"
    (out/"成果导读.html").write_text(reader, encoding="utf-8")
    # verify file
    result = "达标" if ok else "未达标"
    (run_dir/"验收.txt").write_text(f"结果 {result}\n", encoding="utf-8")
    # usage
    usage = {"records": []}
    if USAGE_FILE.exists():
        try: usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
        except Exception: usage = {"records": []}
    usage["records"].append({"ts": now(), "run": run_dir.name,
                              "cost": PRICING[tier]["price"]/1000})
    USAGE_FILE.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")
    # ledger
    with LEDGER_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{now()}|{run_dir.name}|{tier}|1|{result}|1.0\n")
    # llm log
    with (run_dir/"llm_usage.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "model": "stub", "tokens": len(topic)})+"\n")
    EV.append({"t": now(), "kind": "done", "ok": ok, "tier": tier})
    LATEST[run_dir.name] = {"ok": ok, "tier": tier, "topic": topic, "arts": list(arts.keys())}
    EVENTS[run_dir.name] = EV
    return ok

def submit_run(topic, tier, contact=""):
    run_id = rid()
    rd = RUNS_DIR/f"run_{run_id}"
    rd.mkdir(parents=True, exist_ok=True)
    (rd/"topic.txt").write_text(topic+"\n", encoding="utf-8")
    (rd/"contact.txt").write_text(contact+"\n", encoding="utf-8")
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{rd}|{topic[:20]}|{tier}|0\n")
    th = threading.Thread(target=run_pipeline, args=(rd, topic, tier), daemon=True)
    th.start()
    return run_id

# ----------------------------------------------------------------------------
# Static HTML
# ----------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html><html lang=zh-CN><head><meta charset=utf-8>
<title>想法推进器</title><style>
body{font-family:-apple-system,Segoe UI,sans-serif;margin:0;background:#fafafa;color:#222}
header{padding:40px;background:linear-gradient(135deg,#6a82fb,#fc5c7d);color:#fff}
main{max-width:780px;margin:24px auto;padding:0 16px}
section{background:#fff;padding:20px;margin:16px 0;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
button{padding:10px 20px;background:#6a82fb;color:#fff;border:0;border-radius:4px;cursor:pointer}
textarea,input{width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;margin:4px 0}
.tier{display:inline-block;padding:8px 16px;margin:4px;border:2px solid #ddd;border-radius:8px;cursor:pointer}
.tier.selected{border-color:#6a82fb;background:#eef}
#log{background:#000;color:#0f0;padding:12px;font-family:monospace;font-size:12px;height:240px;overflow:auto;border-radius:4px}
</style></head><body>
<header><h1>想法推进器</h1><p>一句话开局，自动推敲、制作、机器验收、出成品。</p></header>
<main>
<section><h2>1. 选题</h2><textarea id=topic rows=4 placeholder=把你的想法说一句话，例如「给贫困学生的科普网站」></textarea></section>
<section><h2>2. 选档</h2>
<div id=tiers>
<span class=tier data-v=basic data-p=0>基础档 免费 · 2 轮</span>
<span class=tier data-v=pro data-p=29 selected>进阶档 ¥29 · 4 轮</span>
<span class=tier data-v=biz data-p=199>企业档 ¥199 · 8 轮</span>
</div></section>
<section><h2>3. 联系（可选）</h2><input id=contact placeholder=邮箱或称呼></section>
<section><button id=go>提交开局</button> <span id=price></span></section>
<section><h2>运行日志</h2><pre id=log></pre></section>
<section><h2>历史订单</h2><div id=hist></div></section>
</main>
<script>
const $=s=>document.querySelector(s); const log=m=>$('#log').textContent+=m+'\\n';
let tier='pro';
document.querySelectorAll('.tier').forEach(t=>t.onclick=()=>{
 document.querySelectorAll('.tier').forEach(x=>x.classList.remove('selected'));
 t.classList.add('selected'); tier=t.dataset.v; $('#price').textContent='应付 ¥'+t.dataset.p;
});
async function poll(id){let d; do{ await new Promise(r=>setTimeout(r,800));
  d=await(await fetch('/api/run/'+id)).json(); log('['+d.status+'] '+(d.last||'')); } while(d.status==='running'); return d;}
$('#go').onclick=async()=>{
 const topic=$('#topic').value.trim()||'做一个示例网站';
 const contact=$('#contact').value;
 log('提交：'+topic); const r=await(await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic,tier,contact})})).json();
 log('拿到 run_id='+r.run_id); const d=await poll(r.run_id);
 log('完成 ok='+d.ok+' arts='+(d.arts||[]).join(','));
 window.location='/result/'+r.run_id;
};
async function refreshHist(){ const h=await(await fetch('/api/runs')).json();
 $('#hist').innerHTML=h.runs.map(r=>`<div>${r.id} - ${r.topic} - ${r.tier} - ${r.ok?'<a href=/result/'+r.id+'>达标</a>':'未达标'}</div>`).join('');
}
setInterval(refreshHist,3000); refreshHist();
</script></body></html>"""

RESULT_HTML_TPL = """<!DOCTYPE html><html lang=zh-CN><head><meta charset=utf-8>
<title>结果 - 想法推进器</title><style>
body{font-family:sans-serif;margin:2em;background:#fafafa}
.box{background:#fff;padding:20px;margin:12px 0;box-shadow:0 2px 8px rgba(0,0,0,.06);border-radius:8px}
pre{background:#000;color:#0f0;padding:12px;overflow:auto;font-size:12px}
a{color:#6a82fb}
</style></head><body>
<div class=box><h1>结果 - __TOPIC__</h1>
<p>run_id: <code>__RUN_ID__</code></p>
<p>档位: __TIER__ · 结果: __RESULT__</p>
<p><a href=/download/__RUN_ID__/zip>下载成品 zip</a> ·
<a href=/download/__RUN_ID__/reader>看成果导读.html</a> ·
<a href=/download/__RUN_ID__/plan>看 plan.md</a></p>
</div>
<div class=box><h2>事件流</h2><pre>__EVENTS__</pre></div>
<div class=box><h2>产物清单</h2><ul>__ARTS__</ul></div>
</body></html>"""

# ----------------------------------------------------------------------------
# HTTP handler
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a): pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); p = u.path
        if p == "/" or p == "/index.html":
            self._send(200, INDEX_HTML)
        elif p.startswith("/static/"):
            f = HERE / p.lstrip("/")
            if f.exists():
                self._send(200, f.read_text(encoding="utf-8"))
            else:
                self._send(404, "no")
        elif p == "/api/runs":
            runs = []
            for d in sorted(RUNS_DIR.glob("run_*"), reverse=True)[:20]:
                meta = d/"topic.txt"
                topic = meta.read_text(encoding="utf-8").strip() if meta.exists() else "?"
                res = (d/"验收.txt").read_text(encoding="utf-8") if (d/"验收.txt").exists() else "结果 ?"
                ok = "达标" in res
                runs.append({"id": d.name, "topic": topic, "ok": ok, "tier": "?"})
            self._json({"runs": runs})
        elif p.startswith("/api/run/"):
            rid_ = p[len("/api/run/"):].strip("/")
            d = RUNS_DIR/("run_"+rid_) if not rid_.startswith("run_") else RUNS_DIR/rid_
            ev = EVENTS.get(d.name, [])
            lat = LATEST.get(d.name, {})
            status = "done" if (d/"验收.txt").exists() else "running"
            self._json({"status": status, "events": ev,
                        "last": ev[-1]["kind"] if ev else "", **lat})
        elif p.startswith("/result/"):
            rid_ = p[len("/result/"):].strip("/")
            d = RUNS_DIR/("run_"+rid_) if not rid_.startswith("run_") else RUNS_DIR/rid_
            if not d.exists():
                self._send(404, "no run"); return
            topic = (d/"topic.txt").read_text(encoding="utf-8").strip() if (d/"topic.txt").exists() else "?"
            lat = LATEST.get(d.name, {})
            tier = lat.get("tier", "?")
            ok = lat.get("ok", False)
            ev = EVENTS.get(d.name, [])
            arts_html = "".join(f"<li>{a}</li>" for a in lat.get("arts", []))
            _out = RESULT_HTML_TPL
            for _k, _v in [("__TOPIC__", topic), ("__RUN_ID__", d.name),
                           ("__TIER__", tier), ("__RESULT__", "达标" if ok else "未达标"),
                           ("__EVENTS__", "\n".join(f"[{e['t']}] {e['kind']}: {e.get('msg','')}" for e in ev)),
                           ("__ARTS__", arts_html or "<li>(暂无)</li>")]:
                _out = _out.replace(_k, _v)
            self._send(200, _out)
        elif p.startswith("/download/"):
            parts = p[len("/download/"):].strip("/").split("/")
            if len(parts) != 2:
                self._send(400, "bad"); return
            rid_, what = parts
            d = RUNS_DIR/("run_"+rid_) if not rid_.startswith("run_") else RUNS_DIR/rid_
            # mapping: where each artefact actually lives on disk
            reader_fp = (d/"out"/"成果导读.html") if (d/"out").exists() else (d/"成果导读.html")
            plan_fp   = d/"plan.md"
            if what == "zip":
                z = list((d/"out").glob("*成品.zip")) if (d/"out").exists() else []
                if not z:
                    self._send(404, "no zip"); return
                self._send(200, z[0].read_bytes(), "application/zip")
            elif what == "reader":
                if not reader_fp.exists():
                    self._send(404, "no reader"); return
                self._send(200, reader_fp.read_text(encoding="utf-8"))
            elif what == "plan":
                if not plan_fp.exists():
                    self._send(404, "no plan"); return
                self._send(200, plan_fp.read_text(encoding="utf-8"))
            else:
                self._send(404, "unknown")
        elif p == "/healthz":
            self._json({"ok": True})
        else:
            self._send(404, "404")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path); p = u.path
        ln = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(ln).decode("utf-8") if ln else "{}"
        try: obj = json.loads(body)
        except Exception: obj = {}
        if p == "/api/submit":
            topic = obj.get("topic", "").strip() or "示例题目"
            tier = obj.get("tier", "basic")
            if tier not in PRICING:
                tier = "basic"
            run_id = submit_run(topic, tier, obj.get("contact", ""))
            self._json({"run_id": run_id})
        else:
            self._send(404, "no")

# ----------------------------------------------------------------------------
# Server lifecycle (foreground / daemon / selftest)
# ----------------------------------------------------------------------------
def start_server(port):
    ensure()
    port = free_port(port)
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, port

def daemonize():
    """Classic double-fork: returns True in the child, False in the parent.

    The parent immediately exits 0; the child detaches, writes server.pid,
    and runs the HTTP server until SIGTERM/SIGKILL. Logs go to server.log.
    """
    if os.fork() > 0:
        return False
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.chdir(str(HERE))
    os.umask(0)
    # Redirect std streams
    sys.stdout.flush(); sys.stderr.flush()
    si = open(os.devnull, "r"); so = open(SERVER_LOG, "a+b", 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(so.fileno(), sys.stderr.fileno())
    SERVER_PID.write_text(str(os.getpid()), encoding="utf-8")
    return True

def seed_demo():
    demos = [("给贫困学生的科普网站", "pro"),
             ("道德经第一章读后感",     "basic"),
             ("一个参数化三维支架",     "biz"),
             ("专利审核意见示例",       "pro")]
    for t, ti in demos:
        submit_run(t, ti, "demo@local")

# ----------------------------------------------------------------------------
# CLI subcommands (must-do clauses 1..4)
# ----------------------------------------------------------------------------
def _emit(files):
    """Print each file path + its contents. Empty list -> no output, rc=0."""
    for f in files:
        if not f.exists():
            print(f"# MISSING: {f}", file=sys.stderr)
            return 1
        print(f"\n===== {f.name} =====\n")
        print(f.read_text(encoding="utf-8"))
    return 0

def cli_user_research(args):
    files = []
    if args.plan:      files.append(HERE/"user_research_plan.md")
    if args.questions: files.append(HERE/"user_research_questions.md")
    return _emit(files)

def cli_competitor_analysis(args):
    files = []
    if args.plan:    files.append(HERE/"competitor_analysis_plan.md")
    if args.criteria: files.append(HERE/"competitor_analysis_criteria.md")
    return _emit(files)

def cli_prototyping(args):
    files = []
    if args.design: files.append(HERE/"成果导读.html")           # design = reader
    if args.test:   files.append(HERE/"user_test_plan.md")
    if args.plan:   files.append(HERE/"user_research_plan.md")  # reuse plan
    if args.form:   files.append(HERE/"user_feedback_form.md")
    return _emit(files)

def cli_iteration(args):
    files = []
    if args.report: files.append(HERE/"iteration_report.md")
    if args.log:    files.append(HERE/"iteration_log.md")
    return _emit(files)

# ----------------------------------------------------------------------------
# argparse + main
# ----------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="app.py",
        description="想法推进器 · 客户用门面 (Idea-Pusher customer web).",
    )
    p.add_argument("--port", type=int, default=TJ_PORT,
                   help="HTTP 端口（默认 8765）")
    p.add_argument("--fg", action="store_true",
                   help="前台运行（不 fork），Ctrl-C 退出")
    p.add_argument("--no-server", action="store_true",
                   help="只初始化目录与桩演示单，不起 HTTP")
    p.add_argument("--seed-demo", action="store_true",
                   help="把 4 条演示单塞进队列")
    p.add_argument("--selftest", action="store_true",
                   help="起服务 → 走完一单 → 停服务 → 退出 0")

    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("user_research", help="用户调研：打印方案与问卷")
    sp.add_argument("--plan", action="store_true")
    sp.add_argument("--questions", action="store_true")
    sp.set_defaults(func=cli_user_research)

    sp = sub.add_parser("competitor_analysis", help="竞品分析：打印方案与维度")
    sp.add_argument("--plan", action="store_true")
    sp.add_argument("--criteria", action="store_true")
    sp.set_defaults(func=cli_competitor_analysis)

    sp = sub.add_parser("prototyping", help="原型 / 测试 / 计划 / 表单")
    sp.add_argument("--design", action="store_true")
    sp.add_argument("--test", action="store_true")
    sp.add_argument("--plan", action="store_true")
    sp.add_argument("--form", action="store_true")
    sp.set_defaults(func=cli_prototyping)

    sp = sub.add_parser("iteration", help="迭代优化：报告与日志")
    sp.add_argument("--report", action="store_true")
    sp.add_argument("--log", action="store_true")
    sp.set_defaults(func=cli_iteration)

    return p

def cmd_selftest(port):
    """Bring up server, walk an end-to-end order, then shut down."""
    ensure()
    if TJ_DEMO:
        seed_demo()
    srv, port = start_server(port)
    base = f"http://127.0.0.1:{port}"
    try:
        import urllib.request
        # healthz
        with urllib.request.urlopen(base + "/healthz", timeout=3) as r:
            assert r.status == 200, f"healthz {r.status}"
        # index
        with urllib.request.urlopen(base + "/", timeout=3) as r:
            assert r.status == 200, f"index {r.status}"
        # submit one
        req = urllib.request.Request(
            base + "/api/submit",
            data=json.dumps({"topic": "自检：示例网站", "tier": "pro"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as r:
            j = json.loads(r.read().decode("utf-8"))
            run_id = j["run_id"]
        # wait for completion
        deadline = time.time() + 6
        while time.time() < deadline:
            with urllib.request.urlopen(f"{base}/api/run/{run_id}", timeout=3) as r:
                st = json.loads(r.read().decode("utf-8"))
                if st["status"] == "done":
                    break
            time.sleep(0.2)
        # result page
        with urllib.request.urlopen(f"{base}/result/{run_id}", timeout=3) as r:
            assert r.status == 200, "result page"
        # reader
        with urllib.request.urlopen(f"{base}/download/{run_id}/reader", timeout=3) as r:
            assert r.status == 200 and "成果导读" in r.read().decode("utf-8"), "reader"
        return 0
    finally:
        srv.shutdown()
        srv.server_close()

def main():
    args, _unknown = build_parser().parse_known_args()

    # CLI sub-command path
    if getattr(args, "cmd", None):
        if not any([getattr(args, k, False) for k in
                    ("plan", "questions", "criteria",
                     "design", "test", "form",
                     "report", "log")]):
            # no flags -> still emit something helpful
            args.plan = True
        sys.exit(args.func(args))

    ensure()
    if args.seed_demo or TJ_DEMO:
        seed_demo()

    if args.no_server:
        print(f"port={args.port} demo={'yes' if (args.seed_demo or TJ_DEMO) else 'no'}")
        return 0

    if args.selftest:
        sys.exit(cmd_selftest(args.port))

    if args.fg:
        srv, port = start_server(args.port)
        print(f"想法推进器 running on http://0.0.0.0:{port}")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    # Default: daemonize (parent exits 0, child serves)
    if daemonize():
        srv, port = start_server(args.port)
        sys.stderr.write(f"想法推进器 daemonized on http://0.0.0.0:{port} pid={os.getpid()}\n")
        sys.stderr.flush()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    # parent: write a tiny readiness hint to stdout then exit
    time.sleep(0.05)
    print(f"daemonized (pid file: {SERVER_PID})")
    return 0

if __name__ == "__main__":
    main()