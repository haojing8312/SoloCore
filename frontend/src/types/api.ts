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
 * 单个上传文件信息
 */
export interface UploadedFileItem {
  filename: string;
  url: string;
  object_key: string;
  media_type: 'markdown' | 'image' | 'video' | 'unknown';
  size: number;
  success: boolean;
}

/**
 * 文件上传统计信息
 */
export interface UploadStats {
  markdown_count: number;
  image_count: number;
  video_count: number;
  total_size: number;
}

/**
 * 文件上传响应（批量上传）
 */
export interface UploadFileResponse {
  items: UploadedFileItem[];
  stats: UploadStats;
  warnings: string[];
}

/**
 * 任务创建请求
 */
export interface CreateTaskRequest {
  fileId: string;  // 前端使用，对应后端的 object_key
  subtitleTemplate: SubtitleTemplate;
  scriptStyle?: ScriptStyle;
  multiVideoCount?: number;
}

/**
 * 任务创建响应
 */
export type CreateTaskResponse = ApiResponse<{
  taskId: string;
  status: TaskStatus;
}>;

/**
 * 任务状态查询响应 - 后端直接返回 Task 对象，不包装
 */
export type GetTaskStatusResponse = VideoTask;

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
 * 任务列表查询响应 - 后端直接返回 Task 数组，不包装
 */
export type GetTasksResponse = VideoTask[];

/**
 * 任务取消响应
 */
export type CancelTaskResponse = ApiResponse;

/**
 * 任务删除响应
 */
export type DeleteTaskResponse = ApiResponse;

/**
 * 统计数据 - 匹配后端 TaskStats 模型
 */
export interface StatsData {
  total_tasks: number;
  pending_tasks: number;
  processing_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  total_media_items: number;
  downloaded_media_items: number;
  average_processing_time: number;
}

/**
 * 统计数据查询响应 - 后端直接返回 TaskStats 对象
 */
export type GetStatsResponse = StatsData;

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
