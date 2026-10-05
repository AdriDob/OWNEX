import { defineConfig, devices } from '@playwright/test'

/**
 * E2E contra el BUILD DE PRODUCCIÓN servido por HTTP (FASE 6 del audit).
 *
 * A diferencia de playwright.config.ts (dev server de Vite), acá se levanta
 * `frontend/dist/` con el static server sin dependencias (frontend/spa-server.cjs).
 * Es la versión más cercana a la que recibe el usuario final.
 *
 * El build debe existir: corré `npm run build` antes (o usá `npm run test:e2e:prod`
 * que lo hace explícito en el README de release).
 */
const PORT = Number(process.env.OWNEX_E2E_PROD_PORT ?? 8090)
const BASE_URL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: 0,
  workers: 2,
  reporter: [['list']],
  outputDir: 'test-results-prod',
  use: {
    baseURL: BASE_URL,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [{ name: 'chromium-prod', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // El build de producción llama a /api same-origin, así que el static server
    // proxea /api y los root-mounted hacia el backend real. Sin esto la app
    // vería 502 en cada fetch y los flujos de datos no se podrían probar.
    command: `node frontend/spa-server.cjs --port ${PORT} --proxy ${process.env.OWNEX_BACKEND_ORIGIN || 'http://127.0.0.1:8000'}`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
