# Data Model: TextLoom Web Frontend

**Date**: 2025-11-26
**Branch**: `001-textloom-web-frontend`

## Purpose

本文档定义 TextLoom Web Frontend 的前端数据模型和 TypeScript 类型定义,作为与后端 API 通信的契约基础。

---

## 1. Core Entities

### 1.1 VideoTask (视频任务)

**用途**: 表示一次视频生成任务的完整生命周期

**TypeScript 定义**:
```typescript
interface VideoTask {
  // 基础字段
  id: string;                      // 任务唯一标识 (UUID)
  filename: string;                // 上传的文件名 (如 "example.md")

  // 状态字段
  status: TaskStatus;              // 任务状态
  progress: number;                // 进度百分比 (0-100)
  currentPhase?: TaskPhase;        // 当前处理阶段

  // 配置字段
  subtitleTemplate: SubtitleTemplate;  // 字幕模板 (hype/minimalist/explosive/vibrant)
  scriptStyle: ScriptStyle;        // 脚本风格 (默认 "default")

  // 结果字段
  videoUrl?: string;               // 生成的视频 URL (completed 状态时存在)
  scriptContent?: string;          // 生成的脚本内容
  thumbnailUrl?: string;           // 视频缩略图 URL

  // 错误字段
  errorMessage?: string;           // 错误信息 (failed 状态时存在)
  errorCode?: string;              // 错误代码

  // 时间字段
  createdAt: string;               // 创建时间 (ISO 8601 格式)
  updatedAt: string;               // 更新时间 (ISO 8601 格式)
  completedAt?: string;            // 完成时间 (completed 状态时存在)

  // 元数据
  duration?: number;               // 视频时长 (秒)
  fileSize?: number;               // 视频文件大小 (字节)
  estimatedTime?: number;          // 预计剩余时间 (秒)
}
```

**状态枚举**:
```typescript
enum TaskStatus {
  PENDING = 'pending',             // 待处理 (任务已创建,等待执行)
  PROCESSING = 'processing',       // 处理中 (正在生成视频)
  COMPLETED = 'completed',         // 已完成 (视频生成成功)
  FAILED = 'failed',               // 失败 (生成过程中出错)
  CANCELLED = 'cancelled'          // 已取消 (用户主动取消)
}
```

**处理阶段枚举**:
```typescript
enum TaskPhase {
  MATERIAL_PROCESSING = 'material_processing',    // 素材处理 (0-25%)
  MATERIAL_ANALYSIS = 'material_analysis',        // 素材分析 (25-50%)
  SCRIPT_GENERATION = 'script_generation',        // 脚本生成 (50-75%)
  VIDEO_GENERATION = 'video_generation'           // 视频生成 (75-100%)
}
```

**状态流转图**:
```
pending → processing → completed
              ↓
            failed
              ↓
          cancelled
```

---

### 1.2 UploadedFile (上传文件)

**用途**: 表示用户上传的 Markdown 文件信息

**TypeScript 定义**:
```typescript
interface UploadedFile {
  id: string;                      // 文件唯一标识
  filename: string;                // 文件名 (如 "example.md")
  size: number;                    // 文件大小 (字节)
  mimeType: string;                // MIME 类型 (text/markdown)
  uploadedAt: string;              // 上传时间 (ISO 8601 格式)
  url: string;                     // 文件 URL (用于下载或预览)
  checksum?: string;               // 文件校验和 (MD5/SHA256)
}
```

**文件验证规则**:
```typescript
interface FileValidation {
  allowedExtensions: string[];     // ['.md', '.markdown', '.txt']
  maxSize: number;                 // 10 * 1024 * 1024 (10MB)
  mimeTypes: string[];             // ['text/markdown', 'text/plain']
}
```

---

### 1.3 SubtitleTemplate (字幕模板)

**用途**: 表示可选的字幕样式

**TypeScript 定义**:
```typescript
type SubtitleTemplate = 'hype' | 'minimalist' | 'explosive' | 'vibrant';

interface SubtitleTemplateInfo {
  id: SubtitleTemplate;            // 模板标识
  name: string;                    // 显示名称 (如 "Hype")
  description: string;             // 模板描述
  previewImage: string;            // 预览图 URL
  example?: string;                // 示例视频 URL
}
```

