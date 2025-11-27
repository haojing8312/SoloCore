/**
 * Custom hook for file upload with validation
 */

import { useState } from 'react';
import { uploadFile } from '@/services/fileService';
import { validateFile } from '@/utils/validation';
import { useTaskStore } from '@/stores/taskStore';
import { useUIStore } from '@/stores/uiStore';

export function useFileUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUploadProgress = useTaskStore((state) => state.setUploadProgress);
  const setUploadedFileId = useTaskStore((state) => state.setUploadedFileId);
  const resetUploadProgress = useTaskStore((state) => state.resetUploadProgress);
  const showToast = useUIStore((state) => state.showToast);

  const upload = async (file: File) => {
    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      const errorMessage = validation.errors.join('; ');
      setError(errorMessage);
      showToast({
        type: 'error',
        message: errorMessage,
      });
      return null;
    }

    setIsUploading(true);
    setError(null);
    resetUploadProgress();

    try {
      const response = await uploadFile(file, (progress) => {
        setUploadProgress(progress);
      });

      if (response.success && response.data) {
        setUploadedFileId(response.data.fileId);
        showToast({
          type: 'success',
          message: '文件上传成功',
        });
        return response.data.fileId;
      } else {
        throw new Error(response.message || '文件上传失败');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件上传失败,请重试';
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

  const reset = () => {
    setIsUploading(false);
    setError(null);
    resetUploadProgress();
    setUploadedFileId(null);
  };

  return {
    upload,
    reset,
    isUploading,
    error,
  };
}
