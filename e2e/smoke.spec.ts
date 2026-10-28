import { test, expect } from '@playwright/test'

/**
 * SMOKE — la app arranca y monta el shell real.
 *
 * Sustituye las aserciones vacías anteriores (`toBeGreaterThanOrEqual(0)`,
 * `bodyText.length > 0`) que no podían fallar: pasaban igual sobre una pantalla
 * blanca, un error o un login wall.
 */

test.describe('Arranque de la app', () => {
  test('el Command Center monta y no queda en blanco', async ({ page }) => {
    await page.goto('/')

    // El layout real (AppLayout) debe existir, no el <router-view> público pelado.
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

    // Evidencia de contenido, no sólo de nodos: el body debe tener texto real.
    const bodyText = (await page.locator('body').innerText()).trim()
    expect(bodyText.length).toBeGreaterThan(80)
  })

  test('el Command Center renderiza sus bloques de estado', async ({ page }) => {
    // Éste es el guard que DEBE fallar si un identificador sin resolver rompe el
    // setup() de IncomeHome. Un ReferenceError en `<script setup>` NO lanza
    // pageerror: Vue lo degrada y deja la zona afectada VACÍA, así que comprobar
    // sólo que `#main-content` existe daba falso verde (verificado: con
    // `useHuntStore` sin importar la app "funcionaba" y el card no se pintaba).
    await page.goto('/')
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

    // Bloques característicos del Command Center.
    await expect(page.locator('body')).toContainText(/MODO OPERATIVO/i, { timeout: 15_000 })
    await expect(page.locator('body')).toContainText(/CAPITAL/i)
  })

  test('no hay errores de runtime al montar la raíz', async ({ page }) => {
    const errors: string[] = []
    const consoleErrors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text())
    })

    await page.goto('/')
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })
    await page.waitForLoadState('networkidle').catch(() => {})

    expect(errors, `errores de runtime: ${errors.join(' | ')}`).toEqual([])

    // 401 sin sesión y el 403 del handshake WebSocket son condiciones
    // PREEXISTENTES del backend (el WS exige token; AuthMiddleware lo deja
    // pasar y el endpoint responde 403). No son regresiones de este release:
    // están documentadas en .ai/KNOWN_DEBT.md. Se filtran para que el guard
    // siga siendo sensible a errores de render/sintaxis, que es lo que
    //debemos detectar (ej. ReferenceError en setup()).
    const knownConditions = /401|403|Unauthorized|Forbidden|Failed to load resource|WebSocket/i
    const fatal = consoleErrors.filter((t) => !knownConditions.test(t))
    expect(fatal, `errores de consola: ${fatal.join(' | ')}`).toEqual([])
  })

  test('el backend es alcanzable desde la app', async ({ page }) => {
    // /api/health es público (AuthMiddleware PUBLIC_PATHS).
    const response = await page.request.get('/api/health')
    expect(response.status()).toBe(200)
  })

  test('el Command Palette abre con Ctrl+K', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

    await page.keyboard.press('Control+k')
    const paletteInput = page
      .locator('input[placeholder*="Comando"], input[placeholder*="Search"]')
      .first()
    await expect(paletteInput).toBeVisible({ timeout: 10_000 })

    await page.keyboard.press('Escape')
  })
})

test.describe('Rutas principales', () => {
  const routes = ['/', '/targets', '/capital', '/intelligence', '/reports', '/operations', '/mission', '/copilot']

  for (const route of routes) {
    test(`renderiza ${route} sin pantalla en blanco`, async ({ page }) => {
      const pageErrors: string[] = []
      page.on('pageerror', (e) => pageErrors.push(e.message))

      await page.goto(route)
      await page.waitForLoadState('domcontentloaded')

      // Criterio real: el layout de la app está montado Y hay texto.
      await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })
      const bodyText = (await page.locator('body').innerText()).trim()
      expect(bodyText.length, `${route} arrancó vacío`).toBeGreaterThan(40)

      // Ninguna ruta debe romper el runtime al montar.
      expect(pageErrors, `${route} → ${pageErrors.join(' | ')}`).toEqual([])
    })
  }
})
