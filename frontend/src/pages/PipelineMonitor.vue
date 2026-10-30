<script setup lang="ts">
import { AlertTriangle, Filter, Play, Trash2, XCircle } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BarChart from '@/components/charts/BarChart.vue'
import Badge from '@/components/ui/Badge.vue'
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
  error: string
  created_at: string
}

const router = useRouter()
const pipelines = ref<PipelineInfo[]>([])
const filter = ref('')
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

async function fetchPipelines() {
  try {
    const url = filter.value ? `/agents/pipelines?status=${filter.value}` : '/agents/pipelines'
    const res = await api.get<{ pipelines: PipelineInfo[] }>(url)
    pipelines.value = res.pipelines || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar pipelines'
  } finally {
    loading.value = false
  }
}

async function handleCancel(id: string) {
  try {
    await api.post(`/agents/pipelines/${id}/cancel`)
    fetchPipelines()
  } catch {
    /* ignore */
  }
}
async function handleDelete(id: string) {
  try {
    await api.delete(`/agents/pipelines/${id}`)
    fetchPipelines()
  } catch {
    /* ignore */
  }
}
async function handleStart() {
  const targetName = prompt('Target name (domain or IP):')
  if (!targetName) return
  try {
    await api.post('/agents/pipeline/start', { target_id: 0, target_name: targetName })
    setTimeout(fetchPipelines, 1000)
  } catch {
    /* ignore */
  }
}

const activePipelines = computed(() =>
  pipelines.value.filter((p) => !['closed', 'failed', 'cancelled'].includes(p.state)),
)
const completedPipelines = computed(() =>
  pipelines.value.filter((p) => ['closed', 'failed', 'cancelled'].includes(p.state)),
)

function stateProgress(state: string) {
  const idx = STATE_ORDER.indexOf(state)
  return idx >= 0 ? ((idx + 1) / STATE_ORDER.length) * 100 : 0
}

