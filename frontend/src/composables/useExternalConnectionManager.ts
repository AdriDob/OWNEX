/**
 * useExternalConnectionManager — Manejo de conexiones externas a plataformas
 *
 * Two-level identity system:
 * Level 1: OWNEX Account — authenticated session, internal user data
 * Level 2: External Account Connections — connected platforms (GitHub, HackerOne, etc.)
 *
 * Canonical backend: /api/connection-manager (api/routers/connection_manager.py)
 * Credential SSOT: cores.identity_vault (AES-256-GCM). No secrets leave the backend.
 *
 * Connection states (OWNEX v10):
 * NOT_CONNECTED, CONNECTING, CONNECTED, EXPIRED, ERROR, REVOKED, MANUAL_SETUP, UNSUPPORTED
 */
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'

export type ConnectionState =
  | 'NOT_CONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'EXPIRED'
  | 'ERROR'
  | 'REVOKED'
  | 'MANUAL_SETUP'
  | 'UNSUPPORTED'

export interface PlatformConnection {
  provider: string
  connected: boolean
  state?: ConnectionState
  auth_mechanism?: string
  username?: string
  email?: string
  earnings?: number
  pending?: number
  last_sync?: string
  created_at?: string
  has_credentials?: boolean
  last_checked?: string
  session_state?: string
  health_status?: 'healthy' | 'unhealthy' | 'unknown'
  requires_authentication?: boolean
}

interface ConnectionManagerAccount {
  provider: string
  state: ConnectionState
  auth_mechanism: string
  connect_supported: boolean
  source_count: number
  email: string
  has_credentials: boolean
  session_state: string | null
  health_status: string | null
  last_checked: string | null
}

export interface ConnectionManagerState {
  loading: boolean
  error: string | null
  refreshing: Record<string, boolean>
  testResults: Record<string, { valid: boolean; message: string }>
  syncStatus: Record<string, { pending: boolean; last?: string }>
}

export interface ConnectOptions {
  provider: string
  email?: string
  token?: string
  password?: string
  onComplete?: (success: boolean, account?: PlatformConnection) => void
}

function toPlatformConnection(a: ConnectionManagerAccount): PlatformConnection {
  return {
    provider: a.provider,
    connected: a.has_credentials,
    state: a.state,
    auth_mechanism: a.auth_mechanism,
    email: a.email || undefined,
    has_credentials: a.has_credentials,
    last_checked: a.last_checked || undefined,
    session_state: a.session_state || a.state,
    health_status: (a.health_status as PlatformConnection['health_status']) || 'unknown',
  }
}

