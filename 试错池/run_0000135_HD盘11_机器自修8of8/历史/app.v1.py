from flask import Flask, render_template, request, redirect, session, jsonify, make_response
import json
import os

app = Flask(__name__)
app.secret_key = 'hdibs_secret_key_2024'
CONTENT_FILE = 'content.json'

def load_content():
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return get_default_content()

def save_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_default_content():
    return {
        "about_hdibs": "HDIBS是一个致力于为贫困地区学生提供科学教育的公益组织。",
        "about_history": "历任社长都为组织的发展做出了重要贡献。",
        "members": [
            {"name": "成员1", "desc": "简介1"},
            {"name": "成员2", "desc": "简介2"},
            {"name": "成员3", "desc": "简介3"},
            {"name": "成员4", "desc": "简介4"},
            {"name": "成员5", "desc": "简介5"},
            {"name": "成员6", "desc": "简介6"},
            {"name": "成员7", "desc": "简介7"},
            {"name": "成员8", "desc": "简介8"},
            {"name": "成员9", "desc": "简介9"},
            {"name": "成员10", "desc": "简介10"}
        ]
    }

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    if password == 'CLIENT_PASSWORD_PLACEHOLDER':
        session['client_logged_in'] = True
        return redirect('/client')
    elif password == 'CONTROL_PASSWORD_PLACEHOLDER':
        session['admin_logged_in'] = True
        return redirect('/admin')
    return redirect('/')

@app.route('/client')
def client():
    if not session.get('client_logged_in'):
        return redirect('/')
    content = load_content()
    return render_template('client.html', content=content)

@app.route('/about')
def about():
    if not session.get('client_logged_in'):
        return redirect('/')
    content = load_content()
    return render_template('about.html', content=content)

@app.route('/members')
def members():
    if not session.get('client_logged_in'):
        return redirect('/')
    content = load_content()
    return render_template('members.html', content=content)

@app.route('/resource/<path:subpath>')
def resource_page(subpath):
    if not session.get('client_logged_in'):
        return redirect('/')
    return render_template('resource_page.html', topic=subpath)

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect('/')
    content = load_content()
    return render_template('admin.html', content=content)

@app.route('/admin/edit', methods=['GET', 'POST'])
def admin_edit():
    if not session.get('admin_logged_in'):
        return redirect('/')
    if request.method == 'POST':
        content = load_content()
        content['about_hdibs'] = request.form.get('about_hdibs', content['about_hdibs'])
        content['about_history'] = request.form.get('about_history', content['about_history'])
        if request.form.get('member1_name'):
            content['members'][0]['name'] = request.form.get('member1_name')
        if request.form.get('member1_desc'):
            content['members'][0]['desc'] = request.form.get('member1_desc')
        save_content(content)
        return render_template('admin_edit.html', content=content, success=True)
    content = load_content()
    return render_template('admin_edit.html', content=content, success=False)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    if not os.path.exists(CONTENT_FILE):
        save_content(get_default_content())
    app.run(host='0.0.0.0', port=8765, debug=False)
