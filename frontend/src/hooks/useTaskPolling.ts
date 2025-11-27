/**
 * Custom hook for task status polling with TanStack Query
 */

import { useQuery } from '@tanstack/react-query';
import { getTaskStatus } from '@/services/taskService';
import { API_CONFIG } from '@/utils/constants';
import { isTaskFinished } from '@/types';

interface UseTaskPollingOptions {
  taskId: string;
  enabled?: boolean;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

export function useTaskPolling({
  taskId,
  enabled = true,
  onSuccess,
  onError,
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
    enabled: enabled && !!taskId,
    refetchInterval: (query) => {
      // Stop polling if task is finished
      const data = query.state.data;
      if (data && isTaskFinished(data.status)) {
        return false;
      }
      return API_CONFIG.POLLING_INTERVAL;
    },
    refetchOnWindowFocus: false,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });

  // Call callbacks
  if (query.isSuccess && onSuccess) {
    onSuccess(query.data);
  }
  if (query.isError && onError) {
    onError(query.error as Error);
  }

  return {
    task: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as Error | null,
    refetch: query.refetch,
  };
}
