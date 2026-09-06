#!/bin/bash
# Integration test
set -e
B=http://localhost:8765
echo "--- root status ---"
curl -s -o /dev/null -w "ROOT=%{http_code}\n" $B/
echo "--- root has password input ---"
curl -s $B/ | grep -c 'type="password"'
echo "--- wrong pw ---"
curl -s -o /tmp/wrong.html -w "WRONG=%{http_code}\n" -X POST -d "password=bad" $B/login
grep -c "欢迎" /tmp/wrong.html || echo "0"
echo "--- client login ---"
curl -s -o /dev/null -w "CLI=%{http_code}\n" -X POST -d "password=CLIENT_PASSWORD_PLACEHOLDER" -c /tmp/cli.jar $B/login
echo "--- client home ---"
curl -s -o /tmp/home.html -w "HOME=%{http_code}\n" -b /tmp/cli.jar $B/client
echo "HDIBS:"; grep -c "HDIBS" /tmp/home.html
echo "欢迎，:"; grep -c "欢迎，" /tmp/home.html
echo "关于我们:"; grep -c "关于我们" /tmp/home.html
echo "社团成员:"; grep -c "社团成员" /tmp/home.html
echo "路径资源:"; grep -c "路径资源" /tmp/home.html
echo "--- about ---"
curl -s -o /tmp/about.html -w "ABOUT=%{http_code}\n" -b /tmp/cli.jar $B/client/about
grep -c "关于HDIBS" /tmp/about.html
grep -c "历任社长" /tmp/about.html
grep -c "返回主页" /tmp/about.html
echo "--- members ---"
curl -s -o /tmp/members.html -w "MEMBERS=%{http_code}\n" -b /tmp/cli.jar $B/client/members
echo "photos:"; grep -oc 'class="photo"' /tmp/members.html
echo "texts:"; grep -oc 'class="mtext"' /tmp/members.html
grep -c "返回主页" /tmp/members.html
echo "--- resources hub ---"
curl -s -o /tmp/res.html -w "RES=%{http_code}\n" -b /tmp/cli.jar $B/client/resources
echo "--- 10 topic pages ---"
curl -s -o /dev/null -w "physics/光学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/物理学/光学"
curl -s -o /dev/null -w "physics/力学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/物理学/力学"
curl -s -o /dev/null -w "physics/电学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/物理学/电学"
curl -s -o /dev/null -w "physics/量子力学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/物理学/量子力学"
curl -s -o /dev/null -w "physics/热学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/物理学/热学"
curl -s -o /dev/null -w "chem/无机化学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/化学/无机化学"
curl -s -o /dev/null -w "chem/有机化学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/化学/有机化学"
curl -s -o /dev/null -w "chem/环境化学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/化学/环境化学"
curl -s -o /dev/null -w "bio/神经生物学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/生物学/神经生物学"
curl -s -o /dev/null -w "bio/其他生物学=%{http_code}\n" -b /tmp/cli.jar "$B/client/resources/生物学/其他生物学"
echo "--- admin login ---"
curl -s -o /dev/null -w "ADM=%{http_code}\n" -X POST -d "password=CONTROL_PASSWORD_PLACEHOLDER" -c /tmp/adm.jar $B/login
echo "--- admin home ---"
curl -s -o /tmp/ah.html -w "AH=%{http_code}\n" -b /tmp/adm.jar $B/admin
grep -c "进入修改" /tmp/ah.html
grep -c "欢迎，感谢你对HDIBS作出的贡献。" /tmp/ah.html
echo "--- admin edit page ---"
curl -s -o /tmp/ae.html -w "AE=%{http_code}\n" -b /tmp/adm.jar $B/admin/edit
echo "--- admin POST content ---"
curl -s -b /tmp/adm.jar -X POST -H "Content-Type: application/json" \
  -d '{"about_hdibs":"新正文XYZ测试","members":[{"photo":"","text":"第一名成员ABC测试"}]}' \
  $B/admin/api/content
echo
echo "--- content.json after edit ---"
cat content.json
echo
echo "--- client api content ---"
curl -s -b /tmp/cli.jar $B/client/api/content
echo
echo "--- size check (templates) ---"
du -bc templates/*.html | tail -1
echo "--- per-page sizes (bytes) ---"
for f in templates/*.html; do echo "$(wc -c < $f) $f"; done
echo "--- max per-page size ---"
maxsize=0
for f in templates/*.html; do
  s=$(wc -c < $f)
  if [ $s -gt $maxsize ]; then maxsize=$s; fi
done
echo "max = $maxsize bytes"
echo "--- DONE ---"