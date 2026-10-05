import { test, expect } from '@playwright/test'
import { E2E_USER, authHeaders } from './_session'

/**
 * El banco producía trabajo real pero la UI no lo listaba, y los ids
 * venía de URLs de GitHub (`owner/repo#7`) — inalcanzables como path param.
 * Este test es el recorrido completo: banco → abrir → Work Room con datos.
 */
test('el Work Room carga desde el banco (IDs path-safe)', async ({ page, request }) => {
  // La app hace autoLogin, pero sin token dispara N 401 y el rate limiter
  // corta la carga ("Rate limit exceeded"). Se inyecta la sesión antes.
  const headers = await authHeaders(request)
  await page.addInitScript((h) => {
    localStorage.setItem('CATEYE-token', (h as { Authorization: string }).Authorization.replace('Bearer ', ''))
  }, headers as unknown as Record<string, string>)

  await page.goto('/operations')
  await expect(page.getByText(/Banco de trabajo/i)).toBeVisible({ timeout: 20_000 })

  // `Tabs.vue` renderiza botones sin role="tab": se busca por texto.
  await page.getByRole('button', { name: /^Trabajo$/ }).click()
  await expect(page.getByText(/Banco de trabajo/i)).toBeVisible({ timeout: 15_000 })

  const abrir = page.getByRole('button', { name: /^Abrir$/ }).first()
  await expect(abrir).toBeVisible({ timeout: 15_000 })
  await abrir.click()

  await page.waitForURL(/\/operations\/work-room\//, { timeout: 20_000 })
  await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })
})
