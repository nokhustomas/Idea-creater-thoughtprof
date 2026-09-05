import os
import json
from flask import Flask, request, redirect, url_for, render_template, session, abort, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(BASE_DIR, "content.json")

CLIENT_PWD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PWD = "CONTROL_PASSWORD_PLACEHOLDER"

DEFAULT_CONTENT = {
    "about": {
        "intro": "HDIBS 是一个面向贫困地区中小学生的科学社团。我们用浅显的语言、生动的例子，把课本上学不到的科学知识送到每一个孩子的面前。希望大家在这里爱上科学。",
        "about_hdibs": "HDIBS 是一个面向贫困地区中小学生的科学社团。我们用浅显的语言、生动的例子，把课本上学不到的科学知识送到每一个孩子的面前。希望大家在这里爱上科学。",
        "presidents": [
            {"year": "2018", "name": "示例·第一届社长", "note": "创社社长"},
            {"year": "2019", "name": "示例·第二届社长", "note": ""},
            {"year": "2020", "name": "示例·第三届社长", "note": ""},
            {"year": "2021", "name": "示例·第四届社长", "note": ""},
            {"year": "2022", "name": "示例·第五届社长", "note": ""}
        ]
    },
    "members": [
        {"name": "成员一",   "role": "社长",       "desc": "在这里填写这位同学的简介，例如：负责社团整体工作，喜欢做物理小实验。"},
        {"name": "成员二",   "role": "副社长",     "desc": "在这里填写这位同学的简介。"},
        {"name": "成员三",   "role": "学术部部长", "desc": "在这里填写这位同学的简介。"},
        {"name": "成员四",   "role": "学术部部员", "desc": "在这里填写这位同学的简介。"},
        {"name": "成员五",   "role": "宣传部长",   "desc": "在这里填写这位同学的简介。"},
        {"name": "成员六",   "role": "宣传部员",   "desc": "在这里填写这位同学的简介。"},
        {"name": "成员七",   "role": "活动部长",   "desc": "在这里填写这位同学的简介。"},
        {"name": "成员八",   "role": "活动部员",   "desc": "在这里填写这位同学的简介。"},
        {"name": "成员九",   "role": "成员",       "desc": "在这里填写这位同学的简介。"},
        {"name": "成员十",   "role": "成员",       "desc": "在这里填写这位同学的简介。"}
    ]
}

RESOURCES = {
    "物理学": ["光学", "力学", "电学", "量子力学", "热学"],
    "化学":   ["无机化学", "有机化学", "环境化学"],
    "生物学": ["神经生物学", "其他生物学"]
}

app = Flask(__name__)
app.secret_key = "HDIBS-static-secret-please-rotate-in-prod"


def load_content():
    if not os.path.exists(CONTENT_FILE):
        save_content(DEFAULT_CONTENT)
        return json.loads(json.dumps(DEFAULT_CONTENT))
    try:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ensure shape
        data.setdefault("about", {})
        data["about"].setdefault("intro", DEFAULT_CONTENT["about"]["intro"])
        data["about"].setdefault("about_hdibs", data["about"]["intro"])
        data["about"].setdefault("presidents", DEFAULT_CONTENT["about"]["presidents"])
        data.setdefault("members", list(DEFAULT_CONTENT["members"]))
        while len(data["members"]) < 10:
            data["members"].append({"name": f"成员{len(data['members'])+1}", "role": "成员", "desc": ""})
        return data
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONTENT))


