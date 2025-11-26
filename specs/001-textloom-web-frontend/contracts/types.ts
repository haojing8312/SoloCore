/**
 * TextLoom Frontend TypeScript Type Definitions
 *
 * 此文件定义前端与后端 API 通信的所有类型
 * 生成自: contracts/api.yaml 和 data-model.md
 *
 * @version 1.0.0
 * @date 2025-11-26
 */

// ============================================================================
// Core Entities
// ============================================================================

/**
 * 任务状态枚举
 */
export enum TaskStatus {
  PENDING = 'pending',         // 待处理
  PROCESSING = 'processing',   // 处理中
  COMPLETED = 'completed',     // 已完成
  FAILED = 'failed',           // 失败
  CANCELLED = 'cancelled'      // 已取消
}

/**
 * 任务处理阶段枚举
 */
export enum TaskPhase {
  MATERIAL_PROCESSING = 'material_processing',  // 素材处理 (0-25%)
  MATERIAL_ANALYSIS = 'material_analysis',      // 素材分析 (25-50%)
  SCRIPT_GENERATION = 'script_generation',      // 脚本生成 (50-75%)
  VIDEO_GENERATION = 'video_generation'         // 视频生成 (75-100%)
}

/**
 * 字幕模板类型
 */
export type SubtitleTemplate = 'hype' | 'minimalist' | 'explosive' | 'vibrant';

/**
 * 脚本风格类型
 */
export type ScriptStyle = 'default';

/**
 * 视频任务实体
 */
export interface VideoTask {
  // 基础字段
  id: string;
  filename: string;

  // 状态字段
  status: TaskStatus;
  progress: number;
  currentPhase?: TaskPhase;

  // 配置字段
  subtitleTemplate: SubtitleTemplate;
  scriptStyle: ScriptStyle;

  // 结果字段
  videoUrl?: string;
  scriptContent?: string;
  thumbnailUrl?: string;

  // 错误字段
  errorMessage?: string;
  errorCode?: string;

  // 时间字段
  createdAt: string;
  updatedAt: string;
  completedAt?: string;

  // 元数据
  duration?: number;
  fileSize?: number;
  estimatedTime?: number;
}

/**
 * 上传文件实体
 */
export interface UploadedFile {
  id: string;
  filename: string;
  size: number;
  mimeType: string;
  uploadedAt: string;
  url: string;
  checksum?: string;
}

/**
 * 字幕模板信息
 */
export interface SubtitleTemplateInfo {
  id: SubtitleTemplate;
  name: string;
  description: string;
  previewImage: string;
  example?: string;
}

/**
 * 脚本内容实体
 */
export interface ScriptContent {
  taskId: string;
  scriptText: string;
  style: ScriptStyle;
  generatedAt: string;
  wordCount?: number;
  estimatedDuration?: number;
  segments?: ScriptSegment[];
}

/**
 * 脚本段落
 */
export interface ScriptSegment {
  index: number;
  text: string;
  duration: number;
  timestamp: number;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * 标准 API 响应包装器
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
}

/**
 * 错误响应
 */
export interface ErrorResponse {
  success: false;
  message: string;
  code?: string;
  details?: unknown;
}

// --- 文件上传 ---

export interface UploadFileResponse extends ApiResponse<{
  fileId: string;
  filename: string;
  size: number;
  url: string;
}> {}

// --- 任务创建 ---

export interface CreateTaskRequest {
  fileId: string;
  subtitleTemplate: SubtitleTemplate;
  scriptStyle?: ScriptStyle;
  multiVideoCount?: number;
}

export interface CreateTaskResponse extends ApiResponse<{
  taskId: string;
  status: TaskStatus;
}> {}

// --- 任务状态查询 ---

export interface GetTaskStatusResponse extends ApiResponse<VideoTask> {}

// --- 任务列表查询 ---

export interface GetTasksRequest {
  status?: TaskStatus | 'all';
  page?: number;
  pageSize?: number;
  sortBy?: 'createdAt' | 'updatedAt';
  order?: 'asc' | 'desc';
}

export interface GetTasksResponse extends ApiResponse<{
  tasks: VideoTask[];
  total: number;
  page: number;
  pageSize: number;
}> {}

