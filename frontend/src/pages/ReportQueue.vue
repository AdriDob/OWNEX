<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { FileText, DollarSign, TrendingUp, Clock, RefreshCw, ArrowRight, AlertTriangle, CheckCircle2, Zap } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'

interface QueueItem {
  id: number; report_id: number; report_title: string; report_status: string
  program: string; vulnerability: string; estimated_reward: number
  confidence_score: number; acceptance_probability: number
  expected_value: number; priority_score: number; priority_rank: number | null
  time_to_submit: string | null; reasoning: string | null
}

const router = useRouter()
const items = ref<QueueItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const recomputing = ref(false)
const filterTime = ref<string>('')

onMounted(async () => { await fetchQueue() })

async function fetchQueue() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: 100 }
    if (filterTime.value) params.time_filter = filterTime.value
    const res = await api.get<{ items: QueueItem[]; total: number }>('/economic/report-queue', params)
    items.value = res.items || []
  } catch (e: any) { error.value = e?.message || 'Error al cargar la cola de reportes' }
  finally { loading.value = false }
}

async function recompute() {
  recomputing.value = true
  try {
    await api.post('/economic/report-queue/recompute')
    await fetchQueue()
  } catch { /* ignore */ }
  finally { recomputing.value = false }
}

const totalExpected = computed(() => items.value.reduce((s, i) => s + i.expected_value, 0))

const statusDistribution = computed(() => {
  const counts: Record<string, number> = {}
  for (const item of items.value) {
    const s = item.report_status || 'unknown'
    counts[s] = (counts[s] || 0) + 1
  }
  return { labels: Object.keys(counts), data: Object.values(counts) }
})

function timeBadge(t: string | null) {
  if (t === 'immediate') return 'destructive' as const
  if (t === 'today') return 'warning' as const
  if (t === 'this_week') return 'info' as const
  return 'default' as const
}

function timeLabel(t: string | null) {
  if (t === 'immediate') return 'Urgente'
  if (t === 'today') return 'Hoy'
  if (t === 'this_week') return 'Esta semana'
  if (t === 'this_month') return 'Este mes'
  return '—'
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Report Queue</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Cola Priorizada</h1>
      <p class="text-sm text-muted-foreground">Reportes ordenados por valor esperado — dinero primero</p>
    </div>

    <!-- Summary + Controls -->
    <div class="flex flex-wrap items-center justify-between gap-3 animate-in">
      <div class="flex items-center gap-4">
        <Card class="p-3">
          <p class="text-[10px] text-muted-foreground">Valor esperado total</p>
          <p class="text-lg font-bold text-gold">${{ totalExpected.toFixed(0) }}</p>
        </Card>
        <Card class="p-3">
          <p class="text-[10px] text-muted-foreground">Reportes en cola</p>
          <p class="text-lg font-bold text-foreground">{{ items.length }}</p>
        </Card>
      </div>
      <div class="flex items-center gap-2">
        <select v-model="filterTime" @change="fetchQueue"
          class="rounded-lg border border-border/60 bg-surface/60 px-3 py-2 text-xs text-foreground">
          <option value="">Todos</option>
          <option value="immediate">Urgentes</option>
          <option value="today">Hoy</option>
          <option value="this_week">Esta semana</option>
          <option value="this_month">Este mes</option>
        </select>
        <Button variant="outline" size="sm" :disabled="recomputing" @click="recompute">
          <RefreshCw class="mr-1 h-3 w-3" :class="{ 'animate-spin': recomputing }" />
          Recalcular
        </Button>
      </div>
    </div>

    <template v-if="loading">
      <div class="space-y-2"><Skeleton v-for="i in 5" :key="i" class="h-16 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="fetchQueue">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="items.length">
      <Card v-if="statusDistribution.labels.length" class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Distribución por Estado</h3>
        <DoughnutChart :labels="statusDistribution.labels" :data="statusDistribution.data" :height="200" />
      </Card>

      <div class="space-y-2 animate-in">
        <div v-for="(item, i) in items" :key="item.id"
          class="flex items-center gap-4 rounded-xl border border-border/40 bg-surface/40 p-4 transition-all hover:border-primary/30 cursor-pointer"
          :style="{ animationDelay: `${i * 30}ms` }"
          @click="router.push({ name: 'reports' })">
          <!-- Rank -->
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
            :class="item.priority_rank && item.priority_rank <= 3 ? 'bg-destructive/15 text-destructive' : 'bg-surface/40 text-muted-foreground'">
            {{ item.priority_rank || i + 1 }}
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-foreground truncate">{{ item.report_title || item.vulnerability || 'Reporte #' + item.report_id }}</p>
            <p class="text-xs text-muted-foreground">{{ item.program }} · {{ item.vulnerability }} · <Badge variant="outline" class="text-[9px]">{{ item.report_status }}</Badge></p>
          </div>
          <!-- Stats -->
          <div class="hidden sm:flex items-center gap-4 text-xs text-muted-foreground">
            <div class="text-center">
              <p class="text-[10px]">Reward</p>
              <p class="font-semibold text-foreground">${{ item.estimated_reward.toFixed(0) }}</p>
            </div>
            <div class="text-center">
              <p class="text-[10px]">Confianza</p>
              <p class="font-semibold" :class="item.confidence_score >= 0.7 ? 'text-success' : item.confidence_score >= 0.4 ? 'text-warning' : 'text-muted-foreground'">{{ (item.confidence_score * 100).toFixed(0) }}%</p>
            </div>
            <div class="text-center">
              <p class="text-[10px]">Aceptación</p>
              <p class="font-semibold text-foreground">{{ (item.acceptance_probability * 100).toFixed(0) }}%</p>
            </div>
          </div>
          <!-- Expected Value -->
          <div class="text-right shrink-0">
            <p class="text-sm font-bold text-gold">${{ item.expected_value.toFixed(0) }}</p>
            <Badge :variant="timeBadge(item.time_to_submit)" class="text-[9px]">{{ timeLabel(item.time_to_submit) }}</Badge>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="flex flex-col items-center py-20 text-center">
      <FileText class="mb-4 h-10 w-10 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No hay reportes en la cola</p>
      <p class="mt-1 text-xs text-muted-foreground">Creá reportes desde Findings Pipeline para verlos acá priorizados</p>
    </div>
  </div>
</template>
