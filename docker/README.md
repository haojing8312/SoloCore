# SoloCore Docker 服务配置

本目录包含 SoloCore 项目所需的 Docker 服务配置。

## ⚠️ 安全警告

**当前配置仅用于开发和测试环境！生产环境使用前必须修改以下配置：**

1. **🔐 修改默认密码**
   - PostgreSQL 密码: `solocore_pass_2024` → 使用强密码
   - Redis 密码: `solocore_redis_pass_2024` → 使用强密码

2. **🌐 限制网络访问**
   - 当前端口绑定 `0.0.0.0` 会暴露到公网
   - 生产环境建议改为 `127.0.0.1` 仅本地访问
   - 或使用防火墙/安全组限制访问 IP

3. **📁 数据持久化**
   - 数据存储在 `./data/` 目录下
   - 请定期备份数据目录

## 服务列表

### PostgreSQL 数据库
- **目录**: `postgres/`
- **端口**: 5432（⚠️ 当前暴露公网，生产环境需修改）
- **默认配置**:
  - 数据库: `solocore`
  - 用户名: `solocore_user`
  - 密码: `solocore_pass_2024` ⚠️ **生产环境必须修改**
  - Schema: `textloom_core`（自动创建）
  - 数据目录: `./postgres/data/`

### Redis 缓存
- **目录**: `redis/`
- **端口**: 6379（⚠️ 当前暴露公网，生产环境需修改）
- **默认配置**:
  - 密码: `solocore_redis_pass_2024` ⚠️ **生产环境必须修改**
  - 持久化: 启用 RDB + AOF
  - 最大内存: 256MB
  - 数据目录: `./redis/data/`

## 快速启动

### 启动 PostgreSQL

```bash
# 进入 postgres 目录
cd docker/postgres

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 启动 Redis

```bash
# 进入 redis 目录
cd docker/redis

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 停止并删除数据卷（⚠️ 会删除所有数据）
docker-compose down -v
```

### 一键启动所有服务

```bash
# 在项目根目录执行
docker-compose -f docker/postgres/docker-compose.yml \
               -f docker/redis/docker-compose.yml \
               up -d

# 停止所有服务
docker-compose -f docker/postgres/docker-compose.yml \
               -f docker/redis/docker-compose.yml \
               down
```

## 连接信息

### PostgreSQL 连接

**连接字符串（asyncpg）**:
```
postgresql+asyncpg://solocore_user:solocore_pass_2024@localhost:5432/solocore
```

**psycopg2 连接字符串**:
```
postgresql+psycopg2://solocore_user:solocore_pass_2024@localhost:5432/solocore
```

**使用 psql 客户端连接**:
```bash
psql -h localhost -p 5432 -U solocore_user -d solocore
# 密码: solocore_pass_2024
```

### Redis 连接

**连接字符串**:
```
redis://:solocore_redis_pass_2024@localhost:6379/0
```

**使用 redis-cli 连接**:
```bash
redis-cli -h localhost -p 6379 -a solocore_redis_pass_2024
```

## 环境变量配置

在 `textloom/.env` 文件中配置：

```env
# PostgreSQL 配置
# ⚠️ 生产环境必须修改密码
database_url=postgresql+asyncpg://solocore_user:solocore_pass_2024@localhost:5432/solocore

# Redis 配置
# ⚠️ 生产环境必须修改密码
redis_host=localhost
redis_port=6379
redis_db=0
redis_password=solocore_redis_pass_2024
```

## 数据持久化

数据存储在各服务目录下的 `data/` 文件夹中：

- **PostgreSQL**: `docker/postgres/data/`
- **Redis**: `docker/redis/data/`

**备份数据：**

```bash
# PostgreSQL 数据备份（方法1：直接复制）
cp -r docker/postgres/data/ postgres-backup-$(date +%Y%m%d)/

# PostgreSQL 数据备份（方法2：使用 pg_dump）
docker exec solocore-postgres pg_dump -U solocore_user solocore > backup-$(date +%Y%m%d).sql

# Redis 数据备份（直接复制）
cp -r docker/redis/data/ redis-backup-$(date +%Y%m%d)/

# Redis 数据备份（使用 SAVE 命令）
docker exec solocore-redis redis-cli -a solocore_redis_pass_2024 SAVE
cp docker/redis/data/dump.rdb redis-backup-$(date +%Y%m%d).rdb
```

**恢复数据：**

```bash
# PostgreSQL 恢复
docker exec -i solocore-postgres psql -U solocore_user solocore < backup.sql

# Redis 恢复（停止容器后替换文件）
docker-compose -f docker/redis/docker-compose.yml down
cp backup.rdb docker/redis/data/dump.rdb
docker-compose -f docker/redis/docker-compose.yml up -d
```

## 健康检查

检查服务状态：

```bash
# 检查 PostgreSQL
docker exec solocore-postgres pg_isready -U solocore_user

# 检查 Redis
docker exec solocore-redis redis-cli -a solocore_redis_pass_2024 ping
```

## 生产环境安全检查清单

⚠️ **生产环境部署前必须完成以下检查**：

### 🔐 密码安全
- [ ] 修改 PostgreSQL 密码（`docker/postgres/docker-compose.yml` 第 14 行）
- [ ] 修改 Redis 密码（`docker/redis/docker-compose.yml` 第 11 行）
- [ ] 更新应用配置中的数据库连接密码
- [ ] 使用至少 16 位强密码（包含大小写字母、数字、特殊字符）

### 🌐 网络安全
- [ ] 修改端口绑定从 `0.0.0.0` 改为 `127.0.0.1`（仅本地访问）
  - PostgreSQL: `docker/postgres/docker-compose.yml` 第 24 行
  - Redis: `docker/redis/docker-compose.yml` 第 17 行
- [ ] 或配置防火墙/安全组限制访问 IP
- [ ] 考虑启用 SSL/TLS 加密连接

### 📁 数据安全
- [ ] 定期备份 `docker/postgres/data/` 和 `docker/redis/data/`
- [ ] 建立自动化备份策略（建议每天备份）
- [ ] 测试数据恢复流程
- [ ] 设置合适的文件权限（避免其他用户访问）

### ⚡ 性能优化
- [ ] 根据实际需求调整 CPU 和内存限制
- [ ] 调整 PostgreSQL 连接池大小
- [ ] 调整 Redis 最大内存限制

### 📊 监控运维
- [ ] 集成监控系统（如 Prometheus + Grafana）
- [ ] 配置告警规则（CPU、内存、磁盘使用率）
- [ ] 设置日志收集和分析

## 故障排除

### PostgreSQL 无法启动

```bash
# 查看日志
docker logs solocore-postgres

# 检查端口占用
netstat -ano | findstr :5432  # Windows
lsof -i :5432                 # Linux/Mac

# 重建容器
cd docker/postgres
docker-compose down -v
docker-compose up -d
```

### Redis 无法启动

```bash
# 查看日志
docker logs solocore-redis

# 检查端口占用
netstat -ano | findstr :6379  # Windows
lsof -i :6379                 # Linux/Mac

# 重建容器
cd docker/redis
docker-compose down -v
docker-compose up -d
```

### 连接被拒绝

1. 确认服务已启动: `docker ps | grep solocore`
2. 检查防火墙设置
3. 验证密码是否正确
4. 检查网络配置

## 许可证

本配置采用 [MIT License](../LICENSE) 开源。
