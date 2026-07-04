import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const mockPost = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({
  api: { post: mockPost },
  getToken: vi.fn(() => localStorage.getItem('CATEYE-token')),
  setToken: vi.fn((t: string) => localStorage.setItem('CATEYE-token', t)),
  clearSession: vi.fn(() => { localStorage.removeItem('CATEYE-token'); localStorage.removeItem('CATEYE-session-expires') }),
  isSessionValid: vi.fn(() => !!localStorage.getItem('CATEYE-token')),
  setSessionExpiry: vi.fn((e: string) => localStorage.setItem('CATEYE-session-expires', e)),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('auth store', () => {
  it('starts unauthenticated with no token', () => {
    const store = useAuthStore()
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('loginWithCredentials sets token and user on success', async () => {
    mockPost.mockResolvedValue({
      session: { token: 'abc123', expires_at: '2027-01-01T00:00:00Z' },
      user: { id: 1, email: 'test@test.com' },
    })
    const store = useAuthStore()
    await store.loginWithCredentials('test@test.com', 'password')
    expect(store.token).toBe('abc123')
    expect(store.user).toEqual({ id: 1, email: 'test@test.com' })
    expect(store.loading).toBe(false)
    expect(localStorage.getItem('CATEYE-token')).toBe('abc123')
  })

  it('loginWithCredentials sets error on failure', async () => {
    mockPost.mockRejectedValue(new Error('Credenciales inválidas'))
    const store = useAuthStore()
    await expect(store.loginWithCredentials('test@test.com', 'wrong')).rejects.toThrow()
    expect(store.error).toBe('Credenciales inválidas')
    expect(store.loading).toBe(false)
    expect(store.token).toBeNull()
  })

  it('register sets token and user on success', async () => {
    mockPost.mockResolvedValue({
      session: { token: 'def456' },
      user: { id: 2, email: 'new@test.com' },
    })
    const store = useAuthStore()
    await store.register('new@test.com', 'password', 'TestUser')
    expect(store.token).toBe('def456')
    expect(store.user).toEqual({ id: 2, email: 'new@test.com' })
    expect(store.loading).toBe(false)
  })

  it('register sets error on failure', async () => {
    mockPost.mockRejectedValue(new Error('Error al registrarse'))
    const store = useAuthStore()
    await expect(store.register('new@test.com', 'password')).rejects.toThrow()
    expect(store.error).toBe('Error al registrarse')
    expect(store.loading).toBe(false)
  })

  it('logout clears token and user', () => {
    const store = useAuthStore()
    store.token = 'abc'
    store.user = { id: 1, email: 'test@test.com' }
    store.logout()
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('CATEYE-token')).toBeNull()
  })

  it('autoLogin returns true on success', async () => {
    mockPost.mockResolvedValue({
      session: { token: 'auto-token' },
      user: { id: 3, email: 'auto@test.com' },
    })
    localStorage.setItem('CATEYE-device-id', 'device-123')
    const store = useAuthStore()
    const result = await store.autoLogin()
    expect(result).toBe(true)
    expect(store.token).toBe('auto-token')
    expect(store.user).toEqual({ id: 3, email: 'auto@test.com' })
  })

  it('autoLogin returns false when already has token', async () => {
    localStorage.setItem('CATEYE-token', 'existing')
    const store = useAuthStore()
    const result = await store.autoLogin()
    expect(result).toBe(true)
    expect(store.token).toBe('existing')
  })

  it('autoLogin returns false without device id', async () => {
    const store = useAuthStore()
    const result = await store.autoLogin()
    expect(result).toBe(false)
  })

  it('autoLogin returns false on API failure', async () => {
    mockPost.mockRejectedValue(new Error('fail'))
    localStorage.setItem('CATEYE-device-id', 'device-123')
    const store = useAuthStore()
    const result = await store.autoLogin()
    expect(result).toBe(false)
  })

  it('isAuthenticated reflects token in localStorage', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    localStorage.setItem('CATEYE-token', 'abc')
    expect(store.isAuthenticated).toBe(false)
    store.token = 'abc'
    expect(store.isAuthenticated).toBe(false)
  })

  it('isAuthenticated is true when created with token', () => {
    localStorage.setItem('CATEYE-token', 'existing-token')
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(true)
  })
})
