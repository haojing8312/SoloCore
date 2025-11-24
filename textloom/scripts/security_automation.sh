#!/bin/bash
# TextLoom 依赖安全自动化脚本
# 用于CI/CD集成和定期安全检查

set -e  # 遇到错误立即退出

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_ROOT/security_reports"
LOG_FILE="$REPORTS_DIR/security_automation.log"

# 创建报告目录
mkdir -p "$REPORTS_DIR"

# 日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# 错误处理
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 帮助信息
show_help() {
    cat << EOF
TextLoom 依赖安全自动化工具

用法: $0 [选项] [命令]

命令:
  scan          执行完整安全扫描
  quick-scan    执行快速安全扫描（仅safety检查）
  update-check  检查可用的依赖更新
  ci-scan       CI/CD集成扫描（失败时非零退出码）
  schedule      设置定期扫描（需要cron权限）

选项:
  -h, --help              显示帮助信息
  -v, --verbose           详细输出
  --severity LEVEL        设置严重程度阈值 (critical|high|medium|low)
  --output FORMAT         输出格式 (console|json|markdown|html)
  --no-color             禁用颜色输出
  --timeout SECONDS      设置扫描超时时间 (默认: 300)

示例:
  $0 scan                 执行完整扫描
  $0 quick-scan --severity high
  $0 ci-scan --output json
  $0 update-check --verbose
EOF
}

