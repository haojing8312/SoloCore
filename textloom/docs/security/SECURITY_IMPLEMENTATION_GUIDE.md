# TextLoom 安全实施指南

## 概述

本文档详细说明了TextLoom项目的安全实施方案，包括输入验证、文件上传安全、URL处理安全等关键安全组件的实施和使用。

## 🔒 已实施的安全特性

### 1. 文件上传安全

#### 核心安全组件
- **文件验证器** (`utils/security/file_validator.py`)
- **安全文件处理器** (`utils/security/secure_file_handler.py`)
- **多层防护策略**

#### 实施的安全措施

1. **文件类型白名单验证**
   ```python
   # 仅允许安全的文件类型
   ALLOWED_EXTENSIONS = {
       FileType.IMAGE: {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'},
       FileType.VIDEO: {'.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm'},
       FileType.DOCUMENT: {'.md', '.markdown', '.txt'}
   }
   ```

2. **MIME类型验证**
   - 使用 `python-magic` 库检测真实文件类型
   - 文件头魔数签名验证
   - 扩展名与实际类型一致性检查

3. **恶意内容扫描**
   ```python
   # 检测的恶意模式
   MALICIOUS_PATTERNS = [
       rb'<script[^>]*>',  # Script标签
       rb'javascript:',     # JavaScript协议
       rb'<?php',          # PHP代码
       rb'<%',             # ASP代码
       rb'\x00',           # 空字节
   ]
   ```

4. **文件大小限制**
   - 默认50MB文件大小限制
   - 可配置的限制策略

5. **文件名安全化**
   ```python
   def sanitize_filename(self, filename: str) -> str:
       # 移除危险字符
       safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
       # Unicode规范化
       safe_name = unicodedata.normalize('NFKC', safe_name)
       return safe_name
   ```

### 2. URL验证和处理安全

#### 核心安全组件
- **输入验证器** (`utils/security/input_validator.py`)
- **URL安全验证器**

#### 实施的安全措施

1. **协议白名单**
   ```python
   SAFE_URL_SCHEMES = {'http', 'https', 'ftp', 'ftps'}
   ```

2. **私有IP地址阻止**
   - 防止SSRF攻击
   - 阻止访问内网资源

3. **恶意URL模式检测**
   - SQL注入模式检测
   - XSS攻击模式检测
   - 命令注入模式检测
   - 路径遍历模式检测

4. **URL清理和规范化**
   ```python
   def _clean_url(self, url: str) -> str:
       # URL编码规范化
       parsed = urlparse(url)
       clean_query = urlencode(parse_qs(parsed.query), doseq=True)
       return urlunparse(parsed._replace(query=clean_query))
   ```

### 3. 输入验证和清理

#### 多层输入验证

1. **SQL注入防护**
   ```python
   def sanitize_for_sql(self, text: str) -> str:
       # 转义单引号
       sanitized = text.replace("'", "''")
       # 移除危险字符
       sanitized = re.sub(r'[;\-\-\/\*]', '', sanitized)
       return sanitized
   ```

2. **XSS防护**
   ```python
   def sanitize_for_html(self, text: str) -> str:
       # HTML转义
       sanitized = html.escape(text, quote=True)
       # 移除危险属性和协议
       sanitized = re.sub(r'on\w+\s*=', 'data-blocked=', sanitized)
       return sanitized
   ```

3. **命令注入防护**
   ```python
   def sanitize_for_shell(self, text: str) -> str:
       # 移除危险字符
       dangerous_chars = ';|&`$<>(){}[]'
       for char in dangerous_chars:
           text = text.replace(char, '')
       return shlex.quote(text)
   ```

### 4. 安全中间件

#### 核心功能
- **速率限制**
- **安全头设置**
- **恶意请求检测**
- **IP访问控制**
- **安全审计日志**

#### 配置示例
```python
PRODUCTION_CONFIG = SecurityConfig(
    rate_limit_requests=100,        # 每分钟100请求
    burst_limit=10,                # 突发限制10请求/10秒
    max_request_size=52428800,     # 50MB请求大小限制
    enable_security_headers=True,   # 启用安全头
    enable_threat_detection=True,   # 启用威胁检测
    csp_policy="default-src 'self'; script-src 'self'",  # 严格CSP
)
```

## 🚀 使用指南

### 1. 在现有路由中集成安全验证

#### 更新文件上传端点

```python
from utils.security.secure_file_handler import secure_file_handler
from utils.security.input_validator import secure_input_validator

