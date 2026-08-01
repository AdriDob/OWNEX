<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Activity, Clock, RefreshCw, Shield,
  DollarSign, FileText, BarChart3, HeartPulse,
  Zap, AlertTriangle,
} from '@lucide/vue'
import ThroughputCore from '@/components/dashboard/ThroughputCore.vue'
import WorkCyclesGrid from '@/components/dashboard/WorkCyclesGrid.vue'
import NextBestAction from '@/components/mission-control/NextBestAction.vue'
import AgentFleet from '@/components/mission-control/AgentFleet.vue'
import OpportunityRadar from '@/components/mission-control/OpportunityRadar.vue'
import KnowledgeFeed from '@/components/mission-control/KnowledgeFeed.vue'
import ReportPipeline from '@/components/dashboard/ReportPipeline.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { fetchOwnexDashboard } from '@/services/ownexData'
import type { OwnexDashboardData } from '@/services/ownexData'
import { useAudio } from '@/composables/useAudio'

const router = useRouter()
const dashboard = ref<OwnexDashboardData | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const degraded = ref(false)
let refreshInterval: ReturnType<typeof setInterval> | null = null
const audio = useAudio()

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const systemOk = computed(() => (dashboard.value?.systemHealth ?? 0) >= 70)

const quickActions = [
  { id: 'hunt', label: 'HUNT', icon: Zap, path: '/baby-mode' },
  { id: 'targets', label: 'Security', icon: Shield, path: '/security' },
  { id: 'bounties', label: 'Forge', icon: Activity, path: '/integrations/platforms' },
  { id: 'capital', label: 'Wealth', icon: DollarSign, path: '/capital' },
  { id: 'reports', label: 'Reportes', icon: FileText, path: '/reports/center' },
  { id: 'pipeline', label: 'Pipeline', icon: BarChart3, path: '/operations/pipelines' },
  { id: 'health', label: 'Health', icon: HeartPulse, path: '/operations/health' },
]

