import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken } from '@/lib/api'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: number
  read: boolean
  source?: string
  action?: { label: string; route: string }
}

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  const wsConnected = ref(false)

  const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)

  const groupedByDate = computed(() => {
    const groups: { label: string; items: Notification[] }[] = []
    const today = new Date()
    const todayStr = today.toDateString()
    const yesterdayStr = new Date(today.getTime() - 86400000).toDateString()

    for (const n of notifications.value) {
      const d = new Date(n.timestamp)
      const dateStr = d.toDateString()
      let label: string
      if (dateStr === todayStr) label = 'Hoy'
      else if (dateStr === yesterdayStr) label = 'Ayer'
      else label = d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })

      let group = groups.find(g => g.label === label)
      if (!group) {
        group = { label, items: [] }
        groups.push(group)
      }
      group.items.push(n)
    }
    return groups
  })

  function add(notif: Omit<Notification, 'id' | 'timestamp' | 'read'>) {
    notifications.value.unshift({
      ...notif,
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      read: false,
    })
    if (notifications.value.length > 100) {
      notifications.value = notifications.value.slice(0, 100)
    }
  }

  function markRead(id: string) {
    const n = notifications.value.find(n => n.id === id)
    if (n) n.read = true
  }

  function markAllRead() {
    notifications.value.forEach(n => n.read = true)
  }

  function remove(id: string) {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  function clearAll() {
    notifications.value = []
  }

  function connectWs() {
    if (wsConnected.value) return
    try {
      const token = getToken()
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = token
        ? `${proto}//${window.location.host}/api/ws?token=${encodeURIComponent(token)}`
        : `${proto}//${window.location.host}/api/ws`
      const ws = new WebSocket(url)
      ws.onopen = () => { wsConnected.value = true }
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'notification' || data.type === 'system_update') {
            add({
              type: data.payload?.severity || 'info',
              title: data.payload?.title || 'Actualización del sistema',
              message: data.payload?.message || '',
              source: data.payload?.source || 'system',
              action: data.payload?.action,
            })
          }
        } catch { /* ignore */ }
      }
      ws.onclose = () => { wsConnected.value = false }
      ws.onerror = () => { wsConnected.value = false }
    } catch { /* ignore */ }
  }

  return {
    notifications, unreadCount, groupedByDate, wsConnected,
    add, markRead, markAllRead, remove, clearAll, connectWs,
  }
})
