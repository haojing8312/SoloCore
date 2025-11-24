#!/bin/bash

# TextLoom 类型检查脚本
# 用于CI/CD流水线和开发环境的类型安全检查

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查uv是否可用
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv 未安装或不在PATH中"
        print_error "请参考 https://docs.astral.sh/uv/ 安装uv"
        exit 1
    fi
}

# 安装类型检查依赖
install_dependencies() {
    print_status "安装类型检查依赖..."
    
    # 确保mypy和类型存根已安装
    uv add --dev mypy types-redis types-requests types-setuptools types-PyYAML
    
    # 安装额外的类型存根
    if ! uv run python -c "import types_setuptools" 2>/dev/null; then
        print_status "安装额外的类型存根..."
        uv add --dev types-setuptools types-cffi types-pyopenssl
    fi
    
    print_success "依赖安装完成"
}

# 运行类型覆盖率分析
analyze_coverage() {
    print_status "分析类型注解覆盖率..."
    
    # 运行覆盖率分析
    uv run python scripts/type_checker.py --coverage --suggest
    
    # 保存覆盖率报告
    uv run python scripts/type_checker.py --coverage --json > type_coverage_report.json
    print_success "覆盖率分析完成，报告已保存到 type_coverage_report.json"
}

# 运行渐进式mypy检查
run_progressive_mypy() {
    print_status "运行渐进式类型检查..."
    
    # 1. 检查核心模型（严格模式）
    print_status "检查核心模型 (严格模式)..."
    if uv run mypy models/ --strict --show-error-codes 2>/dev/null; then
        print_success "✅ 模型类型检查通过"
    else
        print_warning "⚠️  模型类型检查有警告，继续执行..."
        uv run mypy models/ --strict --show-error-codes || true
    fi
    
    # 2. 检查数据库层
    print_status "检查数据库层..."
    if uv run mypy models/database.py models/db_*.py --show-error-codes 2>/dev/null; then
        print_success "✅ 数据库层类型检查通过"
    else
        print_warning "⚠️  数据库层类型检查有警告"
        uv run mypy models/database.py models/db_*.py --show-error-codes || true
    fi
    
    # 3. 检查同步服务
    print_status "检查同步服务..."
    if uv run mypy services/sync_*.py --show-error-codes 2>/dev/null; then
        print_success "✅ 同步服务类型检查通过"
    else
        print_warning "⚠️  同步服务类型检查有警告"
        uv run mypy services/sync_*.py --show-error-codes || true
    fi
    
    # 4. 检查工具函数
    print_status "检查工具函数..."
    if uv run mypy utils/ --show-error-codes 2>/dev/null; then
        print_success "✅ 工具函数类型检查通过"
    else
        print_warning "⚠️  工具函数类型检查有警告"
        uv run mypy utils/ --show-error-codes || true
    fi
    
    # 5. 检查路由（宽松模式）
    print_status "检查API路由 (宽松模式)..."
    if uv run mypy routers/ --ignore-missing-imports --show-error-codes 2>/dev/null; then
        print_success "✅ API路由类型检查通过"
    else
        print_warning "⚠️  API路由类型检查有警告"
        uv run mypy routers/ --ignore-missing-imports --show-error-codes || true
    fi
}

# 运行完整的mypy检查
run_full_mypy() {
    print_status "运行完整的mypy类型检查..."
    
    # 使用配置文件进行检查
    if uv run mypy . --config-file=pyproject.toml 2>/dev/null; then
        print_success "✅ 完整类型检查通过"
        return 0
    else
        print_warning "⚠️  发现类型问题，详细信息："
        uv run mypy . --config-file=pyproject.toml || true
        return 1
    fi
}

