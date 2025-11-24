# CORS 安全配置指南

## 概述

本指南说明如何安全地配置 TextLoom API 的 CORS (Cross-Origin Resource Sharing) 设置，以防止常见的 Web 安全漏洞，同时确保合法的跨域请求能够正常工作。

## 安全原则

### 1. 最小权限原则
- 仅允许业务必需的域名、方法和头部
- 禁用不必要的功能（如凭证传递）

### 2. 明确配置
- 避免使用通配符 `"*"`
- 明确指定每个允许的值

### 3. 环境隔离
- 开发环境和生产环境使用不同的配置
- 生产环境更严格的安全控制

## 配置说明

### 环境变量配置

#### 基础配置
```bash
# 允许的源域名（JSON 数组格式）
ALLOWED_ORIGINS=["https://yourdomain.com", "https://app.yourdomain.com"]

# 是否允许凭证（仅在需要时启用）
CORS_ALLOW_CREDENTIALS=false

# 允许的 HTTP 方法
CORS_ALLOWED_METHODS=["GET", "POST", "PUT", "DELETE"]

# 允许的请求头
CORS_ALLOWED_HEADERS=["Content-Type", "Authorization", "x-test-token"]

# 暴露的响应头
CORS_EXPOSE_HEADERS=["Content-Length", "Content-Type"]

# 预检请求缓存时间（秒）
CORS_MAX_AGE=86400
```

### 环境特定配置

#### 开发环境 (.env.development)
```bash
DEBUG=true
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS=false
```

#### 生产环境 (.env.production)
```bash
DEBUG=false
ALLOWED_ORIGINS=["https://textloom.example.com", "https://api.textloom.example.com"]
CORS_ALLOW_CREDENTIALS=true  # 仅在需要时启用
```

## 配置验证

### 1. 使用内置测试脚本
```bash
# 测试当前配置
python scripts/test_cors_security.py --url http://localhost:8000

# 输出 JSON 格式报告
python scripts/test_cors_security.py --url http://localhost:8000 --format json
```

### 2. 手动验证

#### 验证允许的源域名
```bash
curl -X OPTIONS http://localhost:8000/health \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

期望结果：
```
Access-Control-Allow-Origin: http://localhost:3000
```

#### 验证拒绝非法域名
```bash
curl -X OPTIONS http://localhost:8000/health \
  -H "Origin: https://malicious-site.com" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

期望结果：没有 `Access-Control-Allow-Origin` 头部

## 常见安全问题

### ❌ 危险配置

#### 1. 通配符源域名
```bash
# 危险：允许任意域名
ALLOWED_ORIGINS=["*"]
```

#### 2. 凭证与通配符组合
```bash
# 危险：违反 CORS 规范，可能导致安全问题
ALLOWED_ORIGINS=["*"]
CORS_ALLOW_CREDENTIALS=true
```

#### 3. 过度宽松的方法
```bash
# 危险：允许所有 HTTP 方法
CORS_ALLOWED_METHODS=["*"]
```

#### 4. 过度宽松的头部
```bash
# 危险：允许任意请求头
CORS_ALLOWED_HEADERS=["*"]
```

### ✅ 安全配置

#### 1. 明确的域名白名单
```bash
ALLOWED_ORIGINS=["https://app.example.com", "https://admin.example.com"]
```

#### 2. 最小必要的方法
```bash
CORS_ALLOWED_METHODS=["GET", "POST", "PUT", "DELETE"]
```

#### 3. 限制的请求头
```bash
CORS_ALLOWED_HEADERS=["Content-Type", "Authorization"]
```

## 故障排除

### 问题：跨域请求被阻止

#### 检查步骤
1. 确认请求的源域名在 `ALLOWED_ORIGINS` 中
2. 检查 HTTP 方法是否在 `CORS_ALLOWED_METHODS` 中
3. 验证请求头是否在 `CORS_ALLOWED_HEADERS` 中

#### 调试命令
```bash
# 查看当前 CORS 配置
python -c "from config import settings; print(settings.get_allowed_origins())"

# 测试特定域名
curl -X OPTIONS http://localhost:8000/health \
  -H "Origin: YOUR_DOMAIN" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

### 问题：凭证无法传递

#### 解决方案
```bash
# 确保启用凭证支持（仅在需要时）
CORS_ALLOW_CREDENTIALS=true

# 确保源域名不是通配符
ALLOWED_ORIGINS=["https://specific-domain.com"]
```

### 问题：预检请求失败

#### 检查请求头配置
```bash
# 确保请求头在允许列表中
CORS_ALLOWED_HEADERS=["Content-Type", "Authorization", "x-test-token"]
```

## 安全检查清单

### 部署前检查
- [ ] 生产环境禁用 `DEBUG=true`
- [ ] 源域名列表仅包含可信域名
- [ ] 避免使用通配符 `"*"`
- [ ] HTTP 方法限制为业务必需
- [ ] 请求头限制为最小必要集合
- [ ] 仅在需要时启用凭证支持

### 定期审查
- [ ] 每季度审查域名白名单
- [ ] 监控异常的跨域请求
- [ ] 运行安全测试脚本
- [ ] 检查依赖项的安全更新

## 相关文档

- [CORS 安全审计报告](../CORS_SECURITY_AUDIT_REPORT.md)
- [安全测试脚本](../scripts/test_cors_security.py)
- [OWASP CORS 安全指南](https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny)

## 联系支持

如有 CORS 配置相关问题，请：
1. 运行安全测试脚本
2. 检查配置文件
3. 查看应用日志
4. 提供详细的错误信息和配置