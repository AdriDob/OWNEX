import type { APIRequestContext } from '@playwright/test'

/**
 * Sesión para los e2e que hablan con endpoints protegidos.
 *
 * Desde 2026-10-04 el gate de auth exige credencial también en las rutas
 * montadas en raíz (265 rutas, 139 mutantes): sin token, `/today` y
 * `/direct-work/revenue-ledger` devuelven 401. Eso es lo correcto — devuelven
 * estado financiero — así que el e2e tiene que autenticarse en vez de pedir
 * que el endpoint se abra.
 *
 * El login va contra el mismo origen que la SPA usa, para que el token viaje
 * por el proxy igual que en la app real.
 */
export const E2E_USER = { username: 'e2e_probe', password: 'e2e-probe-12345' }

export async function authHeaders(request: APIRequestContext): Promise<Record<string, string>> {
  // `register` es idempotente-ish: si ya existe, caemos a login.
  await request.post('/api/auth/register', { data: E2E_USER })
  const res = await request.post('/api/auth/login', { data: E2E_USER })
  if (!res.ok()) {
    throw new Error(`e2e login falló: ${res.status()} ${await res.text()}`)
  }
  const body = (await res.json()) as { data?: { token?: string } }
  const token = body.data?.token
  if (!token) throw new Error('e2e login sin token en la respuesta')
  return { Authorization: `Bearer ${token}` }
}
