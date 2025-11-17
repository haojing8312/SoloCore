#!/bin/bash
###############################################################################
# Editly 视频引擎快速部署脚本
#
# 用法:
#   chmod +x scripts/setup_editly.sh
#   ./scripts/setup_editly.sh
#
# 功能:
#   - 检查系统依赖 (Node.js, FFmpeg)
#   - 安装 Editly
#   - 运行测试验证
#   - 生成示例视频
#
# 作者: Claude
# 创建: 2025-11-17
###############################################################################

set -e  # 遇到错误立即退出

echo "============================================================"
echo "  Editly 视频引擎部署脚本"
echo "============================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 检查 Node.js
echo ""
log_info "检查 Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_info "✅ Node.js 已安装: $NODE_VERSION"

    # 检查版本是否满足要求 (>= v12.16.2)
    REQUIRED_VERSION="12.16.2"
    CURRENT_VERSION=$(node --version | sed 's/v//')

    if [[ $(echo -e "$REQUIRED_VERSION\n$CURRENT_VERSION" | sort -V | head -n1) == "$REQUIRED_VERSION" ]]; then
        log_info "✅ Node.js 版本满足要求 (>= $REQUIRED_VERSION)"
    else
        log_warn "⚠️ Node.js 版本过低，建议升级到 v12.16.2+"
        log_warn "   下载地址: https://nodejs.org/"
    fi
else
    log_error "❌ Node.js 未安装"
    log_error "   请安装 Node.js (LTS 版本)"
    log_error "   下载地址: https://nodejs.org/"
    exit 1
fi

# 2. 检查 FFmpeg
echo ""
log_info "检查 FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    log_info "✅ FFmpeg 已安装: $FFMPEG_VERSION"
else
    log_error "❌ FFmpeg 未安装"
    log_error "   请安装 FFmpeg:"
    log_error "   - Windows: choco install ffmpeg"
    log_error "   - macOS:   brew install ffmpeg"
    log_error "   - Linux:   sudo apt-get install ffmpeg"
    exit 1
fi

# 3. 安装 Editly
echo ""
log_info "检查 Editly..."
if command -v editly &> /dev/null; then
    EDITLY_VERSION=$(editly --version 2>&1 || echo "unknown")
    log_info "✅ Editly 已安装: $EDITLY_VERSION"
    log_warn "⚠️ 如需更新，请运行: npm update -g editly"
else
    log_warn "❌ Editly 未安装，开始安装..."
    log_info "运行: npm install -g editly"

    if npm install -g editly; then
        log_info "✅ Editly 安装成功"
    else
        log_error "❌ Editly 安装失败"
        log_error "   请手动运行: npm install -g editly"
        exit 1
    fi
fi

# 4. 验证 Editly
echo ""
log_info "验证 Editly 安装..."
if editly --version &> /dev/null; then
    log_info "✅ Editly 工作正常"
else
    log_error "❌ Editly 验证失败"
    exit 1
fi

# 5. 创建测试目录
echo ""
log_info "创建测试目录..."
mkdir -p workspace/materials/images
mkdir -p workspace/materials/videos
mkdir -p workspace/output
mkdir -p logs
log_info "✅ 目录创建完成"

# 6. 生成示例素材（纯色图片）
echo ""
log_info "生成示例素材..."

if command -v convert &> /dev/null; then
    # 使用 ImageMagick 生成测试图片
    convert -size 1080x1920 xc:blue workspace/materials/images/sample1.jpg
    convert -size 1080x1920 xc:red workspace/materials/images/sample2.jpg
    convert -size 1080x1920 xc:green workspace/materials/images/sample3.jpg
    log_info "✅ 示例素材生成完成 (使用 ImageMagick)"
elif command -v ffmpeg &> /dev/null; then
    # 使用 FFmpeg 生成测试图片
    ffmpeg -f lavfi -i color=c=blue:s=1080x1920:d=1 -frames:v 1 workspace/materials/images/sample1.jpg -y 2>/dev/null
    ffmpeg -f lavfi -i color=c=red:s=1080x1920:d=1 -frames:v 1 workspace/materials/images/sample2.jpg -y 2>/dev/null
    ffmpeg -f lavfi -i color=c=green:s=1080x1920:d=1 -frames:v 1 workspace/materials/images/sample3.jpg -y 2>/dev/null
    log_info "✅ 示例素材生成完成 (使用 FFmpeg)"
else
    log_warn "⚠️ 无法生成示例素材 (需要 ImageMagick 或 FFmpeg)"
    log_warn "   请手动添加图片到 workspace/materials/images/"
fi

# 7. 运行 Python 测试（如果可用）
echo ""
log_info "检查 Python 环境..."
if command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    log_info "✅ Python 已安装: $PYTHON_VERSION"

    log_info "运行测试脚本..."
    if python test_editly_engine.py; then
        log_info "✅ 测试完成"
    else
        log_warn "⚠️ 测试失败，请检查日志"
    fi
else
    log_warn "⚠️ Python 未安装，跳过测试"
fi

# 8. 完成
echo ""
echo "============================================================"
log_info "🎉 Editly 视频引擎部署完成！"
echo "============================================================"
echo ""
log_info "下一步操作:"
echo "  1. 查看文档: docs/EDITLY_INTEGRATION_GUIDE.md"
echo "  2. 运行测试: python test_editly_engine.py"
echo "  3. 生成视频: 参考集成指南中的示例代码"
echo ""
log_info "快速测试:"
echo "  cd textloom"
echo "  python test_editly_engine.py"
echo ""

exit 0
