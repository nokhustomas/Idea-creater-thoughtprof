import json
import os
import threading
from flask import Flask, request, render_template, redirect, url_for, abort

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(BASE_DIR, "content.json")
_content_lock = threading.Lock()

CLIENT_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"

PATH_TREE = {
    "物理学": ["光学", "力学", "电学", "量子力学", "热学"],
    "化学": ["无机化学", "有机化学", "环境化学"],
    "生物学": ["神经生物学", "其他生物学"],
}


def load_content():
    if not os.path.exists(CONTENT_PATH):
        return {"site_title": "HDIBS", "about_text": "", "presidents": [], "members": []}
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_content(data):
    with _content_lock:
        tmp = CONTENT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONTENT_PATH)


@app.route("/", methods=["GET"])
def index():
    # 入口即登录页
    return render_template("login.html", error=None)


@app.route("/login", methods=["POST"])
def login():
    pwd = request.form.get("password", "")
    if pwd == CLIENT_PASSWORD:
        return redirect(url_for("client_home"))
    if pwd == ADMIN_PASSWORD:
        return redirect(url_for("admin_home"))
    # 错误密码
    resp = app.make_response(render_template("login.html", error="密码错误，请重新输入"))
    resp.status_code = 401
    return resp


@app.route("/client", methods=["GET"])
def client_home():
    data = load_content()
    return render_template("client_home.html", data=data)


@app.route("/client/about", methods=["GET"])
def client_about():
    data = load_content()
    return render_template("client_about.html", data=data)


@app.route("/client/members", methods=["GET"])
def client_members():
    data = load_content()
    return render_template("client_members.html", data=data)


@app.route("/client/path", methods=["GET"])
def client_path():
    return render_template("client_path.html", path_tree=PATH_TREE)


@app.route("/client/path/<cat>/<sub>", methods=["GET"])
def client_path_blank(cat, sub):
    # 校验分类与子项合法
    if cat not in PATH_TREE:
        abort(404)
    if sub not in PATH_TREE[cat]:
        abort(404)
    return render_template("client_blank.html", title=f"{cat} - {sub}")


# 控制端
@app.route("/admin", methods=["GET"])
def admin_home():
    return render_template("admin_home.html")


@app.route("/admin/edit", methods=["GET", "POST"])
def admin_edit():
    if request.method == "POST":
        data = load_content()
        about_text = request.form.get("about_text", "")
        if about_text != "":
            data["about_text"] = about_text
        # 处理社员（保证至少 10 个槽位）
        members = data.get("members", [])
        while len(members) < 10:
            members.append({"name": f"成员{len(members)+1}", "role": "", "intro": ""})
        m1_name = request.form.get("member1_name", "")
        m1_role = request.form.get("member1_role", "")
        m1_intro = request.form.get("member1_intro", "")
        if m1_name != "":
            members[0]["name"] = m1_name
        if m1_role != "":
            members[0]["role"] = m1_role
        if m1_intro != "":
            members[0]["intro"] = m1_intro
        data["members"] = members
        save_content(data)
        return redirect(url_for("admin_edit"))
    data = load_content()
    members = data.get("members", [])
    while len(members) < 10:
        members.append({"name": f"成员{len(members)+1}", "role": "", "intro": ""})
    return render_template("admin_edit.html", data=data, members=members)


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)