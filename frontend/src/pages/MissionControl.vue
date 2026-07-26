<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import {
  Activity, Clock, RefreshCw, Shield,
  DollarSign, FileText, BarChart3, HeartPulse,
  Zap,
} from '@lucide/vue'
import ThroughputCore from '@/components/dashboard/ThroughputCore.vue'
import WorkCyclesGrid from '@/components/dashboard/WorkCyclesGrid.vue'
import NextBestAction from '@/components/dashboard/NextBestAction.vue'
import AgentFleet from '@/components/dashboard/AgentFleet.vue'
import OpportunityRadar from '@/components/dashboard/OpportunityRadar.vue'
import KnowledgeFeed from '@/components/dashboard/KnowledgeFeed.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

const router = useRouter()
const data = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const autoRefresh = ref(true)
let refreshInterval: ReturnType<typeof setInterval> | null = null

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const healthColor = (score: number) => {
  if (score >= 90) return 'text-success'
  if (score >= 70) return 'text-warning'
  return 'text-destructive'
}

const quickActions = [
  { id: 'hunt', label: 'HUNT', icon: Zap, path: '/baby-mode' },
  { id: 'targets', label: 'Security', icon: Shield, path: '/targets' },
  { id: 'bounties', label: 'Forge', icon: Activity, path: '/integrations/platforms' },
  { id: 'capital', label: 'Wealth', icon: DollarSign, path: '/capital' },
  { id: 'reports', label: 'Reportes', icon: FileText, path: '/reports/center' },
  { id: 'pipeline', label: 'Pipeline', icon: BarChart3, path: '/operations/pipelines' },
  { id: 'health', label: 'Health', icon: HeartPulse, path: '/operations/health' },
]

async function fetchAll() {
  try {
    const res = await api.get<any>('/mission/status')
    data.value = res
    error.value = null
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAll()
  refreshInterval = setInterval(() => {
    if (autoRefresh.value) fetchAll()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="space-y-6 animate-in">
    <LoadingState v-if="loading" />

    <ErrorState
      v-else-if="error && !data"
      title="Error al cargar Mission Control"
      :message="error"
      :retry="fetchAll"
    />

    <template v-else>
      <!-- Header -->
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1 min-w-0">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX MISSION CONTROL</span>
            <span v-if="data" class="status-dot" :class="data.system?.health_score >= 70 ? 'status-dot-green' : 'status-dot-red'" />
          </div>
          <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
          <p class="text-[9px] font-mono text-muted-foreground tracking-[0.2em] uppercase">OWNEX ● Personal Autonomous Work OS</p>
          <p class="text-xs text-muted-foreground flex items-center gap-2">
            <Clock class="h-3 w-3" />
            {{ data?.system?.timestamp ? new Date(data.system.timestamp).toLocaleString() : '—' }}
            <button @click="fetchAll" class="text-primary hover:underline flex items-center gap-1">
              <RefreshCw class="h-3 w-3" /> Actualizar
            </button>
          </p>
        </div>
        <div v-if="data" class="panel shrink-0 flex flex-col items-center gap-1 rounded-xl px-6 py-3">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider uppercase">Salud del sistema</span>
          <span :class="['text-4xl font-bold font-mono', healthColor(data.system?.health_score || 0)]">{{ data.system?.health_score || '—' }}</span>
          <span class="font-mono text-[9px] text-muted-foreground uppercase">{{ data.system?.status || '—' }}</span>
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
        <ThroughputCore class="lg:col-span-2" />
        <AgentFleet />
      </div>

      <!-- Row 2: Opportunity Radar + Next Best Action -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <OpportunityRadar class="lg:col-span-2" />
        <NextBestAction />
      </div>

      <!-- Row 3: Work Cycles -->
      <WorkCyclesGrid />

      <!-- Row 4: Knowledge Feed -->
      <KnowledgeFeed />
    </template>
  </div>
</template>
