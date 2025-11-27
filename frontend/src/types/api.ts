/**
 * API Request/Response type definitions
 */

import type { VideoTask, TaskStatus, SubtitleTemplate, ScriptStyle } from './task';

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

/**
 * 文件上传响应
 */
export interface UploadFileResponse extends ApiResponse<{
  fileId: string;
  filename: string;
  size: number;
  url: string;
}> {}

/**
 * 任务创建请求
 */
export interface CreateTaskRequest {
  fileId: string;
  subtitleTemplate: SubtitleTemplate;
  scriptStyle?: ScriptStyle;
  multiVideoCount?: number;
}

/**
 * 任务创建响应
 */
export interface CreateTaskResponse extends ApiResponse<{
  taskId: string;
  status: TaskStatus;
}> {}

/**
 * 任务状态查询响应
 */
export interface GetTaskStatusResponse extends ApiResponse<VideoTask> {}

/**
 * 任务列表查询请求
 */
export interface GetTasksRequest {
  status?: TaskStatus | 'all';
  page?: number;
  pageSize?: number;
  sortBy?: 'createdAt' | 'updatedAt';
  order?: 'asc' | 'desc';
}

/**
 * 任务列表查询响应
 */
export interface GetTasksResponse extends ApiResponse<{
  tasks: VideoTask[];
  total: number;
  page: number;
  pageSize: number;
}> {}

/**
 * 任务取消响应
 */
export interface CancelTaskResponse extends ApiResponse {}

/**
 * 任务删除响应
 */
export interface DeleteTaskResponse extends ApiResponse {}

/**
 * 统计数据
 */
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

/**
 * 统计数据查询响应
 */
export interface GetStatsResponse extends ApiResponse<StatsData> {}

/**
 * Type guard for error response
 */
export function isErrorResponse(response: unknown): response is ErrorResponse {
  return (
    typeof response === 'object' &&
    response !== null &&
    'success' in response &&
    response.success === false
  );
}
