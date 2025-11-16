# 🔐 SoloCore Docker 安全配置指南

## ⚠️ 重要提示

**当前配置仅适用于开发和测试环境！生产环境部署前必须修改以下配置。**

---

## 📋 需要修改的配置清单

### 1. PostgreSQL 密码配置

**文件位置**: `docker/postgres/docker-compose.yml`

**第 14 行**:
```yaml
# ⚠️ 生产环境必须修改：请使用强密码替换默认密码
POSTGRES_PASSWORD: solocore_pass_2024
```

**修改为**:
```yaml
POSTGRES_PASSWORD: 你的强密码
```

**强密码要求**:
- 至少 16 位字符
- 包含大写字母、小写字母、数字、特殊字符
- 示例: `P@ssw0rd!2024_Pg#Secure`

---

### 2. PostgreSQL 端口绑定

**文件位置**: `docker/postgres/docker-compose.yml`

**第 24 行**:
```yaml
# ⚠️ 生产环境必须修改：建议改为 "127.0.0.1:5432:5432" 仅本地访问
# 当前配置 0.0.0.0 会暴露到公网，仅适用于测试环境
ports:
  - "0.0.0.0:5432:5432"
```

**生产环境修改为**（仅本地访问）:
```yaml
ports:
  - "127.0.0.1:5432:5432"
```

**或**（指定内网 IP）:
```yaml
ports:
  - "192.168.1.100:5432:5432"  # 替换为你的服务器内网 IP
```

---

### 3. Redis 密码配置

**文件位置**: `docker/redis/docker-compose.yml`

**第 11 行**:
```yaml
# ⚠️ 生产环境必须修改：请使用强密码替换默认密码
command: redis-server /usr/local/etc/redis/redis.conf --requirepass solocore_redis_pass_2024
```

**修改为**:
```yaml
command: redis-server /usr/local/etc/redis/redis.conf --requirepass 你的强密码
```

---

### 4. Redis 端口绑定

**文件位置**: `docker/redis/docker-compose.yml`

**第 17 行**:
```yaml
# ⚠️ 生产环境必须修改：建议改为 "127.0.0.1:6379:6379" 仅本地访问
# 当前配置 0.0.0.0 会暴露到公网，仅适用于测试环境
ports:
  - "0.0.0.0:6379:6379"
```

**生产环境修改为**（仅本地访问）:
```yaml
ports:
  - "127.0.0.1:6379:6379"
```

---

### 5. 应用配置文件

**文件位置**: `textloom/.env` (或你的应用配置文件)

修改数据库连接字符串中的密码：

```env
# ⚠️ 将密码修改为与 docker-compose.yml 中相同的密码

# PostgreSQL 配置
database_url=postgresql+asyncpg://solocore_user:你的PostgreSQL密码@localhost:5432/solocore

# Redis 配置
redis_password=你的Redis密码
```

---

## 🛡️ 安全最佳实践

### 1. 密码管理

✅ **推荐做法**:
- 使用密码管理器生成强密码
- 不同服务使用不同的密码
- 定期更换密码（至少每 90 天）
- 不要在代码中硬编码密码

❌ **避免**:
- 使用简单密码（如 `123456`, `password`）
- 在多个服务中重复使用相同密码
- 将密码提交到 Git 仓库

### 2. 网络安全

✅ **推荐做法**:
- 仅在必要时才暴露端口到公网
- 使用防火墙限制访问来源 IP
- 启用 SSL/TLS 加密连接
- 使用 VPN 或跳板机访问数据库

❌ **避免**:
- 使用 `0.0.0.0` 绑定数据库端口到公网
- 不设置防火墙规则
- 使用弱加密或不加密传输

### 3. 数据安全

✅ **推荐做法**:
- 每天自动备份数据
- 定期测试数据恢复流程
- 加密备份文件
- 异地存储备份

❌ **避免**:
- 不备份数据
- 将备份文件存储在同一台服务器
- 备份文件无加密

---

## 🚀 快速部署检查清单

在生产环境部署前，请确保完成以下检查：

- [ ] ✅ 修改 PostgreSQL 密码 (`docker/postgres/docker-compose.yml` 第 14 行)
- [ ] ✅ 修改 PostgreSQL 端口绑定 (`docker/postgres/docker-compose.yml` 第 24 行)
- [ ] ✅ 修改 Redis 密码 (`docker/redis/docker-compose.yml` 第 11 行)
- [ ] ✅ 修改 Redis 端口绑定 (`docker/redis/docker-compose.yml` 第 17 行)
- [ ] ✅ 更新应用配置文件中的数据库连接密码
- [ ] ✅ 配置防火墙规则（仅允许必要的 IP 访问）
- [ ] ✅ 设置数据备份计划（每天至少一次）
- [ ] ✅ 测试数据恢复流程
- [ ] ✅ 配置监控和告警系统
- [ ] ✅ 审查日志记录配置

---

## 📞 安全问题反馈

如果发现安全漏洞或有安全方面的建议，请通过以下方式联系：

- 📧 邮箱: 364430879@qq.com
- 💬 微信: 见 README.md

**请不要公开披露安全漏洞，我们会在修复后给予致谢。**

---

© 2025 SoloCore Contributors. All rights reserved.
