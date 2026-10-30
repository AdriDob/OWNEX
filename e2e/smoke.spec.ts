import { test, expect } from '@playwright/test'

// Smoke: la app carga y el Command Center renderiza
test('OWNEX Command Center loads', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('networkidle')
  expect(await page.title()).toBeTruthy()
})

// Smoke: la ruta raíz redirige al Command Center (IncomeHome)
test('root renders OWNEX Command Center', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('domcontentloaded')
  // El Command Center muestra al menos un heading o el layout
  const body = await page.locator('body').innerText()
  expect(body.length).toBeGreaterThan(0)
})

// Smoke: el Command Palette se puede abrir con Ctrl+K
test('Command Palette opens with Ctrl+K', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('domcontentloaded')
  await page.keyboard.press('Control+k')
  // Espera el input de la paleta (placeholder en español)
  await expect(page.locator('input[placeholder*="Comando"]').first()).toBeVisible({ timeout: 10000 })
})

// Smoke: navegación al sidebar funciona (Targets)
test('navigate to Targets', async ({ page }) => {
  await page.goto('/targets')
  await page.waitForLoadState('domcontentloaded')
  const body = await page.locator('body').innerText()
  expect(body).toBeTruthy()
})
