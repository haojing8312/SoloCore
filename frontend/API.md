# TextLoom Frontend - API 文档

本文档描述了 TextLoom Web Frontend 与后端 API 的交互方式。

## 📋 目录

- [API 基础配置](#api-基础配置)
- [认证与授权](#认证与授权)
- [API 端点](#api-端点)
- [数据模型](#数据模型)
- [错误处理](#错误处理)
- [示例代码](#示例代码)

## 🔧 API 基础配置

### 基础 URL

```typescript
// 配置位置: src/utils/constants.ts
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:48095',
  TIMEOUT: 30000, // 30 秒
  POLLING_INTERVAL: 3000, // 3 秒
} as const;
```

### Axios 实例配置

```typescript
// 位置: src/services/api.ts
const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### 请求拦截器

```typescript
// 自动添加通用 headers
api.interceptors.request.use(
  (config) => {
    // 未来可在此添加 JWT token
    return config;
  },
  (error) => Promise.reject(error)
);
```

### 响应拦截器

```typescript
// 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 未授权 - 跳转登录
          break;
        case 403:
          // 禁止访问
          break;
        case 404:
          // 资源不存在
          break;
        case 500:
        case 502:
        case 503:
          // 服务器错误
          break;
      }
    }
    return Promise.reject(error);
  }
);
```

## 🔐 认证与授权

### 当前状态

目前应用**不需要认证**，所有 API 端点都是公开的。

### 未来计划

当后端实现 JWT 认证后，将添加：

```typescript
// 请求拦截器添加 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器处理 token 刷新
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token 过期，尝试刷新
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        // 刷新 token 逻辑
      }
    }
    return Promise.reject(error);
  }
);
```

## 📡 API 端点

### 1. 文件上传

#### `POST /api/files/upload`

上传文档文件用于视频生成。

**请求体**: `multipart/form-data`

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | File | ✅ | 文档文件 (.md/.markdown/.txt) |

**响应**: `200 OK`

```typescript
{
  success: true,
  data: {
    fileId: string,      // 文件 ID
    filename: string,    // 原始文件名
    size: number,        // 文件大小（字节）
    uploadedAt: string   // 上传时间（ISO 8601）
  },
  message: "文件上传成功"
}
```

**实现位置**: `src/services/fileService.ts`

```typescript
export async function uploadFile(
  file: File,
  onProgress?: UploadProgressCallback
): Promise<UploadFileResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadFileResponse>(
    '/api/files/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    }
  );

  return response.data;
}
```

---

### 2. 创建任务

#### `POST /api/tasks`

创建新的视频生成任务。

**请求体**: `application/json`

```typescript
{
  fileId: string,              // 文件 ID
  subtitleTemplate: string     // 字幕模板 (hype | minimalist | explosive | vibrant)
}
```

**响应**: `201 Created`

```typescript
{
  success: true,
  data: {
    taskId: string,      // 任务 ID
    status: "pending"    // 初始状态
  },
  message: "任务创建成功"
}
```

**实现位置**: `src/services/taskService.ts`

```typescript
export async function createTask(
  request: CreateTaskRequest
): Promise<ApiResponse<CreateTaskResponse>> {
  const response = await api.post<ApiResponse<CreateTaskResponse>>(
    '/api/tasks',
    request
  );
  return response.data;
}
```

---

### 3. 查询任务状态

#### `GET /api/tasks/:taskId`

获取任务详细信息和当前状态。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| taskId | string | 任务 ID |

**响应**: `200 OK`

```typescript
{
  success: true,
  data: {
    id: string,
    filename: string,
    status: TaskStatus,           // pending | processing | completed | failed | cancelled
    progress: number,             // 0-100
    currentPhase?: TaskPhase,     // material_processing | material_analysis | script_generation | video_generation
    subtitleTemplate: string,
    videoUrl?: string,            // 仅 completed 状态有值
    errorMessage?: string,        // 仅 failed 状态有值
    createdAt: string,
    updatedAt: string,
    startedAt?: string,
    completedAt?: string
  }
}
```

**实现位置**: `src/services/taskService.ts` + `src/hooks/useTaskPolling.ts`

```typescript
// 服务层
export async function getTaskStatus(
  taskId: string
): Promise<ApiResponse<VideoTask>> {
  const response = await api.get<ApiResponse<VideoTask>>(
    `/api/tasks/${taskId}`
  );
  return response.data;
}

