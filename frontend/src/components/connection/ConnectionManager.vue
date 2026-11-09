<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useOwnexState } from '@/composables/useOwnexState'
import { useAuthStore } from '@/stores/auth'
import { useExternalConnectionManager } from '@/composables/useExternalConnectionManager'
import { useToast } from '@/composables/useToast'
import { useRouter } from 'vue-router'

import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Option from '@/components/ui/Option.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import { Plus, Minus, CheckCircle, XCircle, Sync, Clock, AlertTriangle, Shield, Info, LogIn, LogOut } from '@lucide/vue'

const auth = useAuthStore()
const { toast } = useToast()
const router = useRouter()
const { digest, capital, ai, incomePlan, agenda } = useOwnexState()

// Initialize external connection manager
const ecm = useExternalConnectionManager()

// Wait for auth to be ready before loading connections
watch(
  () => auth.isAuthenticated,
  async (authenticated) => {
    if (authenticated) {
      await ecm.loadExternalConnections()
    }
  }
)

// ── Level 1: OWNEX Account Status ──
const ownexStatus = computed(() => ({
  authenticated: auth.isAuthenticated,
  user: auth.user ? {
    id: auth.user?.id,
    name: auth.user?.displayName || auth.user?.email?.split('@')[0],
    email: auth.user?.email,
  } : null,
  // Derived: since we have two levels, show OWNEX account first
  level: 'OWNEX Account' as 'OWNEX Account' | 'External Connections',
}))

// ── Level 2: External Connections ──
const {
  externalConnections,
  connectionLoading,
  connectionError,
  connectionRefreshing,
  connectionTestResults,
  totalEarnings,
  totalPending,
  connectionSummary,
  connect,
  authenticate,
  test,
  sync,
  refresh,
  remove,
  getConnection,
  requiresAuthentication,
} = ecm

// Available providers for connection
const availableProviders = ['fiverr', 'freelancer', 'direct_work']

// ── UI State ──
const selectedProvider = ref<string | null>(null)
const connectForm = ref({
  provider: '' as string,
  email: '' as string,
  token: '' as string,
})

// ── Render Sections ──

// Level 1: OWNEX Account
const level1Section = computed(() => ({
  title: 'Nivel 1: Cuenta OWNEX',
  subtitle: 'Sesión authenticated y datos de usuario',
  content: auth.isAuthenticated
    ? `
      <div class="space-y-3">
        <p class="text-sm text-foreground">Usuario conectado</p>
        <p class="text-xs text-muted-foreground">
          <span class="font-medium">${auth.user?.displayName || auth.user?.email?.split('@')[0] || 'Sin nombre'}</span>
          <span class="ml-2 text-muted-foreground">(${auth.user?.email || 'sin email'})</span>
        </p>
        <Button 
          variant="link" 
          size="sm" 
          class="text-primary/90"
          @click="router.push('/identity')"
        >
          Gestionar identidad
        </Button>
      </div>
    `
    : `
      <div class="space-y-3 p-4 border border-border rounded-lg bg-card">
        <p class="text-sm text-muted-foreground">Iniciar sesión para acceder a la identidad completa</p>
        <Button 
          variant="primary" 
          size="sm" 
          @click="router.push('/activation')"
        >
          Iniciar Sesión
        </Button>
      </div>
    `,
}))

// Level 2: External Connections Summary
const level2Summary = computed(() => {
  const { healthy, total, percentage } = connectionSummary.value
  return {
    title: 'Nivel 2: Conexiones Externas',
    subtitle: `${healthy} de ${total} conexiones saludables (${percentage}%)`,
    statusColor: healthy > 0 ? 'text-success' : 'text-warning',
  }
})

// Available connections list
const connectionList = computed(() => {
  return externalConnections.value.map((conn) => ({
    ...conn,
    // Add display-friendly fields
    displayName: conn.username || conn.email || conn.provider,
    healthClass: conn.health_status === 'healthy' ? 'bg-primary/10 text-primary' :
                  conn.health_status === 'unhealthy' ? 'bg-error/10 text-error' :
                  'bg-muted/10 text-muted',
    healthIcon: conn.health_status === 'healthy' ? 'CheckCircle' :
                conn.health_status === 'unhealthy' ? 'XCircle' :
                'Clock',
  }))
})