export const useExternalConnectionManager = () => {
  const auth = useAuthStore()
  const toast = useToast()
  const router = useRouter()

  // State: Level 1 - OWNEX Account (authenticated session)
  const ownexAccount = ref<any>(null)
  const isOwnexAuthenticated = computed(() => auth.isAuthenticated && !!ownexAccount.value)

  // State: Level 2 - External Account Connections
  const externalConnections = ref<PlatformConnection[]>([])
  const connectionLoading = ref(false)
  const connectionError = ref<string | null>(null)
  const connectionRefreshing = ref<Record<string, boolean>>({})
  const connectionTestResults = ref<Record<string, { valid: boolean; message: string }>>({})
  const connectionSyncStatus = ref<Record<string, { pending: boolean; last?: string }>>({})

  // Initialize: Load both ownex account and external connections
  async function initialize() {
    ownexAccount.value = auth.user
    await loadExternalConnections()
  }

  // Load external connections from the canonical Connection Manager API
  async function loadExternalConnections() {
    if (!auth.isAuthenticated) return
    connectionLoading.value = true
    connectionError.value = null
    try {
      const result = await api.get<{ accounts: ConnectionManagerAccount[] }>(
        '/connection-manager/accounts'
      )
      externalConnections.value = (result.accounts || []).map(toPlatformConnection)
    } catch (e: any) {
      connectionError.value = e?.message || 'Error al cargar conexiones'
      toast.error(connectionError.value)
    } finally {
      connectionLoading.value = false
    }
  }

  // Connect to a new platform (stores credentials via the vault)
  async function connect(options: ConnectOptions): Promise<PlatformConnection | null> {
    const { provider, email, token, password, onComplete } = options
    connectionLoading.value = true
    connectionError.value = null

    try {
      if (!email || (!token && !password)) {
        throw new Error('Email y token o contraseña son requeridos')
      }
      const account = await api.post<ConnectionManagerAccount>(
        `/connection-manager/accounts/${encodeURIComponent(provider)}/connect`,
        { email, token: token || '', password: password || '' }
      )
      await loadExternalConnections()
      const mapped = toPlatformConnection(account)
      onComplete?.(true, mapped)
      return mapped
    } catch (e: any) {
      connectionError.value = e?.message || 'Error al conectar'
      toast.error(connectionError.value)
      onComplete?.(false)
      return null
    } finally {
      connectionLoading.value = false
    }
  }

  // Authenticate / check status of a provider connection
  async function authenticate(provider: string): Promise<{ valid: boolean; message: string }> {
    if (!auth.isAuthenticated) {
      return { valid: false, message: 'Sesión OWNEX no autenticada' }
    }

    const key = `test-${provider}`
    connectionTestResults.value[key] = { valid: false, message: 'Probando...' }

    try {
      const result = await api.get<{
        state: ConnectionState
        session_health?: any
        health_status?: string | null
      }>(`/connection-manager/accounts/${encodeURIComponent(provider)}/status`)

      const valid = result.state === 'CONNECTED'
      connectionTestResults.value[key] = {
        valid,
        message: valid
          ? 'Conexión verificada'
          : `Estado de conexión: ${result.state}`,
      }
      return connectionTestResults.value[key]
    } catch (e: any) {
      connectionTestResults.value[key] = {
        valid: false,
        message: e?.message || 'Error al autenticar',
      }
      return connectionTestResults.value[key]
    }
  }

  // Test connection with a provider (same flow as authenticate)
  async function test(provider: string): Promise<{ valid: boolean; message: string }> {
    return authenticate(provider)
  }

  // Sync data from a provider — honest status check (no fake sync endpoint yet)
  async function sync(provider: string): Promise<{ success: boolean; message: string; accounts?: PlatformConnection[] }> {
    if (!auth.isAuthenticated) {
      return { success: false, message: 'Sesión OWNEX no autenticada' }
    }

    const key = `sync-${provider}`
    connectionRefreshing.value[key] = true

    try {
      const result = await api.get<{ state: ConnectionState; last_checked?: string | null }>(
        `/connection-manager/accounts/${encodeURIComponent(provider)}/status`
      )
      await loadExternalConnections()
      connectionRefreshing.value[key] = false
      return {
        success: true,
        message: `Estado consultado: ${result.state}`,
        accounts: externalConnections.value,
      }
    } catch (e: any) {
      connectionRefreshing.value[key] = false
      const message = e?.message || 'Error durante la sincronización'
      return { success: false, message }
    }
  }

  // Refresh credentials — requires re-entering credentials (no silent refresh)
  async function refresh(provider: string): Promise<{ success: boolean; message: string }> {
    if (!auth.isAuthenticated) {
      return { success: false, message: 'Sesión OWNEX no autenticada' }
    }

    const key = `refresh-${provider}`
    connectionRefreshing.value[key] = true

    try {
      await loadExternalConnections()
      connectionRefreshing.value[key] = false
      return {
        success: true,
        message: 'Para renovar credenciales, reconecta la plataforma',
      }
    } catch (e: any) {
      connectionRefreshing.value[key] = false
      const message = e?.message || 'Error al actualizar credenciales'
      return { success: false, message }
    }
  }

  // Remove/disconnect a platform account
  async function remove(provider: string): Promise<{ success: boolean; message: string }> {
    if (!auth.isAuthenticated) {
      return { success: false, message: 'Sesión OWNEX no autenticada' }
    }

    try {
      await api.post(`/connection-manager/accounts/${encodeURIComponent(provider)}/disconnect`, {})
      await loadExternalConnections()
      return { success: true, message: 'Conexión eliminada' }
    } catch (e: any) {
      const message = e?.message || 'Error al eliminar la conexión'
      return { success: false, message }
    }
  }

  // Get a specific connection by provider
  function getConnection(provider: string): PlatformConnection | undefined {
    return externalConnections.value.find(c => c.provider === provider)
  }

  // Check if any provider requires authentication
  function requiresAuthentication(provider: string): boolean {
    const conn = getConnection(provider)
    return !!conn?.requires_authentication
  }

  // Computed: total earnings across all connected platforms
  const totalEarnings = computed(() => {
    return externalConnections.value
      .filter(c => c.earnings && c.earnings > 0)
      .reduce((sum, c) => sum + (c.earnings || 0), 0)
  })

  // Computed: total pending across all connected platforms
  const totalPending = computed(() => {
    return externalConnections.value
      .filter(c => c.pending && c.pending > 0)
      .reduce((sum, c) => sum + (c.pending || 0), 0)
  })

  // Computed: connection status summary (CONNECTED state preferred)
  const connectionSummary = computed(() => {
    const healthy = externalConnections.value.filter(
      c => c.state ? c.state === 'CONNECTED' : c.health_status === 'healthy'
    ).length
    const total = externalConnections.value.length
    return { healthy, total, percentage: total > 0 ? Math.round((healthy / total) * 100) : 0 }
  })

  // Watch for auth changes - reload connections when auth changes
  watch(
    () => auth.isAuthenticated,
    async (authenticated) => {
      if (authenticated) {
        await loadExternalConnections()
      }
    }
  )

  return {
    // Level 1: OWNEX Account
    ownexAccount,
    isOwnexAuthenticated,

    // Level 2: External Connections
    externalConnections,
    connectionLoading,
    connectionError,
    connectionRefreshing,
    connectionTestResults,
    connectionSyncStatus,

    // Actions
    initialize,
    loadExternalConnections,
    connect,
    authenticate,
    test,
    sync,
    refresh,
    remove,
    getConnection,

    // Computeds
    totalEarnings,
    totalPending,
    connectionSummary,

    // Helpers
    requiresAuthentication,
  }
}
