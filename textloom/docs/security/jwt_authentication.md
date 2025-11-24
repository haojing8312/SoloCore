# JWT认证系统文档

TextLoom 现在支持基于JWT的用户认证系统，提供安全的用户注册、登录和权限管理功能。

## 功能特性

### 🔐 核心功能
- **用户注册和登录**：完整的用户生命周期管理
- **JWT Token管理**：访问Token + 刷新Token双token机制
- **密码安全**：bcrypt哈希加密，强密码策略
- **会话管理**：多设备登录跟踪，单设备或全设备登出
- **权限控制**：基于角色的访问控制（RBAC）
- **向后兼容**：与现有内部测试Token系统完全兼容

### 🛡️ 安全特性
- **Token版本控制**：防止旧Token重放攻击
- **刷新Token撤销**：数据库级别的Token状态管理
- **设备跟踪**：记录登录设备和IP地址
- **密码策略**：强制复杂密码要求
- **会话过期**：自动清理过期Token

## 配置要求

### 环境变量设置

复制 `.env.example` 为 `.env` 并配置以下必需项：

```bash
# JWT认证密钥（必需）
SECRET_KEY=your_secret_key_here  # 使用: openssl rand -hex 32 生成

# JWT配置
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 数据库配置（必需）
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# 内部测试Token（可选，仅开发/测试环境）
INTERNAL_TEST_TOKEN=your_internal_test_token
```

### 数据库迁移

运行数据库迁移以创建用户表：

```bash
# 生成迁移文件
uv run alembic revision --autogenerate -m "add user authentication tables"

# 应用迁移
uv run alembic upgrade head
```

### 创建超级用户

系统部署后，创建第一个管理员账户：

```bash
uv run python scripts/create_superuser.py

# 查看现有超级用户
uv run python scripts/create_superuser.py --list
```

## API端点

### 认证相关

| 端点 | 方法 | 描述 | 认证要求 |
|------|------|------|----------|
| `/auth/register` | POST | 用户注册 | 无 |
| `/auth/login` | POST | 用户登录 | 无 |
| `/auth/refresh` | POST | 刷新访问Token | 刷新Token |
| `/auth/logout` | POST | 用户登出 | 访问Token |
| `/auth/logout-all` | POST | 全设备登出 | 访问Token |

### 用户管理

| 端点 | 方法 | 描述 | 认证要求 |
|------|------|------|----------|
| `/auth/me` | GET | 获取当前用户信息 | 访问Token |
| `/auth/me` | PUT | 更新用户信息 | 访问Token |
| `/auth/change-password` | POST | 修改密码 | 访问Token |
| `/auth/sessions` | GET | 获取活跃会话 | 访问Token |
| `/auth/sessions/{id}` | DELETE | 撤销指定会话 | 访问Token |
| `/auth/stats` | GET | 获取用户统计 | 访问Token |

### 管理员功能

| 端点 | 方法 | 描述 | 认证要求 |
|------|------|------|----------|
| `/auth/admin/users` | GET | 获取用户列表 | 超级用户 |
| `/auth/admin/users/{id}/activate` | PUT | 激活用户 | 超级用户 |
| `/auth/admin/users/{id}/deactivate` | PUT | 停用用户 | 超级用户 |

## 使用示例

### 1. 用户注册

```bash
curl -X POST "http://localhost:48095/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "New User",
    "password": "SecurePassword123!",
    "confirm_password": "SecurePassword123!"
  }'
```

### 2. 用户登录

```bash
curl -X POST "http://localhost:48095/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "SecurePassword123!",
    "remember_me": true,
    "device_info": "Web Browser"
  }'
```

响应示例：
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "New User",
    "is_active": true,
    "is_superuser": false
  }
}
```

### 3. 使用访问Token访问受保护端点

```bash
curl -X GET "http://localhost:48095/auth/me" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 4. 刷新访问Token

```bash
curl -X POST "http://localhost:48095/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

### 5. 用户登出

```bash
curl -X POST "http://localhost:48095/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -d '{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

## 中间件和依赖项

### 认证依赖项

在路由中使用以下依赖项来实现认证：

```python
from utils.auth_middleware import (
    get_current_user,           # 获取当前用户（必需认证）
    get_current_user_optional,  # 获取当前用户（可选认证）
    get_current_active_user,    # 获取当前活跃用户
    get_current_superuser       # 获取当前超级用户
)

# 示例路由
@router.get("/protected")
async def protected_endpoint(
    current_user: UserResponse = Depends(get_current_active_user)
):
    return {"message": f"Hello {current_user.username}!"}

@router.get("/admin-only")
async def admin_endpoint(
    current_user: UserResponse = Depends(get_current_superuser)
):
    return {"message": "Admin access granted"}
```

### 兼容性

认证中间件完全兼容现有的内部测试Token系统：

```python
# 支持内部测试Token
curl -X GET "http://localhost:48095/internal/analyzer/analyze-image" \
  -H "x-test-token: your_internal_test_token"

# 同时支持JWT Token
curl -X GET "http://localhost:48095/auth/me" \
  -H "Authorization: Bearer jwt_access_token"
```

## 安全最佳实践

### 1. 密钥管理
- 使用强随机密钥：`openssl rand -hex 32`
- 定期轮换JWT密钥
- 生产环境禁用内部测试Token

### 2. Token管理
- 访问Token短期有效（30分钟）
- 刷新Token长期有效（7天）
- 实施Token黑名单机制

### 3. 会话安全
- 记录登录设备和IP
- 监控异常登录活动
- 支持强制全设备登出

### 4. 密码安全
- 强制复杂密码策略
- 使用bcrypt哈希
- 支持密码修改历史

## 错误处理

### 常见错误码

| 状态码 | 错误 | 描述 |
|--------|------|------|
| 401 | Unauthorized | Token无效或已过期 |
| 403 | Forbidden | 权限不足 |
| 400 | Bad Request | 请求参数错误 |
| 409 | Conflict | 用户名或邮箱已存在 |

### 错误响应格式

```json
{
  "detail": "Token已过期",
  "type": "token_expired"
}
```

## 数据库模型

### 用户表 (users)

```sql
CREATE TABLE textloom_core.users (
    id UUID PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    avatar_url VARCHAR(500),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'zh-CN',
    token_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);
```

### 刷新Token表 (refresh_tokens)

```sql
CREATE TABLE textloom_core.refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES textloom_core.users(id) ON DELETE CASCADE,
    jti VARCHAR(36) UNIQUE NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_revoked BOOLEAN DEFAULT FALSE,
    device_info VARCHAR(200),
    ip_address VARCHAR(45)
);
```

## 监控和维护

### 清理过期Token

创建定时任务清理过期的刷新Token：

```python
from services.token_service import token_service

async def cleanup_expired_tokens():
    async with get_db_session() as db_session:
        count = await token_service.clean_expired_tokens(db_session)
        print(f"清理了 {count} 个过期Token")
```

### 监控指标

- 活跃用户数量
- Token刷新频率
- 登录失败率
- 会话持续时间

## 故障排除

### 常见问题

1. **Token验证失败**
   - 检查SECRET_KEY配置
   - 验证Token格式和签名
   - 确认Token未过期

2. **数据库连接错误**
   - 检查DATABASE_URL配置
   - 确认数据库服务运行正常
   - 验证迁移已正确应用

3. **权限被拒绝**
   - 确认用户状态为活跃
   - 检查用户权限级别
   - 验证Token版本一致性

### 调试模式

启用调试日志：

```bash
export LOG_LEVEL=DEBUG
uv run uvicorn main:app --reload
```

查看详细的认证日志输出。