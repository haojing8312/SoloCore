# Quick Start: TextLoom Web Frontend

**Date**: 2025-11-26
**Branch**: `001-textloom-web-frontend`

## Purpose

本文档提供 TextLoom Web Frontend 的快速开始指南,帮助开发者在 5 分钟内启动本地开发环境。

---

## 前置条件

在开始之前,请确保已安装以下工具:

```bash
# Node.js 18+ (推荐使用 LTS 版本)
node --version  # 应输出 v18.x.x 或更高

# pnpm (推荐) 或 npm
pnpm --version  # 或使用 npm --version
```

如果未安装 pnpm,可以通过以下命令安装:
```bash
npm install -g pnpm
```

---

## 第一步:克隆项目并安装依赖

```bash
# 1. 克隆 SoloCore 仓库(如果尚未克隆)
git clone https://github.com/haojing8312/SoloCore.git
cd SoloCore

# 2. 切换到功能分支
git checkout 001-textloom-web-frontend

# 3. 进入前端目录
cd frontend

# 4. 安装依赖
pnpm install
```

预计安装时间:1-2 分钟(取决于网络速度)

---

## 第二步:配置环境变量

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件(可选)
# 默认配置已经可以直接使用,如果需要修改 API 地址:
# VITE_API_BASE_URL=http://localhost:48095
```

**重要**: 不要修改根目录的 .env 文件,只修改 `frontend/.env`。

---

## 第三步:启动开发服务器

```bash
# 在 frontend/ 目录下运行
pnpm dev
```

预期输出:
```
  VITE v5.x.x  ready in 200 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

现在打开浏览器访问 `http://localhost:5173`,你应该看到 TextLoom 的首页。

---

## 第四步:启动后端服务(必需)

TextLoom Frontend 需要连接到后端 API 才能正常工作。在另一个终端窗口:

```bash
# 1. 进入后端目录
cd textloom

# 2. 启动所有服务 (API + Celery Worker/Flower/Beat)
./start_all_services.sh
```

预期输出:
```
✅ Starting PostgreSQL and Redis...
✅ Starting TextLoom API on port 48095...
✅ Starting Celery Worker...
✅ Starting Celery Flower on port 5555...
✅ Starting Celery Beat...

All services started successfully!
API: http://localhost:48095
Flower: http://localhost:5555
```

如果遇到错误,请查看 `textloom/README.md` 获取详细的后端设置说明。

---

## 验证安装

### 1. 前端验证

访问 `http://localhost:5173`,你应该看到:
- ✅ TextLoom 标题和导航栏
- ✅ 文件上传区域
- ✅ 字幕模板选择卡片(Hype, Minimalist, Explosive, Vibrant)
- ✅ "开始生成"按钮(未选择文件时禁用)

### 2. 后端验证

访问 `http://localhost:48095/docs`,你应该看到:
- ✅ Swagger UI 文档页面
- ✅ 包含 `/api/files/upload`, `/api/tasks/create` 等端点

### 3. 完整流程验证

1. 在首页点击上传区域,选择一个 Markdown 文件
2. 选择一个字幕模板(如 Hype)
3. 点击"开始生成"按钮
4. 你应该被跳转到任务详情页面,看到进度条开始更新

如果一切正常,恭喜!你已经成功启动 TextLoom 开发环境 🎉

---

## 项目结构快览

```
frontend/
├── src/
│   ├── components/      # UI 组件
│   │   ├── ui/         # shadcn/ui 基础组件
│   │   ├── FileUpload.tsx
│   │   └── TemplateSelector.tsx
│   ├── pages/           # 页面组件
│   │   ├── HomePage.tsx
│   │   ├── TaskListPage.tsx
│   │   └── TaskDetailPage.tsx
│   ├── stores/          # Zustand 状态管理
│   │   ├── taskStore.ts
│   │   └── uiStore.ts
│   ├── services/        # API 服务层
│   │   └── taskService.ts
│   ├── hooks/           # 自定义 React Hooks
│   │   └── useTaskPolling.ts
│   ├── types/           # TypeScript 类型定义
│   │   └── task.ts
│   └── App.tsx          # 根组件
├── public/              # 静态资源
├── .env.example         # 环境变量模板
├── package.json         # 依赖配置
├── vite.config.ts       # Vite 配置
└── README.md            # 用户文档
```

