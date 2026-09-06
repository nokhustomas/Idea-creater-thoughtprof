# HDIBS 科普网站

一行启动：安装依赖并运行：

```
pip install flask
python3 app.py
```

访问地址：浏览器打开 http://localhost:8765/

- 客户端密码：`CLIENT_PASSWORD_PLACEHOLDER`
- 控制端密码：`CONTROL_PASSWORD_PLACEHOLDER`
- 控制端编辑的内容会持久化到 `content.json`，客户端页面读取该文件渲染。