from flask import Flask, request, redirect, url_for, render_template, session, abort
import json
import os

app = Flask(__name__)
app.secret_key = 'hdibs_secret_key_2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(BASE_DIR, 'content.json')

DEFAULT_CONTENT = {
    "about_hdibs": "在这里介绍 HDIBS —— 一个致力于为贫困地区学生科普科学知识的社团。",
    "history_presidents": "历任社长：\n\n· 第一任社长：XXX\n· 第二任社长：XXX",
    "members": [""] * 10
}

CLIENT_PASSWORD = "CONTROL_PASSWORD_PLACEHOLDER"
ADMIN_PASSWORD = "CLIENT_PASSWORD_PLACEHOLDER"

RESOURCE_MAP = {
    "物理学": ["光学", "力学", "电学", "量子力学", "热学"],
    "化学": ["无机化学", "有机化学", "环境化学"],
    "生物学": ["神经生物学", "其他生物学"]
}


def load_content():
    if not os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONTENT, f, ensure_ascii=False, indent=2)
        return json.loads(json.dumps(DEFAULT_CONTENT))
    with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for k, v in DEFAULT_CONTENT.items():
        if k not in data:
            data[k] = v
    while len(data.get("members", [])) < 10:
        data.setdefault("members", []).append("")
    return data


def save_content(content):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


@app.route('/', methods=['GET'])
def login():
    if session.get('is_admin'):
        return redirect(url_for('admin_home'))
    if session.get('is_client'):
        return redirect(url_for('client_home'))
    return render_template('login.html', error=False)


@app.route('/login', methods=['POST'])
def do_login():
    password = request.form.get('password', '')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        session.pop('is_client', None)
        return redirect(url_for('admin_home'))
    if password == CLIENT_PASSWORD:
        session['is_client'] = True
        session.pop('is_admin', None)
        return redirect(url_for('client_home'))
    return render_template('login.html', error=True), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


def _require_client_or_admin():
    if not (session.get('is_client') or session.get('is_admin')):
        return redirect(url_for('login'))
    return None


@app.route('/client')
def client_home():
    r = _require_client_or_admin()
    if r:
        return r
    content = load_content()
    return render_template('client_home.html', content=content)


@app.route('/client/about')
def client_about():
    r = _require_client_or_admin()
    if r:
        return r
    content = load_content()
    return render_template('client_about.html', content=content)


@app.route('/client/members')
def client_members():
    r = _require_client_or_admin()
    if r:
        return r
    content = load_content()
    return render_template('client_members.html', content=content)


@app.route('/client/resource/<category>/<sub>')
def client_resource(category, sub):
    r = _require_client_or_admin()
    if r:
        return r
    if category not in RESOURCE_MAP or sub not in RESOURCE_MAP[category]:
        abort(404)
    return render_template('client_resource.html', category=category, sub=sub)


@app.route('/admin')
def admin_home():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    return render_template('admin_home.html')


@app.route('/admin/edit', methods=['GET', 'POST'])
def admin_edit():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    content = load_content()
    if request.method == 'POST':
        content['about_hdibs'] = request.form.get('about_hdibs', content.get('about_hdibs', ''))
        content['history_presidents'] = request.form.get('history_presidents', content.get('history_presidents', ''))
        members = content.get('members', [])
        while len(members) < 10:
            members.append('')
        for i in range(10):
            key = 'member_%d' % i
            if key in request.form:
                members[i] = request.form.get(key, '')
        content['members'] = members
        save_content(content)
        return render_template('admin_edit.html', content=content, saved=True)
    return render_template('admin_edit.html', content=content, saved=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=False)