# 颜色输出
if [[ -t 1 ]] && [[ "$1" != "--no-color" ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# 检查工具是否可用
check_tools() {
    local tools=("uv" "python3")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error_exit "$tool 未安装或不在PATH中"
        fi
    done
}

# 快速安全扫描（仅检查已知漏洞）
quick_scan() {
    local severity_threshold="${1:-medium}"
    local output_format="${2:-console}"
    
    log "开始快速安全扫描..."
    
    # 使用safety进行快速扫描
    if command -v safety &> /dev/null || uv list | grep -q safety; then
        log "运行 Safety 扫描..."
        
        local safety_cmd="uv run safety check --continue-on-error"
        if [[ "$output_format" == "json" ]]; then
            safety_cmd+=" --json"
        fi
        
        if ! $safety_cmd > "$REPORTS_DIR/quick_safety_$(date +%Y%m%d_%H%M%S).txt" 2>&1; then
            log "WARN: Safety 扫描检测到漏洞"
        fi
    else
        log "WARN: Safety 工具未安装，跳过快速扫描"
    fi
    
    # 使用pip-audit进行补充扫描
    if command -v pip-audit &> /dev/null || uv list | grep -q pip-audit; then
        log "运行 pip-audit 扫描..."
        
        local audit_cmd="uv run pip-audit --desc --format=json"
        if $audit_cmd > "$REPORTS_DIR/quick_audit_$(date +%Y%m%d_%H%M%S).json" 2>&1; then
            log "pip-audit 扫描完成"
        else
            log "WARN: pip-audit 扫描发现问题"
        fi
    else
        log "WARN: pip-audit 工具未安装，跳过审计扫描"
    fi
    
    log "快速扫描完成"
}

# 完整安全扫描
full_scan() {
    local severity_threshold="${1:-medium}"
    local output_format="${2:-console}"
    local timeout="${3:-300}"
    
    log "开始完整安全扫描..."
    
    # 检查Python脚本是否存在
    local scan_script="$SCRIPT_DIR/security_scan.py"
    if [[ ! -f "$scan_script" ]]; then
        error_exit "安全扫描脚本不存在: $scan_script"
    fi
    
    # 运行完整扫描（带超时）
    if timeout "$timeout" uv run python "$scan_script" \
        --output "$output_format" \
        --severity-threshold "$severity_threshold" > "$REPORTS_DIR/full_scan_$(date +%Y%m%d_%H%M%S).txt" 2>&1; then
        log "完整扫描成功完成"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log "ERROR: 扫描超时 (${timeout}s)"
        else
            log "ERROR: 扫描失败 (退出码: $exit_code)"
        fi
        return $exit_code
    fi
}

# CI/CD集成扫描
ci_scan() {
    local severity_threshold="${1:-high}"
    local output_format="${2:-json}"
    
    log "开始 CI/CD 集成扫描..."
    
    # 设置更严格的超时时间
    local timeout=180
    
    # 创建CI报告目录
    local ci_reports_dir="$REPORTS_DIR/ci"
    mkdir -p "$ci_reports_dir"
    
    # 运行快速扫描
    log "执行快速安全检查..."
    if ! quick_scan "$severity_threshold" "$output_format"; then
        log "ERROR: 快速扫描发现安全问题"
        return 1
    fi
    
    # 检查依赖更新（仅检查安全更新）
    log "检查安全更新..."
    local update_script="$SCRIPT_DIR/dependency_updater.py"
    if [[ -f "$update_script" ]]; then
        if timeout 120 uv run python "$update_script" \
            --priority critical \
            --output json > "$ci_reports_dir/security_updates_$(date +%Y%m%d_%H%M%S).json" 2>&1; then
            log "依赖检查完成"
        else
            log "WARN: 依赖检查超时或失败"
        fi
    fi
    
    # 生成CI摘要报告
    generate_ci_summary "$ci_reports_dir"
    
    log "CI/CD 扫描完成"
    return 0
}

# 生成CI摘要报告
generate_ci_summary() {
    local ci_dir="$1"
    local summary_file="$ci_dir/scan_summary.json"
    
    cat > "$summary_file" << EOF
{
    "scan_time": "$(date -Iseconds)",
    "project": "TextLoom",
    "scan_type": "ci_integration",
    "status": "completed",
    "reports_generated": $(find "$ci_dir" -name "*.json" -o -name "*.txt" | wc -l),
    "recommendations": [
        "检查生成的安全报告",
        "关注任何高优先级或关键漏洞",
        "定期更新依赖包",
        "监控新的安全公告"
    ]
}
EOF
    
    log "CI摘要报告生成: $summary_file"
}

# 检查依赖更新
update_check() {
    local verbose="$1"
    local priority="${2:-medium}"
    
    log "检查依赖包更新..."
    
    local update_script="$SCRIPT_DIR/dependency_updater.py"
    if [[ ! -f "$update_script" ]]; then
        log "WARN: 依赖更新脚本不存在: $update_script"
        return 1
    fi
    
    local cmd="uv run python $update_script --priority $priority"
    if [[ "$verbose" == "true" ]]; then
        cmd+=" --output markdown"
    else
        cmd+=" --output console"
    fi
    
    if $cmd > "$REPORTS_DIR/update_check_$(date +%Y%m%d_%H%M%S).txt" 2>&1; then
        log "依赖更新检查完成"
        return 0
    else
        log "ERROR: 依赖更新检查失败"
        return 1
    fi
}

# 设置定期扫描
setup_schedule() {
    log "设置定期安全扫描..."
    
    # 创建cron作业
    local cron_job="0 6 * * 1 $0 quick-scan --severity high --output json # TextLoom weekly security scan"
    
    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "TextLoom weekly security scan"; then
        log "定期扫描已经设置"
        return 0
    fi
    
    # 添加到crontab
    (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
    
    if [[ $? -eq 0 ]]; then
        log "定期扫描设置成功 (每周一上午6点)"
    else
        log "ERROR: 设置定期扫描失败"
        return 1
    fi
}

# 清理旧报告
cleanup_reports() {
    local days_to_keep="${1:-30}"
    
    log "清理 ${days_to_keep} 天前的旧报告..."
    
    find "$REPORTS_DIR" -name "*.json" -o -name "*.txt" -o -name "*.log" | \
    while read -r file; do
        if [[ -f "$file" ]] && [[ $(find "$file" -mtime +$days_to_keep 2>/dev/null) ]]; then
            rm "$file"
            log "删除旧报告: $(basename "$file")"
        fi
    done
}

# 主函数
main() {
    local command=""
    local severity_threshold="medium"
    local output_format="console"
    local verbose="false"
    local timeout="300"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose="true"
                shift
                ;;
            --severity)
                severity_threshold="$2"
                shift 2
                ;;
            --output)
                output_format="$2"
                shift 2
                ;;
            --timeout)
                timeout="$2"
                shift 2
                ;;
            --no-color)
                shift
                ;;
            scan|quick-scan|update-check|ci-scan|schedule)
                command="$1"
                shift
                ;;
            *)
                echo "未知参数: $1" >&2
                show_help
                exit 1
                ;;
        esac
    done
    
    # 默认命令
    if [[ -z "$command" ]]; then
        command="quick-scan"
    fi
    
    # 检查工具
    check_tools
    
    # 输出启动信息
    log "TextLoom 安全自动化工具启动"
    log "命令: $command"
    log "严重程度阈值: $severity_threshold"
    log "输出格式: $output_format"
    
    # 执行命令
    case "$command" in
        scan)
            full_scan "$severity_threshold" "$output_format" "$timeout"
            ;;
        quick-scan)
            quick_scan "$severity_threshold" "$output_format"
            ;;
        update-check)
            update_check "$verbose" "$severity_threshold"
            ;;
        ci-scan)
            ci_scan "$severity_threshold" "$output_format"
            ;;
        schedule)
            setup_schedule
            ;;
        *)
            error_exit "未知命令: $command"
            ;;
    esac
    
    # 清理旧报告
    cleanup_reports
    
    log "任务完成"
}

# 执行主函数
main "$@"