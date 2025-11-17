#!/bin/bash
################################################################################
# Editly 自动安装脚本 - Ubuntu Server
#
# 用法:
#   chmod +x setup_ubuntu.sh
#   ./setup_ubuntu.sh
#
# 功能:
#   - 安装 Node.js (v18 LTS)
#   - 安装 FFmpeg
#   - 安装 Canvas 依赖
#   - 构建 Editly
#   - 运行测试
#
# 系统要求:
#   - Ubuntu 18.04+ / Debian 10+
#   - sudo 权限
#
# 作者: Claude
# 日期: 2025-11-17
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}[STEP]${NC} $1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
    log_warn "不建议以 root 用户运行此脚本"
    log_warn "如果需要 sudo 权限，脚本会自动询问"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║        Editly 视频编辑引擎自动安装脚本                      ║"
echo "║              Ubuntu Server Edition                        ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================
# STEP 1: 更新系统包
# ============================================================
log_step "1/7 更新系统包列表"

log_info "运行: sudo apt-get update"
sudo apt-get update -qq

log_info "✅ 系统包列表已更新"
echo ""

# ============================================================
# STEP 2: 安装基础依赖
# ============================================================
log_step "2/7 安装基础依赖工具"

log_info "安装: curl, git, build-essential"
sudo apt-get install -y -qq \
    curl \
    git \
    build-essential \
    software-properties-common

log_info "✅ 基础依赖已安装"
echo ""

# ============================================================
# STEP 3: 安装 Node.js
# ============================================================
log_step "3/7 安装 Node.js (v18 LTS)"

# 检查是否已安装 Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    log_info "已安装 Node.js: $NODE_VERSION"

    # 检查版本是否满足要求 (>= v12)
    MAJOR_VERSION=$(echo $NODE_VERSION | sed 's/v//' | cut -d. -f1)
    if [ "$MAJOR_VERSION" -lt 12 ]; then
        log_warn "Node.js 版本过低，正在升级..."
        INSTALL_NODE=true
    else
        log_info "Node.js 版本满足要求，跳过安装"
        INSTALL_NODE=false
    fi
else
    log_info "Node.js 未安装，开始安装..."
    INSTALL_NODE=true
fi

if [ "$INSTALL_NODE" = true ]; then
    # 使用 NodeSource 仓库安装 Node.js 18
    log_info "添加 NodeSource 仓库..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

    log_info "安装 Node.js..."
    sudo apt-get install -y -qq nodejs

    NODE_VERSION=$(node --version)
    log_info "✅ Node.js 安装完成: $NODE_VERSION"
else
    log_info "✅ Node.js 已就绪"
fi

NPM_VERSION=$(npm --version)
log_info "npm 版本: $NPM_VERSION"
echo ""

# ============================================================
# STEP 4: 安装 FFmpeg
# ============================================================
log_step "4/7 安装 FFmpeg"

if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
    log_info "已安装 FFmpeg: $FFMPEG_VERSION"
    log_info "跳过安装"
else
    log_info "FFmpeg 未安装，开始安装..."
    sudo apt-get install -y -qq ffmpeg

    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
    log_info "✅ FFmpeg 安装完成: $FFMPEG_VERSION"
fi

# 验证 ffprobe
if command -v ffprobe &> /dev/null; then
    log_info "✅ ffprobe 已就绪"
else
    log_error "ffprobe 未安装，请检查 FFmpeg 安装"
    exit 1
fi
echo ""

# ============================================================
# STEP 5: 安装 Canvas 依赖
# ============================================================
log_step "5/7 安装 Canvas 图形库依赖"

log_info "安装 Cairo, Pango, libjpeg, libgif..."
sudo apt-get install -y -qq \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev

log_info "✅ Canvas 依赖已安装"
echo ""

# ============================================================
# STEP 6: 构建 Editly
# ============================================================
log_step "6/7 构建 Editly"

# 检查是否在 editly 目录中
if [ ! -f "package.json" ]; then
    log_error "package.json 未找到"
    log_error "请在 editly 项目目录中运行此脚本"
    exit 1
fi

log_info "清理旧的 node_modules..."
rm -rf node_modules package-lock.json

log_info "安装 npm 依赖..."
npm install

log_info "构建 Editly..."
npm run build

# 验证构建结果
if [ -f "dist/cli.js" ]; then
    log_info "✅ Editly 构建成功"
else
    log_error "❌ Editly 构建失败，dist/cli.js 未生成"
    exit 1
fi
echo ""

# ============================================================
# STEP 7: 验证安装
# ============================================================
log_step "7/7 验证安装"

log_info "运行: node dist/cli.js --version"
node dist/cli.js --version

log_info "运行: node dist/cli.js --help"
node dist/cli.js --help | head -10

echo ""
log_info "✅ Editly 安装验证通过"
echo ""

# ============================================================
# 完成
# ============================================================
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║               🎉 安装完成！                                 ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_info "环境信息:"
echo "  - Node.js: $(node --version)"
echo "  - npm: $(npm --version)"
echo "  - FFmpeg: $(ffmpeg -version 2>&1 | head -n1 | awk '{print $3}')"
echo "  - Editly: $(node dist/cli.js --version 2>&1 || echo '已安装')"
echo ""

log_info "下一步操作:"
echo "  1. 运行测试: ./run_tests.sh"
echo "  2. 生成示例视频: node dist/cli.js examples/single.json5 --out test.mp4"
echo "  3. 查看文档: cat ../docs/IMPLEMENTATION_ROADMAP.md"
echo ""

log_info "快速测试命令:"
echo "  cd examples"
echo "  node ../dist/cli.js single.json5 --out ../output/test1.mp4"
echo ""

exit 0
