# 敏感项检查

包含客户明文密码 2 处，推公开仓前需用户决定脱敏或改私有。
--- 具体行数 ---
app.py:47:    if password == 'CLIENT_PASSWORD_PLACEHOLDER':
app.py:51:    elif password == 'CONTROL_PASSWORD_PLACEHOLDER':
