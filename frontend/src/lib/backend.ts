/**
 * Backend connection helpers for OWNEX Alpha Desktop.
 *
 * When running inside Tauri, the backend port is dynamic and discovered
 * via a Tauri event emitted after the sidecar health check passes.
 * A polling fallback ensures the port is discovered even if the event
 * fires before the listener is ready (race condition).
 */

const DEFAULT_PORT = 8000
const BACKEND_HOST = '127.0.0.1'

/** True when running inside a Tauri webview. */
export const isTauri: boolean =
  typeof window !== 'undefined' && '__TAURI__' in window

/** Current backend port (updated when backend-ready event fires or via polling). */
let _backendPort = DEFAULT_PORT
let _portResolved = false

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

// ── Port discovery: event + polling fallback ──
if (isTauri) {
  // 1. Listen for Tauri event (primary mechanism)
  import('@tauri-apps/api/event').then(({ listen }) => {
    listen<{ port: number }>('backend-ready', (event) => {
      _backendPort = event.payload.port
      _portResolved = true
      console.log(`[OWNEX] Backend ready on port ${_backendPort} (via event)`)
    })
    listen<{ message: string }>('backend-error', (event) => {
      console.error(`[OWNEX] Backend error: ${event.payload.message}`)
    })
  }).catch(() => {
    // Tauri API not available
  })

  // 2. Polling fallback: try health endpoint every 2s for up to 30s
  //    This catches cases where the event fires before the listener is ready
  let pollAttempts = 0
  const MAX_POLL_ATTEMPTS = 15
  const POLL_INTERVAL = 2000

  async function pollBackend(): Promise<void> {
    if (_portResolved || pollAttempts >= MAX_POLL_ATTEMPTS) return
    pollAttempts++

    for (let port = DEFAULT_PORT; port < DEFAULT_PORT + 10; port++) {
      try {
        const resp = await fetch(`http://${BACKEND_HOST}:${port}/api/health`, {
          signal: AbortSignal.timeout(1000),
        })
        if (resp.ok) {
          _backendPort = port
          _portResolved = true
          console.log(`[OWNEX] Backend found on port ${port} (via polling)`)
          return
        }
      } catch {
        // not this port, try next
      }
    }

    // Schedule next poll
    if (!_portResolved && pollAttempts < MAX_POLL_ATTEMPTS) {
      setTimeout(pollBackend, POLL_INTERVAL)
    }
  }

  // Start polling after a short delay (give sidecar time to start)
  setTimeout(pollBackend, 3000)
}

/** API base constant — now just a convenience alias. */
export const API_BASE = getApiBase()
