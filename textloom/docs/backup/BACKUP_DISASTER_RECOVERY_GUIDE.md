# TextLoom 备份和灾难恢复系统指南

## 概览

TextLoom备份和灾难恢复系统提供了全面的数据保护和业务连续性解决方案，支持：

- **自动化备份**：PostgreSQL数据库、Redis缓存、工作空间文件和日志的定时备份
- **多存储后端**：本地存储、MinIO和华为云OBS支持
- **灾难恢复**：完整的故障检测、评估和恢复流程
- **实时监控**：备份状态监控、告警通知和Web仪表板
- **容器化部署**：基于Docker的可扩展备份服务架构

## 系统架构

### 核心组件

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   备份管理器     │    │   灾难恢复管理   │    │   备份监控器     │
│ BackupManager   │    │ DisasterRecovery │    │ BackupMonitor   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                │
                 ┌─────────────────────────────┐
                 │      存储后端               │
                 │  ┌─────────┬─────────────┐  │
                 │  │本地存储 │远程存储(MinIO/OBS)│  │
                 │  └─────────┴─────────────┘  │
                 └─────────────────────────────┘
```

### 数据流

1. **备份流程**：数据库 → 导出 → 压缩 → 加密 → 本地存储 → 远程同步
2. **监控流程**：收集指标 → 检查规则 → 触发告警 → 发送通知
3. **恢复流程**：故障检测 → 评估损失 → 执行恢复 → 验证结果

## 快速开始

### 1. 环境准备

```bash
# 复制环境配置文件
cp .env.backup.example .env.backup

# 编辑配置文件，设置必要的参数
vim .env.backup

# 确保依赖服务运行
docker-compose up -d postgres redis
```

### 2. 安装备份系统

```bash
# 使用Docker Compose部署
docker-compose -f docker-compose.backup.yml up -d

# 或者本地安装
bash scripts/backup_scheduler.sh install
```

### 3. 验证安装

```bash
# 检查服务状态
curl http://localhost:8081/api/status

# 运行测试备份
python scripts/backup_manager.py backup --type daily

# 查看监控仪表板
open http://localhost:8081
```

## 详细配置

### 环境变量配置

完整的环境变量配置请参考 `.env.backup.example` 文件。主要配置项包括：

#### 备份策略
```bash
BACKUP_DAILY_RETENTION_DAYS=7      # 日备份保留天数
BACKUP_WEEKLY_RETENTION_WEEKS=4    # 周备份保留周数
BACKUP_MONTHLY_RETENTION_MONTHS=12 # 月备份保留月数
BACKUP_COMPRESSION_ENABLED=true    # 启用压缩
BACKUP_ENCRYPTION_ENABLED=true     # 启用加密
```

#### 存储配置
```bash
# 本地存储
BACKUP_LOCAL_DIR=./backups

# MinIO存储
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=textloom-backups

# 华为云OBS
OBS_ACCESS_KEY=your_access_key
OBS_SECRET_KEY=your_secret_key
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
OBS_BUCKET=textloom-backups
```

#### 告警通知
```bash
# 邮件告警
BACKUP_EMAIL_ALERTS_ENABLED=true
BACKUP_SMTP_SERVER=smtp.gmail.com
BACKUP_SMTP_PORT=587
BACKUP_EMAIL_FROM=alerts@yourdomain.com
BACKUP_EMAIL_TO=admin@yourdomain.com

# Slack告警
BACKUP_SLACK_ALERTS_ENABLED=true
BACKUP_SLACK_WEBHOOK_URL=https://hooks.slack.com/your/webhook/url
BACKUP_SLACK_CHANNEL=#alerts
```

## 使用指南

### 备份管理

#### 创建备份
```bash
# 创建全量备份
python scripts/backup_manager.py backup --type full

# 创建增量备份
python scripts/backup_manager.py backup --type incremental

# 备份特定组件
python scripts/backup_manager.py backup --components database redis
```

#### 验证备份
```bash
# 验证指定备份
python scripts/backup_manager.py verify --backup-id 20250820_120000

# 列出所有备份
python scripts/backup_manager.py list
```

#### 恢复备份
```bash
# 从备份恢复
python scripts/backup_manager.py restore --backup-id 20250820_120000

# 恢复特定组件
python scripts/backup_manager.py restore --backup-id 20250820_120000 --components database

# 恢复到指定目录
python scripts/backup_manager.py restore --backup-id 20250820_120000 --target-dir /tmp/restore
```

### 灾难恢复

#### 评估系统状态
```bash
# 评估整体健康状况
python scripts/disaster_recovery.py assess

# 输出示例：
# {
#   "overall_status": "healthy",
#   "services": [
#     {"name": "postgresql", "status": "healthy"},
#     {"name": "redis", "status": "healthy"}
#   ],
#   "recommendations": []
# }
```

#### 执行灾难恢复
```bash
# 数据库故障恢复
python scripts/disaster_recovery.py recover --scenario database_failure