---

## 常用开发命令

```bash
# 启动开发服务器(带 HMR)
pnpm dev

# 构建生产版本
pnpm build

# 预览生产构建
pnpm preview

# 运行代码检查
pnpm lint

# 修复代码风格问题
pnpm lint:fix

# 运行类型检查
pnpm type-check

# 运行单元测试
pnpm test

# 运行测试(带覆盖率)
pnpm test:coverage

# 运行 E2E 测试
pnpm test:e2e
```

---

## 开发工作流

### 1. 创建新组件

```bash
# 在 src/components/ 目录下创建组件
# 例如: src/components/VideoPlayer.tsx
```

组件模板:
```tsx
import React from 'react';

interface VideoPlayerProps {
  videoUrl: string;
  onPlay?: () => void;
}

export function VideoPlayer({ videoUrl, onPlay }: VideoPlayerProps) {
  return (
    <div className="video-player">
      <video src={videoUrl} controls onPlay={onPlay} />
    </div>
  );
}
```

### 2. 创建新页面

```bash
# 在 src/pages/ 目录下创建页面组件
# 例如: src/pages/StatsPage.tsx

# 然后在 src/App.tsx 中添加路由
```

### 3. 添加 API 调用

```bash
# 在 src/services/ 目录下创建服务文件
# 例如: src/services/statsService.ts
```

服务模板:
```typescript
import axios from './api';
import type { GetStatsResponse } from '@/types/api';

export async function getStats(): Promise<GetStatsResponse> {
  const response = await axios.get('/api/stats');
  return response.data;
}
```

### 4. 添加状态管理

```bash
# 在 src/stores/ 目录下创建 Zustand store
# 例如: src/stores/statsStore.ts
```

Store 模板:
```typescript
import { create } from 'zustand';
import type { StatsData } from '@/types/api';

interface StatsStore {
  stats: StatsData | null;
  setStats: (stats: StatsData) => void;
}

export const useStatsStore = create<StatsStore>((set) => ({
  stats: null,
  setStats: (stats) => set({ stats }),
}));
```

---

## 调试技巧

### 1. React DevTools

安装 Chrome 扩展:
- [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)

使用方法:
- 按 F12 打开开发者工具
- 切换到 "Components" 标签查看组件树
- 切换到 "Profiler" 标签分析性能

### 2. 查看 Network 请求

- 按 F12 打开开发者工具
- 切换到 "Network" 标签
- 筛选 "Fetch/XHR" 查看 API 请求
- 点击请求查看详细的 Request/Response

### 3. 查看 TanStack Query 缓存

```tsx
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// 在 App.tsx 中添加
<ReactQueryDevtools initialIsOpen={false} />
```

### 4. 使用 Vite 插件查看构建分析

```bash
# 安装插件
pnpm add -D rollup-plugin-visualizer

# 构建并查看分析
pnpm build
# 打开 stats.html 查看 bundle 大小分析
```

---

## 常见问题

### Q1: 端口 5173 已被占用

**解决方案**:
```bash
# 修改 vite.config.ts 中的端口
export default defineConfig({
  server: {
    port: 3000, // 改为其他端口
  },
});
```

### Q2: API 请求失败(CORS 错误)

**解决方案**:
```bash
# 检查后端是否正确配置 CORS
# 在 textloom/main.py 中确认:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q3: 依赖安装失败

**解决方案**:
```bash
# 清除缓存并重新安装
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Q4: TypeScript 类型错误

**解决方案**:
```bash
# 重启 VSCode 的 TypeScript 服务器
# 按 Ctrl+Shift+P,输入 "Restart TS Server"

# 或者运行类型检查
pnpm type-check
```

---

## 下一步

现在你已经成功启动了开发环境,可以:

1. **查看 README.md** - 了解项目架构和功能
2. **查看 CLAUDE.md** - 了解开发规范和最佳实践
3. **查看 spec.md** - 了解功能需求和用户故事
4. **查看 data-model.md** - 了解数据模型和类型定义
5. **开始实现** - 按照 tasks.md 中的任务列表逐步开发

祝你开发顺利! 如果遇到问题,请查看项目文档或提交 Issue。
