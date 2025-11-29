/**
 * Statistics service
 */

import api from './api';
import type { GetStatsResponse } from '@/types';

/**
 * Get statistics data
 */
export async function getStats(): Promise<GetStatsResponse> {
  const response = await api.get<GetStatsResponse>('/tasks/stats');
  return response.data;
}
