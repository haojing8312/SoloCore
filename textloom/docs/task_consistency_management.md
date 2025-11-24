# 任务一致性管理指南

本文档描述如何处理数据库任务与Redis/Celery任务不一致的问题。

## 问题场景

当手动删除数据库中的任务时，Celery仍会从Redis中拉取任务执行，导致以下错误：
```
创建脚本记录失败
任务 3dbc91ae-8dc7-401c-9f0b-61aaccc0c932 不存在或未更新
```

## 解决方案概述

实现了以下机制确保数据库与Redis的一致性：

1. **任务存在性验证装饰器** - 在Celery任务开始前检查数据库中的任务是否存在
2. **Redis任务清理机制** - 主动清理孤儿任务和过期任务结果
3. **管理工具脚本** - 提供命令行工具进行任务一致性管理

## 核心组件

### 1. 任务验证装饰器 (`utils/task_validation.py`)

- `@validate_task_exists` - 验证主任务存在性
- `@validate_sub_task_exists` - 验证子任务的父任务存在性

**工作原理**：
- 在Celery任务执行前检查数据库中的任务状态
- 如果任务不存在或已完成，自动撤销Celery任务并使用`Ignore`异常静默终止
- 任务状态设置为`REVOKED`而不是`FAILURE`

### 2. Redis清理工具 (`utils/redis_cleanup.py`)

- `RedisTaskCleaner` - 主要清理类
- 检测孤儿任务（Redis中存在但数据库中不存在）
- 撤销孤儿任务并清理过期结果

**功能**：
- 获取数据库和Redis中的活跃任务
- 识别不一致的任务
- 批量撤销孤儿任务
- 清理过期任务结果

### 3. 管理脚本

#### 命令行工具 (`scripts/task_cleanup.py`)

```bash
# 检查所有孤儿任务
python scripts/task_cleanup.py check

# 检查特定任务
python scripts/task_cleanup.py check --task-id <task_id>

# 执行清理（交互确认）
python scripts/task_cleanup.py cleanup

# 强制清理
python scripts/task_cleanup.py cleanup --force

# 监控任务状态
python scripts/task_cleanup.py monitor

# 撤销特定任务
python scripts/task_cleanup.py revoke --task-id <task_id>
```

#### 快速修复脚本 (`scripts/quick_fix_orphaned_tasks.py`)

```bash
# 立即清理所有孤儿任务
python scripts/quick_fix_orphaned_tasks.py
```

## 使用流程

### 立即修复当前问题

1. **停止Celery Worker**：
   ```bash
   ./stop_all.sh
   ```

2. **运行快速修复**：
   ```bash
   python scripts/quick_fix_orphaned_tasks.py
   ```

3. **重启服务**：
   ```bash
   ./start_all_services.sh
   ```

### 日常维护

1. **定期检查**：
   ```bash
   python scripts/task_cleanup.py monitor
   ```

2. **清理孤儿任务**：
   ```bash
   python scripts/task_cleanup.py cleanup
   ```

### 预防措施

1. **避免手动删除数据库任务**：
   - 使用API接口取消任务
   - 通过管理界面停止任务

2. **使用撤销功能**：
   ```bash
   python scripts/task_cleanup.py revoke --task-id <task_id>
   ```

## 自动化维护

### Celery定期任务

系统已配置定期清理任务：
- 任务名称：`cleanup_expired_tasks`
- 队列：`maintenance`
- 功能：自动清理24小时前的过期任务

### 启用定期清理

在Celery Beat中配置：
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-expired-tasks': {
        'task': 'tasks.video_processing_tasks.cleanup_expired_tasks',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
}
```

## 日志与监控

### 日志文件

- 应用日志：`logs/app.log`
- 清理日志：`logs/task_cleanup.log`
- Celery日志：`logs/celery_worker.log`

### 关键日志标识

- `🚫` - 任务被撤销
- `🧹` - 清理操作
- `✅` - 验证通过
- `⚠️` - 发现孤儿任务

## 故障排除

### 常见问题

1. **大量孤儿任务**：
   ```bash
   python scripts/task_cleanup.py cleanup --force
   ```

2. **任务无法撤销**：
   - 检查Redis连接
   - 重启Celery Worker

3. **数据库连接错误**：
   - 检查数据库连接配置
   - 验证数据库权限

### 调试命令

```bash
# 详细检查特定任务
python scripts/task_cleanup.py check --task-id <task_id> -v

# 监控并显示详细信息
python scripts/task_cleanup.py monitor -v
```

## 最佳实践

1. **定期维护**：每周运行一次清理检查
2. **监控日志**：关注任务一致性相关的警告
3. **谨慎操作**：避免直接操作数据库删除任务
4. **测试环境**：在测试环境中验证清理脚本
5. **备份策略**：重要操作前备份数据库

## 配置调优

### Redis连接池

在`config.py`中调整Redis连接参数：
```python
REDIS_MAX_CONNECTIONS = 50
REDIS_RETRY_ON_TIMEOUT = True
```

### Celery任务超时

调整任务超时设置：
```python
task_time_limit = 3600  # 1小时
task_soft_time_limit = 3300  # 55分钟
```

## 扩展功能

可以根据需要扩展以下功能：

1. **邮件通知**：检测到大量孤儿任务时发送通知
2. **Webhook集成**：与监控系统集成
3. **任务迁移**：将孤儿任务重新排队
4. **历史记录**：保留清理操作的历史记录

通过这套完整的任务一致性管理方案，可以有效避免和解决数据库与Redis任务不一致的问题。