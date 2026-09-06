#!/usr/bin/env python3
import subprocess, time, urllib.parse, json, sys, os, re

BASE = "http://localhost:8765"
TOKEN = "probe_" + str(int(time.time()))

def http(args):
    r = subprocess.run(["curl","-s","-o","/tmp/_body","-w","%{http_code}"]+args, capture_output=True, text=True)
    return r.stdout

def section(t):
    print("\n=== "+t+" ===")

section("1 login page")
code = http([BASE+"/"])
print("GET /:", code)
body = open("/tmp/_body",encoding="utf-8").read()
print("password fields:", body.count('type="password"'))

code = http(["-d","password=wrong", BASE+"/login"])
print("POST wrong:", code)
wrong = open("/tmp/_body",encoding="utf-8").read()

r = subprocess.run(["curl","-s","-c","/tmp/cj","-o","/dev/null","-w","%{http_code}","-d","password=CLIENT_PASSWORD_PLACEHOLDER",BASE+"/login"], capture_output=True, text=True)
print("POST client:", r.stdout)
code = http(["-b","/tmp/cj", BASE+"/client"])
print("GET /client:", code)

section("3 home keywords")
http(["-b","/tmp/cj", "-o","/tmp/home.html", BASE+"/client"])
home = open("/tmp/home.html",encoding="utf-8").read()
print("HDIBS:", home.count("HDIBS"))
print("欢迎，:", home.count("欢迎，"))
print("希望你可以:", home.count("希望你可以"))
print("关于我们:", home.count("关于我们"))
print("社团成员:", home.count("社团成员"))
print("路径资源:", home.count("路径资源"))
print("欢迎， matches:", len(re.findall(r"欢迎，", home)))

section("4 wrong pw -> no 欢迎")
print("欢迎 in wrong:", wrong.count("欢迎"))

section("5 about & members")
http(["-b","/tmp/cj","-o","/tmp/about.html",BASE+"/client/about"])
ab = open("/tmp/about.html",encoding="utf-8").read()
print("关于HDIBS:", ab.count("关于HDIBS"))
print("历任社长:", ab.count("历任社长"))
print("返回主页:", ab.count("返回主页"))

http(["-b","/tmp/cj","-o","/tmp/members.html",BASE+"/client/members"])
mb = open("/tmp/members.html",encoding="utf-8").read()
print("member-photo:", mb.count('class="member-photo'))
print("member-text:", mb.count('class="member-text'))
print("返回主页 in members:", mb.count("返回主页"))

section("6 resources")
http(["-b","/tmp/cj","-o","/tmp/res.html",BASE+"/client/resources"])
res = open("/tmp/res.html",encoding="utf-8").read()
for cat in ["物理学","化学","生物学"]:
    print(cat, ":", res.count(cat))
for p in ["物理学/光学","物理学/力学","物理学/电学","物理学/量子力学","物理学/热学","化学/无机化学","化学/有机化学","化学/环境化学","生物学/神经生物学","生物学/其他生物学"]:
    enc = urllib.parse.quote(p)
    code = http(["-b","/tmp/cj", BASE+"/client/resources/"+enc])
    print(p, "->", code)

section("7 admin & control update")
r = subprocess.run(["curl","-s","-c","/tmp/aj","-o","/dev/null","-w","%{http_code}","-d","password=CONTROL_PASSWORD_PLACEHOLDER",BASE+"/login"], capture_output=True, text=True)
print("POST admin:", r.stdout)

code = http(["-b","/tmp/aj","-o","/tmp/admin.html",BASE+"/admin"])
print("GET /admin:", code)
ad = open("/tmp/admin.html",encoding="utf-8").read()
print("进入修改 in /admin:", ad.count("进入修改"))
print("欢迎，感谢你对HDIBS作出 in /admin:", ad.count("欢迎，感谢你对HDIBS作出"))

code = http(["-b","/tmp/aj","-o","/tmp/ctrl.html",BASE+"/control"])
print("GET /control:", code)
ct = open("/tmp/ctrl.html",encoding="utf-8").read()
print("进入修改 in /control:", ct.count("进入修改"))

code = http(["-b","/tmp/aj","-o","/tmp/ctredit.html",BASE+"/control/edit"])
print("GET /control/edit:", code)
cte = open("/tmp/ctredit.html",encoding="utf-8").read()
print("进入修改 in /control/edit:", cte.count("进入修改"))

print("TOKEN=", TOKEN)
endpoints = [
    (BASE+"/control/update", ["-d","about_hdibs="+TOKEN]),
    (BASE+"/api/content", ["-H","Content-Type: application/json","-d",json.dumps({"about_hdibs":TOKEN})]),
    (BASE+"/api/content", ["-H","Content-Type: application/json","-d",json.dumps({"content":{"about_hdibs":TOKEN}})]),
]
for url, args in endpoints:
    code = http(["-b","/tmp/aj","-o","/tmp/upd.json"]+args+[url])
    body = open("/tmp/upd.json",encoding="utf-8").read()
    print(url, "->", code, "body:", body[:200])

http(["-b","/tmp/cj","-o","/tmp/about2.html",BASE+"/client/about"])
ab2 = open("/tmp/about2.html",encoding="utf-8").read()
print("about contains TOKEN?", TOKEN in ab2)
idx = ab2.find("关于HDIBS")
if idx >= 0:
    print("about excerpt around 关于HDIBS:")
    print(ab2[idx:idx+400])

section("8 size")
for f in ["/tmp/_body","/tmp/home.html","/tmp/about.html","/tmp/members.html","/tmp/res.html","/tmp/ctrl.html","/tmp/ctredit.html","/tmp/admin.html","/tmp/about2.html"]:
    if os.path.exists(f):
        print(f, os.path.getsize(f))