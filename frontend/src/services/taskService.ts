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

/**
 * Create a new video generation task
 */
export async function createTask(request: CreateTaskRequest): Promise<CreateTaskResponse> {
  const response = await api.post<CreateTaskResponse>('/api/tasks/create', request);
  return response.data;
}

/**
 * Get task status by ID
 */
export async function getTaskStatus(taskId: string): Promise<GetTaskStatusResponse> {
  const response = await api.get<GetTaskStatusResponse>(`/api/tasks/${taskId}/status`);
  return response.data;
}

/**
 * Get list of tasks with filters
 */
export async function getTasks(params?: GetTasksRequest): Promise<GetTasksResponse> {
  const response = await api.get<GetTasksResponse>('/api/tasks', { params });
  return response.data;
}

/**
 * Cancel a running task
 */
export async function cancelTask(taskId: string): Promise<CancelTaskResponse> {
  const response = await api.post<CancelTaskResponse>(`/api/tasks/${taskId}/cancel`);
  return response.data;
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<DeleteTaskResponse> {
  const response = await api.delete<DeleteTaskResponse>(`/api/tasks/${taskId}`);
  return response.data;
}
