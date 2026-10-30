/**
 * ¿Este error es "todavía no hay sesión" y no un fallo?
 *
 * El gate de auth (2026-10-04) hace que las rutas montadas en raíz exijan
 * credencial, así que una carga sin sesión produce 401 en cada llamada. Eso es
 * el estado inicial esperado de la app, no un error: loguearlo como
 * `console.error` (1) llenaba la consola en cada arranque, (2) escondía los
 * errores reales detrás del ruido y (3) lo leía el smoke de Playwright como
 * fallo de runtime de la app.
 *
 * Un 401 **con** token sí es sesión expirada y debe seguir siendo error.
 */
export function isUnauthenticated(e: unknown): boolean {
  if (!e || typeof e !== 'object') return false
  const err = e as { status?: unknown; message?: unknown }
  return err.status === 401 || (typeof err.message === 'string' && err.message === 'No autenticado.')
}
