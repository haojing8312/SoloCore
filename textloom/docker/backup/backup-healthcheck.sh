#!/bin/bash
"""
TextLoom 备份服务健康检查脚本
===========================

检查备份服务各个组件的健康状态
"""

set -euo pipefail

# 配置
HEALTH_CHECK_TIMEOUT=10
LOG_FILE="/app/logs/healthcheck.log"

# 日志函数
log_health() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [HEALTH] $*" | tee -a "$LOG_FILE" 2>/dev/null || true
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$LOG_FILE" 2>/dev/null || true
}

# 检查Python进程
check_python_services() {
    local service_name="$1"
    local process_pattern="$2"
    
    if pgrep -f "$process_pattern" > /dev/null; then
        log_health "$service_name 服务运行正常"
        return 0
    else
        log_error "$service_name 服务未运行"
        return 1
    fi
}

# 检查HTTP服务
check_http_service() {
    local service_name="$1"
    local url="$2"
    
    if timeout "$HEALTH_CHECK_TIMEOUT" curl -s -f "$url" > /dev/null 2>&1; then
        log_health "$service_name HTTP服务响应正常"
        return 0
    else
        log_error "$service_name HTTP服务无响应"
        return 1
    fi
}

# 检查文件系统
check_filesystem() {
    local path="$1"
    local min_free_gb="${2:-1}"
    
    if [[ ! -d "$path" ]]; then
        log_error "目录不存在: $path"
        return 1
    fi
    
    local free_space_kb
    free_space_kb=$(df "$path" | awk 'NR==2 {print $4}')
    local free_space_gb=$((free_space_kb / 1024 / 1024))
    
    if [[ $free_space_gb -lt $min_free_gb ]]; then
        log_error "磁盘空间不足: $path (${free_space_gb}GB 可用, 需要至少 ${min_free_gb}GB)"
        return 1
    else
        log_health "磁盘空间充足: $path (${free_space_gb}GB 可用)"
        return 0
    fi
}

# 检查网络连接
check_network_connectivity() {
    local host="$1"
    local port="$2"
    local service_name="$3"
    
    if timeout 5 nc -z "$host" "$port" 2>/dev/null; then
        log_health "$service_name 网络连接正常 ($host:$port)"
        return 0
    else
        log_error "$service_name 网络连接失败 ($host:$port)"
        return 1
    fi
}

# 检查备份文件
check_backup_files() {
    local backup_dir="/backups/local"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "备份目录不存在: $backup_dir"
        return 1
    fi
    
    local backup_count
    backup_count=$(find "$backup_dir" -name "*.tar.gz" -mtime -7 | wc -l)
    
    if [[ $backup_count -eq 0 ]]; then
        log_error "最近7天内没有备份文件"
        return 1
    else
        log_health "发现 $backup_count 个最近的备份文件"
        return 0
    fi
}

# 检查系统资源
check_system_resources() {
    # 检查内存使用率
    local memory_usage
    memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    
    if [[ $memory_usage -gt 90 ]]; then
        log_error "内存使用率过高: ${memory_usage}%"
        return 1
    else
        log_health "内存使用率正常: ${memory_usage}%"
    fi
    
    # 检查CPU负载
    local load_avg
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    
    if (( $(echo "$load_avg > 5.0" | bc -l 2>/dev/null || echo 0) )); then
        log_error "CPU负载过高: $load_avg"
        return 1
    else
        log_health "CPU负载正常: $load_avg"
    fi
    
    return 0
}

# 主健康检查
main_health_check() {
    local exit_code=0
    
    log_health "开始备份服务健康检查"
    
    # 检查备份监控服务
    if ! check_python_services "备份监控" "backup_monitor.py"; then
        exit_code=1
    fi
    
    # 检查HTTP监控仪表板
    if ! check_http_service "监控仪表板" "http://localhost:8080/api/status"; then
        exit_code=1
    fi
    
    # 检查Supervisor进程管理
    if ! pgrep -f "supervisord" > /dev/null; then
        log_error "Supervisor进程管理器未运行"
        exit_code=1
    else
        log_health "Supervisor进程管理器运行正常"
    fi
    
    # 检查Cron服务
    if ! pgrep -f "crond" > /dev/null; then
        log_error "Cron调度服务未运行"
        exit_code=1
    else
        log_health "Cron调度服务运行正常"
    fi
    
    # 检查文件系统
    if ! check_filesystem "/backups/local" 2; then
        exit_code=1
    fi
    
    if ! check_filesystem "/app/logs" 1; then
        exit_code=1
    fi
    
    # 检查备份文件存在性
    if ! check_backup_files; then
        # 如果没有备份文件，不算致命错误，只是警告
        log_health "备份文件检查完成（警告级别）"
    fi
    
    # 检查系统资源
    if ! check_system_resources; then
        exit_code=1
    fi
    
    # 检查外部服务连接
    if [[ -n "${DATABASE_URL:-}" ]]; then
        # 从DATABASE_URL提取主机和端口
        local db_host db_port
        db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [[ -n "$db_host" && -n "$db_port" ]]; then
            if ! check_network_connectivity "$db_host" "$db_port" "数据库"; then
                exit_code=1
            fi
        fi
    fi
    
    if [[ -n "${REDIS_HOST:-}" ]]; then
        local redis_port="${REDIS_PORT:-6379}"
        if ! check_network_connectivity "$REDIS_HOST" "$redis_port" "Redis"; then
            exit_code=1
        fi
    fi
    
    # 检查MinIO连接（如果配置了）
    if [[ "${BACKUP_REMOTE_STORAGE_ENABLED:-false}" == "true" && -n "${MINIO_ENDPOINT:-}" ]]; then
        local minio_host minio_port
        minio_host=$(echo "$MINIO_ENDPOINT" | cut -d: -f1)
        minio_port=$(echo "$MINIO_ENDPOINT" | cut -d: -f2)
        
        if [[ -n "$minio_host" && -n "$minio_port" ]]; then
            if ! check_network_connectivity "$minio_host" "$minio_port" "MinIO"; then
                # MinIO连接失败不算致命错误，因为可能只使用本地备份
                log_health "MinIO连接失败，但继续使用本地备份"
            fi
        fi
    fi
    
    # 综合健康状态
    if [[ $exit_code -eq 0 ]]; then
        log_health "备份服务健康检查通过"
        echo "健康"
    else
        log_error "备份服务健康检查失败"
        echo "不健康"
    fi
    
    return $exit_code
}

# 简化版健康检查（用于Docker HEALTHCHECK）
simple_health_check() {
    # 只检查最关键的服务
    if pgrep -f "supervisord" > /dev/null && \
       curl -s -f "http://localhost:8080/api/status" > /dev/null 2>&1 && \
       [[ -d "/backups/local" ]] && \
       [[ -d "/app/logs" ]]; then
        echo "健康"
        return 0
    else
        echo "不健康"
        return 1
    fi
}

# 主执行逻辑
case "${1:-simple}" in
    "full")
        main_health_check
        ;;
    "simple"|*)
        simple_health_check
        ;;
esac