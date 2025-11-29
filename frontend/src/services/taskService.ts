/**
 * Task management service
 */

import api from './api';
import type {
  CreateTaskRequest,
  CreateTaskResponse,
  GetTaskStatusResponse,
  GetTasksRequest,
  GetTasksResponse,
  CancelTaskResponse,
  DeleteTaskResponse,
} from '@/types';
import type { VideoTask as Task } from '@/types/task';

/**
 * Create a new video generation task
 */
export async function createTask(request: CreateTaskRequest): Promise<CreateTaskResponse> {
  // 后端接口期望 Form 数据，而不是 JSON
  const formData = new FormData();

  // media_urls 是素材 URL 列表，fileId 实际是上传后返回的 URL
  formData.append('media_urls', request.fileId);

  // title 必填
  formData.append('title', '视频生成任务');

  // description 可选
  formData.append('description', `使用 ${request.subtitleTemplate} 模板生成视频`);

  // mode 默认为 multi_scene
  formData.append('mode', 'multi_scene');

  // script_style
  formData.append('script_style', request.scriptStyle || 'default');

  // multi_video_count
  formData.append('multi_video_count', String(request.multiVideoCount || 3));

  // 后端直接返回 Task 对象，需要包装成 ApiResponse 格式
  const response = await api.post<Task>('/tasks/create-video-task', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  // 将 Task 对象转换为前端期望的 CreateTaskResponse 格式
  return {
    success: true,
    data: {
      taskId: response.data.id,
      status: response.data.status,
    },
  };
}

/**
 * Get task status by ID
 */
export async function getTaskStatus(taskId: string): Promise<GetTaskStatusResponse> {
  // 后端直接返回 Task 对象
  const response = await api.get<GetTaskStatusResponse>(`/tasks/${taskId}/status`);
  return response.data;
}

/**
 * Get list of tasks with filters
 */
export async function getTasks(params?: GetTasksRequest): Promise<GetTasksResponse> {
  // 后端直接返回 Task 数组
  const response = await api.get<GetTasksResponse>('/tasks', { params });
  return response.data;
}

/**
 * Cancel a running task
 *
 * ⚠️ 警告：后端当前没有实现取消任务的接口
 */
export async function cancelTask(taskId: string): Promise<CancelTaskResponse> {
  // TODO: 后端需要实现 POST /tasks/{task_id}/cancel 接口
  throw new Error('取消任务功能暂未实现');

  // 当后端实现后，使用以下代码：
  // const response = await api.post<CancelTaskResponse>(`/tasks/${taskId}/cancel`);
  // return response.data;
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<DeleteTaskResponse> {
  const response = await api.delete<DeleteTaskResponse>(`/tasks/${taskId}`);
  return response.data;
}
