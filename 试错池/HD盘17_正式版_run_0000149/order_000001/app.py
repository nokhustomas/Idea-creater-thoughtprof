import os
import json
import threading
from flask import Flask, request, redirect, url_for, render_template, make_response, abort

app = Flask(__name__)
app.secret_key = "hdibs-light-secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(BASE_DIR, "content.json")

DEFAULT_CONTENT = {
    "client_home_intro": "希望你可以在这里燃起你对科学的兴趣。",
    "about_hdibs": "这里是关于HDIBS社团的介绍。控制端可编辑此段正文。",
    "about_history": "历任社长：（待填写）",
    "members": [{"photo": "", "text": "成员 {}".format(i + 1)} for i in range(10)],
}

_content_lock = threading.Lock()


def load_content():
    if not os.path.exists(CONTENT_PATH):
        with open(CONTENT_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONTENT, f, ensure_ascii=False, indent=2)
        return json.loads(json.dumps(DEFAULT_CONTENT))
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception:
            data = json.loads(json.dumps(DEFAULT_CONTENT))
    members = data.get("members")
    if not isinstance(members, list):
        members = []
    while len(members) < 10:
        members.append({"photo": "", "text": "成员 {}".format(len(members) + 1)})
    members = members[:10]
    data["members"] = members
    for k, v in DEFAULT_CONTENT.items():
        if k not in data:
            data[k] = v
    return data


def save_content(data):
    with _content_lock:
        with open(CONTENT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


CLIENT_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"


def is_client_authed(req):
    return req.cookies.get("client_auth") == CLIENT_PASSWORD


def is_admin_authed(req):
    return req.cookies.get("admin_auth") == ADMIN_PASSWORD


# ---------------- Auth pages ----------------

@app.route("/", methods=["GET"])
def root():
    if is_admin_authed(request):
        return redirect(url_for("admin_home"))
    if is_client_authed(request):
        return redirect(url_for("client_home"))
    return render_template("login.html", role="client")


@app.route("/login", methods=["POST"])
def login_post():
    pw = request.form.get("password", "")
    if pw == CLIENT_PASSWORD:
        resp = redirect(url_for("client_home"))
        resp.set_cookie("client_auth", CLIENT_PASSWORD, max_age=60 * 60 * 8, httponly=True)
        return resp
    if pw == ADMIN_PASSWORD:
        resp = redirect(url_for("admin_home"))
        resp.set_cookie("admin_auth", ADMIN_PASSWORD, max_age=60 * 60 * 8, httponly=True)
        return resp
    return make_response(render_template("login.html", role="client", error="密码错误，请重试"), 401)


@app.route("/logout", methods=["GET"])
def logout():
    resp = redirect(url_for("root"))
    resp.delete_cookie("client_auth")
    resp.delete_cookie("admin_auth")
    return resp


# ---------------- Client pages ----------------

@app.route("/client", methods=["GET"])
def client_home():
    if not is_client_authed(request):
        return redirect(url_for("root"))
    content = load_content()
    return render_template("client_home.html", client_home_intro=content.get("client_home_intro", ""))


@app.route("/client/about", methods=["GET"])
def client_about():
    if not is_client_authed(request):
        return redirect(url_for("root"))
    content = load_content()
    return render_template(
        "client_about.html",
        about_hdibs=content.get("about_hdibs", ""),
        about_history=content.get("about_history", ""),
    )


@app.route("/client/members", methods=["GET"])
def client_members():
    if not is_client_authed(request):
        return redirect(url_for("root"))
    content = load_content()
    return render_template("client_members.html", members=content.get("members", []))


# Path resources — 10 blank subpages
PATH_TREE = {
    "物理学": ["光学", "力学", "电学", "量子力学", "热学"],
    "化学": ["无机化学", "有机化学", "环境化学"],
    "生物学": ["神经生物学", "其他生物学"],
}


@app.route("/client/resources", methods=["GET"])
def client_resources():
    if not is_client_authed(request):
        return redirect(url_for("root"))
    return render_template("client_resources.html")


@app.route("/client/resources/<category>/<path:topic>", methods=["GET"])
def client_resources_topic(category, topic):
    if not is_client_authed(request):
        return redirect(url_for("root"))
    if category not in PATH_TREE or topic not in PATH_TREE[category]:
        abort(404)
    return render_template("client_resources_topic.html", category=category, topic=topic)


@app.route("/client/api/content", methods=["GET"])
def client_api_content():
    return app.response_class(
        response=json.dumps(load_content(), ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


# ---------------- Admin pages (legacy /admin/*) ----------------

@app.route("/admin", methods=["GET"])
def admin_home():
    if not is_admin_authed(request):
        return redirect(url_for("root"))
    return render_template("admin_home.html")


@app.route("/admin/edit", methods=["GET"])
def admin_edit():
    if not is_admin_authed(request):
        return redirect(url_for("root"))
    return render_template("admin_edit.html", content=load_content())


# ---------------- Admin pages (alias /control/* for acceptance) ----------------

@app.route("/control", methods=["GET"])
def control_home():
    if not is_admin_authed(request):
        return redirect(url_for("root"))
    return render_template("admin_home.html")


@app.route("/control/home", methods=["GET"])
def control_home_alias():
    if not is_admin_authed(request):
        return redirect(url_for("root"))
    return render_template("admin_home.html")


@app.route("/control/edit", methods=["GET"])
def control_edit():
    if not is_admin_authed(request):
        return redirect(url_for("root"))
    return render_template("admin_edit.html", content=load_content())


# ---------------- Content update helpers ----------------

def _apply_update(payload):
    """Apply an update payload to current content. Returns the new content dict."""
    cur = load_content()
    if not isinstance(payload, dict):
        payload = {}

    # Accept both flat and nested (content.about_hdibs) shapes.
    sources = [payload]
    nested = payload.get("content") if isinstance(payload.get("content"), dict) else None
    if nested is not None:
        sources.append(nested)

    for src in sources:
        if "about_hdibs" in src and isinstance(src["about_hdibs"], str):
            cur["about_hdibs"] = src["about_hdibs"]
        if "about_history" in src and isinstance(src["about_history"], str):
            cur["about_history"] = src["about_history"]
        if "client_home_intro" in src and isinstance(src["client_home_intro"], str):
            cur["client_home_intro"] = src["client_home_intro"]
        members_payload = src.get("members")
        if isinstance(members_payload, list):
            new_members = []
            for i in range(10):
                item = members_payload[i] if i < len(members_payload) and isinstance(members_payload[i], dict) else {}
                new_members.append({
                    "photo": str(item.get("photo", "") or ""),
                    "text": str(item.get("text", "") or ""),
                })
            cur["members"] = new_members

    save_content(cur)
    return cur


def _form_update():
    """Build a payload dict from a standard HTML form POST."""
    payload = {}
    for key in ("about_hdibs", "about_history", "client_home_intro"):
        if key in request.form:
            payload[key] = request.form.get(key, "")
    if "members" in request.form:
        # Not commonly used; allow JSON in a single field if present.
        try:
            payload["members"] = json.loads(request.form.get("members", "[]"))
        except Exception:
            payload["members"] = []
    return payload


# ---------------- Update endpoints (POST) ----------------

@app.route("/admin/api/content", methods=["POST"])
def admin_api_content_post():
    if not is_admin_authed(request):
        return make_response("未授权", 401)
    payload = request.get_json(silent=True)
    if payload is None:
        payload = _form_update()
    cur = _apply_update(payload)
    return app.response_class(
        response=json.dumps({"ok": True, "about_hdibs": cur.get("about_hdibs", "")}, ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


@app.route("/api/content", methods=["POST"])
def api_content_post():
    if not is_admin_authed(request):
        return make_response("未授权", 401)
    payload = request.get_json(silent=True)
    if payload is None:
        payload = _form_update()
    cur = _apply_update(payload)
    return app.response_class(
        response=json.dumps({"ok": True, "about_hdibs": cur.get("about_hdibs", "")}, ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


@app.route("/control/update", methods=["POST"])
def control_update_post():
    if not is_admin_authed(request):
        return make_response("未授权", 401)
    payload = request.get_json(silent=True)
    if payload is None:
        payload = _form_update()
    cur = _apply_update(payload)
    return app.response_class(
        response=json.dumps({"ok": True, "about_hdibs": cur.get("about_hdibs", "")}, ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


@app.route("/api/content", methods=["GET"])
def api_content_get():
    return app.response_class(
        response=json.dumps(load_content(), ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


@app.route("/admin/api/content", methods=["GET"])
def admin_api_content_get():
    if not is_admin_authed(request):
        return make_response("未授权", 401)
    return app.response_class(
        response=json.dumps(load_content(), ensure_ascii=False),
        status=200,
        mimetype="application/json",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    app.run(host="0.0.0.0", port=port, debug=False)