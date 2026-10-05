import { defineConfig, devices } from '@playwright/test'

/**
 * E2E de OWNEX. El config vive en la RAÍZ del repo (testDir ./e2e) y por eso
 * el webServer usa `--prefix frontend`: el path anterior (`--prefix ../frontend`)
 * resolvía a /home/adriel/projects/frontend, que no existe, y el runner no
 * podía arrancar su propio frontend.
 */
const PORT = Number(process.env.OWNEX_E2E_PORT ?? 5173)
const BASE_URL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  // Con retries:0 el trace 'on-first-retry' NUNCA se retenía: contradicción
  // entre la config y la promesa de artefactos. En CI se reintenta 1 vez.
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]]
    : [['list']],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // El backend devuelve 401 en /api/* sin credenciales: se autentica por
    // cookie de sesión vía el flujo de device-login.
    ignoreHTTPSErrors: true,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run dev --prefix frontend -- --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
})