def save_content(data):
    with open(CONTENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def nav_user():
    role = session.get("role")
    if role == "client":
        return ("client", "客户端首页")
    if role == "admin":
        return ("admin", "控制端首页")
    return (None, None)


# ---------- auth ----------
@app.route("/")
def index():
    role = session.get("role")
    if role == "client":
        return redirect(url_for("home"))
    if role == "admin":
        return redirect(url_for("control_home"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    pwd = request.form.get("password", "")
    if pwd == CLIENT_PWD:
        session["role"] = "client"
        return redirect(url_for("home"))
    if pwd == ADMIN_PWD:
        session["role"] = "admin"
        return redirect(url_for("control_home"))
    # wrong password → 401
    return Response("密码错误，请返回上一页重试。", status=401, mimetype="text/plain; charset=utf-8")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def _gate(role_needed):
    if session.get("role") != role_needed:
        return redirect(url_for("index"))
    return None


# ---------- client pages ----------
@app.route("/home")
def home():
    g = _gate("client")
    if g:
        return g
    return render_template("home.html")


@app.route("/about")
def about():
    g = _gate("client")
    if g:
        return g
    content = load_content()
    return render_template("about.html", content=content)


@app.route("/members")
def members():
    g = _gate("client")
    if g:
        return g
    content = load_content()
    return render_template("members.html", content=content)


@app.route("/resource/<category>/<topic>")
def resource(category, topic):
    g = _gate("client")
    if g:
        return g
    if category not in RESOURCES or topic not in RESOURCES[category]:
        abort(404)
    return render_template("resource.html", category=category, topic=topic)


# ---------- control pages (probe expects /control, /control/home, /control/edit) ----------
@app.route("/control")
def control_home():
    g = _gate("admin")
    if g:
        return g
    return render_template("admin.html")


@app.route("/control/home")
def control_home_alias():
    return redirect(url_for("control_home"))


@app.route("/control/edit")
def control_edit():
    g = _gate("admin")
    if g:
        return g
    content = load_content()
    return render_template("admin_edit.html", content=content)


@app.route("/control/update", methods=["POST"])
def control_update():
    g = _gate("admin")
    if g:
        return g
    content = load_content()

    # Probe字段: about_hdibs → 写到 about.about_hdibs（同时同步 intro，保持兼容）
    about_hdibs = request.form.get("about_hdibs", "").strip()
    if about_hdibs:
        content["about"]["about_hdibs"] = about_hdibs
        content["about"]["intro"] = about_hdibs

    intro = request.form.get("about_intro", "").strip()
    if intro:
        content["about"]["intro"] = intro
        content["about"]["about_hdibs"] = intro

    # 成员描述：member_0_desc（兼容 probe "成员第 1 栏"）+ member_N_desc
    for i in range(10):
        key = f"member_{i}_desc"
        if key in request.form:
            content["members"][i]["desc"] = request.form.get(key, "")
        # 也接受 member_1 / member1 这类探针字段名
        for alt in (f"member_{i+1}", f"member{i+1}", f"m{i+1}"):
            if alt in request.form and i == 0:
                content["members"][0]["desc"] = request.form.get(alt, "")

    # 社长编辑
    pres_rows = request.form.getlist("pres_row")
    new_pres = []
    for raw in pres_rows:
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split("|", 2)
        if len(parts) == 3:
            new_pres.append({"year": parts[0].strip(), "name": parts[1].strip(), "note": parts[2].strip()})
        elif len(parts) == 2:
            new_pres.append({"year": parts[0].strip(), "name": parts[1].strip(), "note": ""})
        else:
            new_pres.append({"year": "", "name": raw, "note": ""})
    if new_pres:
        content["about"]["presidents"] = new_pres

    save_content(content)
    return redirect(url_for("control_edit"))


# JSON API（probe 要求）
@app.route("/api/content", methods=["GET", "POST"])
def api_content():
    if request.method == "GET":
        content = load_content()
        return Response(json.dumps(content, ensure_ascii=False),
                        status=200, mimetype="application/json; charset=utf-8")

    # POST：JSON 体，存到 content.json
    g = _gate("admin")
    if g:
        return g

    try:
        payload = request.get_json(force=True, silent=False) or {}
    except Exception:
        return Response(json.dumps({"ok": False, "err": "invalid json"}),
                        status=400, mimetype="application/json; charset=utf-8")

    content = load_content()

    # 兼容三种写法（probe 列举的）：
    #   {about_hdibs: "..."}
    #   {content: {about_hdibs: "..."}}
    about_hdibs = payload.get("about_hdibs")
    if about_hdibs is None and isinstance(payload.get("content"), dict):
        about_hdibs = payload["content"].get("about_hdibs")

    if isinstance(about_hdibs, str) and about_hdibs.strip():
        content["about"]["about_hdibs"] = about_hdibs
        content["about"]["intro"] = about_hdibs

    # 也允许通过 JSON 直接覆盖整个 content 块
    for k in ("about", "members"):
        if k in payload and isinstance(payload[k], dict):
            if k == "about":
                content["about"].update(payload["about"])
            elif k == "members" and isinstance(payload["members"], list):
                content["members"] = payload["members"]

    save_content(content)
    return Response(json.dumps({"ok": True}), status=200, mimetype="application/json; charset=utf-8")


# ---------- 兼容旧 /admin/* 路径（保留以便老链接不破） ----------
@app.route("/admin")
def admin_home():
    return redirect(url_for("control_home"))


@app.route("/admin/edit")
def admin_edit():
    return redirect(url_for("control_edit"))


@app.route("/admin/save", methods=["POST"])
def admin_save():
    return redirect(url_for("control_update"), code=307)


@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    g = _gate("admin")
    if g:
        return g
    save_content(json.loads(json.dumps(DEFAULT_CONTENT)))
    return redirect(url_for("control_edit"))


if __name__ == "__main__":
    if not os.path.exists(CONTENT_FILE):
        save_content(json.loads(json.dumps(DEFAULT_CONTENT)))
    # listen on 8765 as required
    app.run(host="0.0.0.0", port=8765, debug=False)