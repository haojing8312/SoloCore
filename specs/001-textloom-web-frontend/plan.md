# Implementation Plan: TextLoom Web Frontend

**Branch**: `001-textloom-web-frontend` | **Date**: 2025-11-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-textloom-web-frontend/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

TextLoom Web Frontend 是一个单页应用(SPA),用于将 Markdown 文档转换为视频。用户可以上传文件、选择字幕模板、监控生成进度、播放视频、管理历史任务和查看统计数据。技术栈采用 React + TypeScript + Vite + shadcn/ui,与现有的 TextLoom Python 后端集成。

## Technical Context

**Language/Version**: TypeScript 5.x, Node.js 18+  
**Primary Dependencies**: React 18, Vite 5, shadcn/ui (Radix UI + Tailwind CSS), Zustand (状态管理), React Router 6, TanStack Query (数据获取), Recharts (图表), Axios (HTTP 客户端)  
**Storage**: LocalStorage (用户偏好), 无需数据库(所有数据通过 API 从后端获取)  
**Testing**: Vitest (单元测试), React Testing Library (组件测试), Playwright (E2E 测试)  
**Target Platform**: 现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)  
**Project Type**: 单项目 Web 应用 (frontend-only SPA)  
**Performance Goals**: 
  - 首次内容绘制 (FCP) < 1.5s
  - 最大内容绘制 (LCP) < 2.5s
  - 首次输入延迟 (FID) < 100ms
  - 累计布局偏移 (CLS) < 0.1
  - API 响应展示 < 200ms
  
**Constraints**: 
  - 必须兼容 TextLoom 现有后端 API (FastAPI, 端口 48095)
  - 不实现用户认证(当前版本)
  - 单任务单视频模式(multi_video_count=1)
  - 轮询间隔固定为 3 秒
  - 文件上传限制 10MB
  
**Scale/Scope**: 
  - 5 个页面/视图 (首页、任务列表、任务详情、统计、脚本查看)
  - ~15 个 React 组件
  - ~8 个 API 端点集成
  - 支持单用户本地部署

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Monorepo Architecture ✅ PASS

- **规则**: 每个子项目独立的构建系统和依赖管理
- **检查**: 
  - ✅ frontend/ 目录将有独立的 package.json 和 node_modules
  - ✅ 不会与 textloom/ (Python) 或 easegen-admin/ (Java) 共享依赖
  - ✅ 通过 REST API 与后端通信,无直接代码导入
- **结论**: 符合宪法要求

### II. Configuration Safety ✅ PASS

- **规则**: 不修改 .env 文件,仅使用 .env.example 作为模板
- **检查**: 
  - ✅ 将创建 frontend/.env.example 定义 API 端点等配置
  - ✅ 不会创建或修改根目录的 .env 文件
  - ✅ 环境变量通过 Vite 的 import.meta.env 访问
- **结论**: 符合宪法要求

### III. Database Integrity ✅ N/A

- **规则**: 数据库更改必须使用迁移工具
- **检查**: 
  - ✅ Frontend 不直接访问数据库
  - ✅ 所有数据通过后端 API 获取
- **结论**: 不适用(前端无数据库)

### IV. Async-First Development ⚠️ PARTIAL

- **规则**: TextLoom 必须全程使用 async/await (针对 Python 后端)
- **检查**: 
  - ✅ Frontend 使用 async/await 处理 API 调用(标准 JavaScript/TypeScript 实践)
  - ⚠️ 此规则主要针对 textloom/ Python 后端,前端自然符合
- **结论**: 符合(JavaScript 原生支持异步)

### V. Testing Discipline ⚠️ NEEDS ATTENTION

- **规则**: 功能必须通过多层测试验证
- **计划**: 
  - ✅ 单元测试: 使用 Vitest 测试工具函数和 hooks
  - ✅ 组件测试: 使用 React Testing Library 测试 UI 组件
  - ⚠️ 集成测试: 使用 MSW (Mock Service Worker) 模拟 API
  - ⚠️ E2E 测试: 使用 Playwright 测试完整用户流程(可选,根据时间决定)
- **行动**: Phase 1 设计阶段将定义测试策略,确保关键用户故事(P1)有完整测试覆盖

### VI. Documentation Standards ✅ PASS

