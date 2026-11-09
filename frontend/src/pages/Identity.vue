<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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
import { Plus, Minus, Check, Shield, Info, Globe, Target, Clock, Eye } from '@lucide/vue'

const auth = useAuthStore()
const { toast } = useToast()
const router = useRouter()

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
const isOwnexAuthenticated = computed(() => auth.isAuthenticated)

const ownexAccountInfo = computed(() => {
  if (!auth.user) return null
  return {
    id: auth.user?.id,
    name: auth.user?.displayName || auth.user?.email?.split('@')[0] || 'Sin nombre',
    email: auth.user?.email,
    joined: new Date(auth.user?.created_at || Date.now()).toLocaleDateString(),
  }
})

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
</script>

<template>
  <div class="min-h-screen bg-background/80 backdrop-blur-sm text-foreground">
    <!-- Top Bar with two-level identity indicator -->
    <header class="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50 px-4 py-3">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <!-- Level 1: OWNEX Account -->
          <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
            :class="isOwnexAuthenticated.value ? 'bg-primary/10 text-primary' : 'bg-border'"
          >
            <Globe class="w-5 h-5" v-if="isOwnexAuthenticated.value" />
            <Key v-else class="w-5 h-5" />
          </div>
          <div class="hidden sm:block">
            <h2 class="font-medium text-foreground">Identity Center</h2>
            <p class="text-xs text-muted-foreground">Nivel 1: Cuenta OWNEX</p>
          </div>
          <div class="sm:hidden">
            <p class="text-xs text-muted-foreground">OWNEX Account</p>
          </div>
        </div>

        <!-- Level 2: Connection status indicator -->
        <div class="flex items-center gap-2">
          <span class="text-xs rounded bg-primary/10 text-primary px-2 py-0.5">
            {{ connectionSummary.value.healthy }} / {{ connectionSummary.value.total }} conectadas
          </span>
          <Button
            variant="link"
            size="sm"
            class="text-primary/90 flex items-center gap-1"
            @click="router.push('/identity')"
          >
            Gestionar
            <svg class="w-3 h-3" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </Button>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <!-- Level 1: OWNEX Account -->
      <section class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
            :class="isOwnexAuthenticated.value ? 'bg-primary/10 text-primary' : 'bg-border'"
          >
            <Globe class="w-6 h-6" v-if="isOwnexAuthenticated.value" />
            <Key v-else class="w-6 h-6" />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-foreground">
              {{ isOwnexAuthenticated.value ? 'OWNEX Account Active' : 'Inicia Sesión para Acceso Completo' }}
            </h3>
            <p v-if="isOwnexAuthenticated.value" class="text-sm text-muted-foreground">
              Bienvenido de vuelta, {{ ownexAccountInfo.value?.name || 'Operador' }}
            </p>
            <p v-else class="text-sm text-muted-foreground">
              Inicia sesión para acceder a todas las features, conexiones externas y gestión de identidad.
            </p>
          </div>
        </div>

        <!-- Account actions -->
        <div class="mt-4 pt-4 border-t border-border">
          <Button
            v-if="isOwnexAuthenticated.value"
            variant="link"
            size="sm"
            class="text-primary/90"
            @click="router.push('/work/opportunities')"
          >
            Ver Oportunidades
            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </Button>
          <Button
            v-if="isOwnexAuthenticated.value"
            variant="link"
            size="sm"
            class="text-primary/90 ml-2"
            @click="openConnectFlow('fiverr')"
          >
            Conectar Fiverr
          </Button>
          <Button
            v-if="isOwnexAuthenticated.value"
            variant="link"
            size="sm"
            class="text-primary/90 ml-2"
            @click="openConnectFlow('freelancer')"
          >
            Conectar Freelancer
          </Button>
          <Button
            v-if="isOwnexAuthenticated.value"
            variant="link"
            size="sm"
            class="text-primary/90 ml-2"
            @click="openConnectFlow('direct_work')"
          >
            Conectar Direct Work
          </Button>
          <Button
            v-if="!isOwnexAuthenticated.value"
            variant="primary"
            size="sm"
            @click="router.push('/activation')"
          >
            Iniciar Sesión
          </Button>
        </div>
      </section>

      <!-- Level 2: External Connections -->
      <section v-if="isOwnexAuthenticated.value" class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <h3 class="font-semibold text-foreground mb-2">Nivel 2: Conexiones Externas</h3>
        <p class="text-sm text-muted-foreground">
          {{ connectionSummary.value.healthy }} de {{ connectionSummary.value.total }} conexiones
          saludables ({{ connectionSummary.value.percentage }}%)
        </p>

        <!-- Earnings/KPIs -->
        <div class="grid grid-cols-2 gap-2 mt-4">
          <span class="px-3 py-1 rounded bg-primary/10 text-primary text-xs">
            ${{ totalEarnings.value }} USD (ganancias)
          </span>
          <span class="px-3 py-1 rounded bg-yellow/10 text-yellow text-xs">
            ${{ totalPending.value }} USD (pendientes)
          </span>
        </div>

        <!-- Connections list -->
        <div class="mt-4 space-y-3">
          <Card
            v-for="(conn, i) in externalConnections" :key="i"
            class="p-3 hover:bg-hover rounded-none border-0"
          >
            <div class="flex items-start gap-3">
              <!-- Health status -->
              <div class="w-2 h-2 rounded-full flex-shrink-0"
                :class="conn.health_status === 'healthy' ? 'bg-primary' :
                       conn.health_status === 'unhealthy' ? 'bg-error' : 'bg-muted'"
              >
              </div>

              <div class="flex-1 min-w-0">
                <p class="font-medium text-foreground truncated" title="{{ conn.displayName }}">
                  {{ conn.displayName || conn.provider }}
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ conn.last_checked || 'Sin verificar' }}
                </p>
              </div>

              <div class="flex gap-1 flex-shrink-0">
                <!-- Earnings -->
                <span v-if="conn.earnings" class="text-xs rounded bg-primary/10 text-primary px-1.5 py-0.5">
                  ${{ conn.earnings }}
                </span>

                <!-- Pending -->
                <span v-if="conn.pending" class="text-xs rounded bg-yellow/10 text-yellow px-1.5 py-0.5">
                  ${{ conn.pending }} pend
                </span>

                <!-- Buttons -->
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
                  :title="conn.health_status !== 'healthy' ? 'Autenticar' : 'Conexión OK'"
                  :disabled="conn.health_status === 'healthy'"
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
                  <Clock class="w-3 h-3" />
                </Button>
                <Button
                  variant="link"
                  size="icon"
                  class="p-1 text-error"
                  @click="executeRemove(conn.provider)"
                  title="Eliminar"
                >
                  <Minus class="w-3 h-3" />
                </Button>
              </div>
            </div>
          </Card>

          <!-- No connections message -->
          <div v-if="externalConnections.length === 0" class="p-3 text-center text-muted-foreground">
            <Info class="w-6 h-6 mx-auto mb-2" />
            <p>No hay conexiones externas conectadas</p>
            <Button
              variant="link"
              size="sm"
              @click="openConnectFlow('fiverr')"
            >
              Conectar Primera Plataforma
            </Button>
          </div>
        </div>
      </section>

      <!-- Test Result Toast -->
      <transition name="fade">
        <div v-if="testResult" class="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
          <div :class="testResult.valid ? 'bg-success text-success' : 'bg-error text-error'"
               class="px-6 py-3 rounded-lg max-w-sm w-full shadow-lg">
            <div class="flex items-center gap-2">
              <span v-if="testResult.valid" class="text-success">
                <Check class="w-4 h-4" />
              </span>
              <span v-else class="text-error">
                <X class="w-4 h-4" />
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
/* Identity/Connection page specific styles */
.connection-provider-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 500;
}

.connection-provider-fiverr {
  background: #FFC949;
  color: #1a1a1a;
}

.connection-provider-freelancer {
  background: #006b75;
  color: #ffffff;
}

.connection-provider-direct-work {
  background: #e82127;
  color: #ffffff;
}

/* Toast container */
.toast-container {
  z-index: 100;
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease-out;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>