import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from "vite-tsconfig-paths";

// https://vite.dev/config/
export default defineConfig({
  build: {
    sourcemap: 'hidden',
  },
  server: {
    // 开发时代理 API 请求到后端
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:28081',
        changeOrigin: true,
        ws: true,
      },
      '/health': {
        target: 'http://127.0.0.1:28081',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://127.0.0.1:28081',
        changeOrigin: true,
      },
    },
  },
  plugins: [
    react({
      babel: {
        plugins: [
          'react-dev-locator',
        ],
      },
    }),
    tsconfigPaths()
  ],
})
