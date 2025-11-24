#!/bin/bash
"""
TextLoom 自动化备份调度脚本
========================

提供Cron和systemd定时器集成的自动化备份调度：
- 每日、每周、每月备份调度
- 备份前预检查
- 备份后验证
- 失败重试机制
- 日志记录和监控
- 资源使用优化

Usage:
    bash backup_scheduler.sh install    # 安装调度任务
    bash backup_scheduler.sh uninstall  # 卸载调度任务
    bash backup_scheduler.sh run daily  # 手动运行日备份
    bash backup_scheduler.sh status     # 查看调度状态
"""

set -euo pipefail

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
BACKUP_LOG="$LOG_DIR/backup_scheduler.log"
ERROR_LOG="$LOG_DIR/backup_scheduler.error.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 环境配置
PYTHON_CMD="${PYTHON_CMD:-python3}"
VENV_PATH="${VENV_PATH:-$PROJECT_DIR/.venv}"
USER_NAME="${BACKUP_USER:-$(whoami)}"

# 备份配置
BACKUP_SCRIPT="$SCRIPT_DIR/backup_manager.py"
MONITOR_SCRIPT="$SCRIPT_DIR/backup_monitor.py"
DISASTER_SCRIPT="$SCRIPT_DIR/disaster_recovery.py"

# Cron配置
CRON_FILE="/tmp/textloom_backup_cron"
SYSTEMD_PATH="/etc/systemd/system"

# 日志函数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$BACKUP_LOG"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$ERROR_LOG" >&2
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" | tee -a "$BACKUP_LOG"
}

# 检查环境
check_environment() {
    log_info "检查环境..."
    
    # 检查Python环境
    if [[ -d "$VENV_PATH" ]]; then
        source "$VENV_PATH/bin/activate"
        log_info "使用虚拟环境: $VENV_PATH"
    elif command -v uv &> /dev/null; then
        log_info "使用uv运行环境"
        PYTHON_CMD="uv run python"
    else
        log_info "使用系统Python: $PYTHON_CMD"
    fi
    
    # 检查备份脚本
    if [[ ! -f "$BACKUP_SCRIPT" ]]; then
        log_error "备份脚本不存在: $BACKUP_SCRIPT"
        exit 1
    fi
    
    # 检查权限
    if [[ ! -w "$LOG_DIR" ]]; then
        log_error "日志目录无写权限: $LOG_DIR"
        exit 1
    fi
    
    log_info "环境检查完成"
}

# 预备份检查
pre_backup_check() {
    local backup_type="$1"
    log_info "执行预备份检查: $backup_type"
    
    # 检查磁盘空间
    local available_space
    available_space=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    local min_space=5242880  # 5GB in KB
    
    if (( available_space < min_space )); then
        log_error "磁盘空间不足: ${available_space}KB 可用, 需要至少 ${min_space}KB"
        return 1
    fi
    
    # 检查系统负载
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local max_load=5.0
    
    if (( $(echo "$load_avg > $max_load" | bc -l) )); then
        log_warn "系统负载较高: $load_avg, 可能影响备份性能"
    fi
    
    # 检查关键服务状态
    if ! $PYTHON_CMD "$DISASTER_SCRIPT" assess > /dev/null 2>&1; then
        log_warn "系统状态检查发现问题，但继续执行备份"
    fi
    
    log_info "预备份检查完成"
    return 0
}

# 执行备份
run_backup() {
    local backup_type="$1"
    local start_time=$(date +%s)
    
    log_info "开始执行 $backup_type 备份"
    
    # 预备份检查
    if ! pre_backup_check "$backup_type"; then
        log_error "预备份检查失败，取消备份"
        return 1
    fi
    
    # 执行备份
    local backup_output
    local backup_result=0
    
    if backup_output=$($PYTHON_CMD "$BACKUP_SCRIPT" backup --type "$backup_type" 2>&1); then
        log_info "备份执行成功"
        log_info "备份输出: $backup_output"
    else
        backup_result=$?
        log_error "备份执行失败 (退出码: $backup_result)"
        log_error "错误输出: $backup_output"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "$backup_type 备份完成，耗时: ${duration}秒"
    
    # 后备份验证
    if [[ $backup_result -eq 0 ]]; then
        post_backup_verify "$backup_output"
    fi
    
    return $backup_result
}

