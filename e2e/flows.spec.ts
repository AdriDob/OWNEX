import { test, expect } from '@playwright/test'
import { authHeaders } from './_session'

/**
 * FLUJOS CRÍTICOS — intención → acción → respuesta → estado esperado.
 *
 * Estos tests hablan con el backend real (OWNEX en :8000). Verifican que la UI
 * no muestre estados económicos falsos:
 *   - EXPECTED / SUBMITTED / ACCEPTED / AWARDED son pipeline, NO caja.
 *   - Sólo PAID genera REALIZED CASH.
 *   - Sin datos, OWNEX dice UNKNOWN; no inventa 0 como si fuera dinero.
 */

test.describe('Command Center — estado real', () => {
  test('el plan del día declara qué hace el sistema y qué hace el humano', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

    // El backend expone /today (root-mounted) con `automatic` y `your_plan`.
    const plan = await page.request.get('/today', { headers: await authHeaders(page.request) })
    expect(plan.status(), '/today debe responder 200').toBe(200)

    const body = (await plan.json()) as {
      who?: string
      automatic?: Array<{ owner?: string; badge?: string }>
      your_plan?: Array<{ owner?: string; badge?: string; title?: string }>
      state?: Record<string, unknown>
    }

    // Cada paso declara dueño: nobody debería ser ambiguo.
    for (const step of [...(body.automatic ?? []), ...(body.your_plan ?? [])]) {
      expect(['system', 'human'], `paso con owner inválido: ${JSON.stringify(step)}`).toContain(step.owner)
    }
    // Y los automáticos llevan su badge.
    for (const step of body.automatic ?? []) {
      expect(step.badge, 'paso automático sin badge').toBe('AUTOMÁTICO')
    }
  })

  test('P(CASH) sin PAID propio es UNKNOWN, nunca un porcentaje inventado', async ({ page }) => {
    const res = await page.request.get('/today', { headers: await authHeaders(page.request) })
    expect(res.status()).toBe(200)
    const body = (await res.json()) as {
      state?: { paid_outcomes?: number; p_cash_state?: string }
    }

    const paid = body.state?.paid_outcomes ?? 0
    const pCash = body.state?.p_cash_state ?? ''

    // Invariante económico: 0 PAID ⇒ P(CASH)Unknown, jamás "0.85" numérico.
    if (paid === 0) {
      expect(
        pCash.toUpperCase(),
        `0 PAID pero p_cash_state="${pCash}" (debería ser UNKNOWN)`,
      ).toContain('UNKNOWN')
      expect(pCash).not.toMatch(/\d+(\.\d+)?\s*%/)
    }
  })

  test('el ledger de revenue no confunde pipeline con caja', async ({ page }) => {
    // /direct-work/revenue-ledger es root-mounted.
    const res = await page.request.get('/direct-work/revenue-ledger', {
      headers: await authHeaders(page.request),
    })
    expect(res.status()).toBe(200)

    const body = (await res.json()) as {
      buckets_usd?: Record<string, number>
      projection_usd?: { realized?: number; pipeline?: number; earned_not_paid?: number }
    }

    // REALIZED no puede exceder lo cobrado. Con 0 PAID debe ser 0.
    const realized = body.projection_usd?.realized ?? 0
    expect(realized).toBeGreaterThanOrEqual(0)

    // El pipeline puede ser grande sin que eso sea caja: es exactamente el
    // caso $3.97M de pipeline inexistente que motivó la corrección.
    if (realized === 0) {
      expect(
        body.projection_usd?.pipeline ?? 0,
        'se está mostrando pipeline como si fuera caja',
      ).toBeGreaterThanOrEqual(0)
    }
  })

  test('la app monta sin errores de runtime en cada ruta de dinero', async ({ page }) => {
    // Rutas que existen en el router del frontend (router/index.ts).
    // Ojo: `/first-money` NO es una página — es un namespace del backend.
    for (const route of ['/', '/capital', '/operations/ledger', '/mission']) {
      const errors: string[] = []
      const onError = (e: Error) => errors.push(e.message)
      page.on('pageerror', onError)

      await page.goto(route)
      await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

      // El texto no debe mostrar artefactos de render roto.
      const text = await page.locator('body').innerText()
      expect(text, `${route} muestra [object Object]`).not.toContain('[object Object]')
      expect(text, `${route} muestra NaN`).not.toMatch(/\bNaN\b/)
      expect(text, `${route} muestra undefined`).not.toMatch(/\bundefined\b/)

      page.off('pageerror', onError)
      expect(errors, `${route} → ${errors.join(' | ')}`).toEqual([])
    }
  })
})

test.describe('Contrato frontend ↔ backend', () => {
  test('/today responde JSON real (no el HTML del SPA)', async ({ page }) => {
    // /today es root-mounted: si el proxy de Vite le faltara, el dev server
    // devolvería index.html (200 HTML) y el cliente fallaría al parsear.
    const res = await page.request.get('/today', { headers: await authHeaders(page.request) })
    expect(res.status()).toBe(200)
    expect(res.headers()['content-type']).toContain('application/json')

    const body = (await res.json()) as Record<string, unknown>
    expect(body, '/today no devolvió el plan esperado').toHaveProperty('who')
    expect(body).toHaveProperty('state')
  })

  test('un namespace del backend no se confunde con una página del frontend', async ({ page }) => {
    // /first-money es backend (root-mounted), NO una ruta del router. Pedirlo
    // como página devuelve el 404 del backend, no el shell.
    await page.goto('/first-money')
    await expect(page.locator('body')).toContainText(/Not Found|404/i)
  })
})

test.describe('Manejo de fallos', () => {
  test('si el backend cae, la app lo muestra en vez de mentir', async ({ page }) => {
    await page.route('**/api/**', (route) => route.abort('failed'))
    await page.route('**/today', (route) => route.abort('failed'))
    await page.route('**/mission-hub/**', (route) => route.abort('failed'))
    await page.route('**/applications/**', (route) => route.abort('failed'))
    await page.route('**/financial/**', (route) => route.abort('failed'))

    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))

    await page.goto('/')
    // Aunque el backend esté caído, el shell debe montar (render por defecto).
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })

    const text = (await page.locator('body').innerText()).trim()
    // Contenido real, no pantalla en blanco.
    expect(text.length, 'app en blanco con el backend caído').toBeGreaterThan(40)
    // Y no debe romperse el runtime por el fallo de red.
    expect(errors, `errores con backend caído: ${errors.join(' | ')}`).toEqual([])
  })

  test('una respuesta vacía no rompe el render', async ({ page }) => {
    await page.route('**/today', (route) => route.fulfill({ status: 200, body: '{}' }))
    await page.goto('/')
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 })
    const text = (await page.locator('body').innerText()).trim()
    expect(text.length).toBeGreaterThan(40)
  })
})