// Connection actions state
const actionLoading = ref<{ provider: string; action: string; loading: boolean }>({} as any)

// Connection test result for display
const testResult = ref<{ provider: string; valid: boolean; message: string } | null>(null)

// Open connect modal / flow
async function openConnectFlow(provider: string) {
  selectedProvider.value = provider
  connectForm.value = {
    provider,
    email: '',
    token: '',
  }
}

// Close connect flow
function closeConnectFlow() {
  selectedProvider.value = null
  connectForm.value = {
    provider: '',
    email: '',
    token: '',
  }
}

// Execute connect
async function executeConnect() {
  const { provider } = connectForm.value
  if (!provider) return

  const success = await connect({
    provider,
    email: connectForm.value.email,
    token: connectForm.value.token,
  })
  if (success) {
    toast.success(`${provider} conectado correctamente`)
    closeConnectFlow()
    // Refresh connections
    await ecm.loadExternalConnections()
  } else {
    toast.error('Error al conectar ' + provider)
  }
}

// Execute authenticate
async function executeAuthenticate() {
  const provider = (connectForm.value || {}).provider
  if (!provider) return

  const result = await authenticate(provider)
  testResult.value = result

  if (result.valid) {
    toast.success('Autenticación exitosa: ' + result.message)
  } else {
    toast.error('Error de autenticación: ' + result.message)
  }
}

// Execute test
async function executeTest() {
  const provider = (connectForm.value || {}).provider
  if (!provider) return

  const result = await test(provider)
  testResult.value = result

  if (result.valid) {
    toast.success('Test exitoso: ' + result.message)
  } else {
    toast.error('Error en test: ' + result.message)
  }
}

// Execute sync
async function executeSync() {
  const provider = (connectForm.value || {}).provider
  if (!provider) return

  const result = await sync(provider)
  if (result.success) {
    toast.success('Sincronización completada: ' + result.message)
    await ecm.loadExternalConnections()
  } else {
    toast.error('Error en sincronización: ' + result.message)
  }
}

// Execute refresh
async function executeRefresh() {
  const provider = (connectForm.value || {}).provider
  if (!provider) return

  const result = await refresh(provider)
  if (result.success) {
    toast.success('Credenciales actualizadas: ' + result.message)
    await ecm.loadExternalConnections()
  } else {
    toast.error('Error al actualizar: ' + result.message)
  }
}

// Execute remove
async function executeRemove(provider: string) {
  const result = await remove(provider)
  if (result.success) {
    toast.success('Conexión eliminada')
    await ecm.loadExternalConnections()
  } else {
    toast.error('Error al eliminar: ' + result.message)
  }
}
</script>