# 后备份验证
post_backup_verify() {
    local backup_output="$1"
    log_info "执行后备份验证"
    
    # 从输出中提取备份ID
    local backup_id
    if backup_id=$(echo "$backup_output" | grep -oP '备份创建成功: \K\w+' | tail -1); then
        log_info "验证备份: $backup_id"
        
        if $PYTHON_CMD "$BACKUP_SCRIPT" verify --backup-id "$backup_id"; then
            log_info "备份验证成功: $backup_id"
        else
            log_error "备份验证失败: $backup_id"
        fi
    else
        log_warn "无法从输出中提取备份ID，跳过验证"
    fi
}

# 失败重试
retry_backup() {
    local backup_type="$1"
    local max_retries="${BACKUP_MAX_RETRIES:-3}"
    local retry_delay="${BACKUP_RETRY_DELAY:-300}"  # 5分钟
    
    for ((i=1; i<=max_retries; i++)); do
        log_info "第 $i 次尝试备份: $backup_type"
        
        if run_backup "$backup_type"; then
            log_info "备份成功"
            return 0
        else
            log_error "第 $i 次备份尝试失败"
            
            if [[ $i -lt $max_retries ]]; then
                log_info "等待 ${retry_delay} 秒后重试..."
                sleep "$retry_delay"
            fi
        fi
    done
    
    log_error "备份失败，已达到最大重试次数: $max_retries"
    
    # 发送告警
    send_failure_alert "$backup_type" "$max_retries"
    
    return 1
}

# 发送失败告警
send_failure_alert() {
    local backup_type="$1"
    local attempts="$2"
    
    log_error "备份彻底失败，发送告警通知"
    
    # 通过监控系统发送告警
    if [[ -f "$MONITOR_SCRIPT" ]]; then
        $PYTHON_CMD "$MONITOR_SCRIPT" alert --test || true
    fi
    
    # 记录到系统日志
    logger -p user.err "TextLoom备份失败: $backup_type 备份在 $attempts 次尝试后失败"
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理旧备份文件"
    
    # 备份目录
    local backup_dir="$PROJECT_DIR/backups"
    
    if [[ -d "$backup_dir" ]]; then
        # 删除超过保留期的本地备份
        find "$backup_dir" -name "*.tar.gz" -type f -mtime +30 -delete || true
        find "$backup_dir" -name "*.json" -type f -mtime +30 -delete || true
        
        log_info "本地旧备份清理完成"
    fi
    
    # 清理日志文件（保留30天）
    find "$LOG_DIR" -name "backup_*.log*" -type f -mtime +30 -delete || true
}

# 安装Cron调度任务
install_cron_jobs() {
    log_info "安装Cron调度任务"
    
    # 生成cron配置
    cat > "$CRON_FILE" << EOF
# TextLoom 备份调度任务
# 环境变量
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
SHELL=/bin/bash

# 每日备份 (凌晨2点)
0 2 * * * $USER_NAME cd "$PROJECT_DIR" && bash "$0" run daily >> "$BACKUP_LOG" 2>> "$ERROR_LOG"

# 每周备份 (周日凌晨3点)
0 3 * * 0 $USER_NAME cd "$PROJECT_DIR" && bash "$0" run weekly >> "$BACKUP_LOG" 2>> "$ERROR_LOG"

# 每月备份 (每月1号凌晨4点)
0 4 1 * * $USER_NAME cd "$PROJECT_DIR" && bash "$0" run monthly >> "$BACKUP_LOG" 2>> "$ERROR_LOG"

# 清理旧备份 (每天凌晨5点)
0 5 * * * $USER_NAME cd "$PROJECT_DIR" && bash "$0" cleanup >> "$BACKUP_LOG" 2>> "$ERROR_LOG"

# 监控系统检查 (每5分钟)
*/5 * * * * $USER_NAME cd "$PROJECT_DIR" && timeout 60 $PYTHON_CMD "$MONITOR_SCRIPT" status > /dev/null 2>&1 || true
EOF

    # 安装cron任务
    if crontab "$CRON_FILE"; then
        log_info "Cron调度任务安装成功"
    else
        log_error "Cron调度任务安装失败"
        return 1
    fi
    
    # 清理临时文件
    rm -f "$CRON_FILE"
}