# Redis故障恢复
python scripts/disaster_recovery.py recover --scenario redis_failure

# 全灾难恢复
python scripts/disaster_recovery.py recover --scenario full_disaster

# 演练模式（不执行实际操作）
python scripts/disaster_recovery.py recover --scenario database_failure --dry-run
```

#### 灾难恢复演练
```bash
# 执行灾难恢复演练
python scripts/disaster_recovery.py drill --scenario database_failure

# 演练结果包含：
# - 恢复时间是否满足RTO目标
# - 发现的问题和改进建议
# - 恢复步骤的执行情况
```

### 监控和告警

#### 启动监控服务
```bash
# 启动监控后台服务
python scripts/backup_monitor.py start

# 启动监控仪表板
python scripts/backup_monitor.py dashboard --port 8081

# 查看当前状态
python scripts/backup_monitor.py status
```

#### 测试告警系统
```bash
# 测试所有告警渠道
python scripts/backup_monitor.py alert --test

# 输出示例：
# 告警测试结果:
#   email: success
#   webhook: success  
#   slack: success
```

#### 监控Web界面

访问 `http://localhost:8081` 可查看：

- **实时指标**：备份成功率、磁盘使用率、最近备份时间
- **历史统计**：7天内的备份趋势和性能指标
- **活跃告警**：当前未解决的告警列表
- **系统状态**：各服务组件的健康状态

### 自动化调度

#### 安装调度任务
```bash
# 安装Cron调度（普通用户）
bash scripts/backup_scheduler.sh install

# 安装systemd定时器（需要root权限）
sudo bash scripts/backup_scheduler.sh install
```

#### 查看调度状态
```bash
# 查看当前调度配置
bash scripts/backup_scheduler.sh status

# 输出包含：
# - Cron任务列表
# - systemd定时器状态
# - 最近备份记录
```

#### 手动执行调度任务
```bash
# 手动运行日备份
bash scripts/backup_scheduler.sh run daily

# 手动运行清理任务
bash scripts/backup_scheduler.sh cleanup
```

## 容器化部署

### Docker Compose 部署

```bash
# 启动完整的备份服务栈
docker-compose -f docker-compose.backup.yml up -d

# 查看服务状态
docker-compose -f docker-compose.backup.yml ps

# 查看日志
docker-compose -f docker-compose.backup.yml logs backup-manager
docker-compose -f docker-compose.backup.yml logs backup-monitor
```

### 服务说明

| 服务名称 | 端口 | 描述 |
|---------|------|------|
| backup-manager | - | 备份执行和管理服务 |
| backup-monitor | 8081 | 监控和告警服务 |
| backup-scheduler | - | 定时调度服务 |
| minio | 9000/9001 | 对象存储服务 |

### 数据卷

| 卷名称 | 路径 | 描述 |
|--------|------|------|
| backup-data | /backups/local | 本地备份存储 |
| backup-logs | /app/logs | 备份服务日志 |
| minio-data | /data | MinIO数据存储 |

## 故障排除

### 常见问题

#### 1. 备份失败
```bash
# 检查磁盘空间
df -h /backups

# 查看错误日志
tail -f logs/backup_manager.error.log

# 检查数据库连接
python -c "
import asyncio
import asyncpg
asyncio.run(asyncpg.connect('$DATABASE_URL'))
print('数据库连接正常')
"
```

#### 2. 监控服务无响应
```bash
# 检查服务进程
ps aux | grep backup_monitor

# 重启监控服务
docker-compose -f docker-compose.backup.yml restart backup-monitor

# 检查端口占用
netstat -tlnp | grep 8081
```

#### 3. 告警不工作
```bash
# 测试告警配置
python scripts/backup_monitor.py alert --test

# 检查环境变量
env | grep BACKUP_

# 验证SMTP配置
python -c "
import smtplib
server = smtplib.SMTP('$BACKUP_SMTP_SERVER', $BACKUP_SMTP_PORT)
server.starttls()
server.login('$BACKUP_SMTP_USERNAME', '$BACKUP_SMTP_PASSWORD')
print('SMTP连接正常')
server.quit()
"
```

#### 4. 恢复失败
```bash
# 验证备份文件完整性
python scripts/backup_manager.py verify --backup-id BACKUP_ID

# 检查目标路径权限
ls -la /path/to/restore/target

# 查看详细错误信息
python scripts/disaster_recovery.py recover --scenario database_failure --dry-run
```

### 日志文件

| 日志文件 | 描述 |
|---------|------|
| logs/backup_manager.log | 备份管理器日志 |
| logs/backup_monitor.log | 监控服务日志 |
| logs/disaster_recovery.log | 灾难恢复日志 |
| logs/backup_scheduler.log | 调度任务日志 |
| logs/system_metrics.log | 系统指标日志 |

