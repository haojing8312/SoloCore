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

      // 后端返回批量上传格式: { items: [...], stats: {...}, warnings: [...] }
      // 检查第一个上传项是否成功
      if (response.items && response.items.length > 0) {
        const uploadedFile = response.items[0];

        if (uploadedFile.success) {
          // 使用 object_key 作为 fileId
          setUploadedFileId(uploadedFile.object_key);
          showToast({
            type: 'success',
            message: `文件上传成功: ${uploadedFile.filename}`,
          });

          // 如果有警告，显示警告信息
          if (response.warnings && response.warnings.length > 0) {
            showToast({
              type: 'warning',
              message: response.warnings.join('; '),
            });
          }

          return uploadedFile.object_key;
        } else {
          throw new Error(`文件上传失败: ${uploadedFile.filename}`);
        }
      } else {
        throw new Error('文件上传失败: 服务器未返回上传结果');
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
