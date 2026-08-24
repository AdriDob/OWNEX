import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Root-mounted backend routers (no /api prefix)
      '/direct-work': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/mobile': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/wear-os': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
