import { ref, onUnmounted } from 'vue'
import { getToken } from '@/lib/api'
import { wsUrl } from '@/lib/backend'
import type { WsConnectionStatus, WsEvent } from '@/types'

type EventHandler = (event: WsEvent) => void

let _ws: WebSocket | null = null
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
let _reconnectAttempts = 0
const MAX_RECONNECT_DELAY = 30000
const handlers = new Map<string, Set<EventHandler>>()

const status = ref<WsConnectionStatus>('disconnected')
const lastEvent = ref<WsEvent | null>(null)

function getWsUrl(): string | null {
  const token = getToken()
  if (!token) return null
  return wsUrl('/api/ws', token)
}

function scheduleReconnect() {
  if (_reconnectTimer) clearTimeout(_reconnectTimer)
  const delay = Math.min(1000 * 2 ** _reconnectAttempts, MAX_RECONNECT_DELAY)
  _reconnectAttempts++
  _reconnectTimer = setTimeout(connect, delay)
}

function handleMessage(data: string) {
  try {
    const event = JSON.parse(data) as WsEvent
    lastEvent.value = event
    for (const [pattern, hs] of handlers) {
      if (pattern === '*') { for (const h of hs) h(event); continue }
      if (pattern === event.type) { for (const h of hs) h(event); continue }
      if (pattern.endsWith(':') && event.type.startsWith(pattern)) { for (const h of hs) h(event) }
    }
  } catch { /* ignore */ }
}

export function connect() {
  if (_ws?.readyState === WebSocket.OPEN || _ws?.readyState === WebSocket.CONNECTING) return
  const url = getWsUrl()
  if (!url) { status.value = 'disconnected'; scheduleReconnect(); return }

  status.value = 'connecting'
  try { _ws = new WebSocket(url) } catch { status.value = 'disconnected'; scheduleReconnect(); return }

  _ws.onopen = () => {
    status.value = 'connected'
    _reconnectAttempts = 0
    _ws?.send(JSON.stringify({ type: 'subscribe', pattern: '*' }))
  }
  _ws.onmessage = (msg) => handleMessage(msg.data)
  _ws.onclose = () => { status.value = 'disconnected'; _ws = null; scheduleReconnect() }
  _ws.onerror = () => {}
}

export function disconnect() {
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  _reconnectAttempts = 0
  handlers.clear()
  if (_ws) { _ws.onclose = null; _ws.close(); _ws = null }
  status.value = 'disconnected'
}

export function onWsEvent(type: string, handler: EventHandler) {
  if (!handlers.has(type)) handlers.set(type, new Set())
  handlers.get(type)!.add(handler)
  return () => { handlers.get(type)?.delete(handler) }
}

export function useBountyStream() {
  return { status, lastEvent, connect, disconnect, onWsEvent }
}