// Hook 层（自动轮询）
export function useTaskPolling({
  taskId,
  enabled = true,
}: UseTaskPollingOptions) {
  const query = useQuery({
    queryKey: ['task', taskId],
    queryFn: async () => {
      const response = await getTaskStatus(taskId);
      if (response.success && response.data) {
        return response.data;
      }
      throw new Error(response.message || '获取任务状态失败');
    },
    enabled: !!taskId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // 任务完成后停止轮询
      if (data && isTaskFinished(data.status)) {
        return false;
      }
      return API_CONFIG.POLLING_INTERVAL; // 3 秒
    },
  });

  return {
    task: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
```

---

### 4. 查询任务列表

#### `GET /api/tasks`

获取任务列表，支持筛选和排序。

**查询参数**:

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | TaskStatus \| 'all' | ❌ | all | 状态筛选 |
| page | number | ❌ | 1 | 页码 |
| pageSize | number | ❌ | 20 | 每页数量 |
| sortBy | string | ❌ | createdAt | 排序字段 |
| order | 'asc' \| 'desc' | ❌ | desc | 排序方向 |

**响应**: `200 OK`

```typescript
{
  success: true,
  data: {
    tasks: VideoTask[],
    total: number,
    page: number,
    pageSize: number,
    totalPages: number
  }
}
```

**实现位置**: `src/services/taskService.ts`

```typescript
export async function getTasks(
  params?: GetTasksRequest
): Promise<ApiResponse<GetTasksResponse>> {
  const response = await api.get<ApiResponse<GetTasksResponse>>(
    '/api/tasks',
    { params }
  );
  return response.data;
}
```

---

### 5. 取消任务

#### `POST /api/tasks/:taskId/cancel`

取消正在处理中的任务。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| taskId | string | 任务 ID |

**响应**: `200 OK`

```typescript
{
  success: true,
  message: "任务已取消"
}
```

**实现位置**: `src/services/taskService.ts`

```typescript
export async function cancelTask(
  taskId: string
): Promise<ApiResponse<void>> {
  const response = await api.post<ApiResponse<void>>(
    `/api/tasks/${taskId}/cancel`
  );
  return response.data;
}
```

---

### 6. 删除任务

#### `DELETE /api/tasks/:taskId`

删除已完成、失败或已取消的任务。

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| taskId | string | 任务 ID |

**响应**: `200 OK`

```typescript
{
  success: true,
  message: "任务已删除"
}
```

**实现位置**: `src/services/taskService.ts`

```typescript
export async function deleteTask(
  taskId: string
): Promise<ApiResponse<void>> {
  const response = await api.delete<ApiResponse<void>>(
    `/api/tasks/${taskId}`
  );
  return response.data;
}
```

---

### 7. 获取统计数据

#### `GET /api/stats`

获取任务统计和分析数据。

**响应**: `200 OK`

```typescript
{
  success: true,
  data: {
    totalTasks: number,              // 总任务数
    todayTasks: number,              // 今日生成数
    successRate: number,             // 成功率 (0-1)
    avgDuration: number,             // 平均耗时（秒）
    statusDistribution: {            // 状态分布
      pending: number,
      processing: number,
      completed: number,
      failed: number,
      cancelled: number
    },
    recentTrend: Array<{             // 最近 7 天趋势
      date: string,                  // YYYY-MM-DD
      count: number                  // 当日生成数
    }>
  }
}
```

**实现位置**: `src/services/statsService.ts`

```typescript
export async function getStats(): Promise<ApiResponse<StatsData>> {
  const response = await api.get<ApiResponse<StatsData>>('/api/stats');
  return response.data;
}
```

---

## 📊 数据模型

### TaskStatus (任务状态)

```typescript
export enum TaskStatus {
  PENDING = 'pending',         // 等待中
  PROCESSING = 'processing',   // 处理中
  COMPLETED = 'completed',     // 已完成
  FAILED = 'failed',           // 失败
  CANCELLED = 'cancelled'      // 已取消
}
```

### TaskPhase (任务阶段)

```typescript
export enum TaskPhase {
  MATERIAL_PROCESSING = 'material_processing',   // 素材处理 (0-25%)
  MATERIAL_ANALYSIS = 'material_analysis',       // 素材分析 (25-50%)
  SCRIPT_GENERATION = 'script_generation',       // 脚本生成 (50-75%)
  VIDEO_GENERATION = 'video_generation'          // 视频生成 (75-100%)
}
```

### SubtitleTemplate (字幕模板)

```typescript
export enum SubtitleTemplate {
  HYPE = 'hype',               // 动感活力
  MINIMALIST = 'minimalist',   // 简约优雅
  EXPLOSIVE = 'explosive',     // 爆炸效果
  VIBRANT = 'vibrant'          // 活力四射
}
```

### VideoTask (视频任务)

```typescript
export interface VideoTask {
  id: string;
  filename: string;
  status: TaskStatus;
  progress: number;                    // 0-100
  currentPhase?: TaskPhase;
  subtitleTemplate: SubtitleTemplate;
  videoUrl?: string;
  errorMessage?: string;
  createdAt: string;                   // ISO 8601
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
}
```

### ApiResponse (统一响应格式)

```typescript
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: ErrorDetail[];
}

