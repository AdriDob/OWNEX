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
      // Root-mounted backend routers (no /api prefix) — espejo de
      // ROOT_MOUNTED_PREFIXES en src/lib/backend.ts (guard: test_frontend_api_contract.py)
        ...Object.fromEntries(
          [
            '/career', '/decision', '/dev-bounty', '/devin', '/direct-work',
            '/enhanced-personalization', '/finance', '/first-money', '/fiverr',
            '/life-management', '/mission-hub', '/mobile', '/oar', '/onboarding',
            '/opensource', '/platform-guides', '/productivity', '/remote',
            '/result-based', '/revenue-timeline', '/supabase', '/today',
            '/version-backup', '/voice', '/wear-os', '/webhook', '/zero-barrier',
          ].map((p) => [p, { target: 'http://127.0.0.1:8000', changeOrigin: true }]),
        ),
    },
  },
})
