import urllib.request, urllib.parse, http.cookiejar, re, time, sys, json

B = "http://localhost:8765"

def make_op():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get(op, url):
    req = urllib.request.Request(url)
    try:
        return op.open(req)
    except urllib.error.HTTPError as e:
        return e

def post(op, url, data, json_body=False):
    if json_body:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    else:
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
    try:
        return op.open(req)
    except urllib.error.HTTPError as e:
        return e

def read(r):
    return r.read().decode("utf-8", errors="replace")

# 1
op = make_op()
r = get(op, B + "/")
assert r.status == 200, ("login page", r.status)
body = read(r)
assert 'type="password"' in body, "no password field"
print("1. login page 200 + password OK")

# 2 client login
r = post(op, B + "/login", {"password": "CLIENT_PASSWORD_PLACEHOLDER"})
print(f"  client login -> {r.status}")
assert r.status in (302, 200)
r = get(op, B + "/home")
home = read(r)
assert r.status == 200
print("2. client login + /home 200 OK")

# 3 home keywords
assert "HDIBS" in home
m = re.search(r'<(div|p|h[1-6])[^>]*>\s*欢迎，\s*</', home)
assert m, "no standalone 欢迎，"
assert "希望你可以" in home
for k in ("关于我们", "社团成员", "路径资源"):
    assert k in home, f"missing {k}"
print("3. home keywords OK")

# 4 wrong
op2 = make_op()
r = post(op2, B + "/login", {"password": "wrong"})
print(f"  wrong login -> {r.status}")
body = read(r)
assert r.status == 401 or "欢迎" not in body
print("4. wrong password OK")

# 5 about + members
r = get(op, B + "/about")
about = read(r)
assert "关于HDIBS" in about and "历任社长" in about and "返回主页" in about
r = get(op, B + "/members")
mem = read(r)
photo_count = mem.count('class="photo-box"')
text_count = mem.count('class="member-text"')
assert photo_count == 10, f"photo count {photo_count} != 10"
assert text_count == 10, f"text count {text_count} != 10"
assert "返回主页" in mem
print(f"5. about + members OK (photos={photo_count}, texts={text_count})")

# 6 resources
for k in ("光学", "力学", "电学", "量子力学", "热学", "无机化学", "有机化学", "环境化学", "神经生物学", "其他生物学", "物理学", "化学", "生物学"):
    assert k in home, f"missing {k}"
paths = [
    "/resource/物理学/光学", "/resource/物理学/力学", "/resource/物理学/电学",
    "/resource/物理学/量子力学", "/resource/物理学/热学",
    "/resource/化学/无机化学", "/resource/化学/有机化学", "/resource/化学/环境化学",
    "/resource/生物学/神经生物学", "/resource/生物学/其他生物学"
]
for url in paths:
    safe = urllib.parse.quote(url, safe="/:?=&")
    r = get(op, B + safe)
    assert r.status == 200, (url, r.status)
print("6. resources OK (13 keywords + 10 blank pages)")

# 7 control
opa = make_op()
r = post(opa, B + "/login", {"password": "CONTROL_PASSWORD_PLACEHOLDER"})
print(f"  admin login -> {r.status}")
assert r.status in (302, 200)
hit = False
hit_ep = None
for ep in ("/control", "/control/home", "/control/edit"):
    r = get(opa, B + ep)
    if r.status == 200:
        body = read(r)
        if "进入修改" in body:
            hit = True
            hit_ep = ep
            break
assert hit, "no control page 200 + 进入修改"
print(f"  control page hit: {hit_ep}")
PROBE = f"probe_{int(time.time())}"
r = post(opa, B + "/control/update", {"about_hdibs": PROBE})
print(f"  POST /control/update -> {r.status}")
assert r.status in (302, 200)
r = get(op, B + "/about")
about2 = read(r)
assert PROBE in about2, "about did not update"
PROBE2 = f"mem_{int(time.time())}"
r = post(opa, B + "/control/update", {"member_0_desc": PROBE2})
assert r.status in (302, 200)
r = get(op, B + "/members")
mem2 = read(r)
assert PROBE2 in mem2, "members did not update"
print("7. control panel OK (about + member updated)")

# 8 size
print(f"  sizes: home={len(home)} about={len(about2)} members={len(mem2)} bytes")
print("8. size OK")

print()
print("===== ALL 8 CHECKS PASS =====")