export interface ErrorDetail {
  field?: string;
  message: string;
  code?: string;
}
```

---

## ⚠️ 错误处理

### 错误响应格式

```typescript
{
  success: false,
  message: "错误描述",
  errors: [
    {
      field: "fileId",
      message: "文件不存在",
      code: "FILE_NOT_FOUND"
    }
  ]
}
```

### HTTP 状态码

| 状态码 | 说明 | 处理方式 |
|--------|------|----------|
| 200 | 成功 | 正常处理 |
| 201 | 创建成功 | 正常处理 |
| 400 | 请求参数错误 | 显示错误信息 |
| 401 | 未授权 | 跳转登录页 |
| 403 | 禁止访问 | 显示权限错误 |
| 404 | 资源不存在 | 显示 404 页面 |
| 422 | 验证失败 | 显示字段错误 |
| 500 | 服务器错误 | 显示通用错误 |
| 502 | 网关错误 | 显示服务不可用 |
| 503 | 服务不可用 | 显示维护提示 |

### 错误处理示例

```typescript
// useFileUpload.ts
export function useFileUpload() {
  const upload = async (file: File) => {
    try {
      const validation = validateFile(file);
      if (!validation.valid) {
        setError(validation.errors[0]);
        showToast({
          type: 'error',
          message: validation.errors[0],
        });
        return null;
      }

      setIsUploading(true);
      const response = await uploadFile(file, setUploadProgress);

      if (response.success && response.data) {
        setUploadedFileId(response.data.fileId);
        showToast({
          type: 'success',
          message: '文件上传成功',
        });
        return response.data;
      }
    } catch (err) {
      const errorMessage = err instanceof Error
        ? err.message
        : '文件上传失败';
      setError(errorMessage);
      showToast({
        type: 'error',
        message: errorMessage,
      });
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  return { upload, reset, isUploading, error };
}
```

---

## 💡 示例代码

### 完整的任务创建流程

```typescript
import { useFileUpload } from '@/hooks/useFileUpload';
import { createTask } from '@/services/taskService';
import { useTaskStore } from '@/stores/taskStore';
import { useUIStore } from '@/stores/uiStore';
import { useNavigate } from 'react-router-dom';

function CreateTaskExample() {
  const navigate = useNavigate();
  const { upload } = useFileUpload();
  const { uploadedFileId, selectedTemplate } = useTaskStore();
  const { showToast } = useUIStore();

  const handleCreateTask = async () => {
    // 1. 验证输入
    if (!uploadedFileId || !selectedTemplate) {
      showToast({
        type: 'error',
        message: '请先上传文件并选择模板',
      });
      return;
    }

    try {
      // 2. 创建任务
      const response = await createTask({
        fileId: uploadedFileId,
        subtitleTemplate: selectedTemplate,
      });

      if (response.success && response.data) {
        // 3. 跳转到任务详情页
        navigate(`/tasks/${response.data.taskId}`);

        showToast({
          type: 'success',
          message: '任务创建成功',
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error
        ? err.message
        : '任务创建失败';
      showToast({
        type: 'error',
        message: errorMessage,
      });
    }
  };

  return (
    <button onClick={handleCreateTask}>
      开始生成
    </button>
  );
}
```

### 使用 TanStack Query 进行数据获取

```typescript
import { useQuery } from '@tanstack/react-query';
import { getTasks } from '@/services/taskService';
import { TaskStatus } from '@/types';

function TaskListExample() {
  const [selectedStatus, setSelectedStatus] = useState<TaskStatus | 'all'>('all');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['tasks', selectedStatus],
    queryFn: async () => {
      const response = await getTasks({
        status: selectedStatus,
        sortBy: 'createdAt',
        order: 'desc',
      });

      if (response.success && response.data) {
        return response.data;
      }

      throw new Error(response.message || '获取任务列表失败');
    },
  });

  if (isLoading) return <div>加载中...</div>;
  if (isError) return <div>加载失败</div>;

  return (
    <div>
      {data?.tasks.map((task) => (
        <div key={task.id}>{task.filename}</div>
      ))}
    </div>
  );
}
```

---

## 🔗 相关资源

- [TypeScript 类型定义](./src/types/)
- [API 服务实现](./src/services/)
- [自定义 Hooks](./src/hooks/)
- [Zustand 状态管理](./src/stores/)
- [后端 API 文档](../textloom/docs/API.md)

---

**最后更新**: 2025-01-27
