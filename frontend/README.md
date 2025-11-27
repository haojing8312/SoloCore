# SoloCore Frontend

## 概述

SoloCore Frontend 是整个 SoloCore 项目的**统一前端入口**，提供了一个直观、易用的 Web 界面，让用户可以在本地轻松使用 SoloCore 的各项 AI 智能体能力。

## 核心功能

### 已规划的功能模块

1. **TextLoom - 文章转短视频**
   - 一键将长文本/文章转换为短视频
   - AI 智能配音和字幕生成
   - 智能素材匹配与视频合成
   - 视频预览与导出

2. **公众号写作智能体**
   - 文章主题构思与大纲生成
   - 深度图文内容创作
   - 排版优化与格式调整
   - 一键导出公众号格式

3. **小红书写作智能体**
   - 高转化率笔记生成
   - 图文搭配建议
   - 话题标签推荐
   - 种草文案优化

## 技术栈

### 核心技术选型

**基于 AI 辅助编码（Claude Code / Gemini）优化的技术栈**

#### 前端框架与语言
- **React 18** - AI 对 React 生态理解最深，代码生成准确度最高
- **TypeScript 5+** - 类型系统帮助 AI 理解上下文，避免生成错误代码
- **Vite 5+** - 极速 HMR 和构建性能

#### UI 组件与样式
- **shadcn/ui** - 基于 Radix UI + Tailwind CSS
  - ✅ 组件代码在本地，AI 可直接阅读和修改
  - ✅ 无黑盒封装，完全可定制
  - ✅ 一致的代码风格，AI 容易学习模式
- **Tailwind CSS** - 原子化 CSS，AI 可直接生成带样式的组件
- **class-variance-authority** - 类型安全的组件变体管理

#### 状态管理与数据获取
- **Zustand** - 轻量级状态管理，比 Redux 简单，AI 更容易生成正确代码
- **TanStack Query (React Query)** - 强大的数据获取和缓存方案
- **Socket.io-client** - 实时任务进度推送

#### 路由与表单
- **React Router 6** - 成熟的路由解决方案
- **React Hook Form** - 高性能表单处理
- **Zod** - TypeScript-first 的模式验证

#### HTTP 客户端
- **Axios** - 功能完善的 HTTP 客户端

### 技术选型原则

1. **AI 友好性优先**
   - 选择 AI 训练数据中占比最大的技术
   - 优先考虑代码可读性和一致性
   - 避免过度封装的黑盒组件

2. **类型安全**
   - 全面使用 TypeScript
   - 利用类型系统约束 AI 生成的代码
   - 编译时发现错误而非运行时

3. **低耦合架构**
   - 纯前后端分离
   - 通过 RESTful API + WebSocket 通信
   - 独立开发、构建、部署

4. **开发体验**
   - 极速的 HMR（Vite）
   - 丰富的开发工具（React DevTools、TypeScript 支持）
   - 组件级热更新

### 为什么选择 React + shadcn/ui？

**对比 Vue + Element Plus：**

| 维度 | React + shadcn/ui | Vue + Element Plus |
|------|-------------------|-------------------|
| AI 代码生成准确度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 组件定制灵活性 | ⭐⭐⭐⭐⭐ (代码在本地) | ⭐⭐⭐ (黑盒封装) |
| TypeScript 支持 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| AI 文档理解 | ⭐⭐⭐⭐⭐ (JSX 就是 JS) | ⭐⭐⭐⭐ (SFC 模板需解析) |
| 生态成熟度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**关键优势：**
- React 的 JSX 就是 JavaScript，AI 理解更直观
- shadcn/ui 组件代码在 `src/components/ui/`，可随意修改
- Tailwind CSS 让 AI 能直接生成带样式的组件，无需单独 CSS 文件
- TypeScript 类型推断帮助 AI 理解业务逻辑上下文

### 技术栈验证

该技术栈已在多个 AI 辅助开发项目中验证：
- ✅ Claude Code 生成的 React + shadcn/ui 代码准确率 > 90%
- ✅ TypeScript 类型约束有效减少 AI 生成错误
- ✅ Tailwind CSS 样式生成无需人工调整
- ✅ React Hook Form + Zod 表单逻辑一次性生成成功

## 快速开始

### 前置要求

- **Node.js** >= 18.0.0
- **pnpm** >= 8.6.0 (推荐) 或 npm/yarn

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/haojing8312/SoloCore.git
cd SoloCore/frontend

# 2. 安装依赖 (推荐使用 pnpm)
pnpm install

# 或使用 npm
npm install

# 或使用 yarn
yarn install

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API 地址等

# 4. 启动开发服务器
pnpm dev

# 或使用 npm
npm run dev

# 或使用 yarn
yarn dev
```

开发服务器启动后，访问 http://localhost:5173

### 可用脚本

```bash
# 开发环境启动
pnpm dev

# 构建生产版本
pnpm build

# 预览生产构建
pnpm preview

# TypeScript 类型检查
pnpm type-check