# 创建systemd定时器
create_systemd_timers() {
    log_info "创建systemd定时器"
    
    # 检查权限
    if [[ $EUID -ne 0 ]]; then
        log_error "创建systemd定时器需要root权限"
        return 1
    fi
    
    # 创建服务文件
    cat > "$SYSTEMD_PATH/textloom-backup@.service" << EOF
[Unit]
Description=TextLoom Backup Service (%i)
After=network.target

[Service]
Type=oneshot
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/bin/bash $0 run %i
StandardOutput=append:$BACKUP_LOG
StandardError=append:$ERROR_LOG

[Install]
WantedBy=multi-user.target
EOF

    # 创建定时器文件 - 日备份
    cat > "$SYSTEMD_PATH/textloom-backup-daily.timer" << EOF
[Unit]
Description=TextLoom Daily Backup Timer
Requires=textloom-backup@daily.service

[Timer]
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 创建定时器文件 - 周备份
    cat > "$SYSTEMD_PATH/textloom-backup-weekly.timer" << EOF
[Unit]
Description=TextLoom Weekly Backup Timer
Requires=textloom-backup@weekly.service

[Timer]
OnCalendar=Sun 03:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 创建定时器文件 - 月备份
    cat > "$SYSTEMD_PATH/textloom-backup-monthly.timer" << EOF
[Unit]
Description=TextLoom Monthly Backup Timer
Requires=textloom-backup@monthly.service

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 创建清理定时器
    cat > "$SYSTEMD_PATH/textloom-backup-cleanup.service" << EOF
[Unit]
Description=TextLoom Backup Cleanup Service
After=network.target

[Service]
Type=oneshot
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=/bin/bash $0 cleanup
StandardOutput=append:$BACKUP_LOG
StandardError=append:$ERROR_LOG
EOF

    cat > "$SYSTEMD_PATH/textloom-backup-cleanup.timer" << EOF
[Unit]
Description=TextLoom Backup Cleanup Timer
Requires=textloom-backup-cleanup.service

[Timer]
OnCalendar=05:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd配置
    systemctl daemon-reload
    
    # 启用定时器
    systemctl enable textloom-backup-daily.timer
    systemctl enable textloom-backup-weekly.timer
    systemctl enable textloom-backup-monthly.timer
    systemctl enable textloom-backup-cleanup.timer
    
    # 启动定时器
    systemctl start textloom-backup-daily.timer
    systemctl start textloom-backup-weekly.timer
    systemctl start textloom-backup-monthly.timer
    systemctl start textloom-backup-cleanup.timer
    
    log_info "systemd定时器创建完成"
}

