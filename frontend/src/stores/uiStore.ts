/**
 * Global UI state management with Zustand
 */

import { create } from 'zustand';

export interface ErrorState {
  message: string;
  code?: string;
  details?: unknown;
}

export interface ToastState {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface UIStore {
  // Loading state
  isGlobalLoading: boolean;
  setGlobalLoading: (loading: boolean) => void;

  // Error state
  error: ErrorState | null;
  setError: (error: ErrorState | null) => void;
  clearError: () => void;

  // Toast state
  toast: ToastState | null;
  showToast: (toast: ToastState) => void;
  hideToast: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  // Loading
  isGlobalLoading: false,
  setGlobalLoading: (loading) => set({ isGlobalLoading: loading }),

  // Error
  error: null,
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),

  // Toast
  toast: null,
  showToast: (toast) => set({ toast }),
  hideToast: () => set({ toast: null }),
}));
