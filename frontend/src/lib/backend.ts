/**
 * Backend connection helpers for OWNEX Alpha Desktop.
 *
 * When running inside Tauri, the backend port is dynamic and discovered
 * via a Tauri event emitted after the sidecar health check passes.
 * In browser mode (dev), the Vite proxy handles /api → localhost:8000.
 */

const DEFAULT_PORT = 8000
const BACKEND_HOST = '127.0.0.1'

/** True when running inside a Tauri webview. */
export const isTauri: boolean =
  typeof window !== 'undefined' && '__TAURI__' in window

/** Current backend port (updated when backend-ready event fires). */
let _backendPort = DEFAULT_PORT

/** Get the current backend HTTP base URL. */
export function getApiBase(): string {
  if (!isTauri) return '/api'
  return `http://${BACKEND_HOST}:${_backendPort}/api`
}

/** Get the current backend WebSocket base URL. */
export function getWsBase(): string {
  if (!isTauri) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}`
  }
  return `ws://${BACKEND_HOST}:${_backendPort}`
}

/** Build a WebSocket URL for a given path. */
export function wsUrl(path: string, token?: string): string {
  const base = getWsBase()
  const url = `${base}${path}`
  return token ? `${url}?token=${encodeURIComponent(token)}` : url
}

/** API base constant (re-evaluated on import). */
export const API_BASE = getApiBase()

// ── Listen for Tauri events to update port ──
if (isTauri) {
  import('@tauri-apps/api/event').then(({ listen }) => {
    listen<{ port: number }>('backend-ready', (event) => {
      _backendPort = event.payload.port
      console.log(`[OWNEX] Backend ready on port ${_backendPort}`)
    })
  }).catch(() => {
    // Tauri API not available (e.g. in test environment)
  })
}