### 性能调优

#### 备份性能优化
```bash
# 增加并行任务数
export BACKUP_PARALLEL_JOBS=8

# 调整压缩块大小
export BACKUP_CHUNK_SIZE=134217728  # 128MB

# 启用增量备份
python scripts/backup_manager.py backup --type incremental
```

#### 监控性能优化
```bash
# 调整监控间隔
export BACKUP_MONITOR_INTERVAL=600  # 10分钟

# 减少指标保留天数
export BACKUP_METRICS_RETENTION_DAYS=7
```

## 安全考虑

### 备份加密

备份系统支持AES-256加密：

```bash
# 生成新的加密密钥
python -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())
"

# 设置加密密钥
export BACKUP_ENCRYPTION_KEY="your_generated_key"
```

### 访问控制

- 备份文件权限：仅备份用户可读写
- 网络访问：监控端口仅内网访问
- API认证：可选的API密钥认证

### 审计日志

系统记录所有备份和恢复操作：

```bash
# 查看审计日志
tail -f logs/backup_audit.log

# 日志格式：
# [2025-08-20 12:00:00] [AUDIT] USER=backup ACTION=create_backup BACKUP_ID=20250820_120000 STATUS=success
```

## 高可用配置

### 主备模式

```yaml
# docker-compose.ha.yml
services:
  backup-manager-primary:
    # 主备份服务
  
  backup-manager-standby:
    # 备用备份服务
    environment:
      - BACKUP_MODE=standby
```

### 负载均衡

```bash
# 多个监控实例
docker-compose -f docker-compose.backup.yml up --scale backup-monitor=3
```

## API参考

### 监控API

```bash
# 获取系统状态
GET /api/status

# 获取实时指标
GET /api/metrics

# 获取告警列表
GET /api/alerts

# 确认告警
POST /api/alerts/{alert_id}/acknowledge
```

### 响应示例

```json
{
  "monitoring_status": "running",
  "current_metrics": {
    "backup_success_rate": 1.0,
    "last_backup_age_hours": 2.5,
    "disk_space_used_percent": 45.2
  },
  "active_alerts": [],
  "history_stats": {
    "avg_success_rate": 0.98,
    "avg_backup_age_hours": 12.3
  }
}
```

## 最佳实践

### 备份策略
1. **3-2-1规则**：至少3个副本，2种不同介质，1个异地备份
2. **定期测试**：每月至少测试一次恢复流程
3. **监控告警**：设置合理的告警阈值和通知渠道
4. **文档维护**：及时更新恢复程序文档

### 运维建议
1. **容量规划**：备份存储容量为生产数据的3-5倍
2. **网络带宽**：远程备份需要足够的上传带宽
3. **权限管理**：使用专用的备份用户账号
4. **定期演练**：季度进行灾难恢复演练

### 安全实践
1. **加密传输**：所有远程备份使用HTTPS/TLS
2. **密钥管理**：定期轮换加密密钥
3. **访问审计**：记录所有备份和恢复操作
4. **网络隔离**：备份网络与生产网络隔离

## 故障场景和恢复时间

| 故障类型 | RPO目标 | RTO目标 | 恢复步骤 |
|---------|---------|---------|----------|
| 数据库故障 | 1小时 | 30分钟 | 自动检测 → 备份恢复 → 服务重启 |
| Redis故障 | 15分钟 | 10分钟 | 重启服务 → 数据恢复 → 验证功能 |
| 应用故障 | 0分钟 | 5分钟 | 进程重启 → 健康检查 |
| 存储故障 | 2小时 | 1小时 | 存储切换 → 数据同步 → 服务恢复 |
| 全站灾难 | 4小时 | 2小时 | 备用环境 → 数据恢复 → 流量切换 |

## 更新和维护

### 版本升级
```bash
# 停止服务
docker-compose -f docker-compose.backup.yml down

# 拉取新镜像
docker-compose -f docker-compose.backup.yml pull

# 启动新版本
docker-compose -f docker-compose.backup.yml up -d
```

### 配置变更
```bash
# 编辑配置文件
vim .env.backup

# 重启相关服务
docker-compose -f docker-compose.backup.yml restart backup-manager backup-monitor
```

### 清理和维护
```bash
# 清理过期备份
bash scripts/backup_scheduler.sh cleanup

# 清理容器镜像
docker system prune -f

# 检查磁盘使用
du -sh backups/ logs/ minio_data/
```

## 技术支持

如有问题或需要支持，请：

1. 查看本文档的故障排除部分
2. 检查相关日志文件
3. 运行诊断命令验证配置
4. 联系技术支持团队

---

**注意**：本备份和灾难恢复系统是TextLoom项目的核心组件，建议在生产环境使用前充分测试所有功能和恢复流程。