#!/bin/bash
"""
TextLoom 备份服务容器启动脚本
===========================

负责初始化备份服务容器环境并启动相应服务
"""

set -euo pipefail

# 环境变量
BACKUP_USER="${BACKUP_USER:-backup}"
LOG_DIR="/app/logs"
BACKUP_DIR="/backups/local"
CONFIG_DIR="/backups/config"

# 日志函数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

# 初始化环境
init_environment() {
    log_info "初始化备份服务环境"
    
    # 确保目录存在和权限正确
    sudo mkdir -p "$LOG_DIR" "$BACKUP_DIR" "$CONFIG_DIR" /app/backup_monitor_data
    sudo chown -R "$BACKUP_USER:$BACKUP_USER" "$LOG_DIR" "$BACKUP_DIR" "$CONFIG_DIR" /app/backup_monitor_data
    
    # 设置备份配置
    if [[ ! -f "$CONFIG_DIR/backup.conf" ]]; then
        cat > "$CONFIG_DIR/backup.conf" << EOF
# TextLoom 备份服务配置
BACKUP_VERSION=1.0.0
BACKUP_INIT_TIME=$(date -Iseconds)
CONTAINER_ID=$(hostname)
EOF
    fi
    
    # 初始化日志文件
    touch "$LOG_DIR/backup_manager.log"
    touch "$LOG_DIR/backup_monitor.log"
    touch "$LOG_DIR/backup_scheduler.log"
    touch "$LOG_DIR/disaster_recovery.log"
    
    log_info "环境初始化完成"
}

# 等待依赖服务
wait_for_services() {
    log_info "等待依赖服务启动"
    
    # 等待数据库服务
    if [[ -n "${DATABASE_URL:-}" ]]; then
        local host port
        # 从DATABASE_URL提取主机和端口
        host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [[ -n "$host" && -n "$port" ]]; then
            log_info "等待数据库服务: $host:$port"
            while ! nc -z "$host" "$port"; do
                log_info "等待数据库连接..."
                sleep 2
            done
            log_info "数据库服务已就绪"
        fi
    fi
    
    # 等待Redis服务
    if [[ -n "${REDIS_HOST:-}" ]]; then
        local redis_port="${REDIS_PORT:-6379}"
        log_info "等待Redis服务: $REDIS_HOST:$redis_port"
        while ! nc -z "$REDIS_HOST" "$redis_port"; do
            log_info "等待Redis连接..."
            sleep 2
        done
        log_info "Redis服务已就绪"
    fi
    
    log_info "所有依赖服务已就绪"
}

# 初始化备份数据
init_backup_data() {
    log_info "初始化备份数据"
    
    # 创建备份元数据文件
    if [[ ! -f "$BACKUP_DIR/backup_metadata.json" ]]; then
        cat > "$BACKUP_DIR/backup_metadata.json" << EOF
{
    "backup_service_version": "1.0.0",
    "initialized_at": "$(date -Iseconds)",
    "container_info": {
        "hostname": "$(hostname)",
        "user": "$BACKUP_USER"
    },
    "backup_stats": {
        "total_backups": 0,
        "last_backup": null,
        "total_size": 0
    }
}
EOF
    fi
    
    # 创建备份加密密钥（如果不存在）
    if [[ "${BACKUP_ENCRYPTION_ENABLED:-true}" == "true" && ! -f "$CONFIG_DIR/backup.key" ]]; then
        log_info "生成备份加密密钥"
        python3 -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key()
with open('$CONFIG_DIR/backup.key', 'wb') as f:
    f.write(key)
"
        chmod 600 "$CONFIG_DIR/backup.key"
        log_info "备份加密密钥已生成"
    fi
    
    log_info "备份数据初始化完成"
}

# 启动Cron服务
start_cron() {
    log_info "启动Cron调度服务"
    
    # 启动crond
    sudo crond -l 8 -f &
    
    log_info "Cron调度服务已启动"
}

# 启动备份监控
start_monitor() {
    log_info "启动备份监控服务"
    
    cd /app
    python3 scripts/backup_monitor.py start &
    
    log_info "备份监控服务已启动"
}

# 启动备份仪表板
start_dashboard() {
    log_info "启动备份监控仪表板"
    
    cd /app
    python3 scripts/backup_monitor.py dashboard --host 0.0.0.0 --port 8080 &
    
    log_info "备份监控仪表板已启动"
}

# 启动Supervisor
start_supervisor() {
    log_info "启动Supervisor进程管理"
    
    exec supervisord -n -c /etc/supervisor/conf.d/backup.conf
}

# 运行指定的备份任务
run_backup() {
    local backup_type="${1:-daily}"
    
    log_info "运行备份任务: $backup_type"
    
    cd /app
    python3 scripts/backup_manager.py backup --type "$backup_type"
}

# 运行灾难恢复评估
run_disaster_assessment() {
    log_info "运行灾难恢复评估"
    
    cd /app
    python3 scripts/disaster_recovery.py assess
}

# 主函数
main() {
    local command="${1:-supervisor}"
    
    # 公共初始化
    init_environment
    wait_for_services
    init_backup_data
    
    case "$command" in
        "supervisor")
            start_supervisor
            ;;
            
        "monitor")
            start_monitor
            # 保持容器运行
            while true; do sleep 60; done
            ;;
            
        "dashboard")
            start_dashboard
            # 保持容器运行
            while true; do sleep 60; done
            ;;
            
        "cron")
            start_cron
            # 保持容器运行
            while true; do sleep 60; done
            ;;
            
        "backup")
            run_backup "${2:-daily}"
            ;;
            
        "assess")
            run_disaster_assessment
            ;;
            
        "shell")
            log_info "启动交互式Shell"
            exec /bin/bash
            ;;
            
        *)
            log_error "未知命令: $command"
            echo "支持的命令:"
            echo "  supervisor  - 启动Supervisor进程管理 (默认)"
            echo "  monitor     - 启动备份监控服务"
            echo "  dashboard   - 启动监控仪表板"
            echo "  cron        - 启动Cron调度服务"
            echo "  backup      - 运行备份任务"
            echo "  assess      - 运行灾难评估"
            echo "  shell       - 启动交互式Shell"
            exit 1
            ;;
    esac
}

# 信号处理
trap 'log_info "收到停止信号，正在关闭服务..."; exit 0' TERM INT

# 执行主函数
main "$@"