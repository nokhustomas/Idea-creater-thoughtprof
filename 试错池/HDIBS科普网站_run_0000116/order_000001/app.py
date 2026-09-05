from flask import Flask, request, jsonify, redirect, render_template, send_from_directory
import os
import json

app = Flask(__name__)
app.secret_key = 'hdi_bs_secret_key_2024'

CONTENT_FILE = 'content.json'

def load_content():
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "about_hdibs": "这里将显示关于HDIBS的内容...",
        "past_presidents": "这里将显示历任社长的信息...",
        "members": [
            {"name": "", "description": ""} for _ in range(10)
        ]
    }

def save_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    
    if password == 'CLIENT_PASSWORD_PLACEHOLDER':
        return redirect('/client/home')
    elif password == 'CONTROL_PASSWORD_PLACEHOLDER':
        return redirect('/control')
    else:
        return render_template('login.html', error='密码错误')

@app.route('/client/<page>')
def client_page(page):
    if page == 'home':
        return render_template('client_home.html')
    elif page == 'about':
        content = load_content()
        return render_template('about.html', content=content)
    elif page == 'members':
        content = load_content()
        return render_template('members.html', content=content)
    elif page.startswith('resource_'):
        return render_template('resource_blank.html', category=page)
    else:
        return "页面不存在", 404

@app.route('/control')
def control_index():
    return render_template('control_home.html')

@app.route('/control/edit')
def control_edit():
    content = load_content()
    return render_template('control_edit.html', content=content)

@app.route('/api/content', methods=['GET'])
def api_get_content():
    return jsonify(load_content())

@app.route('/api/content', methods=['POST'])
def api_update_content():
    data = request.get_json()
    if data:
        save_content(data)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8765, debug=False)