**预定义模板**:
```typescript
const SUBTITLE_TEMPLATES: SubtitleTemplateInfo[] = [
  {
    id: 'hype',
    name: 'Hype',
    description: '动感活力,适合年轻受众',
    previewImage: '/assets/templates/hype-preview.png'
  },
  {
    id: 'minimalist',
    name: 'Minimalist',
    description: '极简风格,专业简洁',
    previewImage: '/assets/templates/minimalist-preview.png'
  },
  {
    id: 'explosive',
    name: 'Explosive',
    description: '爆炸效果,吸引注意力',
    previewImage: '/assets/templates/explosive-preview.png'
  },
  {
    id: 'vibrant',
    name: 'Vibrant',
    description: '多彩活泼,色彩丰富',
    previewImage: '/assets/templates/vibrant-preview.png'
  }
];
```

---

### 1.4 ScriptContent (脚本内容)

**用途**: 表示 AI 生成的视频脚本

**TypeScript 定义**:
```typescript
interface ScriptContent {
  taskId: string;                  // 关联的任务 ID
  scriptText: string;              // 脚本文本内容
  style: ScriptStyle;              // 脚本风格
  generatedAt: string;             // 生成时间 (ISO 8601 格式)
  wordCount?: number;              // 字数
  estimatedDuration?: number;      // 预计视频时长 (秒)
  segments?: ScriptSegment[];      // 脚本分段
}

type ScriptStyle = 'default';      // 当前版本只支持 default

interface ScriptSegment {
  index: number;                   // 段落索引
  text: string;                    // 段落文本
  duration: number;                // 段落时长 (秒)
  timestamp: number;               // 起始时间戳 (秒)
}
```

---

## 2. API Request/Response Models

### 2.1 文件上传请求

```typescript
interface UploadFileRequest {
  file: File;                      // 文件对象 (FormData)
}

interface UploadFileResponse {
  success: boolean;
  data: {
    fileId: string;                // 上传成功后的文件 ID
    filename: string;
    size: number;
    url: string;
  };
  message?: string;
}
```

---

### 2.2 创建任务请求

```typescript
interface CreateTaskRequest {
  fileId: string;                  // 上传文件的 ID
  subtitleTemplate: SubtitleTemplate;  // 字幕模板
  scriptStyle?: ScriptStyle;       // 脚本风格 (默认 "default")
  multiVideoCount?: number;        // 固定为 1 (当前版本)
}

interface CreateTaskResponse {
  success: boolean;
  data: {
    taskId: string;                // 创建成功的任务 ID
    status: TaskStatus;
  };
  message?: string;
}
```

---

### 2.3 查询任务状态请求

```typescript
interface GetTaskStatusRequest {
  taskId: string;                  // 路径参数
}

interface GetTaskStatusResponse {
  success: boolean;
  data: VideoTask;                 // 完整的任务对象
}
```

---

### 2.4 查询任务列表请求

```typescript
interface GetTasksRequest {
  status?: TaskStatus | 'all';     // 状态筛选 (可选)
  page?: number;                   // 页码 (默认 1)
  pageSize?: number;               // 每页数量 (默认 20)
  sortBy?: 'createdAt' | 'updatedAt';  // 排序字段 (默认 createdAt)
  order?: 'asc' | 'desc';          // 排序方向 (默认 desc)
}

interface GetTasksResponse {
  success: boolean;
  data: {
    tasks: VideoTask[];            // 任务列表
    total: number;                 // 总数
    page: number;                  // 当前页
    pageSize: number;              // 每页数量
  };
}
```

---

### 2.5 取消任务请求

```typescript
interface CancelTaskRequest {
  taskId: string;                  // 路径参数
}

interface CancelTaskResponse {
  success: boolean;
  message?: string;
}
```

---

### 2.6 删除任务请求

```typescript
interface DeleteTaskRequest {
  taskId: string;                  // 路径参数
}

interface DeleteTaskResponse {
  success: boolean;
  message?: string;
}
```