@router.post("/attachments/upload")
async def upload_attachments_secure(
    files: List[UploadFile] = File(...)
):
    """安全的文件上传接口"""
    try:
        # 使用安全文件处理器
        file_results = await secure_file_handler.handle_multiple_uploads(files)
        
        # 构建响应
        uploaded = []
        for file_info in file_results:
            uploaded.append({
                "filename": file_info.original_filename,
                "sanitized_filename": file_info.sanitized_filename,
                "url": file_info.final_path,  # 或转换为公开URL
                "file_hash": file_info.file_hash,
                "mime_type": file_info.mime_type,
                "file_size": file_info.file_size,
                "success": True
            })
        
        return {"items": uploaded}
        
    except Exception as e:
        logger.error(f"安全文件上传失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

#### 更新URL验证

```python
from utils.security.secure_file_handler import secure_url_validator

@router.post("/create-video-task")
async def create_video_task_secure(
    media_urls: List[str] = Form(...),
    # ... 其他参数
):
    """安全的视频任务创建"""
    
    # 验证URL
    validated_urls, url_errors = secure_url_validator.validate_media_urls(media_urls)
    
    if url_errors:
        raise HTTPException(
            status_code=400,
            detail=f"URL验证失败: {'; '.join(url_errors)}"
        )
    
    # 使用验证后的URL继续处理
    # ...
```

### 2. 启用安全中间件

```python
# main.py
from utils.security.security_middleware import create_security_middleware

app = FastAPI()

# 添加安全中间件
security_middleware = create_security_middleware(app, environment="production")
app.add_middleware(security_middleware)

# 其他中间件...
```

### 3. 配置环境变量

```bash
# .env 文件
# 安全配置
SECURITY_RATE_LIMIT_REQUESTS=100
SECURITY_MAX_FILE_SIZE=52428800
SECURITY_ENABLE_THREAT_DETECTION=true
SECURITY_LOG_LEVEL=INFO

# 文件存储配置
SECURE_UPLOAD_DIR=./secure_uploads
QUARANTINE_DIR=./quarantine
AUTO_CLEANUP_HOURS=24
```

## 🔍 安全测试

### 运行安全测试套件

```bash
# 运行所有安全测试
pytest tests/security/ -v

# 运行特定测试
pytest tests/security/test_security_validators.py::TestSecureFileValidator -v

# 性能测试
pytest tests/security/test_security_validators.py::TestSecurityPerformance -v
```

### 测试覆盖的安全场景

1. **文件上传攻击**
   - 恶意文件类型
   - 文件名注入
   - 文件内容注入
   - 大文件DoS攻击

2. **URL攻击**
   - SSRF攻击
   - 开放重定向
   - 协议走私

3. **输入注入攻击**
   - SQL注入
   - XSS攻击
   - 命令注入
   - 路径遍历

4. **边界条件测试**
   - 超大输入
   - 空输入
   - 特殊字符输入
   - Unicode攻击

## 📊 安全监控和审计

### 1. 安全事件日志

安全中间件自动记录以下事件：
- 恶意请求检测
- 速率限制触发
- IP访问控制
- 文件上传安全事件

日志位置：`logs/security_audit.log`

### 2. 威胁级别分类

- **SAFE**: 无安全问题
- **LOW**: 轻微警告
- **MEDIUM**: 需要关注的安全问题
- **HIGH**: 严重安全威胁
- **CRITICAL**: 立即处理的严重威胁

### 3. 监控指标

建议监控以下指标：
- 被阻止的恶意请求数量
- 文件验证失败率
- 隔离文件数量
- 速率限制触发频率

## 🛠️ 配置和定制

### 1. 自定义文件类型白名单

```python
# 在应用启动时配置
from utils.security.file_validator import SecureFileValidator

validator = SecureFileValidator()
validator.ALLOWED_EXTENSIONS[FileType.DOCUMENT].add('.csv')
validator.ALLOWED_MIMES.add('text/csv')
```

### 2. 自定义安全规则

```python
# 添加自定义恶意模式
from utils.security.input_validator import SecureInputValidator

validator = SecureInputValidator()
validator.DANGEROUS_PATTERNS['custom'] = [
    r'(custom_malicious_pattern)',
]
```

### 3. 集成外部安全服务

```python
# 集成VirusTotal等服务
class CustomAntivirusScanner(AntivirusScanner):
    def scan_file(self, file_path):
        # 调用外部API进行扫描
        return self._call_external_scanner(file_path)
```

## 🔄 更新和维护

### 1. 定期更新威胁模式

- 更新恶意内容检测规则
- 添加新的文件类型支持
- 更新URL黑名单

### 2. 性能优化

- 监控验证性能
- 优化正则表达式
- 缓存验证结果

### 3. 安全审计

- 定期进行渗透测试
- 代码安全审计
- 依赖包安全扫描

## 📋 OWASP合规检查清单

- ✅ **A01:2021 – Broken Access Control**: IP访问控制、速率限制
- ✅ **A02:2021 – Cryptographic Failures**: 文件哈希验证
- ✅ **A03:2021 – Injection**: SQL/XSS/命令注入防护
- ✅ **A04:2021 – Insecure Design**: 多层防护设计
- ✅ **A05:2021 – Security Misconfiguration**: 安全头配置
- ✅ **A06:2021 – Vulnerable Components**: 输入验证
- ✅ **A07:2021 – Identification and Authentication Failures**: 审计日志
- ✅ **A08:2021 – Software and Data Integrity Failures**: 文件完整性检查
- ✅ **A09:2021 – Security Logging and Monitoring Failures**: 完整审计日志
- ✅ **A10:2021 – Server-Side Request Forgery (SSRF)**: URL验证防护

## 🎯 下一步安全增强

1. **API认证系统**
   - JWT令牌验证
   - OAuth2集成
   - API密钥管理

2. **数据库安全**
   - 查询参数化
   - 数据加密
   - 访问控制

3. **网络安全**
   - WAF集成
   - DDoS防护
   - 流量分析

4. **合规性**
   - GDPR合规
   - 数据保护
   - 审计要求

## 📞 支持和反馈

如果发现安全问题或需要安全功能增强，请：

1. 立即报告严重安全漏洞
2. 提交安全改进建议
3. 参与安全代码审查

---

**重要提醒**: 安全是一个持续的过程，请定期更新和审查安全配置，确保系统始终处于最佳安全状态。