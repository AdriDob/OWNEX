<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { fetchGuidedNextAction, type GuidedNextAction } from '@/services/ownexData'
import { useOwnexState } from '@/composables/useOwnexState'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useToast } from '@/composables/useToast'
import { useGlobalShortcuts } from '@/composables/useGlobalShortcuts'
import { useThemeEngine } from '@/composables/useThemeEngine'

import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  Flag,
  Folder,
  FolderOpen,
  Globe,
  Home,
  Info,
  Layout,
  Mail,
  PieChart,
  Plus,
  Server,
  Shield,
  ShieldCheck,
  ShieldX,
  Sync,
  TrendingDown,
  TrendingUp,
  Wallet,
} from '@lucide/vue'

import { useRouter } from 'vue-router'

const auth = useAuthStore()
const settings = useSettingsStore()
const { toast } = useToast()
const router = useRouter()
const { digest, capital, ai, incomePlan, agenda } = useOwnexState()
const guidedNext = ref<GuidedNextAction | null>(null)

// Guided Earning: next best action toward first verified revenue
const guidedAction = computed(() => guidedNext.value?.action ?? null)

// ── Command Center State ──

// System status derived from digest
const systemStatus = computed(() => {
  if (!digest.value) return 'unknown'
  const d = digest.value
  // Determine status based on findings and targets
  if (d.targets && d.targets > 0 && d.endpoints && d.endpoints > 0) {
    const rate = d.findings / d.targets
    if (rate > 0.3) return 'healthy'
    if (rate > 0.1) return 'moderate'
    return 'needs_attention'
  }
  return 'initializing'
})

// Next best action derived from agenda and opportunities
const nextAction = computed(() => {
  if (!agenda.value) return null
  const a = agenda.value
  // Find the first actionable item
  if (a.next_actions && a.next_actions.length > 0) {
    return a.next_actions[0]
  }
  // Fallback: look at agenda items
  if (a.items && a.items.length > 0) {
    const first = a.items.find((item: any) => item.status === 'pending' || item.status === 'active')
    if (first) return {
      title: first.title || 'Next action',
      reason: first.reason || 'Requiere atención',
      effort: first.effort || 'medium',
      estimatedReward: first.reward || 0
    }
  }
  return null
})

// KPIs from digest
const kpis = computed(() => {
  if (!digest.value) return []
  const d = digest.value
  return [
    { label: 'Oportunidades', value: d.opportunities?.length || 0, icon: TrendingUp, color: '#00b8ff' },
    { label: 'Ingresos/mes', value: capital.value?.usdPerHour * 160 || 0, icon: DollarSign, color: '#ffab00' },
    { label: 'Fuentes activas', value: d.sources?.length || 0, icon: Globe, color: '#00ff41' },
    { label: 'Pagos pendientes', value: incomePlan.value?.pendingTotal || 0, icon: Clock, color: '#ff6600' }
  ]
})

// Available jobs (opportunities from digest)
const availableJobs = computed(() => {
  if (!digest.value) return []
  const d = digest.value
  return d.opportunities?.slice(0, 5) || []
})

// Compatible sources
const compatibleSources = computed(() => {
  if (!digest.value) return []
  const d = digest.value
  return d.sources?.filter((s: any) => s.argentina_compatible) || []
})

onMounted(async () => {
  try {
    guidedNext.value = await fetchGuidedNextAction()
  } catch {
    guidedNext.value = null
  }
})

