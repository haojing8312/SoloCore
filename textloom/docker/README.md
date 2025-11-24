# Docker 配置文件

本目录包含 TextLoom 项目的所有 Docker 相关配置文件，按功能分类组织。

## 📁 目录结构

```
docker/
├── README.md                          # 本说明文件
├── compose/                           # Docker Compose 文件
│   ├── docker-compose.yml            # 主要服务编排
│   ├── docker-compose.backup.yml     # 备份服务配置
│   ├── docker-compose.optimized.yml  # 优化版本配置
│   └── monitoring-stack.yml          # 监控堆栈编排
├── dockerfiles/                       # Dockerfile 文件
│   ├── Dockerfile                     # 主应用 Dockerfile
│   └── Dockerfile.backup             # 备份服务 Dockerfile
├── config/                            # 服务配置文件
│   ├── prometheus/                    # Prometheus 配置
│   │   ├── prometheus.yml            # Prometheus 主配置
│   │   └── alert_rules.yml           # 告警规则配置
│   ├── grafana/                       # Grafana 配置
│   │   └── provisioning/             # 自动配置
│   │       ├── dashboards/           # 仪表板配置
│   │       └── datasources/          # 数据源配置
│   └── alertmanager/                  # Alertmanager 配置
│       └── alertmanager.yml          # 告警管理器配置
├── backup/                            # 备份相关配置
│   ├── backup-crontab                # 备份定时任务
│   ├── backup-entrypoint.sh          # 备份入口脚本
│   ├── backup-healthcheck.sh         # 备份健康检查
│   └── backup-supervisor.conf        # Supervisor 配置
└── monitoring/                        # 监控相关配置
```

## 🚀 快速启动

### 基础服务启动

```bash
# 启动主要服务
docker-compose -f docker/compose/docker-compose.yml up -d

# 启动优化版本
docker-compose -f docker/compose/docker-compose.optimized.yml up -d
```

### 监控堆栈启动

```bash
# 启动完整监控堆栈 (Prometheus + Grafana + Alertmanager)
docker-compose -f docker/compose/monitoring-stack.yml up -d
```

### 备份服务启动

```bash
# 启动备份服务
docker-compose -f docker/compose/docker-compose.backup.yml up -d
```

## 🔧 配置说明

### Prometheus 监控
- **配置文件**: `config/prometheus/prometheus.yml`
- **告警规则**: `config/prometheus/alert_rules.yml`
- **端口**: 9090 (默认)
- **功能**: 系统指标收集和告警

### Grafana 仪表板
- **配置目录**: `config/grafana/provisioning/`
- **端口**: 3000 (默认)
- **功能**: 指标可视化和仪表板

### Alertmanager 告警
- **配置文件**: `config/alertmanager/alertmanager.yml`
- **端口**: 9093 (默认)
- **功能**: 告警通知管理

### 备份服务
- **定时任务**: `backup/backup-crontab`
- **入口脚本**: `backup/backup-entrypoint.sh`
- **健康检查**: `backup/backup-healthcheck.sh`
- **进程管理**: `backup/backup-supervisor.conf`

## 🛠️ 开发指南

### 构建自定义镜像

```bash
# 构建主应用镜像
docker build -f docker/dockerfiles/Dockerfile -t textloom:latest .

# 构建备份服务镜像
docker build -f docker/dockerfiles/Dockerfile.backup -t textloom-backup:latest .
```

### 环境变量配置

在使用 Docker Compose 之前，请确保已配置以下环境变量：

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
nano .env
```

关键环境变量：
- `DATABASE_URL`: 数据库连接字符串
- `REDIS_URL`: Redis 连接字符串  
- `SECRET_KEY`: JWT 密钥
- `OPENAI_API_KEY` / `GEMINI_API_KEY`: AI 模型 API 密钥

### 网络和端口配置

默认端口映射：
- **主应用**: 8000
- **Celery Flower**: 5555
- **Prometheus**: 9090
- **Grafana**: 3000
- **Alertmanager**: 9093
- **Redis**: 6379
- **PostgreSQL**: 5432

## 📊 监控和日志

### 日志查看

```bash
# 查看服务日志
docker-compose -f docker/compose/docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f docker/compose/docker-compose.yml logs -f textloom-api
```

### 健康检查

```bash
# 检查服务状态
docker-compose -f docker/compose/docker-compose.yml ps

# 检查服务健康状态
docker-compose -f docker/compose/docker-compose.yml exec textloom-api curl http://localhost:8000/health
```

## 🔒 安全注意事项

1. **环境变量**: 生产环境中确保敏感信息通过环境变量或 Docker secrets 管理
2. **网络隔离**: 使用 Docker 网络进行服务间通信隔离
3. **镜像安全**: 定期更新基础镜像和依赖包
4. **访问控制**: 配置防火墙规则限制端口访问

## 🔄 维护操作

### 服务更新

```bash
# 停止服务
docker-compose -f docker/compose/docker-compose.yml down

# 拉取最新镜像
docker-compose -f docker/compose/docker-compose.yml pull

# 重新启动服务
docker-compose -f docker/compose/docker-compose.yml up -d
```

### 数据备份

```bash
# 手动触发备份
docker-compose -f docker/compose/docker-compose.backup.yml exec backup-service /app/backup-entrypoint.sh
```

## 📝 故障排除

### 常见问题

1. **端口冲突**: 检查端口是否被占用，修改 docker-compose.yml 中的端口映射
2. **数据库连接**: 确认数据库服务已启动且环境变量配置正确
3. **内存不足**: 监控容器内存使用，调整资源限制
4. **网络连接**: 检查 Docker 网络配置和服务发现

### 调试命令

```bash
# 进入容器调试
docker-compose -f docker/compose/docker-compose.yml exec textloom-api bash

# 查看容器资源使用
docker stats

# 检查网络连接
docker-compose -f docker/compose/docker-compose.yml exec textloom-api ping redis
```

---

更多详细信息请参考项目主文档 [`docs/README.md`](../docs/README.md)。