# 组件使用指南

本文档详细介绍 TextLoom Frontend 中所有可复用组件的使用方法。

## 📋 目录

- [UI 基础组件](#ui-基础组件)
- [业务组件](#业务组件)
- [自定义 Hooks](#自定义-hooks)
- [组件开发规范](#组件开发规范)

## 🎨 UI 基础组件

### Button (按钮)

位置: `src/components/ui/button.tsx`

基于 shadcn/ui 的按钮组件，支持多种变体和尺寸。

#### 使用示例

```tsx
import { Button } from '@/components/ui/button';

function Example() {
  return (
    <>
      {/* 默认按钮 */}
      <Button>点击我</Button>

      {/* 次要按钮 */}
      <Button variant="secondary">次要操作</Button>

      {/* 危险按钮 */}
      <Button variant="destructive">删除</Button>

      {/* 大尺寸按钮 */}
      <Button size="lg">大按钮</Button>

      {/* 小尺寸按钮 */}
      <Button size="sm">小按钮</Button>

      {/* 带图标的按钮 */}
      <Button>
        <svg className="w-4 h-4 mr-2" />
        开始生成
      </Button>
    </>
  );
}
```

#### Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| variant | 'default' \| 'destructive' \| 'outline' \| 'secondary' \| 'ghost' \| 'link' | 'default' | 按钮变体 |
| size | 'default' \| 'sm' \| 'lg' \| 'icon' | 'default' | 按钮尺寸 |
| asChild | boolean | false | 作为子组件渲染 |
| disabled | boolean | false | 禁用状态 |

---

## 📦 业务组件

### FileUpload (文件上传)

位置: `src/components/FileUpload.tsx`

支持拖拽和点击上传的文件上传组件。

#### 功能特性

- ✅ 拖拽上传
- ✅ 点击选择文件
- ✅ 实时进度显示
- ✅ 文件格式验证
- ✅ 文件大小限制（10MB）
- ✅ 错误提示

#### 使用示例

```tsx
import { FileUpload } from '@/components/FileUpload';

function HomePage() {
  const handleFileUploaded = (fileId: string, filename: string) => {
    console.log('文件上传成功:', fileId, filename);
    // 保存 fileId 到状态
  };

  return (
    <FileUpload onFileUploaded={handleFileUploaded} />
  );
}
```

#### Props

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| onFileUploaded | (fileId: string, filename: string) => void | ✅ | 上传成功回调 |

#### 内部实现

```typescript
// 使用 useFileUpload hook
const { upload, isUploading, error } = useFileUpload();

// 处理文件选择
const handleFileSelect = async (file: File) => {
  const result = await upload(file);
  if (result) {
    onFileUploaded(result.fileId, result.filename);
  }
};

// 拖拽事件处理
const handleDrop = useCallback((e: React.DragEvent) => {
  e.preventDefault();
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFileSelect(files[0]);
  }
}, [handleFileSelect]);
```

---

### TemplateSelector (模板选择器)

位置: `src/components/TemplateSelector.tsx`

字幕模板选择组件，展示所有可用模板。

#### 功能特性

- ✅ 4 种字幕模板
- ✅ 可视化卡片展示
- ✅ 选中状态高亮
- ✅ 响应式网格布局

#### 使用示例

```tsx
import { TemplateSelector } from '@/components/TemplateSelector';

function HomePage() {
  const handleTemplateSelect = (templateId: string) => {
    console.log('选择模板:', templateId);
    // 保存模板到状态
  };

  return (
    <TemplateSelector onTemplateSelect={handleTemplateSelect} />
  );
}
```

#### Props

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| onTemplateSelect | (templateId: SubtitleTemplate) => void | ✅ | 模板选择回调 |

#### 模板信息

```typescript
// src/utils/constants.ts
export const SUBTITLE_TEMPLATES: SubtitleTemplateInfo[] = [
  {
    id: 'hype',
    name: 'Hype',
    description: '动感活力，适合年轻受众',
    previewImage: '/templates/hype-preview.png',
  },
  {
    id: 'minimalist',
    name: 'Minimalist',
    description: '简约优雅，适合商务场景',
    previewImage: '/templates/minimalist-preview.png',
  },
  {
    id: 'explosive',
    name: 'Explosive',
    description: '爆炸效果，适合惊喜内容',
    previewImage: '/templates/explosive-preview.png',
  },
  {
    id: 'vibrant',
    name: 'Vibrant',
    description: '活力四射，适合娱乐内容',
    previewImage: '/templates/vibrant-preview.png',
  },
];
```

---

### ProgressBar (进度条)

位置: `src/components/ProgressBar.tsx`

任务进度展示组件，带阶段指示器。

#### 功能特性

- ✅ 百分比显示
- ✅ 当前阶段标签
- ✅ 4 阶段网格指示器
- ✅ 平滑动画过渡

#### 使用示例

```tsx
import { ProgressBar } from '@/components/ProgressBar';
import { TaskPhase } from '@/types';

function TaskDetailPage() {
  const progress = 65; // 65%
  const currentPhase = TaskPhase.SCRIPT_GENERATION;

  return (
    <ProgressBar
      progress={progress}
      currentPhase={currentPhase}
    />
  );
}
```

#### Props

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| progress | number | ✅ | 进度值 (0-100) |
| currentPhase | TaskPhase | ❌ | 当前阶段 |

#### 阶段映射

```typescript
const PHASE_LABELS: Record<TaskPhase, string> = {
  [TaskPhase.MATERIAL_PROCESSING]: '素材处理',    // 0-25%
  [TaskPhase.MATERIAL_ANALYSIS]: '素材分析',      // 25-50%
  [TaskPhase.SCRIPT_GENERATION]: '脚本生成',      // 50-75%
  [TaskPhase.VIDEO_GENERATION]: '视频生成',       // 75-100%
};
```

---

### VideoPlayer (视频播放器)

位置: `src/components/VideoPlayer.tsx`

HTML5 视频播放器，带下载功能。

#### 功能特性

- ✅ HTML5 原生播放器
- ✅ 下载按钮
- ✅ 播放事件回调
- ✅ 错误处理

#### 使用示例

```tsx
import { VideoPlayer } from '@/components/VideoPlayer';

function TaskDetailPage() {
  const handlePlay = () => {
    console.log('视频开始播放');
  };

  return (
    <VideoPlayer
      videoUrl="https://example.com/video.mp4"
      filename="我的视频.mp4"
      onPlay={handlePlay}
    />
  );
}
```

#### Props

| 属性 | 类型 | 必需 | 说明 |
|------|------|------|------|
| videoUrl | string | ✅ | 视频 URL |
| filename | string | ❌ | 下载文件名 |
| onPlay | () => void | ❌ | 播放回调 |

#### 下载实现

```typescript
const handleDownload = () => {
  const link = document.createElement('a');
  link.href = videoUrl;
  link.download = filename || 'video.mp4';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
```

---

### Toast (通知组件)

位置: `src/components/Toast.tsx`

全局通知组件，支持多种类型。

#### 功能特性

- ✅ 4 种通知类型（success, error, warning, info）
- ✅ 自动消失（默认 3 秒）
- ✅ 手动关闭
- ✅ 动画效果
- ✅ 全局单例

#### 使用示例

```tsx
// 1. 在 App.tsx 中添加 Toast 组件
import { Toast } from '@/components/Toast';

function App() {
  return (
    <>
      {/* 其他组件 */}
      <Toast />
    </>
  );
}

// 2. 在任何组件中使用
import { useUIStore } from '@/stores/uiStore';

function SomeComponent() {
  const showToast = useUIStore((state) => state.showToast);

  const handleSuccess = () => {
    showToast({
      type: 'success',
      message: '操作成功',
      duration: 3000, // 可选，默认 3000ms
    });
  };

  const handleError = () => {
    showToast({
      type: 'error',
      message: '操作失败，请重试',
    });
  };

  return (
    <>
      <button onClick={handleSuccess}>成功</button>
      <button onClick={handleError}>错误</button>
    </>
  );
}
```

#### Toast 类型

```typescript
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastState {
  type: ToastType;
  message: string;
  duration?: number; // 默认 3000ms
}
```

---

### ErrorBoundary (错误边界)

位置: `src/components/ErrorBoundary.tsx`

React 错误边界组件，捕获组件错误。

#### 功能特性

- ✅ 捕获子组件错误
- ✅ 友好错误页面
- ✅ 错误信息展示
- ✅ 重新加载按钮

#### 使用示例

```tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      {/* 可能会抛出错误的组件 */}
      <SomeComponent />
    </ErrorBoundary>
  );
}
```

#### 错误页面

当组件抛出错误时，显示：

- 错误标题
- 错误信息
- 错误堆栈（开发环境）
- 重新加载按钮

---

## 🎣 自定义 Hooks

### useFileUpload (文件上传逻辑)

位置: `src/hooks/useFileUpload.ts`

封装文件上传逻辑的自定义 Hook。

#### 功能特性

- ✅ 文件验证（格式、大小）
- ✅ 上传进度跟踪
- ✅ 错误处理
- ✅ Toast 通知
- ✅ 状态管理集成

#### 使用示例

```tsx
import { useFileUpload } from '@/hooks/useFileUpload';

function UploadComponent() {
  const { upload, reset, isUploading, error } = useFileUpload();

  const handleFileSelect = async (file: File) => {
    const result = await upload(file);
    if (result) {
      console.log('上传成功:', result.fileId);
    }
  };

  return (
    <div>
      <input
        type="file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileSelect(file);
        }}
        disabled={isUploading}
      />
      {error && <div className="text-red-500">{error}</div>}
      {isUploading && <div>上传中...</div>}
    </div>
  );
}
```

#### 返回值

```typescript
{
  upload: (file: File) => Promise<UploadFileResponse | null>,
  reset: () => void,
  isUploading: boolean,
  error: string | null
}
```

---

### useTaskPolling (任务轮询逻辑)

位置: `src/hooks/useTaskPolling.ts`

基于 TanStack Query 的任务状态轮询 Hook。

#### 功能特性

- ✅ 自动轮询（3 秒间隔）
- ✅ 任务完成后自动停止
- ✅ 错误处理和重试
- ✅ 手动刷新
- ✅ 自动缓存

#### 使用示例

```tsx
import { useTaskPolling } from '@/hooks/useTaskPolling';
import { useParams } from 'react-router-dom';

function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();

  const { task, isLoading, isError, error, refetch } = useTaskPolling({
    taskId: taskId || '',
    enabled: !!taskId,
  });

  if (isLoading) return <div>加载中...</div>;
  if (isError) return <div>加载失败: {error?.message}</div>;
  if (!task) return <div>任务不存在</div>;

  return (
    <div>
      <h1>{task.filename}</h1>
      <p>状态: {task.status}</p>
      <p>进度: {task.progress}%</p>
      <button onClick={() => refetch()}>手动刷新</button>
    </div>
  );
}
```

#### 参数

```typescript
{
  taskId: string,
  enabled?: boolean  // 默认 true
}
```

#### 返回值

```typescript
{
  task: VideoTask | undefined,
  isLoading: boolean,
  isError: boolean,
  error: Error | null,
  refetch: () => void
}
```

#### 轮询逻辑

```typescript
refetchInterval: (query) => {
  const data = query.state.data;
  // 任务完成（completed/failed/cancelled）后停止轮询
  if (data && isTaskFinished(data.status)) {
    return false;
  }
  // 否则每 3 秒轮询一次
  return 3000;
}
```

---

## 📐 组件开发规范

### 文件命名

- 组件文件: PascalCase (如 `FileUpload.tsx`)
- Hook 文件: camelCase (如 `useFileUpload.ts`)
- 工具文件: camelCase (如 `validation.ts`)

### 组件结构

```tsx
/**
 * 组件说明文档
 */

import { /* 第三方库 */ } from 'library';
import { /* 内部导入 */ } from '@/...';

// Props 接口定义
interface ComponentProps {
  prop1: string;
  prop2?: number;
  onEvent: (param: string) => void;
}

// 组件实现
export function Component({ prop1, prop2 = 0, onEvent }: ComponentProps) {
  // Hooks (遵循 Hook 规则)
  const [state, setState] = useState(0);

  // 事件处理函数
  const handleClick = () => {
    onEvent('clicked');
  };

  // 渲染
  return (
    <div>
      {/* JSX */}
    </div>
  );
}

// 子组件（如需要）
function SubComponent() {
  return <div>Sub</div>;
}
```

### TypeScript 规范

```typescript
// ✅ 推荐：使用类型定义
interface Props {
  name: string;
  age?: number;
}

// ❌ 避免：使用 any
const data: any = {};

// ✅ 推荐：明确类型
const data: VideoTask = {};

// ✅ 推荐：使用泛型
function useQuery<T>(key: string): T {
  // ...
}
```

### 状态管理规范

```typescript
// ✅ 推荐：使用 Zustand store
const showToast = useUIStore((state) => state.showToast);

// ✅ 推荐：使用 TanStack Query 获取服务端数据
const { data } = useQuery({
  queryKey: ['tasks'],
  queryFn: getTasks,
});

// ❌ 避免：本地状态管理服务端数据
const [tasks, setTasks] = useState([]); // 不推荐
```

### 样式规范

```tsx
// ✅ 推荐：使用 Tailwind CSS
<div className="flex items-center gap-4 p-6 bg-card rounded-lg">
  <h1 className="text-2xl font-bold">Title</h1>
</div>

// ✅ 推荐：使用 cn() 工具合并类名
import { cn } from '@/lib/utils';

<div className={cn(
  'base-class',
  isActive && 'active-class',
  className
)}>
  Content
</div>

// ❌ 避免：内联样式
<div style={{ color: 'red' }}>Bad</div>

// ❌ 避免：传统 CSS 文件（shadcn/ui 除外）
import './styles.css';
```

### 错误处理规范

```typescript
// ✅ 推荐：Try-catch + Toast
try {
  const result = await someAsyncOperation();
  showToast({ type: 'success', message: '操作成功' });
} catch (err) {
  const errorMessage = err instanceof Error
    ? err.message
    : '操作失败';
  showToast({ type: 'error', message: errorMessage });
}

// ✅ 推荐：使用 ErrorBoundary 包裹
<ErrorBoundary>
  <Component />
</ErrorBoundary>
```

---

## 🔗 相关资源

- [shadcn/ui 文档](https://ui.shadcn.com/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [React Hooks 文档](https://react.dev/reference/react)
- [TanStack Query 文档](https://tanstack.com/query/latest)
- [Zustand 文档](https://docs.pmnd.rs/zustand/)

---

**最后更新**: 2025-01-27
