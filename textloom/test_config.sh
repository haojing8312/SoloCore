#!/bin/bash
# 配置一致性快速测试脚本
# 用于在提交前验证配置字段映射正确性

echo "🧪 运行配置一致性测试..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 运行单元测试
echo ""
echo "📋 1. 配置字段映射测试"
uv run pytest tests/unit/test_config_consistency.py -v --tb=short

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 配置字段映射测试失败！"
    echo "这通常表示 web_configs.py 与 config.py 之间存在字段名不匹配"
    echo "请检查错误信息并修复字段映射"
    exit 1
fi

# 运行集成测试
echo ""
echo "📋 2. 存储服务集成测试"
uv run pytest tests/integration/test_file_upload_integration.py -v --tb=short

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 存储服务集成测试失败！"
    echo "请检查错误信息"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 所有配置测试通过！"
echo ""
echo "💡 提示："
echo "  - 配置字段映射正确"
echo "  - 所有存储类可以安全初始化"
echo "  - 文件上传功能配置完整"
echo ""
