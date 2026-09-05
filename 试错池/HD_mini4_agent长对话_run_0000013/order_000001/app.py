#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDIBS 科学之光 网站 - 控制端 + 客户端
启动: python3 app.py
默认端口: 8765
"""
import json
import os
import threading
from flask import Flask, request, redirect, url_for, session, render_template, jsonify, abort

app = Flask(__name__)
app.secret_key = "HDIBS_SECRET_KEY_CHANGE_ME_IN_PROD_2024"

# ---------- 配置 ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(BASE_DIR, "content.json")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

CLIENT_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"

# ---------- content.json 默认内容 ----------
DEFAULT_CONTENT = {
    "site_title": "HDIBS",
    "about": {
        "about_hdibs_title": "关于HDIBS",
        "about_hdibs_body": "HDIBS 是一个致力于为贫困地区学生科普科学知识的学生社团。我们希望通过简单、生动的方式，让每一位孩子都能感受到科学的魅力。",
        "presidents_title": "历任社长",
        "presidents_body": "第一届社长：张同学\n第二届社长：李同学\n第三届社长：王同学\n第四届社长：赵同学\n第五届社长：陈同学"
    },
    "members": [
        {"name": "成员 1", "intro": "这是第一位社团成员的介绍文字，你可以在控制端修改它。"},
        {"name": "成员 2", "intro": "这是第二位社团成员的介绍文字。"},
        {"name": "成员 3", "intro": "这是第三位社团成员的介绍文字。"},
        {"name": "成员 4", "intro": "这是第四位社团成员的介绍文字。"},
        {"name": "成员 5", "intro": "这是第五位社团成员的介绍文字。"},
        {"name": "成员 6", "intro": "这是第六位社团成员的介绍文字。"},
        {"name": "成员 7", "intro": "这是第七位社团成员的介绍文字。"},
        {"name": "成员 8", "intro": "这是第八位社团成员的介绍文字。"},
        {"name": "成员 9", "intro": "这是第九位社团成员的介绍文字。"},
        {"name": "成员 10", "intro": "这是第十位社团成员的介绍文字。"}
    ],
    "resource_pages": {
        "光学": {"title": "光学", "body": "光学知识页面 - 待填充"},
        "力学": {"title": "力学", "body": "力学知识页面 - 待填充"},
        "电学": {"title": "电学", "body": "电学知识页面 - 待填充"},
        "量子力学": {"title": "量子力学", "body": "量子力学知识页面 - 待填充"},
        "热学": {"title": "热学", "body": "热学知识页面 - 待填充"},
        "无机化学": {"title": "无机化学", "body": "无机化学知识页面 - 待填充"},
        "有机化学": {"title": "有机化学", "body": "有机化学知识页面 - 待填充"},
        "环境化学": {"title": "环境化学", "body": "环境化学知识页面 - 待填充"},
        "神经生物学": {"title": "神经生物学", "body": "神经生物学知识页面 - 待填充"},
        "其他生物学": {"title": "其他生物学", "body": "其他生物学知识页面 - 待填充"}
    }
}

_content_lock = threading.Lock()

def load_content():
    if not os.path.exists(CONTENT_FILE):
        save_content(DEFAULT_CONTENT)
        return json.loads(json.dumps(DEFAULT_CONTENT))
    try:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = False
        for k, v in DEFAULT_CONTENT.items():
            if k not in data:
                data[k] = json.loads(json.dumps(v))
                changed = True
        if changed:
            save_content(data)
        return data
    except Exception:
        save_content(DEFAULT_CONTENT)
        return json.loads(json.dumps(DEFAULT_CONTENT))

def save_content(data):
    with _content_lock:
        with open(CONTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

@app.context_processor
def inject_content():
    return {"content": load_content()}

@app.route("/", methods=["GET"])
def index():
    role = session.get("role")
    if role == "client":
        return redirect(url_for("client_home"))
    if role == "admin":
        return redirect(url_for("admin_home"))
    return render_template("login.html", error=None)

@app.route("/login", methods=["POST"])
def login():
    pwd = request.form.get("password", "")
    if pwd == CLIENT_PASSWORD:
        session["role"] = "client"
        session.permanent = False
        return redirect(url_for("client_home"))
    if pwd == ADMIN_PASSWORD:
        session["role"] = "admin"
        session.permanent = False
        return redirect(url_for("admin_home"))
    return render_template("login.html", error="密码错误，请重试。"), 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/client")
def client_home():
    if session.get("role") not in ("client", "admin"):
        return redirect(url_for("index"))
    return render_template("client_home.html")

@app.route("/about")
def about_page():
    return render_template("about.html")

@app.route("/members")
def members_page():
    return render_template("members.html")

RESOURCE_MAP = {
    "guangxue": "光学",
    "lixue": "力学",
    "dianxue": "电学",
    "liangzi": "量子力学",
    "rexue": "热学",
    "wuji": "无机化学",
    "youji": "有机化学",
    "huanjing": "环境化学",
    "shenjing": "神经生物学",
    "qita": "其他生物学",
}

@app.route("/resource/<key>")
def resource_page(key):
    if key not in RESOURCE_MAP:
        abort(404)
    name = RESOURCE_MAP[key]
    return render_template("resource_blank.html", page_name=name)

@app.route("/admin")
def admin_home():
    if session.get("role") != "admin":
        return redirect(url_for("index"))
    return render_template("admin_home.html")

@app.route("/admin/edit", methods=["GET", "POST"])
def admin_edit():
    if session.get("role") != "admin":
        return redirect(url_for("index"))
    data = load_content()
    msg = None
    if request.method == "POST":
        about_body = request.form.get("about_hdibs_body", "")
        if about_body:
            data["about"]["about_hdibs_body"] = about_body
        m1_name = request.form.get("member_1_name", "")
        m1_intro = request.form.get("member_1_intro", "")
        if m1_name or m1_intro:
            if len(data["members"]) >= 1:
                if m1_name:
                    data["members"][0]["name"] = m1_name
                if m1_intro:
                    data["members"][0]["intro"] = m1_intro
        presidents_body = request.form.get("presidents_body", "")
        if presidents_body:
            data["about"]["presidents_body"] = presidents_body
        save_content(data)
        msg = "保存成功！"
    return render_template("admin_edit.html", data=data, msg=msg)

@app.route("/api/content")
def api_content():
    return jsonify(load_content())

if __name__ == "__main__":
    load_content()
    app.run(host="0.0.0.0", port=8765, debug=False)