# 生成类型检查报告
generate_report() {
    print_status "生成类型检查报告..."
    
    REPORT_FILE="type_check_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$REPORT_FILE" << EOF
# TextLoom 类型检查报告

生成时间: $(date '+%Y-%m-%d %H:%M:%S')

## 类型注解覆盖率

\`\`\`
$(uv run python scripts/type_checker.py --coverage)
\`\`\`

## MyPy 检查结果

### 核心模块检查
\`\`\`
$(uv run mypy models/ --strict --show-error-codes 2>&1 || echo "有类型错误")
\`\`\`

### 服务层检查
\`\`\`
$(uv run mypy services/sync_*.py --show-error-codes 2>&1 || echo "有类型错误")
\`\`\`

### 工具函数检查
\`\`\`
$(uv run mypy utils/ --show-error-codes 2>&1 || echo "有类型错误")
\`\`\`

## 改进建议

$(uv run python scripts/type_checker.py --suggest | tail -n +$(uv run python scripts/type_checker.py --suggest | grep -n "改进建议" | cut -d: -f1))

EOF

    print_success "报告已生成: $REPORT_FILE"
}

# 修复常见的类型问题
auto_fix_types() {
    print_status "自动修复常见类型问题..."
    
    # 创建修复脚本
    cat > temp_fix_types.py << 'EOF'
import os
import re
from pathlib import Path

def fix_missing_return_types():
    """修复缺失的返回类型注解"""
    patterns = [
        # FastAPI路由函数
        (r'(@router\.(get|post|put|delete|patch)\([^)]*\)\s*\n\s*)async def (\w+)\([^)]*\):', 
         r'\1async def \3(\4) -> dict:'),
        
        # 简单的getter函数
        (r'def get_(\w+)\(self\):', r'def get_\1(self) -> Any:'),
        
        # 布尔返回函数
        (r'def (is_|has_|can_|should_)(\w+)\([^)]*\):', r'def \1\2(\3) -> bool:'),
    ]
    
    for root, dirs, files in os.walk('.'):
        # 跳过不需要处理的目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', '.venv']]
        
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified = False
                for pattern, replacement in patterns:
                    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        modified = True
                
                if modified:
                    print(f"修复了文件: {file_path}")
                    # 注释掉实际写入，避免意外修改
                    # with open(file_path, 'w', encoding='utf-8') as f:
                    #     f.write(content)
                    
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {e}")

if __name__ == "__main__":
    print("这是一个示例修复脚本，实际使用时请仔细检查")
    fix_missing_return_types()
EOF

    print_warning "自动修复功能已准备，但需要手动启用以确保安全"
    print_warning "请检查 temp_fix_types.py 脚本后手动运行"
}

# 主函数
main() {
    print_status "开始TextLoom类型检查流程..."
    
    # 解析命令行参数
    COVERAGE_ONLY=false
    FULL_CHECK=false
    PROGRESSIVE=true
    GENERATE_REPORT=false
    AUTO_FIX=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --coverage-only)
                COVERAGE_ONLY=true
                shift
                ;;
            --full)
                FULL_CHECK=true
                PROGRESSIVE=false
                shift
                ;;
            --progressive)
                PROGRESSIVE=true
                shift
                ;;
            --report)
                GENERATE_REPORT=true
                shift
                ;;
            --auto-fix)
                AUTO_FIX=true
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --coverage-only    仅运行覆盖率分析"
                echo "  --full            运行完整的mypy检查"
                echo "  --progressive     运行渐进式检查（默认）"
                echo "  --report          生成详细报告"
                echo "  --auto-fix        准备自动修复脚本"
                echo "  --help            显示帮助信息"
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 基础检查
    check_uv
    install_dependencies
    
    # 执行类型检查
    if [[ "$COVERAGE_ONLY" == true ]]; then
        analyze_coverage
    elif [[ "$FULL_CHECK" == true ]]; then
        analyze_coverage
        run_full_mypy
    elif [[ "$PROGRESSIVE" == true ]]; then
        analyze_coverage
        run_progressive_mypy
    fi
    
    # 生成报告
    if [[ "$GENERATE_REPORT" == true ]]; then
        generate_report
    fi
    
    # 自动修复
    if [[ "$AUTO_FIX" == true ]]; then
        auto_fix_types
    fi
    
    print_success "类型检查流程完成！"
    
    # 清理临时文件
    [ -f temp_fix_types.py ] && rm -f temp_fix_types.py
}

# 如果直接运行此脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi