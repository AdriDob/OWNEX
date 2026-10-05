import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, clearSession, getToken, isSessionValid, setToken } from '@/lib/api'
import type { DeviceLoginEnvelope, TokenResponse } from '@/types/index'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(getToken())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => isSessionValid())

  /**
   * Login por credenciales contra `/auth/users/login`.
   * Contrato real (api/routers/auth_users.py): LoginRequest exige `username`
   * (no email) y la respuesta es un TokenResponse plano con `access_token`
   * — sin envelope y sin `session`. Antes se mandaba `{email,password}` y se
   * leía `res.session.token`, lo que producía 422 y un token nunca guardado.
   */
  async function loginWithCredentials(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post<TokenResponse>(
        '/auth/users/login',
        { username, password },
        true,
      )
      if (res?.access_token) {
        setToken(res.access_token)
        token.value = res.access_token
        user.value = { username }
        return true
      }
      error.value = 'Credenciales inválidas'
      return false
    } catch (e: any) {
      error.value = e?.message || 'Credenciales inválidas'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Contrato real: RegisterRequest = { username, email, password }. */
  async function register(username: string, email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.post<TokenResponse>(
        '/auth/users/register',
        { username, email, password },
        true,
      )
      if (res?.access_token) {
        setToken(res.access_token)
        token.value = res.access_token
        user.value = { username, email }
        return true
      }
      error.value = 'No se pudo completar el registro'
      return false
    } catch (e: any) {
      error.value = e?.message || 'Error al registrarse'
      return false
    } finally {
      loading.value = false
    }
  }

  async function autoLogin() {
    if (token.value) return true
    const deviceId = tryGetDeviceId()
    if (!deviceId) return false
    try {
      // Contrato real: APIEnvelope → data.token (antes leíamos res.session.token,
      // clave que ningún endpoint emite ⇒ el token nunca se guardaba).
      const res = await api.post<DeviceLoginEnvelope>(
        '/auth/login',
        { device_id: deviceId, device_info: 'vue-frontend' },
        true,
      )
      const issued = res?.data?.token
      if (issued) {
        setToken(issued)
        token.value = issued
        return true
      }
    } catch {
      /* silent — sin backend la app sigue navegable, la API protege las mutaciones */
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
