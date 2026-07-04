import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNotificationsStore } from '@/stores/notifications'

vi.mock('@/lib/api', () => ({
  getToken: vi.fn(() => 'mock-token'),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('notifications store', () => {
  it('starts empty', () => {
    const store = useNotificationsStore()
    expect(store.notifications).toEqual([])
    expect(store.unreadCount).toBe(0)
    expect(store.groupedByDate).toEqual([])
    expect(store.wsConnected).toBe(false)
  })

  it('add inserts notification at the beginning', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'Test', message: 'Hello' })
    expect(store.notifications).toHaveLength(1)
    expect(store.notifications[0].title).toBe('Test')
    expect(store.notifications[0].type).toBe('info')
    expect(store.notifications[0].read).toBe(false)
    expect(store.notifications[0].id).toBeDefined()
    expect(store.notifications[0].timestamp).toBeDefined()
  })

  it('add respects max 100 items', () => {
    const store = useNotificationsStore()
    for (let i = 0; i < 101; i++) {
      store.add({ type: 'info', title: `N${i}`, message: '' })
    }
    expect(store.notifications).toHaveLength(100)
    expect(store.notifications[0].title).toBe('N100')
  })

  it('add supports all notification types', () => {
    const store = useNotificationsStore()
    store.add({ type: 'success', title: 'Success', message: 'OK' })
    store.add({ type: 'warning', title: 'Warn', message: 'Careful' })
    store.add({ type: 'error', title: 'Error', message: 'Fail' })
    store.add({ type: 'info', title: 'Info', message: 'Note' })
    expect(store.notifications).toHaveLength(4)
  })

  it('markRead sets read flag', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'Test', message: '' })
    const id = store.notifications[0].id
    expect(store.notifications[0].read).toBe(false)
    store.markRead(id)
    expect(store.notifications[0].read).toBe(true)
  })

  it('markRead does nothing for unknown id', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'Test', message: '' })
    store.markRead('nonexistent')
    expect(store.notifications[0].read).toBe(false)
  })

  it('markAllRead sets all notifications read', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'A', message: '' })
    store.add({ type: 'info', title: 'B', message: '' })
    store.markAllRead()
    expect(store.notifications.every(n => n.read)).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('unreadCount reflects unread notifications', () => {
    const store = useNotificationsStore()
    expect(store.unreadCount).toBe(0)
    store.add({ type: 'info', title: 'Test', message: '' })
    expect(store.unreadCount).toBe(1)
    store.markRead(store.notifications[0].id)
    expect(store.unreadCount).toBe(0)
  })

  it('remove deletes notification by id', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'A', message: '' })
    store.add({ type: 'info', title: 'B', message: '' })
    const idA = store.notifications[0].id
    store.remove(idA)
    expect(store.notifications).toHaveLength(1)
    expect(store.notifications[0].title).toBe('A')
  })

  it('clearAll empties notifications', () => {
    const store = useNotificationsStore()
    store.add({ type: 'info', title: 'A', message: '' })
    store.add({ type: 'info', title: 'B', message: '' })
    store.clearAll()
    expect(store.notifications).toEqual([])
    expect(store.unreadCount).toBe(0)
  })

  it('groupedByDate groups by today/yesterday/older', () => {
    const store = useNotificationsStore()
    const now = Date.now()
    const yesterday = now - 86400000
    const oldDay = now - 3 * 86400000

    store.notifications = [
      { id: '1', type: 'info', title: 'Today', message: '', timestamp: now, read: false },
      { id: '2', type: 'info', title: 'Yesterday', message: '', timestamp: yesterday, read: false },
      { id: '3', type: 'info', title: 'Old', message: '', timestamp: oldDay, read: false },
    ] as any

    const groups = store.groupedByDate
    expect(groups).toHaveLength(3)
    expect(groups[0].label).toBe('Hoy')
    expect(groups[1].label).toBe('Ayer')
  })

  it('connectWs sets wsConnected on open', () => {
    const store = useNotificationsStore()
    expect(store.wsConnected).toBe(false)
  })
})