// --- 任务取消 ---

export interface CancelTaskResponse extends ApiResponse {}

// --- 任务删除 ---

export interface DeleteTaskResponse extends ApiResponse {}

// --- 统计数据 ---

export interface StatsData {
  totalTasks: number;
  todayTasks: number;
  successRate: number;
  avgDuration: number;
  statusDistribution: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    cancelled: number;
  };
  recentTrend: Array<{
    date: string;
    count: number;
  }>;
}

export interface GetStatsResponse extends ApiResponse<StatsData> {}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * 错误状态
 */
export interface ErrorState {
  message: string;
  code?: string;
  details?: unknown;
}

/**
 * Toast 通知状态
 */
export interface ToastState {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

/**
 * 全局 UI 状态
 */
export interface UIStore {
  isGlobalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  error: ErrorState | null;
  setError: (error: ErrorState | null) => void;

  toast: ToastState | null;
  showToast: (toast: ToastState) => void;
  hideToast: () => void;
}

/**
 * 任务状态 Store
 */
export interface TaskStore {
  currentTask: VideoTask | null;
  setCurrentTask: (task: VideoTask | null) => void;

  selectedTemplate: SubtitleTemplate | null;
  setSelectedTemplate: (template: SubtitleTemplate) => void;

  uploadProgress: number;
  setUploadProgress: (progress: number) => void;
}

// ============================================================================
// Validation Types
// ============================================================================

/**
 * 验证结果
 */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * 文件验证配置
 */
export interface FileValidation {
  allowedExtensions: string[];
  maxSize: number;
  mimeTypes: string[];
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * 分页参数
 */
export interface PaginationParams {
  page: number;
  pageSize: number;
  total?: number;
}

/**
 * 排序参数
 */
export interface SortParams<T = string> {
  sortBy: T;
  order: 'asc' | 'desc';
}

/**
 * 文件上传进度回调
 */
export type UploadProgressCallback = (progress: number) => void;

/**
 * 轮询配置
 */
export interface PollingConfig {
  interval: number;
  enabled: boolean;
  onUpdate?: (data: VideoTask) => void;
  onError?: (error: Error) => void;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * API 配置常量
 */
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:48095',
  TIMEOUT: 30000,
  POLLING_INTERVAL: 3000,
} as const;

/**
 * 文件上传配置常量
 */
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 10 * 1024 * 1024,
  ALLOWED_EXTENSIONS: ['.md', '.markdown', '.txt'],
  CHUNK_SIZE: 1024 * 1024,
} as const;

/**
 * 任务配置常量
 */
export const TASK_CONFIG = {
  MULTI_VIDEO_COUNT: 1,
  DEFAULT_SCRIPT_STYLE: 'default' as ScriptStyle,
} as const;

/**
 * UI 配置常量
 */
export const UI_CONFIG = {
  TOAST_DURATION: 3000,
  DEBOUNCE_DELAY: 300,
  ITEMS_PER_PAGE: 20,
} as const;

/**
 * 预定义字幕模板列表
 */
export const SUBTITLE_TEMPLATES: SubtitleTemplateInfo[] = [
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
] as const;

// ============================================================================
// Type Guards
// ============================================================================

/**
 * 检查是否为错误响应
 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    response.success === false
  );
}

/**
 * 检查任务是否可以取消
 */
export function canCancelTask(status: TaskStatus): boolean {
  return status === TaskStatus.PROCESSING;
}

/**
 * 检查任务是否可以删除
 */
export function canDeleteTask(status: TaskStatus): boolean {
  return [
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED
  ].includes(status);
}

/**
 * 检查任务是否可以重试
 */
export function canRetryTask(status: TaskStatus): boolean {
  return status === TaskStatus.FAILED;
}

/**
 * 检查任务是否正在进行
 */
export function isTaskInProgress(status: TaskStatus): boolean {
  return [TaskStatus.PENDING, TaskStatus.PROCESSING].includes(status);
}

/**
 * 检查任务是否已结束
 */
export function isTaskFinished(status: TaskStatus): boolean {
  return [
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED
  ].includes(status);
}
