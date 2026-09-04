import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('useCompanion', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.resetModules()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  const setupFetch = (mockImpl: any) => {
    vi.stubGlobal('fetch', vi.fn(mockImpl))
  }

  it('should initialize with empty status and null lastPoll', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { status, lastPoll } = useCompanion()

    expect(status.value).toEqual({})
    expect(lastPoll.value).toBeNull()
  })

  it('should poll status and update on success', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { status, lastPoll, pollStatus } = useCompanion()

    setupFetch(
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ cpu: 50, memory: 60, disk: 30 }),
      }),
    )

    await pollStatus()

    expect(status.value).toEqual({ cpu: 50, memory: 60, disk: 30 })
    expect(lastPoll.value).not.toBeNull()
    expect(fetch).toHaveBeenCalledWith('/api/mobile/status')
  })

  it('should start polling at given interval', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { startPolling, stopPolling } = useCompanion()

    setupFetch(
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ cpu: 50 }),
      }),
    )

    startPolling(60000)

    // Initial poll should have run
    expect(fetch).toHaveBeenCalledTimes(1)

    // Advance timer by interval
    vi.advanceTimersByTime(60000)

    // Second poll should have run
    expect(fetch).toHaveBeenCalledTimes(2)

    // Stop polling
    stopPolling()

    // Advance timer again - no more polls
    vi.advanceTimersByTime(60000)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('should not start polling twice', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { startPolling } = useCompanion()

    setupFetch(
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ cpu: 50 }),
      }),
    )

    startPolling(60000)
    startPolling(60000) // Second call should be no-op

    vi.advanceTimersByTime(60000)

    // Only initial + one interval
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('should stop polling and clear timer', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { startPolling, stopPolling } = useCompanion()

    setupFetch(
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ cpu: 50 }),
      }),
    )

    startPolling(60000)
    // Initial poll runs immediately
    expect(fetch).toHaveBeenCalledTimes(1)

    stopPolling()

    // Advance timer - no more polls
    vi.advanceTimersByTime(60000)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('should not update status on fetch error (network failure)', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { status, lastPoll, pollStatus } = useCompanion()

    setupFetch(vi.fn().mockRejectedValue(new Error('Network error')))

    await pollStatus()

    expect(status.value).toEqual({})
    expect(lastPoll.value).toBeNull()
  })

  it('should not update status on non-ok response', async () => {
    const { useCompanion } = await import('./useCompanion')
    const { status, lastPoll, pollStatus } = useCompanion()

    setupFetch(
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      }),
    )

    await pollStatus()

    expect(status.value).toEqual({})
    expect(lastPoll.value).toBeNull()
  })

  it('should return all expected methods', async () => {
    const { useCompanion } = await import('./useCompanion')
    const companion = useCompanion()

    expect(typeof companion.pollStatus).toBe('function')
    expect(typeof companion.startPolling).toBe('function')
    expect(typeof companion.stopPolling).toBe('function')
    expect(companion.status).toBeDefined()
    expect(companion.lastPoll).toBeDefined()
  })
})
