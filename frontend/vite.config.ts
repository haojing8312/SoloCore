import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:48095',  // 使用 IPv4 地址避免 Windows IPv6 连接问题
        changeOrigin: true,
      },
      '/tasks': {
        target: 'http://127.0.0.1:48095',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://127.0.0.1:48095',
        changeOrigin: true,
      },
      '/personas': {
        target: 'http://127.0.0.1:48095',
        changeOrigin: true,
      },
      '/internal': {
        target: 'http://127.0.0.1:48095',
        changeOrigin: true,
      },
      '/dynamic-subtitles': {
        target: 'http://127.0.0.1:48095',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@radix-ui/react-slot'],
          'chart-vendor': ['recharts'],
          'query-vendor': ['@tanstack/react-query'],
          'utils-vendor': ['axios', 'date-fns', 'zustand'],
        },
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.');
          const ext = info?.[info.length - 1];
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name ?? '')) {
            return 'assets/images/[name]-[hash][extname]';
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name ?? '')) {
            return 'assets/fonts/[name]-[hash][extname]';
          }
          return `assets/${ext}/[name]-[hash][extname]`;
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },
    chunkSizeWarningLimit: 1000, // Increase to 1MB for chart library
  },
});