# 卸载调度任务
uninstall_schedule() {
    log_info "卸载调度任务"
    
    # 卸载cron任务
    if crontab -l 2>/dev/null | grep -v "TextLoom 备份调度任务" | grep -v "$0" | crontab -; then
        log_info "Cron任务卸载成功"
    else
        log_warn "Cron任务卸载可能失败"
    fi
    
    # 卸载systemd定时器（需要root权限）
    if [[ $EUID -eq 0 ]]; then
        systemctl stop textloom-backup-*.timer 2>/dev/null || true
        systemctl disable textloom-backup-*.timer 2>/dev/null || true
        
        rm -f "$SYSTEMD_PATH"/textloom-backup*.service
        rm -f "$SYSTEMD_PATH"/textloom-backup*.timer
        
        systemctl daemon-reload
        
        log_info "systemd定时器卸载成功"
    else
        log_warn "需要root权限才能卸载systemd定时器"
    fi
}

# 查看调度状态
show_schedule_status() {
    log_info "调度任务状态:"
    
    echo "=== Cron任务 ==="
    if crontab -l 2>/dev/null | grep -q "$0"; then
        echo "已安装Cron调度任务:"
        crontab -l 2>/dev/null | grep "$0" | sed 's/^/  /'
    else
        echo "未安装Cron调度任务"
    fi
    
    echo ""
    echo "=== systemd定时器 ==="
    if command -v systemctl &> /dev/null; then
        systemctl list-timers textloom-backup-* --no-pager 2>/dev/null || echo "未找到systemd定时器"
    else
        echo "systemd不可用"
    fi
    
    echo ""
    echo "=== 最近备份记录 ==="
    if [[ -f "$BACKUP_LOG" ]]; then
        tail -20 "$BACKUP_LOG" | grep -E "(备份|清理)" || echo "没有最近的备份记录"
    else
        echo "备份日志文件不存在"
    fi
}

# 主函数
main() {
    local command="${1:-help}"
    
    case "$command" in
        "install")
            check_environment
            log_info "安装备份调度任务"
            
            # 优先使用systemd，fallback到cron
            if command -v systemctl &> /dev/null && [[ $EUID -eq 0 ]]; then
                create_systemd_timers
            else
                install_cron_jobs
                if [[ $EUID -ne 0 ]]; then
                    log_warn "非root用户，仅安装Cron任务。建议使用sudo运行以安装systemd定时器"
                fi
            fi
            
            log_info "调度任务安装完成"
            ;;
            
        "uninstall")
            log_info "卸载备份调度任务"
            uninstall_schedule
            log_info "调度任务卸载完成"
            ;;
            
        "run")
            local backup_type="${2:-daily}"
            check_environment
            
            if [[ "$backup_type" =~ ^(daily|weekly|monthly)$ ]]; then
                retry_backup "$backup_type"
            else
                log_error "无效的备份类型: $backup_type"
                echo "支持的备份类型: daily, weekly, monthly"
                exit 1
            fi
            ;;
            
        "cleanup")
            check_environment
            cleanup_old_backups
            ;;
            
        "status")
            show_schedule_status
            ;;
            
        "help"|*)
            echo "TextLoom 备份调度器"
            echo ""
            echo "用法: $0 <命令> [参数]"
            echo ""
            echo "命令:"
            echo "  install           安装调度任务"
            echo "  uninstall         卸载调度任务"
            echo "  run <type>        运行指定类型的备份 (daily/weekly/monthly)"
            echo "  cleanup           清理旧备份文件"
            echo "  status            查看调度状态"
            echo "  help              显示此帮助信息"
            echo ""
            echo "环境变量:"
            echo "  BACKUP_USER                   备份运行用户 (默认: 当前用户)"
            echo "  BACKUP_MAX_RETRIES           最大重试次数 (默认: 3)"
            echo "  BACKUP_RETRY_DELAY           重试间隔秒数 (默认: 300)"
            echo "  PYTHON_CMD                    Python命令 (默认: python3)"
            echo "  VENV_PATH                     虚拟环境路径 (默认: PROJECT/.venv)"
            echo ""
            echo "示例:"
            echo "  $0 install                    # 安装调度任务"
            echo "  $0 run daily                  # 手动运行日备份"
            echo "  $0 status                     # 查看状态"
            ;;
    esac
}

# 执行主函数
main "$@"