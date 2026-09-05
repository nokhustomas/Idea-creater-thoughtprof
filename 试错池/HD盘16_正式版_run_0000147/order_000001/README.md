# HDIBS 科学之光（客户端 + 控制端）

启动方式：
1. 安装依赖：`pip install flask`
2. 启动命令：`python3 app.py`
3. 访问地址：浏览器打开 `http://localhost:8765/`，端口 **8765**

密码：
- 客户端密码：`CLIENT_PASSWORD_PLACEHOLDER`
- 控制端密码：`CONTROL_PASSWORD_PLACEHOLDER`

控制端在 `/admin/edit` 可修改"关于HDIBS"正文与社团成员第 1 栏文字等内容，修改保存到 `content.json`，客户端页面立即可见。