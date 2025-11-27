/**
 * File upload service
 */

import api from './api';
import type { UploadFileResponse } from '@/types';

/**
 * Upload progress callback type
 */
export type UploadProgressCallback = (progress: number) => void;

/**
 * Upload a file to the server
 */
export async function uploadFile(
  file: File,
  onProgress?: UploadProgressCallback
): Promise<UploadFileResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadFileResponse>('/api/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
}
