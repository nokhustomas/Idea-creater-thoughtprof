# HDIBS · 科学之光科普站

## 三行启动
1. 安装依赖：`pip install Flask`
2. 启动命令：`python3 app.py`
3. 访问地址：浏览器打开 http://localhost:8765

## 密码
- 客户端密码：`CLIENT_PASSWORD_PLACEHOLDER`
- 控制端密码：`CONTROL_PASSWORD_PLACEHOLDER`

## 目录结构
```
app.py                 # Flask 服务端（端口 8765）
content.json           # 客户端可编辑内容持久化文件
templates/             # Jinja2 模板
  login.html           # 密码登录页
  _base.html           # 公共导航与样式
  home.html            # 客户端首页
  about.html           # 关于我们
  members.html         # 社团成员（10 栏）
  resource.html        # 路径资源二级页面（10 个空白页）
  admin.html           # 控制端首页
  admin_edit.html      # 控制端修改页
README.md
```

## 功能
- 客户端首页 / 关于我们 / 社团成员（10 栏）/ 路径资源（两级弹出菜单：物理学、化学、生物学，共 10 个空白子页）
- 控制端：登录后修改 `content.json`；保存后客户端页面立即读到新内容
- 全部静态资源内联，无外链 CDN；任一页面 HTML+CSS+JS ≤ 200KB