from flask import Flask, request, redirect, url_for, render_template, session, jsonify, make_response
import json
import os

app = Flask(__name__)
app.secret_key = 'hdis_secret_key_435879'
CONTENT_FILE = 'content.json'

def load_content():
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "about_hdibs": "这里是关于HDIBS的详细介绍内容。",
        "previous_leaders": "历任社长信息待添加。",
        "members": ["", "", "", "", "", "", "", "", "", ""]
    }

def save_content(content):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    if not session.get('client_auth'):
        return render_template('login.html', mode='client')
    return render_template('client_home.html', content=load_content())

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password', '')
    
    if password == 'CLIENT_PASSWORD_PLACEHOLDER':
        session['client_auth'] = True
        session['control_auth'] = False
        return redirect(url_for('client_home'))
    elif password == 'CONTROL_PASSWORD_PLACEHOLDER':
        session['client_auth'] = True
        session['control_auth'] = True
        return redirect(url_for('control_home'))
    else:
        return redirect(url_for('login_error', mode='client'))

@app.route('/login/error')
def login_error():
    return render_template('login.html', mode='client', error=True)

@app.route('/client/home')
def client_home():
    if not session.get('client_auth'):
        return redirect(url_for('index'))
    return render_template('client_home.html', content=load_content())

@app.route('/client/about')
def client_about():
    if not session.get('client_auth'):
        return redirect(url_for('index'))
    return render_template('client_about.html', content=load_content())

@app.route('/client/members')
def client_members():
    if not session.get('client_auth'):
        return redirect(url_for('index'))
    return render_template('client_members.html', content=load_content())

@app.route('/client/resource/<category>/<subcategory>')
def client_resource(category, subcategory):
    if not session.get('client_auth'):
        return redirect(url_for('index'))
    categories = {
        'physics': {'name': '物理学', 'sub': {'optics': '光学', 'mechanics': '力学', 'electricity': '电学', 'quantum': '量子力学', 'thermal': '热学'}},
        'chemistry': {'name': '化学', 'sub': {'inorganic': '无机化学', 'organic': '有机化学', 'environmental': '环境化学'}},
        'biology': {'name': '生物学', 'sub': {'neuro': '神经生物学', 'other': '其他生物学'}}
    }
    if category in categories and subcategory in categories[category]['sub']:
        return render_template('resource_page.html', 
                               category_name=categories[category]['name'],
                               subcategory_name=categories[category]['sub'][subcategory])
    return "Page not found", 404

@app.route('/control/home')
def control_home():
    if not session.get('control_auth'):
        return redirect(url_for('index'))
    return render_template('control_home.html')

@app.route('/control/edit')
def control_edit():
    if not session.get('control_auth'):
        return redirect(url_for('index'))
    return render_template('control_edit.html', content=load_content())

@app.route('/control/update', methods=['POST'])
def control_update():
    if not session.get('control_auth'):
        return redirect(url_for('index'))
    
    content = load_content()
    content['about_hdibs'] = request.form.get('about_hdibs', '')
    content['previous_leaders'] = request.form.get('previous_leaders', '')
    
    for i in range(10):
        member_text = request.form.get(f'member_{i}', '')
        content['members'][i] = member_text
    
    save_content(content)
    return redirect(url_for('control_edit'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(CONTENT_FILE):
        save_content(load_content())
    app.run(host='0.0.0.0', port=8765, debug=True)
