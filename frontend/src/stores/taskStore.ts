/**
 * Task-related state management with Zustand
 */

import { create } from 'zustand';
import type { VideoTask, SubtitleTemplate } from '@/types';

interface TaskStore {
  // Current task
  currentTask: VideoTask | null;
  setCurrentTask: (task: VideoTask | null) => void;

  // Template selection
  selectedTemplate: SubtitleTemplate | null;
  setSelectedTemplate: (template: SubtitleTemplate | null) => void;

  // Upload progress
  uploadProgress: number;
  setUploadProgress: (progress: number) => void;
  resetUploadProgress: () => void;

  // Uploaded file
  uploadedFileId: string | null;
  setUploadedFileId: (fileId: string | null) => void;
}

export const useTaskStore = create<TaskStore>((set) => ({
  // Current task
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),

  // Template selection
  selectedTemplate: null,
  setSelectedTemplate: (template) => set({ selectedTemplate: template }),

  // Upload progress
  uploadProgress: 0,
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  resetUploadProgress: () => set({ uploadProgress: 0 }),

  // Uploaded file
  uploadedFileId: null,
  setUploadedFileId: (fileId) => set({ uploadedFileId: fileId }),
}));
