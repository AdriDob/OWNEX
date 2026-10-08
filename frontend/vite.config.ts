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
      // Root-mounted backend routers (no /api prefix) — espejo exacto de
      // ROOT_MOUNTED_PREFIXES en src/lib/backend.ts (guard:
      // test_frontend_api_contract.py).
      //
      // Antes eran 5 de 13: /career, /first-money, /mission-hub, /oar,
      // /revenue-timeline, /version-backup, /voice y /zero-barrier no
      // estaban. En dev, esas llamadas iban a /api/... y el proxy no las
      // cubría: 404 que sólo aparecían en desarrollo.
        ...Object.fromEntries(
          [
            // Debe coincidir con ROOT_MOUNTED_PREFIXES de lib/backend.ts.
            // Si un namespace no está en esa lista, el front lo pide bajo
            // /api y este proxy sobra: `/api` ya cubre todo.
            '/career', '/direct-work', '/first-money', '/mission-hub',
            '/mobile', '/oar', '/platform-guides', '/result-based', '/revenue-timeline',
            '/today', '/version-backup', '/voice', '/wear-os', '/zero-barrier',
          ].map((p) => [p, { target: 'http://127.0.0.1:8000', changeOrigin: true }]),
        ),
    },
  },
})
