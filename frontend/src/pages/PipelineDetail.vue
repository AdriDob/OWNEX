<script setup lang="ts">
import { Activity, AlertTriangle, ArrowLeft, CheckCircle2, Clock, Loader2, RefreshCw, User, XCircle } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BarChart, LineChart } from '@/components/charts'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface StageEntry {
  from_state: string
  to_state: string
  agent_id: string
  status: string
  timestamp: string
  metadata?: Record<string, unknown>
}

interface PipelineInfo {
  id: string
  target_id: number
  target_name: string
  state: string
  retries: number
  quality_score: number
  stages: StageEntry[]
  error: string | null
  created_at: string
}

const route = useRoute()
const router = useRouter()
const pipelineId = computed(() => String(route.params.id))

const pipeline = ref<PipelineInfo | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let interval: ReturnType<typeof setInterval> | null = null

const STATE_ORDER = [
  'pending',
  'discovery',
  'validation',
  'evidence',
  'ai_review',
  'ready',
  'submitted',
  'triaged',
  'paid',
  'closed',
]
const STATE_LABELS: Record<string, string> = {
  pending: 'Pending',
  discovery: 'Discovery',
  validation: 'Validation',
  evidence: 'Evidence',
  ai_review: 'AI Review',
  ready: 'Ready',
  submitted: 'Submitted',
  triaged: 'Triaged',
  paid: 'Paid',
  closed: 'Closed',
}
const STATE_COLORS: Record<string, string> = {
  pending: 'var(--ownex-text-muted)',
  discovery: 'var(--ownex-text-primary)',
  validation: 'var(--ownex-text-secondary)',
  evidence: 'var(--ownex-yellow)',
  ai_review: 'var(--ownex-green)',
  ready: 'var(--ownex-green)',
  submitted: 'var(--ownex-text-secondary)',
  triaged: 'var(--ownex-yellow)',
  paid: 'var(--ownex-text-secondary)',
  closed: 'var(--ownex-green)',
  failed: 'var(--ownex-accent)',
  cancelled: 'var(--ownex-text-muted)',
}

async function fetchPipeline() {
  try {
    const res = await api.get<PipelineInfo>(`/agents/pipelines/${pipelineId.value}`)
    pipeline.value = res
  } catch (e: any) {
    if (!error.value) error.value = e?.message || 'Error al cargar el pipeline'
  } finally {
    loading.value = false
  }
}

function stateProgress(state: string) {
  const idx = STATE_ORDER.indexOf(state)
  return idx >= 0 ? ((idx + 1) / STATE_ORDER.length) * 100 : 0
}

const stageProgressionData = computed(() => {
  if (!pipeline.value) return { labels: [], datasets: [] }
  const labels = STATE_ORDER.map((s) => STATE_LABELS[s] || s)
  const currentIdx = STATE_ORDER.indexOf(pipeline.value.state)
  const data = STATE_ORDER.map((_, i) => (i <= currentIdx ? 1 : 0))
  return {
    labels,
    datasets: [
      {
        label: 'Completado',
        data: data.map((v) => v * 100),
        backgroundColor: data.map((v) => (v ? 'rgba(22,163,74,0.7)' : 'rgba(107,114,128,0.3)')),
      },
    ],
  }
})

const qualityMetricsData = computed(() => {
  if (!pipeline.value) return { labels: [], datasets: [] }
  return {
    labels: ['Calidad', 'Progreso', 'Retries (inv)'],
    datasets: [
      {
        label: 'Métrica',
        data: [
          pipeline.value.quality_score * 100,
          stateProgress(pipeline.value.state),
          Math.max(0, 100 - pipeline.value.retries * 20),
        ],
        backgroundColor: ['rgba(22,163,74,0.7)', 'rgba(255, 255, 255,0.7)', 'rgba(217, 119, 6,0.7)'],
      },
    ],
  }
})

const activeStageIndex = computed(() => STATE_ORDER.indexOf(pipeline.value?.state || 'pending'))

function stageStatus(index: number) {
  if (!pipeline.value) return 'pending'
  if (pipeline.value.state === 'failed' || pipeline.value.state === 'cancelled') return 'failed'
  if (index < activeStageIndex.value) return 'completed'
  if (index === activeStageIndex.value) return 'active'
  return 'pending'
}

const stageEntriesByState = computed(() => {
  if (!pipeline.value) return []
  const groups: { state: string; entries: StageEntry[] }[] = []
  const stateMap = new Map<string, StageEntry[]>()
  for (const stage of pipeline.value.stages) {
    const s = stage.to_state || stage.from_state
    if (!stateMap.has(s)) stateMap.set(s, [])
    stateMap.get(s)!.push(stage)
  }
  for (const state of STATE_ORDER) {
    const entries = stateMap.get(state)
    if (entries && entries.length > 0) {
      groups.push({ state, entries })
    }
  }
  return groups
})

const isTerminal = computed(() => {
  if (!pipeline.value) return false
  return ['closed', 'failed', 'cancelled'].includes(pipeline.value.state)
})

