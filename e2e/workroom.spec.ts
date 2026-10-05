import { test, expect } from '@playwright/test'
import { authHeaders } from './_session'

/**
 * Regresión del 2026-10-05: los ids del banco venían de URLs de GitHub
 * (`owner/repo#7`). En FastAPI/Starlette `/` crea una ruta nueva y `#` trunca
 * el fragmento ANTES de que el router matchee — ni `encodeURIComponent` salva
 * eso. Medido: **los 11 items eran inalcanzables por API**, o sea que el
 * Work Room no cargaba para ningún trabajo real.
 *
 * Este test navega directo a la ruta del Work Room con un id real, que es
 * exactamente lo que se rompió. No hace clic en pestañas ni atraviesa overlays:
 * verifica la navegación, que es lo que el fix garantiza.
 */
const WORK_ITEM_ID = 'github_bounty_github_warpspeedopen-source_warpspeed-bounties_1'

test('el Work Room carga con un id real del banco', async ({ page, request }) => {
  const headers = (await authHeaders(request)) as { Authorization: string }
  const token = headers.Authorization.replace('Bearer ', '')

  await page.context().addInitScript((t: string) => {
    window.localStorage.setItem('CATEYE-token', t)
  }, token)

  await page.goto(`/operations/work-room/${WORK_ITEM_ID}`)
  await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

  // El id roto (con `/` y `#`) lo que hoy NO se puede ni construir en una URL.
  const body = (await page.locator('body').innerText()).trim()
  expect(body.length).toBeGreaterThan(80), 'la vista no quedó en blanco'
  expect(body, 'no debe pedir ayuda para encontrar trabajo').not.toContain('No encontrado')
})
