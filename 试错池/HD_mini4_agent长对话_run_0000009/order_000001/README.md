# HDIBS 科学之光 网站

## 安装依赖
pip install flask

## 启动命令
python3 app.py

## 访问地址
浏览器打开 http://localhost:8765/

端口：8765
客户端密码：CLIENT_PASSWORD_PLACEHOLDER
控制端密码：CONTROL_PASSWORD_PLACEHOLDER

文件说明：
- app.py：Flask 服务端（路由、密码校验、JSON 持久化）
- content.json：可编辑内容（关于HDIBS正文、历任社长、社员信息等）
- templates/：HTML 模板
- static/：CSS 与 JS