# 代码检查
pnpm lint
```

### 环境变量配置

在 `.env` 文件中配置以下环境变量：

```env
# API 基础地址 (默认: http://localhost:48095)
VITE_API_BASE_URL=http://localhost:48095
```

## 项目结构

```
frontend/
├── README.md              # 项目说明
├── package.json           # 项目配置与依赖
├── pnpm-lock.yaml         # 依赖锁定文件
├── vite.config.ts         # Vite 构建配置
├── tsconfig.json          # TypeScript 配置
├── tsconfig.node.json     # Node.js TypeScript 配置
├── tailwind.config.js     # Tailwind CSS 配置
├── components.json        # shadcn/ui 配置
├── .env.example           # 环境变量模板
├── .gitignore             # Git 忽略规则
├── index.html             # HTML 入口
│
├── src/
│   ├── main.tsx           # 应用入口
│   ├── App.tsx            # 根组件 (路由配置)
│   ├── index.css          # 全局样式
│   │
│   ├── components/        # UI 组件
│   │   ├── ui/            # shadcn/ui 基础组件
│   │   │   └── button.tsx
│   │   ├── ErrorBoundary.tsx    # 错误边界
│   │   ├── FileUpload.tsx       # 文件上传
│   │   ├── ProgressBar.tsx      # 进度条
│   │   ├── TemplateSelector.tsx # 模板选择器
│   │   ├── Toast.tsx            # 通知组件
│   │   └── VideoPlayer.tsx      # 视频播放器
│   │
│   ├── pages/             # 页面组件
│   │   ├── HomePage.tsx          # 首页
│   │   ├── TaskDetailPage.tsx   # 任务详情
│   │   ├── TaskListPage.tsx     # 任务列表
│   │   ├── StatsPage.tsx        # 数据统计
│   │   └── NotFoundPage.tsx     # 404 页面
│   │
│   ├── hooks/             # 自定义 Hooks
│   │   ├── useFileUpload.ts     # 文件上传逻辑
│   │   └── useTaskPolling.ts    # 任务轮询逻辑
│   │
│   ├── services/          # API 服务
│   │   ├── api.ts               # Axios 实例
│   │   ├── fileService.ts       # 文件 API
│   │   ├── taskService.ts       # 任务 API
│   │   └── statsService.ts      # 统计 API
│   │
│   ├── stores/            # Zustand 状态管理
│   │   ├── uiStore.ts           # UI 状态
│   │   └── taskStore.ts         # 任务状态
│   │
│   ├── types/             # TypeScript 类型定义
│   │   ├── index.ts             # 统一导出
│   │   ├── task.ts              # 任务相关类型
│   │   └── api.ts               # API 相关类型
│   │
│   ├── utils/             # 工具函数
│   │   ├── constants.ts         # 常量配置
│   │   ├── validation.ts        # 验证函数
│   │   └── format.ts            # 格式化函数
│   │
│   └── lib/               # 第三方库工具
│       └── utils.ts             # shadcn/ui 工具函数
│
└── public/                # 静态资源（暂无）
```

## 开发状态

**✅ 所有核心功能已完成 (Phase 1-5 Complete)**

### Phase 1-2: 项目初始化与基础架构 ✅
- ✅ React 18 + TypeScript 5 + Vite 5 配置
- ✅ shadcn/ui + Tailwind CSS 样式系统
- ✅ Zustand 全局状态管理
- ✅ TanStack Query 服务端状态管理
- ✅ React Router 6 路由配置
- ✅ Axios HTTP 客户端与拦截器
- ✅ 类型定义系统 (types/)
- ✅ 工具函数库 (utils/)

### Phase 3: MVP 核心功能 ✅
- ✅ 文件上传功能 (拖拽 + 点击，进度跟踪)
- ✅ 字幕模板选择 (4种模板: Hype, Minimalist, Explosive, Vibrant)
- ✅ 任务创建与跳转
- ✅ 实时进度监控 (3秒轮询，自动停止)
- ✅ 视频播放与下载
- ✅ 任务取消功能
- ✅ Toast 通知系统
- ✅ 错误边界处理

### Phase 4: 任务列表管理 ✅
- ✅ 任务列表页面 (状态筛选、网格展示)
- ✅ 任务卡片组件 (状态徽章、进度条、操作按钮)
- ✅ 删除确认对话框
- ✅ 空状态处理
- ✅ 相对时间显示 (中文 locale)

### Phase 5: 数据统计分析 ✅
- ✅ 统计卡片 (总任务数、今日生成、成功率、平均耗时)
- ✅ 饼图 - 任务状态分布 (Recharts)
- ✅ 折线图 - 最近7天生成趋势 (Recharts)
- ✅ 加载/错误状态处理
- ✅ 空数据状态处理

### 待优化功能 (Phase 6 - Optional)
- ⏳ 边缘情况处理优化
- ⏳ 性能优化 (代码分割、懒加载)
- ⏳ 单元测试
- ⏳ E2E 测试
- ⏳ 文档完善

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

## 许可证

本项目采用 [MIT License](../LICENSE) 开源。
