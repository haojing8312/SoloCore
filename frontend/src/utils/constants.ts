/**
 * Application constants
 */

import type { SubtitleTemplateInfo, ScriptStyle } from '@/types';

/**
 * API Configuration
 */
export const API_CONFIG = {
  // Use relative path in development to leverage Vite proxy (avoids CORS)
  // Use full URL in production or when VITE_API_BASE_URL is explicitly set
  BASE_URL: import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? '' : 'http://localhost:48095'),
  TIMEOUT: 30000,
  POLLING_INTERVAL: 3000,
} as const;

/**
 * File Upload Configuration
 */
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_EXTENSIONS: ['.md', '.markdown', '.txt'],
  ALLOWED_MIME_TYPES: ['text/markdown', 'text/plain'],
  CHUNK_SIZE: 1024 * 1024, // 1MB
} as const;

/**
 * Task Configuration
 */
export const TASK_CONFIG = {
  MULTI_VIDEO_COUNT: 1,
  DEFAULT_SCRIPT_STYLE: 'default' as ScriptStyle,
} as const;

/**
 * UI Configuration
 */
export const UI_CONFIG = {
  TOAST_DURATION: 3000,
  DEBOUNCE_DELAY: 300,
  ITEMS_PER_PAGE: 20,
} as const;

/**
 * Subtitle Templates
 */
export const SUBTITLE_TEMPLATES: SubtitleTemplateInfo[] = [
  {
    id: 'hype',
    name: 'Hype',
    description: '动感活力,适合年轻受众',
    previewImage: '/assets/templates/hype-preview.png'
  },
  {
    id: 'minimalist',
    name: 'Minimalist',
    description: '极简风格,专业简洁',
    previewImage: '/assets/templates/minimalist-preview.png'
  },
  {
    id: 'explosive',
    name: 'Explosive',
    description: '爆炸效果,吸引注意力',
    previewImage: '/assets/templates/explosive-preview.png'
  },
  {
    id: 'vibrant',
    name: 'Vibrant',
    description: '多彩活泼,色彩丰富',
    previewImage: '/assets/templates/vibrant-preview.png'
  }
] as const;