---

### 2.7 查询统计数据请求

```typescript
interface GetStatsRequest {
  // 无参数 (查询全部统计)
}

interface GetStatsResponse {
  success: boolean;
  data: {
    totalTasks: number;            // 总任务数
    todayTasks: number;            // 今日生成数
    successRate: number;           // 成功率 (0-100)
    avgDuration: number;           // 平均耗时 (秒)
    statusDistribution: {          // 状态分布
      pending: number;
      processing: number;
      completed: number;
      failed: number;
      cancelled: number;
    };
    recentTrend: {                 // 最近 7 天趋势
      date: string;                // 日期 (YYYY-MM-DD)
      count: number;               // 任务数量
    }[];
  };
}
```

---

## 3. UI State Models

### 3.1 全局 UI 状态 (Zustand Store)

```typescript
interface UIStore {
  // Loading 状态
  isGlobalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  // 错误提示
  error: ErrorState | null;
  setError: (error: ErrorState | null) => void;

  // Toast 通知
  toast: ToastState | null;
  showToast: (toast: ToastState) => void;
  hideToast: () => void;
}

interface ErrorState {
  message: string;                 // 错误消息
  code?: string;                   // 错误代码
  details?: unknown;               // 错误详情
}

interface ToastState {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;               // 显示时长 (毫秒,默认 3000)
}
```

---

### 3.2 任务状态 (Zustand Store)

```typescript
interface TaskStore {
  // 当前任务
  currentTask: VideoTask | null;
  setCurrentTask: (task: VideoTask | null) => void;

  // 选中的字幕模板
  selectedTemplate: SubtitleTemplate | null;
  setSelectedTemplate: (template: SubtitleTemplate) => void;

  // 上传进度
  uploadProgress: number;
  setUploadProgress: (progress: number) => void;
}
```

---

## 4. Validation Rules

### 4.1 文件验证

```typescript
function validateFile(file: File): ValidationResult {
  const errors: string[] = [];

  // 文件类型检查
  const allowedExtensions = ['.md', '.markdown', '.txt'];
  const extension = file.name.substring(file.name.lastIndexOf('.'));
  if (!allowedExtensions.includes(extension.toLowerCase())) {
    errors.push('仅支持 Markdown (.md) 文件');
  }

  // 文件大小检查
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    errors.push('文件大小不能超过 10MB');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
}
```

---

### 4.2 任务状态转换规则

```typescript
function canCancelTask(status: TaskStatus): boolean {
  return status === TaskStatus.PROCESSING;
}

function canDeleteTask(status: TaskStatus): boolean {
  return [
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED
  ].includes(status);
}

function canRetryTask(status: TaskStatus): boolean {
  return status === TaskStatus.FAILED;
}
```

---

## 5. Constants

```typescript
// API 配置
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:48095',
  TIMEOUT: 30000,                  // 30 秒超时
  POLLING_INTERVAL: 3000,          // 3 秒轮询间隔
};

// 文件上传配置
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_EXTENSIONS: ['.md', '.markdown', '.txt'],
  CHUNK_SIZE: 1024 * 1024,         // 1MB 分片上传 (可选)
};

// 任务配置
export const TASK_CONFIG = {
  MULTI_VIDEO_COUNT: 1,            // 固定单视频
  DEFAULT_SCRIPT_STYLE: 'default' as ScriptStyle,
};

// UI 配置
export const UI_CONFIG = {
  TOAST_DURATION: 3000,            // 3 秒
  DEBOUNCE_DELAY: 300,             // 300ms 防抖
  ITEMS_PER_PAGE: 20,              // 每页 20 条
};
```

---

## Summary

数据模型定义完成,涵盖:
- **4 个核心实体**: VideoTask, UploadedFile, SubtitleTemplate, ScriptContent
- **7 组 API 契约**: 文件上传、任务创建、状态查询、列表查询、取消、删除、统计
- **2 个 UI 状态模型**: UIStore, TaskStore
- **验证规则**: 文件验证、状态转换规则
- **常量配置**: API、上传、任务、UI 配置

下一步: 生成 API contracts (OpenAPI 规范)。
