import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useHuntStore } from '@/stores/hunt'

const mockApi = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('hunt store', () => {
  it('starts idle', () => {
    const store = useHuntStore()
    expect(store.status).toBe('idle')
    expect(store.isActive).toBe(false)
    expect(store.label).toBe('Idle')
    expect(store.startedAt).toBeNull()
    expect(store.findingsFound).toBe(0)
    expect(store.targetsScanned).toBe(0)
    expect(store.loading).toBe(false)
  })

  it('start transitions to running', async () => {
    mockApi.post.mockResolvedValue({ status: 'running', started_at: '2025-01-01T00:00:00Z' })
    const store = useHuntStore()
    await store.start()
    expect(store.status).toBe('running')
    expect(store.startedAt).toBe('2025-01-01T00:00:00Z')
    expect(store.isActive).toBe(true)
    expect(store.label).toBe('Running')
    expect(store.loading).toBe(false)
  })

  it('start reverts to idle on failure', async () => {
    mockApi.post.mockRejectedValue(new Error('fail'))
    const store = useHuntStore()
    await store.start()
    expect(store.status).toBe('idle')
    expect(store.loading).toBe(false)
  })

  it('pause transitions to paused', async () => {
    mockApi.post.mockResolvedValue({})
    const store = useHuntStore()
    store.status = 'running'
    await store.pause()
    expect(store.status).toBe('paused')
    expect(store.isActive).toBe(true)
    expect(store.label).toBe('Paused')
    expect(store.loading).toBe(false)
  })

  it('pause keeps current status on failure', async () => {
    mockApi.post.mockRejectedValue(new Error('fail'))
    const store = useHuntStore()
    store.status = 'running'
    await store.pause()
    expect(store.status).toBe('running')
  })

  it('resume transitions to running', async () => {
    mockApi.post.mockResolvedValue({})
    const store = useHuntStore()
    store.status = 'paused'
    await store.resume()
    expect(store.status).toBe('running')
    expect(store.loading).toBe(false)
  })

  it('resume keeps current status on failure', async () => {
    mockApi.post.mockRejectedValue(new Error('fail'))
    const store = useHuntStore()
    store.status = 'paused'
    await store.resume()
    expect(store.status).toBe('paused')
  })

  it('stop transitions to idle', async () => {
    mockApi.post.mockResolvedValue({})
    const store = useHuntStore()
    store.status = 'running'
    store.startedAt = '2025-01-01T00:00:00Z'
    await store.stop()
    expect(store.status).toBe('idle')
    expect(store.startedAt).toBeNull()
    expect(store.isActive).toBe(false)
    expect(store.loading).toBe(false)
  })

  it('stop keeps current status on failure', async () => {
    mockApi.post.mockRejectedValue(new Error('fail'))
    const store = useHuntStore()
    store.status = 'running'
    store.startedAt = '2025-01-01T00:00:00Z'
    await store.stop()
    expect(store.status).toBe('running')
    expect(store.startedAt).toBe('2025-01-01T00:00:00Z')
  })

  it('fetchStatus updates all fields', async () => {
    mockApi.get.mockResolvedValue({
      status: 'running',
      started_at: '2025-06-01T00:00:00Z',
      findings_found: 42,
      targets_scanned: 7,
    })
    const store = useHuntStore()
    await store.fetchStatus()
    expect(store.status).toBe('running')
    expect(store.startedAt).toBe('2025-06-01T00:00:00Z')
    expect(store.findingsFound).toBe(42)
    expect(store.targetsScanned).toBe(7)
  })

  it('fetchStatus silently ignores errors', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useHuntStore()
    store.status = 'running'
    await store.fetchStatus()
    expect(store.status).toBe('running')
  })

  it('isActive is false when idle', () => {
    const store = useHuntStore()
    expect(store.isActive).toBe(false)
    store.status = 'running'
    expect(store.isActive).toBe(true)
    store.status = 'paused'
    expect(store.isActive).toBe(true)
    store.status = 'idle'
    expect(store.isActive).toBe(false)
  })

  it('label returns correct text for each state', () => {
    const store = useHuntStore()
    expect(store.label).toBe('Idle')
    store.status = 'running'
    expect(store.label).toBe('Running')
    store.status = 'paused'
    expect(store.label).toBe('Paused')
  })
})
