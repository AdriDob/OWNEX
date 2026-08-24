/**
 * Backend discovery + lifecycle tests (FASE 3/4/7 contract).
 *
 * The module under test is imported OUTSIDE Tauri in vitest, so:
 *   - isTauri === false → getApiBase() is same-origin '/api'
 *   - the Tauri event/invoke/poll wiring never boots
 * The __testHooks surface drives state transitions deterministically.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  __testHooks,
  backendLifecycle,
  backendPort,
  backendStatus,
  getApiBase,
  getWsBase,
  isTauri,
  markStopping,
  whenBackendReady,
  wsUrl,
} from '../backend'

describe('backend discovery (web mode)', () => {
  it('is not Tauri and resolves API base to same-origin /api', () => {
    expect(isTauri).toBe(false)
    expect(getApiBase()).toBe('/api')
  })

  it('derives WebSocket base from page origin', () => {
    expect(getWsBase()).toMatch(/^wss?:\/\//)
    expect(wsUrl('/ws/terminal')).toMatch(/^wss?:\/\/[^/]+\/ws\/terminal$/)
  })

  it('wsUrl appends token as query param', () => {
    const url = wsUrl('/ws/x', 'abc def')
    expect(url).toContain('token=abc%20def')
  })
})

describe('lifecycle transitions', () => {
  beforeEach(() => {
    __testHooks.setAttempts(0)
  })

  it('starts STARTING outside ready', () => {
    expect(['STARTING', 'READY']).toContain(backendLifecycle.value)
  })

  it('setResolved flips READY with port + status', () => {
    __testHooks.setResolved(8042)
    expect(backendLifecycle.value).toBe('READY')
    expect(backendPort.value).toBe(8042)
    expect(backendStatus.value).toBe('ready')
    expect(__testHooks.internal.resolved()).toBe(true)
  })

  it('markUnreachable surfaces FAILED lifecycle', () => {
    __testHooks.markUnreachable()
    expect(backendLifecycle.value).toBe('FAILED')
    expect(backendStatus.value).toBe('unreachable')
    expect(__testHooks.internal.resolved()).toBe(false)
  })

  it('attempts beyond cold-start budget degrade STARTING -> DEGRADED', () => {
    __testHooks.setAttempts(999)
    expect(backendLifecycle.value).toBe('DEGRADED')
    __testHooks.setAttempts(1)
    expect(backendLifecycle.value).toBe('STARTING')
  })
})

describe('whenBackendReady gate (Tauri mode)', () => {
  beforeEach(() => {
    __testHooks.setTauri(true)
    __testHooks.markUnreachable()
    __testHooks.setAttempts(0)
  })

  afterEach(() => {
    __testHooks.setTauri(false)
  })

  it('resolves false on timeout while unresolved (real error, no fake data)', async () => {
    const ok = await whenBackendReady(150)
    expect(ok).toBe(false)
  })

  it('resolves true immediately once resolved', async () => {
    __testHooks.setResolved(8000)
    const ok = await whenBackendReady(50)
    expect(ok).toBe(true)
  }, 1000)

  it('resolves true when resolution lands mid-wait', async () => {
    const pending = whenBackendReady(2000)
    setTimeout(() => __testHooks.setResolved(8055), 60)
    const ok = await pending
    expect(ok).toBe(true)
  }, 3000)

  it('STOPPING short-circuits to false (no new requests during teardown)', async () => {
    markStopping()
    const ok = await whenBackendReady(5000)
    expect(ok).toBe(false)
  }, 2000)

  it('gate recovers: after STOPPING a fresh resolution returns true again', async () => {
    markStopping()
    __testHooks.setResolved(8060)
    const ok = await whenBackendReady(100)
    expect(ok).toBe(true)
  }, 1000)
})
