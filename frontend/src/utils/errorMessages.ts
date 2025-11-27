/**
 * User-friendly error messages mapping
 */

export interface ErrorMessageMap {
  [key: string]: string;
}

/**
 * HTTP status code to user-friendly messages
 */
export const HTTP_ERROR_MESSAGES: ErrorMessageMap = {
  '400': '请求参数有误，请检查后重试',
  '401': '登录已过期，请重新登录',
  '403': '没有权限执行此操作',
  '404': '请求的资源不存在',
  '408': '请求超时，请检查网络连接后重试',
  '413': '上传的文件过大，请选择较小的文件',
  '415': '不支持的文件类型',
  '429': '操作过于频繁，请稍后再试',
  '500': '服务器出错了，请稍后重试',
  '502': '服务暂时不可用，请稍后重试',
  '503': '服务正在维护，请稍后重试',
  '504': '服务器响应超时，请稍后重试',
};

/**
 * Error code to user-friendly messages
 */
export const ERROR_CODE_MESSAGES: ErrorMessageMap = {
  // File upload errors
  FILE_TOO_LARGE: '文件大小超过限制（最大 10MB）',
  FILE_TYPE_NOT_ALLOWED: '仅支持 Markdown 文件（.md, .markdown, .txt）',
  FILE_UPLOAD_FAILED: '文件上传失败，请重试',
  FILE_NOT_FOUND: '文件不存在或已被删除',

  // Task errors
  TASK_NOT_FOUND: '任务不存在或已被删除',
  TASK_ALREADY_CANCELLED: '任务已取消',
  TASK_ALREADY_COMPLETED: '任务已完成',
  TASK_CREATION_FAILED: '创建任务失败，请重试',
  TASK_CANCEL_FAILED: '取消任务失败，请重试',

  // Template errors
  INVALID_TEMPLATE: '选择的字幕模板无效',
  TEMPLATE_NOT_FOUND: '字幕模板不存在',

  // Network errors
  NETWORK_ERROR: '网络连接失败，请检查网络后重试',
  TIMEOUT_ERROR: '请求超时，请重试',

  // Server errors
  INTERNAL_SERVER_ERROR: '服务器内部错误，请联系管理员',
  SERVICE_UNAVAILABLE: '服务暂时不可用，请稍后重试',

  // Validation errors
  INVALID_INPUT: '输入的数据格式不正确',
  MISSING_REQUIRED_FIELD: '缺少必填字段',

  // Resource errors
  RESOURCE_NOT_FOUND: '请求的资源不存在',
  RESOURCE_ALREADY_EXISTS: '资源已存在',
};

/**
 * Get user-friendly error message
 * @param error - Error object or error code
 * @param defaultMessage - Default message if no mapping found
 * @returns User-friendly error message
 */
export function getUserFriendlyErrorMessage(
  error: Error | string | { code?: string; status?: number; message?: string },
  defaultMessage = '操作失败，请重试'
): string {
  // Handle Error object
  if (error instanceof Error) {
    // Check if it's a network error
    if (error.message.includes('Network Error') || error.message.includes('Failed to fetch')) {
      return ERROR_CODE_MESSAGES.NETWORK_ERROR;
    }

    // Check if it's a timeout error
    if (error.message.includes('timeout')) {
      return ERROR_CODE_MESSAGES.TIMEOUT_ERROR;
    }

    return error.message || defaultMessage;
  }

  // Handle string error code
  if (typeof error === 'string') {
    return ERROR_CODE_MESSAGES[error] || error;
  }

  // Handle error object with code/status
  if (typeof error === 'object' && error !== null) {
    // Try error code first
    if (error.code && ERROR_CODE_MESSAGES[error.code]) {
      return ERROR_CODE_MESSAGES[error.code];
    }

    // Try HTTP status code
    if (error.status && HTTP_ERROR_MESSAGES[error.status.toString()]) {
      return HTTP_ERROR_MESSAGES[error.status.toString()];
    }

    // Use custom message if available
    if (error.message) {
      return error.message;
    }
  }

  return defaultMessage;
}

/**
 * Format error for toast notification
 */
export function formatErrorForToast(error: unknown): { type: 'error'; message: string } {
  return {
    type: 'error',
    message: getUserFriendlyErrorMessage(error as Error | string | { code?: string; status?: number }),
  };
}

/**
 * Get error action suggestions
 */
export function getErrorActionSuggestion(errorCode?: string): string | undefined {
  const suggestions: ErrorMessageMap = {
    FILE_TOO_LARGE: '请压缩文件或选择其他文件',
    FILE_TYPE_NOT_ALLOWED: '请选择 .md、.markdown 或 .txt 格式的文件',
    NETWORK_ERROR: '请检查网络连接后重试',
    TIMEOUT_ERROR: '请检查网络连接，或稍后重试',
    TASK_NOT_FOUND: '请刷新页面查看最新任务列表',
  };

  return errorCode ? suggestions[errorCode] : undefined;
}
