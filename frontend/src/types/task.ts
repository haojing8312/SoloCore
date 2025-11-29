/**
 * Task-related type definitions
 */

/**
 * 任务状态枚举
 */
export enum TaskStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

/**
 * 任务处理阶段枚举
 */
export enum TaskPhase {
  MATERIAL_PROCESSING = 'material_processing',
  MATERIAL_ANALYSIS = 'material_analysis',
  SCRIPT_GENERATION = 'script_generation',
  VIDEO_GENERATION = 'video_generation'
}

/**
 * 字幕模板类型 - 基于PyCaps模板系统
 */
export type SubtitleTemplate =
  | 'hype'
  | 'minimalist'
  | 'explosive'
  | 'vibrant'
  | 'classic'
  | 'fast'
  | 'line-focus'
  | 'model'
  | 'neo-minimal'
  | 'retro-gaming'
  | 'word-focus'
  | 'default';

/**
 * 脚本风格类型
 */
export type ScriptStyle = 'default';

/**
 * 视频任务实体 - 匹配后端 Task 模型
 */
export interface VideoTask {
  // 基础字段
  id: string;
  title: string;
  description?: string;
  task_type?: string;

  // 文件相关
  source_file?: string;
  file_path?: string;
  workspace_dir?: string;

  // 任务状态
  creator_id?: string;
  status: TaskStatus;
  progress: number;
  current_stage?: string;

  // 时间戳
  created_at: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;

  // 错误信息
  error_message?: string;
  error_traceback?: string;

  // Celery 相关
  celery_task_id?: string;
  worker_name?: string;
  retry_count?: number;
  max_retries?: number;

  // 脚本相关
  script_style_type?: string;
  script_title?: string;
  script_description?: string;
  script_narration?: string;
  script_tags?: string[];
  script_estimated_duration?: number;
  script_word_count?: number;
  script_material_count?: number;

  // 素材统计
  markdown_count?: number;
  image_count?: number;
  video_count?: number;

  // 视频输出
  video_url?: string;
  thumbnail_url?: string;
  video_duration?: number;
  video_file_size?: number;
  video_quality?: string;
  course_media_id?: number;

  // 多视频任务
  is_multi_video_task?: boolean;
  multi_video_count?: number;
  multi_video_urls?: string[];
  sub_videos_completed?: number;
  multi_video_results?: Record<string, unknown>[];
}

/**
 * 字幕模板信息
 */
export interface SubtitleTemplateInfo {
  id: SubtitleTemplate;
  name: string;
  description: string;
  example?: string;
}

/**
 * Type guards
 */

export function canCancelTask(status: TaskStatus): boolean {
  return status === TaskStatus.PROCESSING;
}

export function canDeleteTask(status: TaskStatus): boolean {
  return [
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED
  ].includes(status);
}

export function canRetryTask(status: TaskStatus): boolean {
  return status === TaskStatus.FAILED;
}

export function isTaskInProgress(status: TaskStatus): boolean {
  return [TaskStatus.PENDING, TaskStatus.PROCESSING].includes(status);
}

export function isTaskFinished(status: TaskStatus): boolean {
  return [
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED
  ].includes(status);
}
