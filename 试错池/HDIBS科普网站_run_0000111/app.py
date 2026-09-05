# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, session, jsonify
import json
import os

app = Flask(__name__)
app.secret_key = 'hdibs_secret_key_435879'
CONTENT_FILE = 'content.json'

DEFAULT_CONTENT = {
    "about_hdibs": "HDIBS是一个致力于科学普及的组织。",
    "past_presidents": "历任社长信息待添加。",
    "members": [
        {"name": "成员1", "info": "个人信息1"},
        {"name": "成员2", "info": "个人信息2"},
        {"name": "成员3", "info": "个人信息3"},
        {"name": "成员4", "info": "个人信息4"},
        {"name": "成员5", "info": "个人信息5"},
        {"name": "成员6", "info": "个人信息6"},
        {"name": "成员7", "info": "个人信息7"},
        {"name": "成员8", "info": "个人信息8"},
        {"name": "成员9", "info": "个人信息9"},
        {"name": "成员10", "info": "个人信息10"}
    ]
}

def load_content():
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONTENT

def save_content(content):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

if not os.path.exists(CONTENT_FILE):
    save_content(DEFAULT_CONTENT)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    if password == 'CLIENT_PASSWORD_PLACEHOLDER':
        session['client_logged_in'] = True
        session['control_logged_in'] = False
        return redirect('/client')
    elif password == 'CONTROL_PASSWORD_PLACEHOLDER':
        session['control_logged_in'] = True
        session['client_logged_in'] = False
        return redirect('/control')
    else:
        return render_template('login.html', error='密码错误')

@app.route('/client')
def client():
    if not session.get('client_logged_in'):
        return redirect('/')
    return render_template('client_home.html', content=load_content())

@app.route('/about')
def about():
    if not session.get('client_logged_in'):
        return redirect('/')
    return render_template('about.html', content=load_content())

@app.route('/members')
def members():
    if not session.get('client_logged_in'):
        return redirect('/')
    return render_template('members.html', content=load_content())

@app.route('/resources/<category>/<subcategory>')
def resource_page(category, subcategory):
    if not session.get('client_logged_in'):
        return redirect('/')
    return render_template('resource_page.html', category=category, subcategory=subcategory)

@app.route('/control')
def control():
    if not session.get('control_logged_in'):
        return redirect('/')
    return render_template('control_home.html')

@app.route('/edit')
def edit():
    if not session.get('control_logged_in'):
        return redirect('/')
    return render_template('control_edit.html', content=load_content())

@app.route('/api/update', methods=['POST'])
def update_content():
    if not session.get('control_logged_in'):
        return jsonify({'success': False, 'error': '未授权'}), 401
    data = request.get_json()
    content = load_content()
    if 'about_hdibs' in data:
        content['about_hdibs'] = data['about_hdibs']
    if 'past_presidents' in data:
        content['past_presidents'] = data['past_presidents']
    if 'members' in data:
        content['members'] = data['members']
    save_content(content)
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    print("启动贫困学生科普网站...")
    print("访问地址: http://localhost:8765")
    app.run(host='0.0.0.0', port=8765, debug=False)
