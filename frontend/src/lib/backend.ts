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

import { ref } from 'vue'
import type { Event } from '@tauri-apps/api/event'

const DEFAULT_PORT = 8000
/** Must stay aligned with find_available_port() in src-tauri/src/lib.rs. */
const MAX_PORT_OFFSET = 99
const BACKEND_HOST = '127.0.0.1'

export type BackendStatus = 'checking' | 'connecting' | 'ready' | 'unreachable'

/** Reactive connection state consumed by UI (ErrorState, status pills, etc.). */
export const backendStatus = ref<BackendStatus>('connecting')
export const backendPort = ref<number>(DEFAULT_PORT)

function setStatus(status: BackendStatus): void {
  if (backendStatus.value !== status) backendStatus.value = status
}

/** True when running inside a Tauri webview (v2 always injects __TAURI_INTERNALS__). */
function detectTauri(): boolean {
  if (typeof window === 'undefined') return false
  const w = window as unknown as Record<string, unknown>
  return '__TAURI_INTERNALS__' in w || '__TAURI__' in w
}

export const isTauri: boolean = detectTauri()

let _backendPort = DEFAULT_PORT
let _portResolved = false

/**
 * Forget the resolved port so the next poll round re-discovers it.
 * Called automatically when a request fails at the network layer
 * (backend restarted on a different port) and by retryConnection().
 */
export function resetBackendDiscovery(): void {
  _portResolved = false
  setStatus('connecting')
}

/** User/UI-initiated reconnect attempt: forget port and rescan immediately. */
export function retryConnection(): void {
  resetBackendDiscovery()
  void pollBackend(true)
}

// ── Health probe + scan loop (module scope so any caller can trigger it) ──

async function probePort(port: number): Promise<boolean> {
  try {
    const resp = await fetch(`http://${BACKEND_HOST}:${port}/api/health`, {
      signal: AbortSignal.timeout(600),
    })
    return resp.ok
  } catch {
    return false
  }
}

const FAST_ATTEMPTS = 30 // ~60 s at 2 s cadence: cold start budget
const SLOW_INTERVAL_MS = 10000 // keep-alive poll forever after that
let _pollAttempts = 0

async function pollBackend(immediate = false): Promise<void> {
  if (!isTauri) return
  if (_portResolved && !immediate) return
  if (!_portResolved) setStatus('connecting')

  for (let offset = 0; offset <= MAX_PORT_OFFSET; offset++) {
    if (_portResolved && !immediate) return
    const port = DEFAULT_PORT + offset
    if (await probePort(port)) {
      setBackendPort(port, 'polling')
      return
    }
  }

  if (!_portResolved) {
    _pollAttempts++
    const delay = _pollAttempts <= FAST_ATTEMPTS ? 2000 : SLOW_INTERVAL_MS
    setTimeout(() => void pollBackend(), delay)
  }
}

function setBackendPort(port: number, via: string): void {
  if (_portResolved && _backendPort === port) return
  const changed = _portResolved && _backendPort !== port
  _backendPort = port
  _portResolved = true
  backendPort.value = port
  setStatus('ready')
  console.info(`[OWNEX] Backend ready on port ${port} (via ${via})`)
  if (changed) {
    // Backend came back on a different port — let in-flight consumers re-read
    // getApiBase() (request-time) and let UI react.
    window.dispatchEvent(new CustomEvent('ownex:backend-port-changed', { detail: { port } }))
  }
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
  setStatus('connecting')
  // 1. Push: Rust emits backend-ready once health passes.
  import('@tauri-apps/api/event')
    .then(({ listen }) =>
      Promise.all([
        listen<{ port: number }>('backend-ready', (event: Event<{ port: number }>) =>
          setBackendPort(event.payload.port, 'event'),
        ),
        listen<{ message: string }>('backend-error', (event) => {
          console.error(`[OWNEX] Backend error: ${event.payload.message}`)
          resetBackendDiscovery()
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

  // 3. Fallback scan starts shortly after boot; pollBackend() lives at module
  //    scope (never gives up: fast retries, then slow keep-alive forever).
  setTimeout(() => void pollBackend(), 2500)
}
