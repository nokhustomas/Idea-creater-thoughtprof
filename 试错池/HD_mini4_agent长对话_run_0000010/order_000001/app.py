#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HDIBS 科普网站 - 客户端 + 控制端
端口: 8765
"""
import os, json, hashlib, secrets, http.cookies, re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(ROOT, 'content.json')

CLIENT_PWD = "CLIENT_PASSWORD_PLACEHOLDER"
ADMIN_PWD = "CONTROL_PASSWORD_PLACEHOLDER"
SESSIONS = {}  # token -> role

DEFAULT_CONTENT = {
    "about_hdibs": "这里是关于HDIBS的简介，等待控制端编辑。",
    "history_presidents": [
        "第一届社长：待填写",
        "第二届社长：待填写",
        "第三届社长：待填写"
    ],
    "members": [
        {"name": "成员1", "intro": "个人介绍待填写"},
        {"name": "成员2", "intro": "个人介绍待填写"},
        {"name": "成员3", "intro": "个人介绍待填写"},
        {"name": "成员4", "intro": "个人介绍待填写"},
        {"name": "成员5", "intro": "个人介绍待填写"},
        {"name": "成员6", "intro": "个人介绍待填写"},
        {"name": "成员7", "intro": "个人介绍待填写"},
        {"name": "成员8", "intro": "个人介绍待填写"},
        {"name": "成员9", "intro": "个人介绍待填写"},
        {"name": "成员10", "intro": "个人介绍待填写"}
    ]
}

def load_content():
    if not os.path.exists(CONTENT_FILE):
        save_content(DEFAULT_CONTENT)
        return DEFAULT_CONTENT.copy()
    try:
        with open(CONTENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONTENT.copy()

def save_content(data):
    with open(CONTENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def html_escape(s):
    if s is None:
        return ''
    return (str(s).replace('&','&amp;').replace('<','&lt;')
            .replace('>','&gt;').replace('"','&quot;'))

def make_session(role):
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = role
    return token

def get_role(handler):
    cookie = handler.headers.get('Cookie', '')
    m = re.search(r'HDIBS_SESS=([A-Za-z0-9_\-]+)', cookie)
    if m and m.group(1) in SESSIONS:
        return SESSIONS[m.group(1)]
    return None

LOGIN_PAGE = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>登录 - HDIBS</title>
<style>body{margin:0;font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f7fa;color:#222;min-height:100vh;display:flex;flex-direction:column;}.navbar{background:#1f2a44;color:#fff;padding:12px 16px;font-size:18px;font-weight:bold;}.navbar a{color:#fff;text-decoration:none;}.main{flex:1;display:flex;align-items:center;justify-content:center;padding:20px;}.card{background:#fff;padding:28px 24px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);width:100%;max-width:340px;}.card h2{margin:0 0 18px 0;font-size:20px;text-align:center;}.card input[type=password]{width:100%;padding:10px 12px;border:1px solid #ccc;border-radius:4px;font-size:15px;box-sizing:border-box;}.card button{margin-top:14px;width:100%;padding:10px 12px;background:#1f6feb;color:#fff;border:none;border-radius:4px;font-size:15px;cursor:pointer;}.card button:hover{background:#1858c4;}.err{color:#d33;font-size:13px;margin-top:10px;text-align:center;min-height:18px;}.foot{text-align:center;color:#888;font-size:12px;padding:12px;}</style></head><body>
<div class="navbar">HDIBS</div>
<div class="main"><form class="card" method="POST" action="/login">
<h2>请输入访问密码</h2>
<input type="password" name="password" placeholder="密码" autofocus required>
<button type="submit">进入</button>
<div class="err">__ERR__</div>
</form></div>
<div class="foot">© HDIBS 科普站</div>
</body></html>'''

CLIENT_CSS = '''*{box-sizing:border-box}body{margin:0;font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#fafafa;color:#222;font-size:15px;line-height:1.7}
.navbar{background:#1f2a44;padding:0 16px;display:flex;align-items:center;height:48px;position:relative}
.navbar .brand{color:#fff;font-weight:bold;font-size:18px;text-decoration:none;margin-right:24px}
.navbar ul{list-style:none;margin:0;padding:0;display:flex;gap:8px}
.navbar li{position:relative}
.navbar li>a{color:#cfd6e4;text-decoration:none;display:block;padding:14px 12px;font-size:15px}
.navbar li>a:hover,.navbar li>a.active{color:#fff;background:#2a3658}
.dropdown{display:none;position:absolute;top:100%;left:0;background:#fff;border:1px solid #ddd;box-shadow:0 2px 6px rgba(0,0,0,0.1);min-width:140px;z-index:50}
.dropdown a{display:block;padding:10px 14px;color:#222;text-decoration:none;font-size:14px}
.dropdown a:hover{background:#f0f4ff}
.has-sub:hover>.dropdown{display:block}
.container{max-width:880px;margin:0 auto;padding:20px 16px}
.welcome{font-size:22px;font-weight:bold;text-align:center;margin:30px 0 10px 0}
.subline{font-size:15px;color:#555;text-align:center;margin-top:10px}
.section h2{border-left:4px solid #1f6feb;padding-left:10px;font-size:18px}
.back{display:inline-block;margin-top:24px;color:#1f6feb;text-decoration:none}
.back:hover{text-decoration:underline}
.members-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
.member{background:#fff;border:1px solid #e1e5ec;border-radius:6px;overflow:hidden}
.photo{width:100%;height:160px;background:#e9eef5;display:flex;align-items:center;justify-content:center;color:#8898b0;font-size:13px}
.member .info{padding:10px 12px;font-size:14px}
.footer{text-align:center;color:#888;font-size:12px;padding:24px 0}
@media(max-width:600px){.navbar ul{gap:0}.navbar li>a{padding:12px 8px;font-size:14px}.welcome{font-size:18px}}
'''

CLIENT_NAV = '''<div class="navbar"><a class="brand" href="/client/home">HDIBS</a><ul>
<li><a href="/client/about" data-k="about">关于我们</a></li>
<li><a href="/client/members" data-k="members">社团成员</a></li>
<li class="has-sub" data-sub="res"><a href="#" id="reslink">路径资源 ▾</a><div class="dropdown">
<div class="has-sub" data-sub="physics"><a href="#" data-cat="physics">物理学 ▸</a><div class="dropdown" style="left:100%;top:0">
<a href="/client/page/physics/optics">光学</a>
<a href="/client/page/physics/mechanics">力学</a>
<a href="/client/page/physics/electricity">电学</a>
<a href="/client/page/physics/quantum">量子力学</a>
<a href="/client/page/physics/thermo">热学</a>
</div></div>
<div class="has-sub" data-sub="chemistry"><a href="#" data-cat="chemistry">化学 ▸</a><div class="dropdown" style="left:100%;top:0">
<a href="/client/page/chemistry/inorganic">无机化学</a>
<a href="/client/page/chemistry/organic">有机化学</a>
<a href="/client/page/chemistry/env">环境化学</a>
</div></div>
<div class="has-sub" data-sub="biology"><a href="#" data-cat="biology">生物学 </a><div class="dropdown" style="left:100%;top:0">
<a href="/client/page/biology/neuro">神经生物学</a>
<a href="/client/page/biology/other">其他生物学</a>
</div></div>
</div></li></ul></div>'''

CLIENT_JS = '''(function(){
  var subs=document.querySelectorAll(".has-sub");
  for(var i=0;i<subs.length;i++){
    (function(s){
      var d=s.querySelector(":scope > .dropdown");
      if(!d) return;
      var link=s.querySelector(":scope > a");
      if(link){
        link.addEventListener("click",function(e){e.preventDefault();});
      }
      s.addEventListener("mouseenter",function(){d.style.display="block";});
      s.addEventListener("mouseleave",function(){d.style.display="none";});
      s.addEventListener("click",function(e){
        var a=e.target.closest("a");
        if(!a) return;
        var href=a.getAttribute("href");
        if(href==="#" || a.dataset.cat){
          e.preventDefault();
        }
      });
    })(subs[i]);
  }
  var path=location.pathname;
  var links=document.querySelectorAll(".navbar li>a[data-k]");
  for(var j=0;j<links.length;j++){
    if(links[j].getAttribute("href")===path){links[j].classList.add("active");}
  }
})();
'''

def client_page(active, body):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>HDIBS</title>'
            '<style>'+CLIENT_CSS+'</style></head><body>'
            +CLIENT_NAV+
            '<div class="container">' + body + '</div>'
            '<div class="footer">© HDIBS 科普站</div>'
            '<script>'+CLIENT_JS+'</script>'
            '</body></html>')

def page_home():
    body = ('<p class="welcome">欢迎，</p>'
            '<p class="subline">希望你可以在这里燃起你对科学的兴趣。</p>')
    return client_page('home', body)

def page_about(content):
    parts = ['<div class="section"><h2>关于HDIBS</h2>',
             '<p>'+html_escape(content.get('about_hdibs',''))+'</p></div>']
    parts.append('<div class="section" style="margin-top:30px"><h2>历任社长</h2><ul>')
    for line in content.get('history_presidents', []):
        parts.append('<li>'+html_escape(line)+'</li>')
    parts.append('</ul></div>')
    parts.append('<a class="back" href="/client/home">← 返回主页</a>')
    return client_page('about', '\n'.join(parts))

def page_members(content):
    parts = ['<div class="section"><h2>社团成员</h2>']
    parts.append('<div class="members-grid">')
    for i, m in enumerate(content.get('members', [])[:10], 1):
        name = html_escape(m.get('name',''))
        intro = html_escape(m.get('intro',''))
        parts.append('<div class="member">'
                     '<div class="photo">照片框</div>'
                     '<div class="info"><strong>'+name+'</strong><br>'+intro+'</div>'
                     '</div>')
    parts.append('</div></div>')
    parts.append('<a class="back" href="/client/home">← 返回主页</a>')
    return client_page('members', '\n'.join(parts))

def page_resources():
    body = ('<div class="section"><h2>路径资源</h2>'
            '<p>请使用顶部菜单中的"路径资源"展开二级菜单。</p></div>'
            '<a class="back" href="/client/home">← 返回主页</a>')
    return client_page('resources', body)

def page_blank(title):
    body = ('<div class="section"><h2>'+html_escape(title)+'</h2>'
            '<p>　</p></div>'
            '<a class="back" href="/client/home">← 返回主页</a>')
    return client_page('', body)

PAGE_TITLES = {
    ('physics','optics'):'光学',
    ('physics','mechanics'):'力学',
    ('physics','electricity'):'电学',
    ('physics','quantum'):'量子力学',
    ('physics','thermo'):'热学',
    ('chemistry','inorganic'):'无机化学',
    ('chemistry','organic'):'有机化学',
    ('chemistry','env'):'环境化学',
    ('biology','neuro'):'神经生物学',
    ('biology','other'):'其他生物学',
}

ADMIN_CSS = '''*{box-sizing:border-box}body{margin:0;font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#fafafa;color:#222;font-size:15px;line-height:1.7}
.navbar{background:#1f2a44;padding:0 16px;display:flex;align-items:center;height:48px}
.navbar a.brand{color:#fff;font-weight:bold;font-size:18px;text-decoration:none;margin-right:24px}
.navbar a.link{color:#cfd6e4;text-decoration:none;padding:14px 12px;font-size:15px}
.navbar a.link:hover{color:#fff;background:#2a3658}
.container{max-width:880px;margin:0 auto;padding:20px 16px}
.welcome{font-size:20px;text-align:center;margin:30px 0}
.card{background:#fff;border:1px solid #e1e5ec;border-radius:6px;padding:16px;margin:16px 0}
.card h3{margin:0 0 10px 0;font-size:16px}
textarea,input[type=text]{width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:14px;font-family:inherit}
textarea{min-height:80px}
button{padding:8px 16px;background:#1f6feb;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px}
button:hover{background:#1858c4}
.member-row{display:flex;gap:10px;margin:8px 0}
.member-row .name{width:120px}
.msg{color:#1a7f37;font-size:14px;margin:6px 0}
'''

def admin_home():
    body = ('<div class="navbar"><a class="brand" href="/admin/home">HDIBS 控制端</a>'
            '<a class="link" href="/admin/edit">进入修改</a>'
            '<a class="link" href="/logout" style="margin-left:auto">退出</a></div>'
            '<div class="container">'
            '<p class="welcome">欢迎，感谢你对HDIBS作出的贡献。</p>'
            '<p style="text-align:center"><a href="/admin/edit">→ 进入修改</a></p>'
            '</div>')
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>HDIBS 控制端</title><style>'+ADMIN_CSS+'</style></head><body>'
            +body+'</body></html>')

def admin_edit(content, msg=""):
    rows = []
    rows.append('<h2>编辑内容</h2>')
    if msg:
        rows.append('<p class="msg">'+html_escape(msg)+'</p>')
    rows.append('<form method="POST" action="/admin/edit">')
    rows.append('<div class="card"><h3>关于HDIBS 正文</h3>'
                '<textarea name="about_hdibs">'+html_escape(content.get('about_hdibs',''))+'</textarea></div>')
    rows.append('<div class="card"><h3>历任社长（每行一个）</h3>'
                '<textarea name="history_presidents">'+html_escape('\n'.join(content.get('history_presidents',[])))+'</textarea></div>')
    rows.append('<div class="card"><h3>社团成员（10 栏）</h3>')
    members = content.get('members', [])
    for i in range(10):
        m = members[i] if i < len(members) else {"name":"","intro":""}
        rows.append('<div class="member-row">'
                    '<span style="width:60px;line-height:34px">第'+(str(i+1))+'栏</span>'
                    '<input class="name" type="text" name="m_name_'+str(i)+'" value="'+html_escape(m.get("name",""))+'" placeholder="姓名">'
                    '<input type="text" name="m_intro_'+str(i)+'" value="'+html_escape(m.get("intro",""))+'" placeholder="个人介绍" style="flex:1">'
                    '</div>')
    rows.append('</div>')
    rows.append('<div style="margin-top:16px"><button type="submit">保存修改</button></div>')
    rows.append('</form>')
    body = ('<div class="navbar"><a class="brand" href="/admin/home">HDIBS 控制端</a>'
            '<a class="link" href="/admin/home">首页</a>'
            '<a class="link" href="/admin/edit">进入修改</a>'
            '<a class="link" href="/logout" style="margin-left:auto">退出</a></div>'
            '<div class="container">'+'\n'.join(rows)+'</div>')
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>编辑 - HDIBS</title><style>'+ADMIN_CSS+'</style></head><body>'
            +body+'</body></html>')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # 静默日志
        pass

    def _send(self, status, body, ctype='text/html; charset=utf-8', extra_headers=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if extra_headers:
            for k,v in extra_headers:
                self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location, set_cookie=None):
        self.send_response(302)
        self.send_header('Location', location)
        self.send_header('Content-Length', '0')
        if set_cookie:
            self.send_header('Set-Cookie', set_cookie)
        self.end_headers()

    def _read_post(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        data = self.rfile.read(length) if length else b''
        return parse_qs(data.decode('utf-8', errors='ignore'))

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        role = get_role(self)

        if path == '/':
            return self._send(200, LOGIN_PAGE.replace('__ERR__',''))
        if path == '/login':
            return self._send(200, LOGIN_PAGE.replace('__ERR__',''))

        if path.startswith('/client/'):
            if role not in ('client','admin'):
                return self._send(401, LOGIN_PAGE.replace('__ERR__','请先登录'))
            sub = path[len('/client/'):]
            content = load_content()
            if sub == 'home':
                return self._send(200, page_home())
            if sub == 'about':
                return self._send(200, page_about(content))
            if sub == 'members':
                return self._send(200, page_members(content))
            if sub == 'resources':
                return self._send(200, page_resources())
            if sub.startswith('page/'):
                parts = sub[len('page/'):].split('/')
                if len(parts)==2:
                    title = PAGE_TITLES.get((parts[0], parts[1]), '资源')
                    return self._send(200, page_blank(title))
            return self._send(404, '404')

        if path.startswith('/admin/'):
            if role != 'admin':
                return self._send(401, LOGIN_PAGE.replace('__ERR__','请使用控制端密码登录'))
            if path == '/admin/home':
                return self._send(200, admin_home())
            if path == '/admin/edit':
                return self._send(200, admin_edit(load_content()))

        if path == '/logout':
            self._redirect('/', set_cookie='HDIBS_SESS=; Path=/; Max-Age=0')
            return

        return self._send(404, '404')

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        form = self._read_post()
        pwd = (form.get('password') or [''])[0]

        if path == '/login':
            if pwd == ADMIN_PWD:
                token = make_session('admin')
                self._redirect('/admin/home', set_cookie=f'HDIBS_SESS={token}; Path=/; HttpOnly')
                return
            if pwd == CLIENT_PWD:
                token = make_session('client')
                self._redirect('/client/home', set_cookie=f'HDIBS_SESS={token}; Path=/; HttpOnly')
                return
            self.send_response(401)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            body = LOGIN_PAGE.replace('__ERR__','密码错误').encode('utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == '/admin/edit':
            if get_role(self) != 'admin':
                return self._send(401, LOGIN_PAGE.replace('__ERR__','请先登录'))
            content = load_content()
            content['about_hdibs'] = (form.get('about_hdibs') or [''])[0]
            hp_raw = (form.get('history_presidents') or [''])[0]
            content['history_presidents'] = [ln.strip() for ln in hp_raw.splitlines() if ln.strip()]
            members = []
            for i in range(10):
                name = (form.get(f'm_name_{i}') or [''])[0]
                intro = (form.get(f'm_intro_{i}') or [''])[0]
                members.append({"name":name, "intro":intro})
            content['members'] = members
            save_content(content)
            return self._send(200, admin_edit(content, msg='保存成功'))

        return self._send(404, '404')


def main():
    if not os.path.exists(CONTENT_FILE):
        save_content(DEFAULT_CONTENT)
    port = 8765
    print(f'HDIBS server starting on port {port} ...')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

if __name__ == '__main__':
    main()