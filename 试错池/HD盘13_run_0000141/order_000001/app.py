#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDIBS 网站服务 - 客户端与控制端
单文件 Flask 应用，端口 8765
"""
import json
import os
from flask import Flask, request, render_template, redirect, url_for, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'hdibs-light-of-science-2024'

# 密码配置
CLIENT_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"

# 内容文件
CONTENT_FILE = os.path.join(BASE_DIR, 'content.json')

# 路径资源配置
PATH_RESOURCES = {
    'physics': ['光学', '力学', '电学', '量子力学', '热学'],
    'chemistry': ['无机化学', '有机化学', '环境化学'],
    'biology': ['神经生物学', '其他生物学']
}

CATEGORY_NAMES = {
    'physics': '物理学',
    'chemistry': '化学',
    'biology': '生物学'
}


def default_content():
    return {
        "about": {
            "main": "HDIBS 是一个致力于为贫困地区学生普及科学知识的公益社团。我们相信，每一个孩子都有探索科学、热爱科学的权利。",
            "presidents": "（历任社长信息）\n\n第一届社长：张同学\n第二届社长：李同学\n第三届社长：王同学"
        },
        "members": [
            {"name": "社长", "text": "本社长寄语：希望科学之光照亮每个孩子的心田。"},
            {"name": "副社长", "text": "负责社团日常事务与科普内容审核。"},
            {"name": "学术部部长", "text": "组织科普讲座与实验活动。"},
            {"name": "宣传部部长", "text": "负责科普内容的编辑与推广。"},
            {"name": "活动部部长", "text": "策划线下科普活动，走进校园。"},
            {"name": "外联部部长", "text": "对接公益资源与合作伙伴。"},
            {"name": "成员", "text": "热爱科学，志愿为贫困地区学生服务。"},
            {"name": "成员", "text": "热爱科学，志愿为贫困地区学生服务。"},
            {"name": "成员", "text": "热爱科学，志愿为贫困地区学生服务。"},
            {"name": "成员", "text": "热爱科学，志愿为贫困地区学生服务。"}
        ]
    }


def load_content():
    if not os.path.exists(CONTENT_FILE):
        c = default_content()
        save_content(c)
        return c
    try:
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = default_content()
    # 保证结构完整
    if 'about' not in data:
        data['about'] = default_content()['about']
    if 'members' not in data:
        data['members'] = default_content()['members']
    while len(data['members']) < 10:
        data['members'].append({"name": f"成员{len(data['members'])+1}", "text": ""})
    return data


def save_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_client():
    return session.get('role') == 'client'


def is_admin():
    return session.get('role') == 'admin'


def require_client():
    if not is_client():
        return redirect(url_for('index'))
    return None


def require_admin():
    if not is_admin():
        return redirect(url_for('index'))
    return None


@app.route('/')
def index():
    if is_admin():
        return redirect(url_for('admin_home'))
    if is_client():
        return redirect(url_for('client_home'))
    return render_template('login.html', error=None, status=200)


@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    if password == CLIENT_PASSWORD:
        session['role'] = 'client'
        return redirect(url_for('client_home'))
    elif password == ADMIN_PASSWORD:
        session['role'] = 'admin'
        return redirect(url_for('admin_home'))
    else:
        return render_template('login.html', error='密码错误，请重新输入', status=401), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ============== 客户端 ==============

@app.route('/client/home')
def client_home():
    guard = require_client()
    if guard:
        return guard
    content = load_content()
    return render_template('client_home.html',
                           content=content,
                           path_resources=PATH_RESOURCES,
                           category_names=CATEGORY_NAMES)


@app.route('/client/about')
def client_about():
    guard = require_client()
    if guard:
        return guard
    content = load_content()
    return render_template('client_about.html', content=content)


@app.route('/client/members')
def client_members():
    guard = require_client()
    if guard:
        return guard
    content = load_content()
    members = content.get('members', [])[:10]
    while len(members) < 10:
        members.append({"name": f"成员{len(members)+1}", "text": ""})
    return render_template('client_members.html', members=members)


@app.route('/client/path/<category>/<topic>')
def client_path(category, topic):
    guard = require_client()
    if guard:
        return guard
    if category not in PATH_RESOURCES:
        return '页面不存在', 404
    if topic not in PATH_RESOURCES[category]:
        return '页面不存在', 404
    cat_name = CATEGORY_NAMES.get(category, category)
    return render_template('path_page.html',
                           category=category,
                           topic=topic,
                           cat_name=cat_name)


# ============== 控制端 ==============

@app.route('/admin/home')
def admin_home():
    guard = require_admin()
    if guard:
        return guard
    return render_template('admin_home.html')


@app.route('/admin/edit')
def admin_edit():
    guard = require_admin()
    if guard:
        return guard
    content = load_content()
    members = content.get('members', [])[:10]
    while len(members) < 10:
        members.append({"name": f"成员{len(members)+1}", "text": ""})
    return render_template('admin_edit.html', content=content, members=members)


@app.route('/admin/update', methods=['POST'])
def admin_update():
    guard = require_admin()
    if guard:
        return guard
    content = load_content()
    if 'about' not in content:
        content['about'] = default_content()['about']
    if 'members' not in content:
        content['members'] = default_content()['members']

    # 更新关于HDIBS正文
    if 'about_main' in request.form:
        content['about']['main'] = request.form.get('about_main', '')
    if 'about_presidents' in request.form:
        content['about']['presidents'] = request.form.get('about_presidents', '')

    members = content['members']
    while len(members) < 10:
        members.append({"name": f"成员{len(members)+1}", "text": ""})

    for i in range(10):
        name_key = f'member_{i}_name'
        text_key = f'member_{i}_text'
        if name_key in request.form:
            members[i]['name'] = request.form.get(name_key, members[i].get('name', ''))
        if text_key in request.form:
            members[i]['text'] = request.form.get(text_key, '')

    content['members'] = members
    save_content(content)
    return redirect(url_for('admin_edit'))


# 健康检查 / 简单探针
@app.route('/health')
def health():
    return {'status': 'ok', 'port': 8765}


if __name__ == '__main__':
    print('=' * 50)
    print('HDIBS 网站已启动')
    print('访问地址: http://localhost:8765/')
    print('客户端密码:', CLIENT_PASSWORD)
    print('控制端密码:', ADMIN_PASSWORD)
    print('=' * 50)
    app.run(host='0.0.0.0', port=8765, debug=False)