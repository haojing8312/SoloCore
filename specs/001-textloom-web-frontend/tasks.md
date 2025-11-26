# Tasks: TextLoom Web Frontend

**Input**: Design documents from `/specs/001-textloom-web-frontend/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, contracts/, research.md, quickstart.md

**Tests**: 规格说明中未明确要求测试,因此本任务列表不包含测试任务。如需添加测试,请在实施后根据需要补充。

**Organization**: 任务按用户故事分组,支持独立实施和测试每个故事。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行(不同文件,无依赖)
- **[Story]**: 所属用户故事(US1, US2, US3)
- 包含文件路径的精确描述

## Path Conventions

- **前端单项目**: `frontend/src/`, `frontend/tests/`, `frontend/public/`
- 路径相对于仓库根目录

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化和基础结构搭建

- [ ] T001 在仓库根目录创建 frontend/ 目录
- [ ] T002 初始化 Node.js 项目,创建 frontend/package.json 配置文件
- [ ] T003 安装核心依赖: React 18, TypeScript 5.x, Vite 5
- [ ] T004 [P] 安装 UI 依赖: shadcn/ui, Radix UI, Tailwind CSS
- [ ] T005 [P] 安装状态管理依赖: Zustand, TanStack Query (React Query)
- [ ] T006 [P] 安装路由依赖: React Router 6
- [ ] T007 [P] 安装工具依赖: Axios, Recharts, date-fns
- [ ] T008 [P] 配置 Vite 构建工具,创建 frontend/vite.config.ts
- [ ] T009 [P] 配置 TypeScript,创建 frontend/tsconfig.json
- [ ] T010 [P] 配置 Tailwind CSS,创建 frontend/tailwind.config.js
- [ ] T011 [P] 配置 shadcn/ui,创建 frontend/components.json
- [ ] T012 创建环境变量模板 frontend/.env.example (定义 VITE_API_BASE_URL)
- [ ] T013 [P] 创建 Git 忽略文件 frontend/.gitignore (忽略 node_modules, dist, .env)
- [ ] T014 [P] 创建全局样式文件 frontend/src/index.css (导入 Tailwind 指令)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 核心基础设施,必须在所有用户故事之前完成

**⚠️ CRITICAL**: 在此阶段完成之前,无法开始任何用户故事的工作

### 项目结构

- [ ] T015 创建目录结构: frontend/src/{components,pages,stores,services,hooks,types,utils}
- [ ] T016 [P] 创建静态资源目录 frontend/public/
- [ ] T017 [P] 创建 shadcn/ui 组件目录 frontend/src/components/ui/

### 类型定义 (从 data-model.md 和 contracts/types.ts)

- [ ] T018 [P] 创建 frontend/src/types/task.ts,定义 VideoTask, TaskStatus, TaskPhase 枚举
- [ ] T019 [P] 创建 frontend/src/types/api.ts,定义 API 请求/响应类型
- [ ] T020 [P] 创建 frontend/src/types/index.ts,导出所有类型

### 常量和工具函数

- [ ] T021 [P] 创建 frontend/src/utils/constants.ts,定义 API_CONFIG, UPLOAD_CONFIG, TASK_CONFIG, UI_CONFIG, SUBTITLE_TEMPLATES
- [ ] T022 [P] 创建 frontend/src/utils/validation.ts,实现 validateFile 函数(文件类型和大小验证)
- [ ] T023 [P] 创建 frontend/src/utils/format.ts,实现日期格式化 formatDate, 文件大小格式化 formatFileSize, 时长格式化 formatDuration

### API 服务层 (Axios 配置)

- [ ] T024 创建 frontend/src/services/api.ts,配置 Axios 实例(baseURL, timeout, 拦截器)
- [ ] T025 在 api.ts 中实现请求拦截器(添加通用 headers)
- [ ] T026 在 api.ts 中实现响应拦截器(统一错误处理,401/500 错误提示)

### 全局状态管理 (Zustand Stores)

- [ ] T027 [P] 创建 frontend/src/stores/uiStore.ts,实现 UIStore (isGlobalLoading, error, toast 状态)
- [ ] T028 [P] 创建 frontend/src/stores/taskStore.ts,实现 TaskStore (currentTask, selectedTemplate, uploadProgress 状态)

### 路由配置

- [ ] T029 创建 frontend/src/App.tsx,配置 React Router 路由(/, /tasks, /tasks/:id, /stats, /404)
- [ ] T030 创建 frontend/src/main.tsx,作为应用入口,渲染 App 组件并包裹 QueryClientProvider
- [ ] T031 创建 frontend/src/pages/NotFoundPage.tsx,实现 404 页面

### shadcn/ui 基础组件安装

- [ ] T032 [P] 安装 shadcn/ui Button 组件到 frontend/src/components/ui/button.tsx
- [ ] T033 [P] 安装 shadcn/ui Card 组件到 frontend/src/components/ui/card.tsx
- [ ] T034 [P] 安装 shadcn/ui Progress 组件到 frontend/src/components/ui/progress.tsx
- [ ] T035 [P] 安装 shadcn/ui Dialog 组件到 frontend/src/components/ui/dialog.tsx
- [ ] T036 [P] 安装 shadcn/ui Tabs 组件到 frontend/src/components/ui/tabs.tsx
- [ ] T037 [P] 安装 shadcn/ui Input 组件到 frontend/src/components/ui/input.tsx
- [ ] T038 [P] 安装 shadcn/ui Badge 组件到 frontend/src/components/ui/badge.tsx
- [ ] T039 [P] 安装 shadcn/ui Toast 组件到 frontend/src/components/ui/toast.tsx (用于通知)

### 公共组件

- [ ] T040 创建 frontend/src/components/ErrorBoundary.tsx,捕获 React 组件错误并显示友好提示

**Checkpoint**: 基础设施就绪 - 用户故事实施现在可以并行开始

---

## Phase 3: User Story 1 - 文档上传并生成视频 (Priority: P1) 🎯 MVP

**Goal**: 用户可以上传 Markdown 文档,选择字幕模板,创建任务,监控进度,播放视频

**Independent Test**: 上传测试 .md 文件 → 选择字幕模板 → 点击"开始生成" → 跳转到任务详情页 → 看到进度条更新 → 任务完成后看到视频播放器

### API 服务层 (User Story 1 专用)

- [ ] T041 [P] [US1] 创建 frontend/src/services/fileService.ts,实现 uploadFile 函数(FormData 上传,支持进度回调)
- [ ] T042 [P] [US1] 创建 frontend/src/services/taskService.ts,实现 createTask, getTaskStatus, cancelTask 函数

### 自定义 Hooks (User Story 1 专用)

- [ ] T043 [P] [US1] 创建 frontend/src/hooks/useFileUpload.ts,封装文件上传逻辑(验证,上传,错误处理)
- [ ] T044 [P] [US1] 创建 frontend/src/hooks/useTaskPolling.ts,封装任务状态轮询逻辑(使用 TanStack Query refetchInterval)

### 组件实现 (User Story 1 专用)

- [ ] T045 [P] [US1] 创建 frontend/src/components/FileUpload.tsx,实现文件上传组件(拖拽区域,点击上传,文件验证,上传进度)
- [ ] T046 [P] [US1] 创建 frontend/src/components/TemplateSelector.tsx,实现字幕模板选择组件(4 个模板卡片,单选高亮)
- [ ] T047 [P] [US1] 创建 frontend/src/components/ProgressBar.tsx,实现进度条组件(百分比显示,当前阶段提示)
- [ ] T048 [P] [US1] 创建 frontend/src/components/VideoPlayer.tsx,实现视频播放器组件(HTML5 video 元素,播放控制,下载按钮)

### 页面实现 (User Story 1 专用)

- [ ] T049 [US1] 创建 frontend/src/pages/HomePage.tsx,集成 FileUpload 和 TemplateSelector 组件
- [ ] T050 [US1] 在 HomePage 中实现"开始生成"按钮逻辑(验证文件和模板,调用 uploadFile → createTask API)
- [ ] T051 [US1] 在 HomePage 中实现任务创建成功后跳转到 /tasks/:taskId
- [ ] T052 [US1] 创建 frontend/src/pages/TaskDetailPage.tsx,显示任务详情(文件名,状态,进度条)
- [ ] T053 [US1] 在 TaskDetailPage 中实现任务状态轮询(使用 useTaskPolling hook,每 3 秒更新)
- [ ] T054 [US1] 在 TaskDetailPage 中实现任务完成后显示 VideoPlayer 组件
- [ ] T055 [US1] 在 TaskDetailPage 中实现"取消任务"按钮(仅 processing 状态显示,调用 cancelTask API)

### 错误处理和边缘案例 (User Story 1 专用)

- [ ] T056 [US1] 实现文件大小超过 10MB 时的错误提示(在 FileUpload 组件中)
- [ ] T057 [US1] 实现文件格式错误时的错误提示(仅允许 .md 文件)
- [ ] T058 [US1] 实现未选择模板就点击"开始生成"时的提示
- [ ] T059 [US1] 实现"开始生成"按钮的 loading 状态(防止重复提交)
- [ ] T060 [US1] 实现轮询失败 3 次后停止轮询,显示错误提示
- [ ] T061 [US1] 实现视频播放失败时的错误提示
- [ ] T062 [US1] 实现网络错误时的友好提示和"重试"按钮

**Checkpoint**: User Story 1 完整实现 - 可独立测试和部署为 MVP

---

## Phase 4: User Story 2 - 查看和管理历史任务 (Priority: P2)

**Goal**: 用户可以查看任务列表,按状态筛选,查看详情,取消/删除任务

**Independent Test**: 导航到 /tasks → 看到任务列表 → 点击状态标签筛选 → 点击任务卡片查看详情 → 取消/删除任务

### API 服务层 (User Story 2 专用)

- [ ] T063 [P] [US2] 在 taskService.ts 中实现 getTasks 函数(支持状态筛选,分页,排序)
- [ ] T064 [P] [US2] 在 taskService.ts 中实现 deleteTask 函数

### 自定义 Hooks (User Story 2 专用)

- [ ] T065 [US2] 创建 frontend/src/hooks/useTasks.ts,封装任务列表管理逻辑(使用 TanStack Query,支持筛选和刷新)

### 组件实现 (User Story 2 专用)

- [ ] T066 [P] [US2] 创建 frontend/src/components/TaskCard.tsx,实现任务卡片组件(显示文件名,状态,进度,创建时间,操作按钮)
- [ ] T067 [US2] 在 TaskCard 组件中实现状态徽章(不同颜色标识 pending/processing/completed/failed/cancelled)
- [ ] T068 [US2] 在 TaskCard 组件中实现"取消任务"按钮(仅 processing 状态显示)
- [ ] T069 [US2] 在 TaskCard 组件中实现"删除"按钮(仅 completed/failed/cancelled 状态显示,需确认对话框)

### 页面实现 (User Story 2 专用)

- [ ] T070 [US2] 创建 frontend/src/pages/TaskListPage.tsx,显示任务列表(使用 useTasks hook)
- [ ] T071 [US2] 在 TaskListPage 中实现状态标签筛选(全部/进行中/已完成/失败,使用 Tabs 组件)
- [ ] T072 [US2] 在 TaskListPage 中实现空状态提示(无任务时显示"还没有任何任务,去创建第一个吧!")
- [ ] T073 [US2] 在 TaskListPage 中实现点击任务卡片跳转到 /tasks/:taskId
- [ ] T074 [US2] 在 TaskListPage 中实现删除任务后自动刷新列表

### 集成到 TaskDetailPage (User Story 2 专用)

- [ ] T075 [US2] 在 TaskDetailPage 中添加"返回任务列表"按钮
- [ ] T076 [US2] 在 TaskDetailPage 中添加"删除任务"按钮(仅 completed/failed 状态显示)

**Checkpoint**: User Story 2 完整实现 - 可独立测试,与 User Story 1 无冲突

---

## Phase 5: User Story 3 - 查看数据统计和分析 (Priority: P3)

**Goal**: 用户可以查看统计数据(任务总数,今日生成数,成功率,平均耗时,状态分布饼图,7 天趋势折线图)

**Independent Test**: 导航到 /stats → 看到 4 个统计卡片 → 看到饼图和折线图 → 刷新页面后数据更新

### API 服务层 (User Story 3 专用)

- [ ] T077 [US3] 创建 frontend/src/services/statsService.ts,实现 getStats 函数

### 组件实现 (User Story 3 专用)

- [ ] T078 [P] [US3] 创建 frontend/src/components/StatCard.tsx,实现统计卡片组件(显示标题,数值,图标,变化趋势)
- [ ] T079 [P] [US3] 创建 frontend/src/components/PieChart.tsx,封装 Recharts 饼图组件(任务状态分布)
- [ ] T080 [P] [US3] 创建 frontend/src/components/LineChart.tsx,封装 Recharts 折线图组件(7 天趋势)

### 页面实现 (User Story 3 专用)

- [ ] T081 [US3] 创建 frontend/src/pages/StatsPage.tsx,显示统计页面布局
- [ ] T082 [US3] 在 StatsPage 中集成 4 个 StatCard 组件(总任务数,今日生成数,成功率,平均耗时)
- [ ] T083 [US3] 在 StatsPage 中集成 PieChart 组件(任务状态分布)
- [ ] T084 [US3] 在 StatsPage 中集成 LineChart 组件(最近 7 天趋势)
- [ ] T085 [US3] 在 StatsPage 中实现数据加载状态(loading spinner)
- [ ] T086 [US3] 在 StatsPage 中实现空数据状态(显示"暂无数据"提示)

**Checkpoint**: User Story 3 完整实现 - 可独立测试,与 User Story 1/2 无冲突

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的改进和文档完善

- [ ] T087 [P] 创建 frontend/README.md (用户快速开始指南,基于 quickstart.md)
- [ ] T088 [P] 创建 frontend/CLAUDE.md (开发者技术文档,包含架构说明和开发规范)
- [ ] T089 优化全局样式 frontend/src/index.css (字体,颜色,间距)
- [ ] T090 添加网站图标 frontend/public/favicon.ico
- [ ] T091 添加网站 logo frontend/public/logo.svg
- [ ] T092 [P] 实现暗黑模式支持(可选,在 tailwind.config.js 中配置 darkMode)
- [ ] T093 优化 Vite 生产构建配置(代码分割,资源压缩)
- [ ] T094 添加性能监控(Web Vitals,使用 web-vitals 库)
- [ ] T095 优化 API 错误提示文案(更友好的用户语言)
- [ ] T096 [P] 添加 package.json scripts (dev, build, preview, lint, type-check)
- [ ] T097 验证所有页面的响应式布局(移动端适配)
- [ ] T098 验证所有交互的键盘导航支持(无障碍)
- [ ] T099 运行 TypeScript 类型检查 (pnpm type-check),修复所有类型错误
- [ ] T100 运行 ESLint 检查 (pnpm lint),修复所有代码风格问题

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - **阻塞所有用户故事**
- **User Story 1 (Phase 3)**: 依赖 Foundational 完成 - 这是 MVP
- **User Story 2 (Phase 4)**: 依赖 Foundational 完成 - 可与 US1 并行(如果有多人)
- **User Story 3 (Phase 5)**: 依赖 Foundational 完成 - 可与 US1/US2 并行(如果有多人)
- **Polish (Phase 6)**: 依赖所有需要的用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: 可在 Foundational (Phase 2) 后开始 - 无其他故事依赖
- **User Story 2 (P2)**: 可在 Foundational (Phase 2) 后开始 - 复用 US1 的 TaskDetailPage,但可独立测试
- **User Story 3 (P3)**: 可在 Foundational (Phase 2) 后开始 - 完全独立,无依赖其他故事

### Within Each User Story

- **User Story 1**:
  - API 服务 (T041-T042) 可并行
  - Hooks (T043-T044) 依赖 API 服务
  - 组件 (T045-T048) 可并行,依赖 Hooks
  - 页面 (T049-T055) 依赖组件,按顺序执行
  - 错误处理 (T056-T062) 依赖页面,可并行

- **User Story 2**:
  - API 服务 (T063-T064) 可并行
  - Hooks (T065) 依赖 API 服务
  - 组件 (T066-T069) 依赖 Hooks
  - 页面 (T070-T074) 依赖组件
  - 集成 (T075-T076) 依赖 US1 的 TaskDetailPage

- **User Story 3**:
  - API 服务 (T077) 无依赖
  - 组件 (T078-T080) 可并行,无依赖
  - 页面 (T081-T086) 依赖组件

### Parallel Opportunities

- **Setup phase**: T004-T007, T008-T011, T013-T014 可并行
- **Foundational phase**: T017-T020, T021-T023, T027-T028, T032-T039 可并行
- **User Story 1**: T041-T042, T043-T044, T045-T048, T056-T062 可并行
- **User Story 2**: T063-T064, T066-T069 可并行
- **User Story 3**: T078-T080 可并行
- **Polish phase**: T087-T088, T090-T091, T092, T096, T097-T098 可并行

- 完成 Foundational (Phase 2) 后,所有用户故事可由不同团队成员并行开发

---

## Parallel Example: User Story 1

```bash
# 在 Foundational (Phase 2) 完成后,并行启动 User Story 1 的所有 API 服务任务:
Task: "创建 fileService.ts,实现 uploadFile 函数"
Task: "创建 taskService.ts,实现 createTask, getTaskStatus, cancelTask 函数"

