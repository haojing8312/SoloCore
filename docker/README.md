# SoloCore Docker 服务配置

本目录包含 SoloCore 项目所需的 Docker 服务配置。

## 服务列表

### PostgreSQL 数据库
- **目录**: `postgres/`
- **端口**: 5432（公网访问）
- **默认配置**:
  - 数据库: `solocore`
  - 用户名: `solocore_user`
  - 密码: `solocore_pass_2024`
  - Schema: `textloom_core`（自动创建）

### Redis 缓存
- **目录**: `redis/`
- **端口**: 6379（公网访问）
- **默认配置**:
  - 密码: `solocore_redis_pass_2024`
  - 持久化: 启用 RDB + AOF
  - 最大内存: 256MB

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
database_url=postgresql+asyncpg://solocore_user:solocore_pass_2024@localhost:5432/solocore

# Redis 配置
redis_host=localhost
redis_port=6379
redis_db=0
redis_password=solocore_redis_pass_2024
```

## 数据持久化

- **PostgreSQL**: 数据存储在 Docker volume `postgres_data`
- **Redis**: 数据存储在 Docker volume `redis_data`

查看数据卷：
```bash
docker volume ls | grep solocore
```

备份数据卷：
```bash
# PostgreSQL 数据备份
docker run --rm \
  -v postgres_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz -C /data .

# Redis 数据备份
docker run --rm \
  -v redis_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup.tar.gz -C /data .
```

## 健康检查

检查服务状态：

```bash
# 检查 PostgreSQL
docker exec solocore-postgres pg_isready -U solocore_user

# 检查 Redis
docker exec solocore-redis redis-cli -a solocore_redis_pass_2024 ping
```

## 生产环境注意事项

⚠️ **当前配置为测试环境，生产环境需要修改**：

1. **修改默认密码** - 使用强密码替换默认密码
2. **限制网络访问** - 将 `0.0.0.0` 改为特定 IP 或使用防火墙
3. **调整资源限制** - 根据实际需求调整 CPU 和内存限制
4. **启用 SSL/TLS** - 配置加密连接
5. **定期备份** - 建立自动化备份策略
6. **监控告警** - 集成监控系统

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
