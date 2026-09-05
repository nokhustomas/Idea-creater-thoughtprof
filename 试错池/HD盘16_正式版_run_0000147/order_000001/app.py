#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDIBS 科学之光 网站（客户端 + 控制端）
单文件 Flask 应用。端口 8765。
"""
import os
import json
from flask import Flask, request, redirect, url_for, render_template, abort, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(BASE_DIR, "content.json")

app = Flask(__name__, template_folder="templates", static_folder="static")

CLIENT_PWD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PWD = "CONTROL_PASSWORD_PLACEHOLDER"


def load_content():
    if not os.path.exists(CONTENT_PATH):
        # 默认初始内容（写文件版会覆盖）
        return {
            "about_hdibs": "HDIBS 是一个面向贫困地区学生的科普社团，致力于传播科学知识。",
            "history": "历任社长：\n· 第一任：张老师\n· 第二任：李同学\n· 第三任：王同学",
            "members": [
                {"name": "成员 1", "desc": "点击修改可填写介绍"},
                {"name": "成员 2", "desc": "点击修改可填写介绍"},
                {"name": "成员 3", "desc": "点击修改可填写介绍"},
                {"name": "成员 4", "desc": "点击修改可填写介绍"},
                {"name": "成员 5", "desc": "点击修改可填写介绍"},
                {"name": "成员 6", "desc": "点击修改可填写介绍"},
                {"name": "成员 7", "desc": "点击修改可填写介绍"},
                {"name": "成员 8", "desc": "点击修改可填写介绍"},
                {"name": "成员 9", "desc": "点击修改可填写介绍"},
                {"name": "成员 10", "desc": "点击修改可填写介绍"},
            ],
            "submenu": {
                "物理学": ["光学", "力学", "电学", "量子力学", "热学"],
                "化学": ["无机化学", "有机化学", "环境化学"],
                "生物学": ["神经生物学", "其他生物学"],
            },
        }
    with open(CONTENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_content(data):
    with open(CONTENT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def page_base(title, nav_role="client"):
    """渲染统一壳：返回 dict 给各路由使用"""
    return {"title": title, "role": nav_role}


# ---------- 登录 ----------
@app.route("/", methods=["GET"])
def login():
    # 登录页：显示密码输入框
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def do_login():
    pwd = request.form.get("password", "")
    if pwd == CLIENT_PWD:
        return redirect(url_for("client_home"))
    if pwd == ADMIN_PWD:
        return redirect(url_for("admin_home"))
    # 错误：回到登录页（不带"欢迎"）
    return Response(
        render_template("login.html", error="密码错误，请重新输入"),
        status=401,
        content_type="text/html; charset=utf-8",
    )


# ---------- 客户端 ----------
@app.route("/client", methods=["GET"])
def client_home():
    return render_template("client_home.html", role="client")


@app.route("/client/about", methods=["GET"])
def client_about():
    data = load_content()
    return render_template(
        "client_about.html",
        role="client",
        about=data.get("about_hdibs", ""),
        history=data.get("history", ""),
    )


@app.route("/client/members", methods=["GET"])
def client_members():
    data = load_content()
    members = data.get("members", [])
    # 保证展示 10 个（不足补空）
    while len(members) < 10:
        members.append({"name": f"成员 {len(members)+1}", "desc": ""})
    members = members[:10]
    return render_template("client_members.html", role="client", members=members)


# 路径资源 10 个空白子页
SUB_PAGES = [
    ("物理学", "光学"),
    ("物理学", "力学"),
    ("物理学", "电学"),
    ("物理学", "量子力学"),
    ("物理学", "热学"),
    ("化学", "无机化学"),
    ("化学", "有机化学"),
    ("化学", "环境化学"),
    ("生物学", "神经生物学"),
    ("生物学", "其他生物学"),
]


@app.route("/client/resource/<cat>/<sub>", methods=["GET"])
def client_resource(cat, sub):
    # 校验：是 10 个白名单之一
    if (cat, sub) not in SUB_PAGES:
        abort(404)
    return render_template("client_resource.html", role="client", cat=cat, sub=sub)


# ---------- 控制端 ----------
@app.route("/admin", methods=["GET"])
def admin_home():
    return render_template("admin_home.html", role="admin")


@app.route("/admin/edit", methods=["GET", "POST"])
def admin_edit():
    data = load_content()
    if request.method == "POST":
        # 更新关于 HDIBS
        about = request.form.get("about_hdibs")
        history = request.form.get("history")
        if about is not None:
            data["about_hdibs"] = about
        if history is not None:
            data["history"] = history
        # 更新社团成员（按 index）
        for i in range(1, 11):
            n = request.form.get(f"member_{i}_name")
            d = request.form.get(f"member_{i}_desc")
            if i - 1 < len(data["members"]):
                if n is not None:
                    data["members"][i - 1]["name"] = n
                if d is not None:
                    data["members"][i - 1]["desc"] = d
        save_content(data)
        return render_template(
            "admin_edit.html",
            role="admin",
            data=data,
            saved=True,
        )
    return render_template("admin_edit.html", role="admin", data=data, saved=False)


if __name__ == "__main__":
    # 确保 content.json 存在
    if not os.path.exists(CONTENT_PATH):
        save_content(load_content())
    app.run(host="0.0.0.0", port=8765, debug=False)