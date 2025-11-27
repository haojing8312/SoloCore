/**
 * File validation utilities
 */

import { UPLOAD_CONFIG } from './constants';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validate uploaded file
 */
export function validateFile(file: File): ValidationResult {
  const errors: string[] = [];

  // Check file size
  if (file.size > UPLOAD_CONFIG.MAX_FILE_SIZE) {
    errors.push(`文件大小不能超过 ${formatFileSize(UPLOAD_CONFIG.MAX_FILE_SIZE)}`);
  }

  // Check file extension
  const extension = getFileExtension(file.name);
  if (!UPLOAD_CONFIG.ALLOWED_EXTENSIONS.includes(extension)) {
    errors.push(`仅支持 ${UPLOAD_CONFIG.ALLOWED_EXTENSIONS.join(', ')} 格式的文件`);
  }

  // Check MIME type (if available)
  if (file.type && !UPLOAD_CONFIG.ALLOWED_MIME_TYPES.includes(file.type)) {
    errors.push('文件类型不正确,仅支持 Markdown 文件');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Get file extension (including the dot)
 */
function getFileExtension(filename: string): string {
  const lastDotIndex = filename.lastIndexOf('.');
  if (lastDotIndex === -1) return '';
  return filename.slice(lastDotIndex).toLowerCase();
}

/**
 * Format file size to human-readable string
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}