<template>
  <div class="min-h-screen bg-background/80 backdrop-blur-sm text-foreground">
    <!-- Top Bar -->
    <header class="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50 px-4 py-3">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Shield class="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 class="font-medium text-foreground">External Connection Manager</h2>
            <p class="text-xs text-muted-foreground">Nivel 2: Conexiones a plataformas externas</p>
          </div>
        </div>
        <Button 
          variant="link" 
          size="sm" 
          @click="router.push('/identity')"
          class="text-sm text-primary/90 flex items-center gap-1"
        >
          Identidad
          <svg class="w-3 h-3" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
          </svg>
        </Button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <!-- Level 1: OWNEX Account -->
      <section class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <h3 class="font-semibold text-foreground mb-2">{{ level1Section.value.title }}</h3>
        <p class="text-sm text-muted-foreground">{{ level1Section.value.subtitle }}</p>
        <div v-html="level1Section.value.content" />
      </section>

      <!-- Level 2 Summary -->
      <section v-if="externalConnections.length > 0" class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <h3 class="font-semibold text-foreground mb-2">{{ level2Summary.value.title }}</h3>
        <p :class="level2Summary.value.statusColor">
          {{ level2Summary.value.subtitle }}
        </p>

        <!-- KPIs for connections -->
        <div class="grid grid-cols-2 gap-2 mt-4">
          <span class="px-3 py-1 rounded bg-primary/10 text-primary text-xs">
            {{ totalEarnings.value }} USD (ganancias)
          </span>
          <span class="px-3 py-1 rounded bg-yellow/10 text-yellow text-xs">
            {{ totalPending.value }} USD (pendientes)
          </span>
        </div>

        <!-- Connection Health Progress -->
        <div class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-muted-foreground">Estado de conexiones</span>
            <span class="text-sm font-medium">
              {{ connectionSummary.value.healthy }} / {{ connectionSummary.value.total }} saludables
            </span>
          </div>
          <div class="w-full bg-border rounded-full h-2">
            <div 
              class="bg-primary rounded-full h-2 transition-width"
              :style="{ width: `${connectionSummary.value.percentage}%` }"
            />
          </div>
        </div>
      </section>

      <!-- No connections message -->
      <section v-else class="mb-6 rounded-lg border border-border bg-card p-6 text-center">
        <Info class="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
        <h3 class="font-medium text-foreground mb-2">No hay conexiones externas</h3>
        <p class="text-muted-foreground">
          Conecta plataformas externas (Fiverr, Freelancer, Direct Work) para
          monitorear ingresos, pagos y oportunidades desde tus cuentas.
        </p>
        <Button 
          variant="primary" 
          size="sm" 
          @click="openConnectFlow('fiverr')"
        >
          Conectar Primera Plataforma
        </Button>
      </section>

      <!-- Connections List -->
      <section v-if="externalConnections.length > 0" class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-foreground">
            {{ externalConnections.length }} conexión{{ externalConnections.length > 1 ? 'es' : 'a' }}
          </h3>
          <Button 
            variant="link" 
            size="sm" 
            class="text-primary/90 flex items-center gap-1"
            @click="router.push('/identity')"
          >
            Ver todo
            <svg class="w-3 h-3" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </Button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Card
            v-for="(conn, i) in connectionList" :key="i"
            class="p-3 hover:bg-hover"
          >
            <div class="flex items-start gap-3">
              <!-- Health status indicator -->
              <div class="w-3 h-3 rounded-full flex-shrink-0"
                :class="conn.healthClass"
              >
                <CheckCircle class="w-1.5 h-1.5 text-primary" v-if="conn.health_status === 'healthy'" />
                <XCircle class="w-1.5 h-1.5 text-error" v-if="conn.health_status === 'unhealthy'" />
                <Clock class="w-1.5 h-1.5 text-muted" v-else />
              </div>

              <div class="flex-1 min-w-0">
                <p class="font-medium text-foreground truncated" title="{{ conn.displayName }}">
                  {{ conn.displayName }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ conn.last_checked || 'Sin verificar' }}
                </p>
              </div>

              <div class="flex gap-1.5 flex-shrink-0">
                <!-- Earnings badge -->
                <span v-if="conn.earnings" class="text-xs rounded bg-primary/10 text-primary px-1.5 py-0.5">
                  ${{ conn.earnings }}
                </span>

                <!-- Pending badge -->
                <span v-if="conn.pending" class="text-xs rounded bg-yellow/10 text-yellow px-1.5 py-0.5">
                  ${{ conn.pending }} pend
                </span>

                <!-- Action buttons -->
                <Button 
                  variant="link" 
                  size="icon" 
                  class="p-1"
                  @click="openConnectFlow(conn.provider)"
                  title="Reconectar"
                >
                  <Plus class="w-3 h-3" />
                </Button>
                <Button 
                  variant="link" 
                  size="icon" 
                  class="p-1"
                  @click="executeAuthenticate()"
                  title="Autenticar"
                  v-if="!conn.health_status || conn.health_status !== 'healthy'"
                >
                  <Shield class="w-3 h-3" />
                </Button>
                <Button 
                  variant="link" 
                  size="icon" 
                  class="p-1"
                  @click="executeSync(conn.provider)"
                  title="Sincronizar"
                >
                  <Sync class="w-3 h-3" />
                </Button>
                <Button 
                  variant="link" 
                  size="icon" 
                  class="p-1 text-error"
                  @click="executeRemove(conn.provider)"
                  title="Eliminar"
                >
                  <XCircle class="w-3 h-3" />
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </section>

      <!-- Connection Action Modal / Flow -->
      <transition name="fade">
        <div v-if="selectedProvider" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div class="bg-white rounded-lg p-6 max-w-sm w-full shadow-2xl transform scale-100 transition-transform">
            <h3 class="font-semibold text-foreground mb-4">
              Conectar {{ selectedProvider }}
            </h3>

            <div v-if="!connectionError" class="mb-4">
              <p class="text-sm text-muted-foreground mb-2">
                Conecta {{ selectedProvider }} para recibir oportunidades,
                rastrear ingresos y sincronizar pagos.
              </p>

              <Input
                v-model="connectForm.email"
                type="email"
                placeholder="Email de la cuenta"
                class="w-full mb-3"
                :disabled="connectForm.provider !== selectedProvider"
              />
              <Input
                v-model="connectForm.token"
                type="password"
                placeholder="Token o contraseña (opcional)"
                class="w-full mb-3"
                :disabled="connectForm.provider !== selectedProvider"
              />
            </div>

            <div class="space-y-3">
              <!-- Connect button -->
              <Button
                v-if="!connectionLoading[selectedProvider]"
                variant="primary"
                :disabled="!connectForm.email"
                @click="executeConnect"
              >
                <span v-if="connectionLoading[selectedProvider]">
                  Conectando...
                </span>
                <span v-else>
                  Conectar {{ selectedProvider }}
                </span>
              </Button>

              <!-- Test Authentication -->
              <Button
                variant="link"
                size="sm"
                class="text-primary/90 w-full justify-center"
                @click="executeAuthenticate"
                :disabled="connectionTestResults[`test-${selectedProvider}`]?.valid"
              >
                <span v-if="connectionTestResults[`test-${selectedProvider}`]?.valid">
                  ✓ Autenticado
                </span>
                <span v-else>
                  <span v-if="testResult?.provider === selectedProvider && !testResult?.valid">
                    ✗ Error: {{ testResult?.message }}
                  </span>
                  <span v-else>
                    Autenticar
                  </span>
                </span>
              </Button>

              <!-- Sync button -->
              <Button
                variant="link"
                size="sm"
                class="text-success/90 w-full justify-center mt-2"
                @click="executeSync"
                :disabled="connectionRefreshing[`sync-${selectedProvider}`]"
              >
                <span v-if="connectionRefreshing[`sync-${selectedProvider}`]">
                  Sincronizando...
                </span>
                <span v-else>
                  Sincronizar datos
                </span>
              </Button>

              <!-- Refresh credentials -->
              <Button
                variant="link"
                size="sm"
                class="text-warning/90 w-full justify-center mt-2"
                @click="executeRefresh"
                :disabled="connectionRefreshing[`refresh-${selectedProvider}`]"
              >
                <span v-if="connectionRefreshing[`refresh-${selectedProvider}`]">
                  Actualizando...
                </span>
                <span v-else>
                  Actualizar credenciales
                </span>
              </Button>

              <!-- Remove connection -->
              <Button
                variant="danger"
                size="sm"
                class="text-error w-full justify-center mt-2"
                @click="executeRemove(selectedProvider)"
                :disabled="connectionLoading[selectedProvider]"
              >
                <span v-if="connectionLoading[selectedProvider]">
                  Eliminando...
                </span>
                <span v-else>
                  Eliminar conexión
                </span>
              </Button>
            </div>

            <button
              class="mt-4 text-sm text-muted-foreground hover:text-foreground"
              @click="closeConnectFlow"
            >
              Cancelar
            </button>
          </div>
        </div>
      </transition>

      <!-- Test Result Toast -->
      <transition name="fade">
        <div v-if="testResult" class="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
          <div :class="testResult.valid ? 'bg-success text-success' : 'bg-error text-error'" 
               class="px-6 py-3 rounded-lg max-w-sm w-full shadow-lg">
            <div class="flex items-center gap-2">
              <span v-if="testResult.valid" class="text-success">
                <CheckCircle class="w-4 h-4" />
              </span>
              <span v-else class="text-error">
                <XCircle class="w-4 h-4" />
              </span>
              <span>{{ testResult.message }}</span>
            </div>
            <button
              class="ml-auto text-xs text-foreground/70 hover:text-foreground"
              @click="testResult = null"
            >
              Cerrar
            </button>
          </div>
        </div>
      </transition>
    </main>
  </div>
</template>

<style scoped>
/* Connection Manager specific styles */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Provider badge colors */
.provider-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 500;
}

.provider-fiverr {
  background: #FFC949;
  color: #1a1a1a;
}

.provider-freelancer {
  background: #006b75;
  color: #ffffff;
}

.provider-direct-work {
  background: #e82127;
  color: #ffffff;
}
</style>