# 然后并行启动所有组件任务:
Task: "创建 FileUpload.tsx,实现文件上传组件"
Task: "创建 TemplateSelector.tsx,实现字幕模板选择组件"
Task: "创建 ProgressBar.tsx,实现进度条组件"
Task: "创建 VideoPlayer.tsx,实现视频播放器组件"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (**关键 - 阻塞所有故事**)
3. 完成 Phase 3: User Story 1
4. **停止并验证**: 独立测试 User Story 1 (上传 → 选择模板 → 生成 → 播放视频)
5. 如果通过,可以部署 MVP 并收集用户反馈

### Incremental Delivery

1. 完成 Setup + Foundational → 基础就绪
2. 添加 User Story 1 → 独立测试 → 部署/演示 (**MVP!**)
3. 添加 User Story 2 → 独立测试 → 部署/演示
4. 添加 User Story 3 → 独立测试 → 部署/演示
5. 每个故事增加价值,不破坏已有故事

### Parallel Team Strategy

如果有多个开发者:

1. 团队一起完成 Setup + Foundational
2. Foundational 完成后:
   - 开发者 A: User Story 1
   - 开发者 B: User Story 2
   - 开发者 C: User Story 3
3. 故事独立完成并集成

---

## Notes

- **[P] 任务** = 不同文件,无依赖,可并行
- **[Story] 标签** 将任务映射到特定用户故事,便于追踪
- 每个用户故事应该可独立完成和测试
- 在任何 checkpoint 停止以独立验证故事
- 避免: 模糊任务,相同文件冲突,破坏独立性的跨故事依赖
- 提交粒度: 每完成一个任务或逻辑组就提交