onMounted(() => {
  fetchPipeline()
  if (!isTerminal.value) {
    interval = setInterval(fetchPipeline, 5000)
  }
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 animate-in">
      <Button variant="ghost" size="icon" @click="router.push('/pipelines')">
        <ArrowLeft class="h-4 w-4" />
      </Button>
      <div class="flex-1 min-w-0">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Pipeline</p>
        <h1 class="font-display text-2xl font-bold text-foreground truncate max-w-lg">
          {{ pipeline?.target_name || `Pipeline ${pipelineId}` }}
        </h1>
        <p v-if="pipeline" class="text-xs font-mono text-muted-foreground">{{ pipeline.id }}</p>
      </div>
      <div v-if="pipeline && !isTerminal" class="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 class="h-3.5 w-3.5 animate-spin" />
        Actualizando cada 5s
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error && !pipeline">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar el pipeline</p>
        <p class="mt-1 text-xs text-muted-foreground max-w-md">{{ error }}</p>
        <Button variant="outline" class="mt-4" @click="fetchPipeline">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!pipeline">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Activity class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Pipeline no encontrado</p>
        <p class="mt-1 text-xs text-muted-foreground">El pipeline solicitado no existe</p>
        <Button variant="outline" class="mt-4" @click="router.push('/pipelines')">
          Volver al Monitor
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Activity class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Estado</span>
          </div>
          <Badge
            :variant="pipeline.state === 'failed' ? 'destructive' : pipeline.state === 'closed' ? 'success' : 'info'"
            class="mt-1 text-xs px-2 py-0.5"
          >
            {{ STATE_LABELS[pipeline.state] || pipeline.state }}
          </Badge>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <CheckCircle2 class="h-4 w-4 text-success" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Calidad</span>
          </div>
          <p class="text-2xl font-bold" :class="pipeline.quality_score >= 0.7 ? 'text-success' : pipeline.quality_score >= 0.4 ? 'text-warning' : 'text-destructive'">
            {{ (pipeline.quality_score * 100).toFixed(0) }}%
          </p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <RefreshCw class="h-4 w-4 text-warning" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Reintentos</span>
          </div>
          <p class="text-2xl font-bold text-foreground">{{ pipeline.retries }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Clock class="h-4 w-4 text-accent" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Creado</span>
          </div>
          <p class="text-sm font-semibold text-foreground">{{ new Date(pipeline.created_at).toLocaleDateString('es-AR') }}</p>
        </Card>
      </div>

      <div v-if="pipeline.error" class="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive animate-in">
        <div class="flex items-center gap-2">
          <XCircle class="h-4 w-4 shrink-0" />
          <span>{{ pipeline.error }}</span>
        </div>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-4">
          <Activity class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Progreso</span>
        </div>
        <div class="mb-4">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-muted-foreground">Estado actual: <strong class="text-foreground">{{ STATE_LABELS[pipeline.state] || pipeline.state }}</strong></span>
            <span class="text-xs font-bold text-foreground">{{ Math.round(stateProgress(pipeline.state)) }}%</span>
          </div>
          <div class="h-2 overflow-hidden rounded-full bg-surface">
            <div class="h-full rounded-full bg-gradient-to-r from-primary to-success transition-all duration-700" :style="{ width: `${stateProgress(pipeline.state)}%` }" />
          </div>
        </div>
        <div class="flex gap-1.5">
          <div v-for="(s, i) in STATE_ORDER" :key="s" class="flex-1 flex flex-col items-center gap-1">
            <div
              class="w-full h-2 rounded-sm transition-all duration-300"
              :class="stageStatus(i) === 'completed' ? 'bg-success' : stageStatus(i) === 'active' ? 'bg-primary' : stageStatus(i) === 'failed' ? 'bg-destructive' : 'bg-surface'"
            />
            <span class="text-[8px] text-muted-foreground truncate w-full text-center">{{ STATE_LABELS[s]?.slice(0, 6) }}</span>
          </div>
        </div>
      </Card>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Progresión por Etapa</span>
          </div>
          <BarChart
            :labels="stageProgressionData.labels"
            :datasets="stageProgressionData.datasets"
            :height="200"
            yLabel="%"
            :show-legend="false"
            :horizontal="true"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <CheckCircle2 class="h-4 w-4 text-success" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Métricas de Calidad</span>
          </div>
          <BarChart
            :labels="qualityMetricsData.labels"
            :datasets="qualityMetricsData.datasets"
            :height="200"
            yLabel="%"
            :show-legend="false"
          />
        </Card>
      </div>

      <div v-if="stageEntriesByState.length > 0" class="animate-in">
        <h2 class="text-sm font-semibold text-foreground mb-3">Transiciones de Estado</h2>
        <div class="space-y-3">
          <Card v-for="group in stageEntriesByState" :key="group.state" class="p-3">
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">{{ STATE_LABELS[group.state] || group.state }}</p>
            <div class="space-y-2">
              <div v-for="(entry, i) in group.entries" :key="i" class="flex items-center gap-3 text-xs">
                <div class="flex items-center gap-1.5 min-w-0 flex-1">
                  <User class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span class="font-mono text-muted-foreground truncate">{{ entry.agent_id?.slice(0, 12) || '—' }}</span>
                </div>
                <Badge
                  :variant="entry.status === 'completed' ? 'success' : entry.status === 'failed' ? 'destructive' : 'warning'"
                  class="text-[9px] px-1.5 py-0 shrink-0"
                >{{ entry.status }}</Badge>
                <span class="text-muted-foreground shrink-0">{{ new Date(entry.timestamp).toLocaleTimeString('es-AR') }}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