onMounted(() => {
  fetchPipelines()
  interval = setInterval(fetchPipelines, 5000)
})
onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between animate-in">
      <div class="min-w-0">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Operations</p>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Pipeline Monitor</h1>
        <p class="text-sm text-muted-foreground">{{ pipelines.length }} pipelines | {{ activePipelines.length }} active</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <select v-model="filter" @change="fetchPipelines"
          class="rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground outline-none focus:border-primary/30"
        >
          <option value="">All</option>
          <option value="discovery">Discovery</option>
          <option value="validation">Validation</option>
          <option value="evidence">Evidence</option>
          <option value="ai_review">AI Review</option>
          <option value="ready">Ready</option>
          <option value="submitted">Submitted</option>
          <option value="triaged">Triaged</option>
          <option value="paid">Paid</option>
          <option value="closed">Closed</option>
          <option value="failed">Failed</option>
        </select>
        <button aria-label="Handlestart" @click="handleStart"
          class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90"
        >
          <Play class="h-3.5 w-3.5" /> New Pipeline
        </button>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Skeleton v-for="i in 3" :key="i" class="h-48 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <button aria-label="Fetchpipelines" @click="fetchPipelines" class="mt-4 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white">Reintentar</button>
      </div>
    </template>

    <template v-else-if="pipelines.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Filter class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay pipelines</p>
        <p class="mt-1 text-xs text-muted-foreground">Iniciá un nuevo pipeline para comenzar</p>
        <button aria-label="Handlestart" @click="handleStart"
          class="mt-4 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white"
        >
          Start Pipeline
        </button>
      </div>
    </template>

    <template v-else>
      <!-- Pipeline Status Chart -->
      <Card class="p-4 animate-in mb-4">
        <h3 class="text-xs font-semibold text-foreground mb-3">Estado de Pipelines</h3>
        <BarChart
          :labels="STATE_ORDER"
          :datasets="[{ label: 'Cantidad', data: STATE_ORDER.map(s => pipelines.filter(p => p.state === s).length) }]"
          :height="200"
        />
      </Card>

      <template v-if="activePipelines.length > 0">
        <div>
          <p class="mb-3 text-xs font-semibold text-foreground">Active ({{ activePipelines.length }})</p>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div v-for="p in activePipelines" :key="p.id"
              class="animate-in cursor-pointer rounded-xl border border-border/40 bg-surface/50 p-4 transition-all hover:border-primary/30"
              @click="router.push(`/pipeline/${p.id}`)"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="min-w-0">
                  <p class="text-sm font-semibold text-foreground truncate">{{ p.target_name || `Target #${p.target_id}` }}</p>
                  <p class="text-[10px] font-mono text-muted-foreground">{{ p.id.slice(0, 12) }}...</p>
                </div>
                <Badge :variant="STATE_COLORS[p.state] === 'var(--ownex-green)' ? 'default' : 'warning'" class="text-[10px]">{{ p.state }}</Badge>
              </div>
              <!-- Progress bar -->
              <div class="mb-3">
                <div class="flex justify-between mb-1">
                  <span class="text-[10px] text-muted-foreground">Progress</span>
                  <span class="text-[10px] font-bold text-foreground">{{ Math.round(stateProgress(p.state)) }}%</span>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-surface">
                  <div class="h-full rounded-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500" :style="{ width: `${stateProgress(p.state)}%` }" />
                </div>
                <div class="mt-2 flex gap-0.5">
                  <div v-for="s in STATE_ORDER" :key="s" :title="s"
                    class="h-1.5 flex-1 rounded-sm transition-all"
                    :class="p.state === 'failed' || p.state === 'cancelled' ? 'bg-destructive' : STATE_ORDER.indexOf(s) < STATE_ORDER.indexOf(p.state) ? 'bg-success' : s === p.state ? 'bg-primary' : 'bg-border-light'"
                  />
                </div>
              </div>
              <div class="mb-3 grid grid-cols-2 gap-3">
                <div>
                  <p class="text-[10px] text-muted-foreground">Quality</p>
                  <p class="text-lg font-bold" :class="p.quality_score >= 0.7 ? 'text-success' : p.quality_score >= 0.4 ? 'text-warning' : 'text-destructive'">
                    {{ (p.quality_score * 100).toFixed(0) }}%
                  </p>
                </div>
                <div>
                  <p class="text-[10px] text-muted-foreground">Retries</p>
                  <p class="text-lg font-bold text-foreground">{{ p.retries }}</p>
                </div>
              </div>
              <div v-if="p.error" class="mb-3 rounded-md bg-destructive/10 px-2 py-1 text-[11px] text-destructive">{{ p.error }}</div>
              <div class="flex gap-2">
                <button @click.stop="handleCancel(p.id)"
                  class="rounded-md border border-warning bg-surface px-2.5 py-1 text-[10px] font-semibold text-warning"
                >Cancel</button>
                <button @click.stop="handleDelete(p.id)"
                  class="rounded-md border border-destructive bg-surface px-2.5 py-1 text-[10px] font-semibold text-destructive"
                >Delete</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="completedPipelines.length > 0">
        <div>
          <p class="mb-3 text-xs font-semibold text-muted-foreground">History ({{ completedPipelines.length }})</p>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div v-for="p in completedPipelines" :key="p.id"
              class="animate-in cursor-pointer rounded-xl border border-border/30 bg-surface/30 p-4 transition-all hover:border-primary/20 opacity-70 hover:opacity-100"
              @click="router.push(`/pipeline/${p.id}`)"
            >
              <div class="flex items-start justify-between mb-2">
                <div class="min-w-0">
                  <p class="text-sm font-semibold text-foreground truncate">{{ p.target_name || `Target #${p.target_id}` }}</p>
                  <p class="text-[10px] font-mono text-muted-foreground">{{ p.id.slice(0, 12) }}...</p>
                </div>
                <Badge variant="default" class="text-[10px]">{{ p.state }}</Badge>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <p class="text-[10px] text-muted-foreground">Quality</p>
                  <p class="text-sm font-bold" :class="p.quality_score >= 0.7 ? 'text-success' : p.quality_score >= 0.4 ? 'text-warning' : 'text-destructive'">
                    {{ (p.quality_score * 100).toFixed(0) }}%
                  </p>
                </div>
                <div>
                  <p class="text-[10px] text-muted-foreground">Retries</p>
                  <p class="text-sm font-bold text-foreground">{{ p.retries }}</p>
                </div>
              </div>
              <button @click.stop="handleDelete(p.id)"
                class="mt-2 rounded-md border border-destructive bg-surface px-2.5 py-1 text-[10px] font-semibold text-destructive"
              >Delete</button>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
