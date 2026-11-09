import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, getToken, setToken, clearSession, isSessionValid, setSessionExpiry } from '@/lib/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(getToken())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => isSessionValid())

  // ── Level 1: OWNEX Account ──
  // Authenticated session user data
  const ownexAccount = computed(() => user.value)

  async function loginWithCredentials(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post<{ session: { token: string; expires_at?: string }; user: any }>(
        '/auth/users/login', { email, password }, true
      )
      if (res?.session?.token) {
        setToken(res.session.token)
        token.value = res.session.token
        user.value = res.user
        if (res.session.expires_at) {
          setSessionExpiry(res.session.expires_at)
        }
      }
    } catch (e: any) {
      error.value = e?.message || 'Credenciales inválidas'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function loginWithToken(token: string) {
    // Login with a manual JWT token (for platform tokens, bug bounty workflows).
    loading.value = true
    error.value = null
    try {
      // Validate the token by calling the internal sessions validate endpoint
      const res = await api.post<{ valid: boolean; user?: any }>(
        '/auth/internal/sessions/validate', { token }, true
      )
      if (res?.valid && res?.user) {
        setToken(token)
        token.value = token
        user.value = res.user
        // Set session expiry from token if available
        const tokenExpires = Date.now() + 30 * 24 * 60 * 60 * 1000
        setSessionExpiry(String(tokenExpires))
      } else {
        error.value = 'Token inválido o expirado'
        throw new Error('Token inválido o expirado')
      }
    } catch (e: any) {
      error.value = e?.message || 'Error al validar el token'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function autoLogin() {
    if (token.value) return true
    const deviceId = tryGetDeviceId()
    if (!deviceId) return false
    try {
      const res = await api.post<{ session: { token: string; expires_at?: string }; user?: any }>(
        '/auth/login', { device_id: deviceId, device_info: 'vue-frontend' }, true
      )
      if (res?.session?.token) {
        setToken(res.session.token)
        token.value = res.session.token
        if (res.session.expires_at) {
          setSessionExpiry(res.session.expires_at)
        }
        if (res.user) user.value = res.user
        return true
      }
    } catch { /* silent */ }
    return false
  }

  function logout() {
    clearSession()
    token.value = null
    user.value = null
    // Also clear external connections when logging out
    // (will be refetched on next login)
  }

  function tryGetDeviceId(): string | null {
    try { return localStorage.getItem('CATEYE-device-id') } catch { return null }
  }

  // ── Level 2: External Account Connections ──
  // Connected platforms (Fiverr, Freelancer, Direct Work, etc.)
  // These are separate from the OWNEX account but linked to it
  // Connection state is managed by useExternalConnectionManager
  return {
    user, token, loading, error, isAuthenticated,
    ownexAccount,
    // External connection manager access
    getPlatformAccounts: async () => {
      return await (await import('@/composables/useExternalConnectionManager')).getPlatformAccounts()
    },
    storePlatformCredentials: async (provider: string, email: string, token: string) => {
      return await (await import('@/composables/useExternalConnectionManager')).storePlatformCredentials(provider, email, token)
    },
    removePlatformAccount: async (provider: string) => {
      return await (await import('@/composables/useExternalConnectionManager')).removePlatformAccount(provider)
    },
    getPlatformStatus: async (provider: string) => {
      return await (await import('@/composables/useExternalConnectionManager')).getPlatformStatus(provider)
    },
    loginWithToken,
  }
})