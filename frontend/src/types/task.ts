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
 * 视频任务实体
 */
export interface VideoTask {
  id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  currentPhase?: TaskPhase;
  subtitleTemplate: SubtitleTemplate;
  scriptStyle: ScriptStyle;
  videoUrl?: string;
  scriptContent?: string;
  thumbnailUrl?: string;
  errorMessage?: string;
  errorCode?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  duration?: number;
  fileSize?: number;
  estimatedTime?: number;
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
