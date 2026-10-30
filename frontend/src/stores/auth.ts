import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, clearSession, getToken, isSessionValid, setSessionExpiry, setToken } from '@/lib/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(getToken())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => isSessionValid())

  async function loginWithCredentials(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post<{ session: { token: string; expires_at?: string }; user: any }>(
        '/auth/users/login',
        { email, password },
        true,
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

  async function register(email: string, password: string, displayName?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post<{ session: { token: string; expires_at?: string }; user: any }>(
        '/auth/users/register',
        { email, password, display_name: displayName || email.split('@')[0] },
        true,
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
      error.value = e?.message || 'Error al registrarse'
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
        '/auth/login',
        { device_id: deviceId, device_info: 'vue-frontend' },
        true,
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
    } catch {
      /* silent */
    }
    return false
  }

  function logout() {
    clearSession()
    token.value = null
    user.value = null
  }

  function tryGetDeviceId(): string | null {
    try {
      return localStorage.getItem('CATEYE-device-id')
    } catch {
      return null
    }
  }

  return { user, token, loading, error, isAuthenticated, loginWithCredentials, register, autoLogin, logout }
})