async function load() {
  try {
    const data = await fetchOwnexDashboard()
    dashboard.value = data
    degraded.value = false
    error.value = null
    audio.play('success')
  } catch (e: any) {
    if (!dashboard.value) {
      error.value = e?.message || 'Error al cargar'
      audio.play('error')
    } else {
      degraded.value = true
      audio.play('warning')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  audio.play('startup')
  load()
  refreshInterval = setInterval(() => load(), 30000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

// ── Adapters: service shapes → component prop shapes ──

const fleetAgents = computed(() =>
  (dashboard.value?.agents || []).map((a, i) => ({
    id: String(i),
    name: a.name,
    role: a.description || 'Agente',
    status: a.status,
    model: undefined as string | undefined,
    progress: undefined as number | undefined,
    currentTask: a.description,
  })),
)

const radarOpportunities = computed(() =>
  (dashboard.value?.opportunities || []).map((o) => ({
    id: o.id,
    title: o.title,
    platform: 'custom' as const,
    type: (o.type === 'bug-bounty' || o.type === 'vdp' || o.type === 'ctf' || o.type === 'freelance' || o.type === 'research'
      ? o.type : 'research') as 'bug-bounty' | 'vdp' | 'ctf' | 'freelance' | 'research',
    severity: 'info' as const,
    reward: o.reward ? `$${o.reward.toLocaleString()}` : undefined,
    confidence: o.confidence,
    tags: [o.source],
    postedAt: new Date().toISOString(),
  })),
)

const feedItems = computed(() =>
  (dashboard.value?.knowledgeFeed || []).map((k) => ({
    id: k.id,
    type: (k.type === 'alert' || k.type === 'pattern' || k.type === 'learning' || k.type === 'decision'
      ? (k.type === 'alert' ? 'alert' : k.type === 'pattern' ? 'pattern' : k.type === 'learning' ? 'learning' : 'insight')
      : 'system') as 'insight' | 'learning' | 'pattern' | 'alert' | 'achievement' | 'system',
    title: k.message,
    description: k.typeLabel,
    timestamp: k.timestamp,
    tags: [],
  })),
)
</script>

<template>
  <div class="space-y-6 animate-in">
    <LoadingState v-if="loading" />

    <ErrorState
      v-else-if="error && !dashboard"
      title="Error al cargar Mission Control"
      :message="error"
      :retry="load"
    />

    <template v-else>
      <!-- Degraded banner -->
      <div
        v-if="degraded"
        class="flex items-center gap-2 rounded-lg bg-warning/10 border border-warning/30 px-4 py-2 text-xs text-warning"
      >
        <AlertTriangle class="h-3.5 w-3.5 shrink-0" />
        <span>Datos parciales — algunos servicios no responden</span>
      </div>

      <!-- Header -->
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1 min-w-0">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX MISSION CONTROL</span>
            <span class="status-dot" :class="systemOk ? 'status-dot-green' : 'status-dot-red'" />
          </div>
          <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
          <p class="text-[9px] font-mono text-muted-foreground tracking-[0.2em] uppercase">OWNEX ● Personal Autonomous Work OS</p>
          <p class="text-xs text-muted-foreground flex items-center gap-2">
            <Clock class="h-3 w-3" />
            {{ dashboard?.timestamp ? new Date(dashboard.timestamp).toLocaleString() : '—' }}
            <button @click="load" class="text-primary hover:underline flex items-center gap-1">
              <RefreshCw class="h-3 w-3" /> Actualizar
            </button>
          </p>
        </div>
        <div class="panel shrink-0 flex flex-col items-center gap-1 rounded-xl px-6 py-3">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider uppercase">Salud del sistema</span>
          <span
            :class="['text-4xl font-bold font-mono', dashboard && dashboard.systemHealth >= 90 ? 'text-success' : dashboard && dashboard.systemHealth >= 70 ? 'text-warning' : 'text-destructive']"
          >
            {{ dashboard?.systemHealth ?? '—' }}
          </span>
          <span class="font-mono text-[9px] text-muted-foreground uppercase">{{ dashboard?.systemStatus || '—' }}</span>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="flex flex-wrap items-center gap-2 rounded-xl bg-surface/20 border border-border/30 px-4 py-3">
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider text-muted-foreground mr-1">Acciones rápidas</span>
        <button
          v-for="qa in quickActions" :key="qa.id"
          @click="router.push(qa.path)"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-foreground/80 hover:text-foreground hover:bg-primary/10 border border-border/30 transition-colors"
        >
          <component :is="qa.icon" class="h-3.5 w-3.5" />
          {{ qa.label }}
        </button>
      </div>

      <!-- Row 1: Throughput + Agent Fleet -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ThroughputCore
          v-if="dashboard"
          :stages="dashboard.throughputStages"
          :efficiency="dashboard.throughputEfficiency"
          class="lg:col-span-2"
        />
        <ThroughputCore v-else class="lg:col-span-2" />
        <AgentFleet v-if="dashboard" :agents="fleetAgents" />
        <AgentFleet v-else :agents="[]" />
      </div>

      <!-- Row 2: Opportunity Radar + Next Best Action -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <OpportunityRadar
          v-if="dashboard && radarOpportunities.length > 0"
          :opportunities="radarOpportunities"
          class="lg:col-span-2"
        />
        <OpportunityRadar v-else :opportunities="[]" class="lg:col-span-2" />
        <NextBestAction
          v-if="dashboard && dashboard.nextAction"
          :title="dashboard.nextAction.title"
          :description="dashboard.nextAction.reason || 'Revisar prioridades en Mission Control'"
          :primary-action="{ label: 'Ejecutar', variant: 'primary' }"
          :secondary-action="{ label: 'Posponer', variant: 'ghost' }"
          :reasoning="dashboard.nextAction.reason || ''"
          :meta="{
            esfuerzo: dashboard.nextAction.effort || '—',
            recompensa: dashboard.nextAction.estimatedReward
              ? `$${dashboard.nextAction.estimatedReward}`
              : '—',
          }"
        />
        <NextBestAction v-else title="Sin acción pendiente" description="Revisar oportunidades o iniciar un ciclo de trabajo" :primary-action="{ label: 'Ejecutar', variant: 'primary' }" />
      </div>

      <!-- Row 3: Report Pipeline (Daily/Weekly Top -->
      <ReportPipeline />

      <!-- Row 4: Work Cycles -->
      <WorkCyclesGrid />

      <!-- Row 5: Knowledge Feed -->
      <KnowledgeFeed
        v-if="dashboard && feedItems.length > 0"
        :items="feedItems"
      />
      <KnowledgeFeed v-else :items="[]" />
    </template>
  </div>
</template>