function openExternal(url: string) {
  window.open(url, '_blank', 'noopener')
}
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <nav class="border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Home class="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 class="font-medium text-foreground">OWNEX Command Center</h2>
              <p class="text-sm/6 text-muted-foreground">Dashboard personal integrada</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              @click="router.push('/work')"
              class="text-sm px-3 py-1.5"
            >
              Trabajo
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              @click="router.push('/income')"
              class="text-sm px-3 py-1.5"
            >
              Ingresos
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              @click="router.push('/identity')"
              class="text-sm px-3 py-1.5"
            >
              Identidad
            </Button>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <!-- System Status Header -->
      <section class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0" :class="systemStatus === 'healthy' ? 'bg-primary/10 text-primary' : 'bg-border'">
            <Server class="w-6 h-6" />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-foreground mb-1">Estado del Sistema</h3>
            <p class="text-sm/6 text-muted-foreground" :class="systemStatus === 'healthy' ? 'text-success' : 'text-warning'">
              <span v-if="systemStatus !== 'unknown'">{{ systemStatus }}</span>
                <span v-else class="opacity-60">Conectando...</span>
            </p>
          </div>
        </div>

        <!-- Key Metrics Row -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          <KPIBlock 
            v-for="(kpi, i) in kpis" 
            :key="i" 
            :label="kpi.label" 
            :value="kpi.value" 
            :icon="kpi.icon" 
            :color="kpi.color" 
          />
        </div>
      </section>

      <!-- Next Best Action (Guided Earning) -->
      <section v-if="guidedAction" class="mb-6 rounded-lg border border-primary/30 bg-card p-4 sm:p-6">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-primary/10 text-primary">
            <Plus class="w-5 h-5" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs uppercase tracking-widest text-primary mb-1">Próxima Mejor Acción</p>
            <h3 class="font-semibold text-foreground mb-1">{{ guidedAction.title }}</h3>
            <p class="text-sm/6 text-muted-foreground mb-2">{{ guidedAction.instruction }}</p>
            <p class="text-xs text-muted-foreground">
              {{ guidedAction.actor_label }} • {{ guidedAction.justification }}
            </p>
            <div class="flex flex-wrap gap-2 mt-3">
              <Button variant="default" size="sm" @click="router.push('/earning')">
                Ver siguiente acción
              </Button>
              <Button variant="outline" size="sm" @click="router.push(guidedAction.guide_url)">
                Abrir guía del trabajo
              </Button>
              <Button v-if="guidedAction.url" variant="outline" size="sm" @click="openExternal(guidedAction.url)">
                Ir a la plataforma ↗
              </Button>
            </div>
            <div v-if="guidedNext?.alternatives?.length" class="mt-3 border-t border-border pt-3">
              <p class="text-xs text-muted-foreground mb-1">Otras acciones posibles:</p>
              <ul class="space-y-1">
                <li v-for="alt in guidedNext.alternatives" :key="alt.item_id" class="text-xs text-muted-foreground">
                  · {{ alt.title }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <!-- Next Best Action (legacy fallback) -->
      <section v-else-if="nextAction" class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 bg-primary/10 text-primary">
            <Plus class="w-5 h-5" />
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-foreground mb-1">Próxima Mejor Acción</h3>
            <p class="text-sm/6 text-muted-foreground mb-2">
              {{ nextAction.title }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{ nextAction.reason }} • Esfuerzo: {{ nextAction.effort }}
            </p>
            <p class="text-xs font-medium" v-if="nextAction.estimatedReward > 0">
              Recompensa estimada: ${{ nextAction.estimatedReward }}
            </p>
          </div>
          <Button 
            variant="link" 
            size="sm" 
            class="text-primary hover:text-primary/90 flex items-center gap-1"
            @click="router.push('/work/opportunities')"
          >
            Ver detalles
            <svg class="w-3 h-3" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </Button>
        </div>
      </section>

      <!-- Opportunities & Jobs -->
      <section class="mb-6 rounded-lg border border-border bg-card p-4 sm:p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-foreground">Oportunidades Disponibles</h3>
          <Button 
            variant="link" 
            size="sm" 
            class="text-primary hover:text-primary/90"
            @click="router.push('/work/opportunities')"
          >
            Ver todas
            <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7" />
            </svg>
          </Button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <Card v-for="(job, i) in availableJobs" :key="i" class="p-3 hover:bg-hover">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-foreground truncated" :title="job.title">{{ job.title }}</p>
                <p class="text-xs text-muted-foreground">{{ job.source }}</p>
              </div>
              <span class="text-xs rounded bg-primary/10 text-primary px-2 py-0.5">
                ${{ job.reward || 0 }}
              </span>
            </div>
          </Card>
        </div>
      </section>

      <!-- Connected Sources & Income -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <!-- Compatible Sources -->
        <Card class="h-full">
          <div class="p-3">
            <h4 class="font-medium text-foreground mb-2">Fuentes Compatibles con Argentina</h4>
            <p class="text-xs text-muted-foreground">
              {{ compatibleSources.length }} fuentes
            </p>
            <div class="grid grid-cols-2 gap-1 mt-2">
              <span v-for="src in compatibleSources.slice(0, 4)" :key="src.name" class="text-xs rounded bg-primary/10 text-primary px-1.5 py-0.5">
                {{ src.name || 'Fuente' }}
              </span>
            </div>
          </div>
        </Card>

        <!-- Income Status -->
        <Card class="h-full">
          <div class="p-3">
            <h4 class="font-medium text-foreground mb-2">Ingresos</h4>
            <p class="text-xs text-muted-foreground mb-1">Cobrados este mes</p>
            <p class="font-medium" v-if="capital.value">
              ${{ capital.value.usdPerHour * 160 || 0 }}/mes
            </p>
            <p v-else class="text-muted-foreground">Cargando...</p>
          </div>
        </Card>

        <!-- Pending Payments -->
        <Card class="h-full">
          <div class="p-3">
            <h4 class="font-medium text-foreground mb-2">Pagos Pendientes</h4>
            <p class="text-xs text-muted-foreground mb-1">Total pendiente</p>
            <p class="font-medium" v-if="incomePlan.value">
              ${{ incomePlan.value.pendingTotal || 0 }}
            </p>
            <p v-else class="text-muted-foreground">Cargando...</p>
          </div>
        </Card>

        <!-- Connection State -->
        <Card class="h-full">
          <div class="p-3">
            <h4 class="font-medium text-foreground mb-2">Estado de Conexión</h4>
            <p class="text-xs text-muted-foreground">
              <span v-if="auth.isLoggedIn" class="text-success">Conectado</span>
                <span v-else class="text-warning">Desconectado</span>
            </p>
          </div>
        </Card>

        <!-- Alerts -->
        <Card class="h-full">
          <div class="p-3">
            <h4 class="font-medium text-foreground mb-2">Alertas</h4>
            <p class="text-xs text-muted-foreground">
              <span v-if="digest.value?.alerts?.length">
                {{ digest.alerts.length }} alertas
              </span>
                <span v-else class="opacity-60">Ninguna</span>
            </p>
          </div>
        </Card>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* Tesla Theme: No gradients, no glows, pure colors */
:root {
  --primary: #e82127;
  --primary-foreground: #ffffff;
  --background: #0a0a0f;
  --foreground: #fafafa;
  --muted: #71717a;
  --muted-foreground: #a1a1a6;
  --card: #11111a;
  --border: #2a2a3a;
  --input: #1a1a24;
}

/* Ensure no accidental gradients or glows */
* {
  --glow: none;
  --gradient: none;
}
</style>