- **规则**: 每个子项目需要 README.md 和 CLAUDE.md
- **计划**: 
  - ✅ 将创建 frontend/README.md (用户快速开始)
  - ✅ 将创建 frontend/CLAUDE.md (开发者技术指南)
  - ✅ API 文档将通过 TypeScript 类型定义和 JSDoc 注释提供
- **结论**: 将在 Phase 1 完成文档创建

### 总体评估: ✅ PASS (with minor warnings)

所有强制性规则均已满足。测试策略需要在 Phase 1 详细规划。

## Project Structure

### Documentation (this feature)

```text
specs/001-textloom-web-frontend/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (技术选型和最佳实践)
├── data-model.md        # Phase 1 output (前端状态模型和类型定义)
├── quickstart.md        # Phase 1 output (本地开发快速开始)
├── contracts/           # Phase 1 output (API 契约和类型定义)
│   ├── api.yaml        # OpenAPI 规范(后端 API)
│   └── types.ts        # TypeScript 类型定义
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
frontend/
├── public/              # 静态资源
│   ├── favicon.ico
│   └── logo.svg
├── src/
│   ├── components/      # UI 组件
│   │   ├── ui/         # shadcn/ui 基础组件 (Button, Card, Progress, etc.)
│   │   ├── FileUpload.tsx
│   │   ├── TemplateSelector.tsx
│   │   ├── VideoPlayer.tsx
│   │   ├── TaskCard.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── StatCard.tsx
│   │   └── ErrorBoundary.tsx
│   ├── pages/           # 页面组件
│   │   ├── HomePage.tsx           # 文档上传和生成
│   │   ├── TaskListPage.tsx       # 任务列表
│   │   ├── TaskDetailPage.tsx     # 任务详情
│   │   ├── StatsPage.tsx          # 统计页面
│   │   └── NotFoundPage.tsx       # 404 页面
│   ├── stores/          # Zustand 状态管理
│   │   ├── taskStore.ts           # 任务状态
│   │   └── uiStore.ts             # UI 状态(loading, errors)
│   ├── services/        # API 服务层
│   │   ├── api.ts                 # Axios 实例配置
│   │   ├── taskService.ts         # 任务 API 调用
│   │   ├── fileService.ts         # 文件上传 API
│   │   └── statsService.ts        # 统计 API
│   ├── hooks/           # 自定义 React Hooks
│   │   ├── useTaskPolling.ts      # 任务状态轮询
│   │   ├── useFileUpload.ts       # 文件上传逻辑
│   │   └── useTasks.ts            # 任务列表管理
│   ├── types/           # TypeScript 类型定义
│   │   ├── task.ts                # VideoTask, TaskStatus 等
│   │   ├── api.ts                 # API 请求/响应类型
│   │   └── index.ts               # 导出所有类型
│   ├── utils/           # 工具函数
│   │   ├── format.ts              # 日期、文件大小格式化
│   │   ├── validation.ts          # 文件验证
│   │   └── constants.ts           # 常量定义
│   ├── App.tsx          # 根组件(路由配置)
│   ├── main.tsx         # 应用入口
│   └── index.css        # 全局样式(Tailwind)
├── tests/               # 测试文件
│   ├── unit/           # 单元测试
│   │   ├── utils.test.ts
│   │   └── hooks.test.ts
│   ├── components/     # 组件测试
│   │   ├── FileUpload.test.tsx
│   │   └── TaskCard.test.tsx
│   └── e2e/            # E2E 测试(可选)
│       └── video-generation.spec.ts
├── .env.example         # 环境变量模板
├── package.json         # 依赖管理
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
├── tailwind.config.js   # Tailwind CSS 配置
├── components.json      # shadcn/ui 配置
├── README.md            # 用户文档
├── CLAUDE.md            # 开发者文档
└── PRODUCT_DESIGN_V2.md # 产品设计文档(已存在)
```

**Structure Decision**: 
选择单项目 Web 应用结构,因为:
1. TextLoom Frontend 是独立的 SPA,不需要后端代码
2. 与现有的 textloom/ (Python 后端) 通过 REST API 集成
3. 所有前端资源(组件、页面、状态)在 frontend/ 目录下组织
4. 符合 Monorepo 架构约束:独立的 node_modules 和构建系统

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

无宪法违规需要记录。所有检查均通过或已计划解决。
