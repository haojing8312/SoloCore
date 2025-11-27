/**
 * Custom hook for theme management
 */

import { useEffect } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ThemeStore {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  actualTheme: 'light' | 'dark';
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'system',
      actualTheme: 'light',
      setTheme: (theme) => {
        set({ theme });
        applyTheme(theme);
      },
    }),
    {
      name: 'theme-storage',
    }
  )
);

function applyTheme(theme: Theme) {
  const root = window.document.documentElement;

  // Remove existing theme classes
  root.classList.remove('light', 'dark');

  // Determine actual theme
  let actualTheme: 'light' | 'dark';

  if (theme === 'system') {
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
    actualTheme = systemTheme;
  } else {
    actualTheme = theme;
  }

  // Apply theme class
  root.classList.add(actualTheme);

  // Update store
  useThemeStore.setState({ actualTheme });
}

export function useTheme() {
  const { theme, setTheme, actualTheme } = useThemeStore();

  useEffect(() => {
    // Apply theme on mount
    applyTheme(theme);

    // Listen for system theme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (theme === 'system') {
        applyTheme('system');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  return {
    theme,
    setTheme,
    actualTheme,
  };
}
