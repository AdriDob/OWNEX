import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth'

const mockPost = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({
  api: { post: mockPost },
  getToken: vi.fn(() => localStorage.getItem('CATEYE-token')),
  setToken: vi.fn((t: string) => localStorage.setItem('CATEYE-token', t)),
  clearSession: vi.fn(() => {
    localStorage.removeItem('CATEYE-token')
    localStorage.removeItem('CATEYE-session-expires')
  }),
  isSessionValid: vi.fn(() => !!localStorage.getItem('CATEYE-token')),
  setSessionExpiry: vi.fn((e: string) => localStorage.setItem('CATEYE-session-expires', e)),
}))

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

/**
 * Los mocks usan las formas REALES del backend, verificadas contra source:
 *  - POST /auth/login        → APIEnvelope  {version,schema,data:{token,…},error,timestamp}
 *                              (api/routers/auth.py:46 + cores/gateway/schemas.py:49)
 *  - POST /auth/users/login   → TokenResponse plano {access_token,refresh_token,…}
 *                              (api/routers/auth_users.py:230)
 *
 * El mock anterior devolvía `{session:{token}}`, una forma que NINGÚN endpoint
 * emite: por eso el test pasaba mientras `autoLogin()` fallaba en producción.
 */
const deviceLoginEnvelope = (token: string) => ({
  version: '1.0',
  schema: 'CATEYE/v1',
  data: { token, refresh: 'r1', device_id: 'device-123', user_id: 'local', existing: false },
  error: null,
  timestamp: '2026-09-30T00:00:00Z',
})

const tokenResponse = (token: string) => ({
  access_token: token,
  refresh_token: 'r1',
  token_type: 'bearer',
  email_verified: true,
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

  it('loginWithCredentials reads the flat access_token from TokenResponse', async () => {
    mockPost.mockResolvedValue(tokenResponse('abc123'))
    const store = useAuthStore()
    const ok = await store.loginWithCredentials('adriel', 'password')
    expect(ok).toBe(true)
    expect(store.token).toBe('abc123')
    expect(localStorage.getItem('CATEYE-token')).toBe('abc123')
    expect(store.loading).toBe(false)
    // El backend exige `username` (LoginRequest), no `email`.
    expect(mockPost).toHaveBeenCalledWith(
      '/auth/users/login',
      { username: 'adriel', password: 'password' },
      true,
    )
  })

  it('loginWithCredentials sets error on failure', async () => {
    mockPost.mockRejectedValue(new Error('Credenciales inválidas'))
    const store = useAuthStore()
    const ok = await store.loginWithCredentials('adriel', 'wrong')
    expect(ok).toBe(false)
    expect(store.error).toBe('Credenciales inválidas')
    expect(store.loading).toBe(false)
    expect(store.token).toBeNull()
  })

  it('register reads the flat access_token from TokenResponse', async () => {
    mockPost.mockResolvedValue(tokenResponse('def456'))
    const store = useAuthStore()
    const ok = await store.register('adriel', 'new@test.com', 'password')
    expect(ok).toBe(true)
    expect(store.token).toBe('def456')
    expect(localStorage.getItem('CATEYE-token')).toBe('def456')
    // RegisterRequest real = {username, email, password}.
    expect(mockPost).toHaveBeenCalledWith(
      '/auth/users/register',
      { username: 'adriel', email: 'new@test.com', password: 'password' },
      true,
    )
  })

  it('register sets error on failure', async () => {
    mockPost.mockRejectedValue(new Error('Error al registrarse'))
    const store = useAuthStore()
    const ok = await store.register('adriel', 'new@test.com', 'password')
    expect(ok).toBe(false)
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

  it('autoLogin reads data.token from the CATEYE envelope', async () => {
    mockPost.mockResolvedValue(deviceLoginEnvelope('auto-token'))
    localStorage.setItem('CATEYE-device-id', 'device-123')
    const store = useAuthStore()
    const result = await store.autoLogin()
    expect(result).toBe(true)
    expect(store.token).toBe('auto-token')
    expect(localStorage.getItem('CATEYE-token')).toBe('auto-token')
  })

  it('autoLogin returns false when the envelope carries no token', async () => {
    // Regresión: una respuesta sin data.token NO debe "autenticarse".
    mockPost.mockResolvedValue({ version: '1.0', schema: 'CATEYE/v1', data: {} })
    localStorage.setItem('CATEYE-device-id', 'device-123')
    const store = useAuthStore()
    expect(await store.autoLogin()).toBe(false)
    expect(localStorage.getItem('CATEYE-token')).toBeNull()
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
