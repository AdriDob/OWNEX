/**
 * Backend connection helpers for OWNEX Alpha Desktop.
 *
 * Port discovery inside the Tauri webview uses three complementary paths:
 *   1. Push:   'backend-ready' event emitted by the Rust shell after health OK.
 *   2. Pull:   invoke('is_backend_ready') + invoke('get_backend_port').
 *   3. Fallback: HTTP health scan across the full dynamic range (8000-8099).
 *
 * getApiBase() is evaluated at REQUEST TIME so late resolution is picked up
 * by every consumer without reload.
 */

import type { Event } from '@tauri-apps/api/event'

const DEFAULT_PORT = 8000
/** Must stay aligned with find_available_port() in src-tauri/src/lib.rs. */
const MAX_PORT_OFFSET = 99
const BACKEND_HOST = '127.0.0.1'

/** True when running inside a Tauri webview (v2 always injects __TAURI_INTERNALS__). */
function detectTauri(): boolean {
  if (typeof window === 'undefined') return false
  const w = window as unknown as Record<string, unknown>
  return '__TAURI_INTERNALS__' in w || '__TAURI__' in w
}

export const isTauri: boolean = detectTauri()

let _backendPort = DEFAULT_PORT
let _portResolved = false

function setBackendPort(port: number, via: string): void {
  if (_portResolved && _backendPort === port) return
  _backendPort = port
  _portResolved = true
  console.info(`[OWNEX] Backend ready on port ${port} (via ${via})`)
}

/** Current backend HTTP base URL (request-time evaluation). */
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

// ── Port discovery ──────────────────────────────────────────────────────────
if (isTauri) {
  // 1. Push: Rust emits backend-ready once health passes.
  import('@tauri-apps/api/event')
    .then(({ listen }) =>
      Promise.all([
        listen<{ port: number }>('backend-ready', (event: Event<{ port: number }>) =>
          setBackendPort(event.payload.port, 'event'),
        ),
        listen<{ message: string }>('backend-error', (event) => {
          console.error(`[OWNEX] Backend error: ${event.payload.message}`)
        }),
      ]),
    )
    .catch((e) => console.warn('[OWNEX] Tauri event API unavailable:', e))

  // 2. Pull: poll the shell commands until readiness flips true.
  import('@tauri-apps/api/core')
    .then(async ({ invoke }) => {
      for (let i = 0; i < 90 && !_portResolved; i++) {
        try {
          if (await invoke<boolean>('is_backend_ready')) {
            const port = await invoke<number | null>('get_backend_port')
            if (port && port > 0) setBackendPort(port, 'invoke')
            break
          }
        } catch {
          // command bridge not ready yet this tick
        }
        await new Promise((r) => setTimeout(r, 1000))
      }
    })
    .catch((e) => console.warn('[OWNEX] Tauri invoke API unavailable:', e))

  // 3. Fallback: direct health scan over the full dynamic range. Catches any
  //    case where the IPC bridge itself is degraded but fetch still works.
  let pollAttempts = 0
  const MAX_POLL_ATTEMPTS = 30
  const POLL_INTERVAL_MS = 2000

  async function pollBackend(): Promise<void> {
    if (_portResolved || pollAttempts >= MAX_POLL_ATTEMPTS) return
    pollAttempts++

    for (let offset = 0; offset <= MAX_PORT_OFFSET; offset++) {
      const port = DEFAULT_PORT + offset
      try {
        const resp = await fetch(`http://${BACKEND_HOST}:${port}/api/health`, {
          signal: AbortSignal.timeout(600),
        })
        if (resp.ok) {
          setBackendPort(port, 'polling')
          return
        }
      } catch {
        // not this port
      }
    }

    if (!_portResolved) setTimeout(pollBackend, POLL_INTERVAL_MS)
    else console.warn('[OWNEX] Backend not found on any port 8000-8099 after 30s of polling')
  }

  setTimeout(pollBackend, 2500)
}
