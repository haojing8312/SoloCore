# TextLoom Web Frontend - 快速入门指南

本文档将帮助您快速上手 TextLoom Web Frontend，从安装到创建第一个视频。

## 📋 目录

- [环境准备](#环境准备)
- [安装步骤](#安装步骤)
- [启动应用](#启动应用)
- [使用指南](#使用指南)
- [常见问题](#常见问题)

## 🔧 环境准备

在开始之前，请确保您的系统已安装以下软件：

### 必需软件

| 软件 | 最低版本 | 推荐版本 | 下载地址 |
|------|----------|----------|----------|
| Node.js | 18.0.0 | 20.x LTS | https://nodejs.org/ |
| pnpm | 8.6.0 | 最新版本 | `npm install -g pnpm` |

### 验证安装

```bash
# 检查 Node.js 版本
node --version
# 输出示例: v20.10.0

# 检查 pnpm 版本
pnpm --version
# 输出示例: 8.15.0
```

## 📦 安装步骤

### 1. 克隆项目

```bash
# 克隆主仓库
git clone https://github.com/haojing8312/SoloCore.git

# 进入前端目录
cd SoloCore/frontend
```

### 2. 安装依赖

```bash
# 使用 pnpm 安装（推荐）
pnpm install

# 或使用 npm
npm install

# 或使用 yarn
yarn install
```

安装过程大约需要 1-3 分钟，取决于您的网络速度。

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 使用文本编辑器打开 .env 文件
# Windows: notepad .env
# macOS/Linux: nano .env 或 vim .env
```

编辑 `.env` 文件内容：

```env
# API 基础地址（默认为本地 TextLoom 后端）
VITE_API_BASE_URL=http://localhost:48095
```

> ⚠️ **重要提示**: 请确保 TextLoom 后端服务正在运行在 `http://localhost:48095`

## 🚀 启动应用

### 开发模式启动

```bash
# 启动开发服务器
pnpm dev

# 或使用 npm
npm run dev

# 或使用 yarn
yarn dev
```

启动成功后，您会看到如下输出：

```
VITE v5.4.21  ready in 588 ms

➜  Local:   http://localhost:5173/
➜  Network: http://192.168.x.x:5173/
```

在浏览器中打开 `http://localhost:5173` 即可访问应用。

### 其他可用命令

```bash
# 构建生产版本
pnpm build

# 预览生产构建
pnpm preview

# TypeScript 类型检查
pnpm type-check

# ESLint 代码检查
pnpm lint
```

## 📖 使用指南

### 第一步：上传文档

1. 在首页点击上传区域或拖拽文件到上传框
2. 支持的文件格式：`.md`, `.markdown`, `.txt`
3. 文件大小限制：10MB
4. 上传进度会实时显示

![上传文件示意图]

### 第二步：选择字幕模板

选择您喜欢的字幕样式（4 种可选）：

- **Hype** - 动感活力，适合年轻受众
- **Minimalist** - 简约优雅，适合商务场景
- **Explosive** - 爆炸效果，适合惊喜内容
- **Vibrant** - 活力四射，适合娱乐内容

### 第三步：创建任务

1. 确认文件已上传且模板已选择
2. 点击"开始生成"按钮
3. 自动跳转到任务详情页

### 第四步：监控进度

任务详情页会自动轮询（每 3 秒刷新一次）：

- **素材处理** (0-25%) - 提取文档中的图片和媒体
- **素材分析** (25-50%) - AI 分析内容并生成描述
- **脚本生成** (50-75%) - 生成视频脚本和配音
- **视频生成** (75-100%) - 合成最终视频

### 第五步：下载视频

- 视频生成完成后会自动显示播放器
- 点击"下载视频"按钮保存到本地
- 支持在线预览播放

## 🎯 功能导航

### 主页 (`/`)
- 文件上传
- 模板选择
- 任务创建

### 任务详情 (`/tasks/:taskId`)
- 实时进度监控
- 视频播放与下载
- 取消任务（处理中）

### 任务列表 (`/tasks`)
- 查看所有任务
- 按状态筛选（全部/进行中/已完成/失败）
- 删除已完成/失败的任务

### 数据统计 (`/stats`)
- 总任务数、今日生成、成功率、平均耗时
- 任务状态分布饼图
- 最近 7 天生成趋势折线图

## ❓ 常见问题

### Q1: 为什么文件上传失败？

**可能原因：**
- 文件格式不支持（仅支持 .md/.markdown/.txt）
- 文件大小超过 10MB
- 后端服务未启动

**解决方法：**
```bash
# 检查后端服务是否运行
curl http://localhost:48095/health

# 如果未运行，请启动 TextLoom 后端
cd ../textloom
./start_all_services.sh
```

### Q2: 为什么任务一直显示"进行中"？

**可能原因：**
- 后端 Celery Worker 未启动
- Redis 服务未运行
- 网络连接问题

**解决方法：**
```bash
# 检查 Celery Worker 状态
cd ../textloom
celery -A celery_config inspect active

# 检查 Redis 是否运行
redis-cli ping
# 应输出: PONG
```

### Q3: 为什么看不到统计数据？

**可能原因：**
- 数据库中还没有任务数据
- 后端 API 返回错误

**解决方法：**
- 先创建几个任务生成视频
- 检查浏览器控制台的错误信息
- 检查后端日志：`tail -f ../textloom/logs/app.log`

### Q4: 开发服务器启动失败怎么办？

**可能原因：**
- 端口被占用
- 依赖安装不完整
- Node.js 版本过低

**解决方法：**
```bash
# 清理依赖重新安装
rm -rf node_modules pnpm-lock.yaml
pnpm install

# 检查 Node.js 版本
node --version
# 必须 >= 18.0.0

# 如果端口被占用，可以修改 vite.config.ts 中的端口号
```

### Q5: 视频播放失败怎么办？

**可能原因：**
- 视频文件损坏
- 浏览器不支持视频格式
- 视频 URL 过期

**解决方法：**
- 使用现代浏览器（Chrome/Firefox/Edge 最新版）
- 检查视频文件是否存在
- 重新生成视频

## 🔗 相关链接

- [项目主页](https://github.com/haojing8312/SoloCore)
- [TextLoom 后端文档](../textloom/README.md)
- [问题反馈](https://github.com/haojing8312/SoloCore/issues)
- [技术架构文档](./README.md#技术栈)

## 📞 获取帮助

如果您遇到问题：

1. **查看文档**: 先查阅本文档和 [README.md](./README.md)
2. **搜索 Issues**: 在 [GitHub Issues](https://github.com/haojing8312/SoloCore/issues) 中搜索相似问题
3. **提交 Issue**: 如果问题未解决，请创建新的 Issue
4. **查看日志**: 检查浏览器控制台和后端日志以获取详细错误信息

## 🎉 下一步

恭喜！您已经成功启动了 TextLoom Web Frontend。

**推荐操作：**

1. 创建您的第一个视频任务
2. 探索不同的字幕模板效果
3. 查看数据统计了解使用情况
4. 阅读 [README.md](./README.md) 了解更多技术细节

**进阶学习：**

- 了解组件结构和状态管理
- 学习如何自定义主题和样式
- 探索 API 服务层的实现
- 尝试贡献代码改进项目

---

**祝您使用愉快！** 🚀

如果觉得项目有用，欢迎 ⭐ Star 支持我们！
