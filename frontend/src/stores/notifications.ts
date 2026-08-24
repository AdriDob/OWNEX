import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken } from '@/lib/api'
import { wsUrl } from '@/lib/backend'

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
      const url = wsUrl('/api/ws', token ?? undefined)
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
          // ATLAS/ODYSSEY event notifications
          if (data.type?.startsWith('atlas:') || data.type?.startsWith('odyssey:')) {
            const eventType = data.type as string
            const titles: Record<string, string> = {
              'atlas:price:sync:started': 'Sincronizando precios',
              'atlas:price:sync:completed': 'Precios sincronizados',
              'atlas:price:sync:failed': 'Error al sincronizar precios',
              'atlas:rebalance:check:started': 'Verificando rebalanceo',
              'atlas:rebalance:check:completed': 'Rebalanceo verificado',
              'odyssey:bet:sync:started': 'Sincronizando apuestas',
              'odyssey:bet:sync:completed': 'Apuestas sincronizadas',
              'odyssey:bet:sync:failed': 'Error al sincronizar apuestas',
              'odyssey:analytics:recalculated': 'Analítica recalculada',
            }
            const sev: Record<string, 'info' | 'success' | 'warning' | 'error'> = {
              failed: 'error',
              started: 'info',
              completed: 'success',
              recalculated: 'success',
            }
            const key = Object.keys(titles).find(k => eventType.includes(k.split(':').slice(1).join(':')))
            const title = titles[eventType] || (key ? titles[key] : `Evento: ${eventType}`)
            const severity = Object.entries(sev).find(([s]) => eventType.includes(s))?.[1] || 'info'
            add({ type: severity, title, message: data.payload?.error || '', source: eventType.split(':')[0] })
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
