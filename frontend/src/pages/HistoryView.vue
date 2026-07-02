<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, getTimeline } from '@/lib/api'
import type { TimelineEvent } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import {
  History, Lightbulb, AlertTriangle, ChevronLeft, ChevronRight,
  Calendar, Clock, Filter, RefreshCw, Target, Bug, FileText,
  CheckCircle2, Zap, Activity,
} from '@lucide/vue'

interface DecisionEntry {
  id: number; key: string; details: { action?: string; outcome?: string; reason?: string; confidence?: number; source?: string } | null
}

interface InsightEntry {
  id: number; key: string; details: { title?: string; severity?: string; description?: string; insight_type?: string; source?: string } | null
}

// ── State ──
const decisions = ref<DecisionEntry[]>([])
const insights = ref<InsightEntry[]>([])
const stats = ref<{ total_executions: number } | null>(null)
const timelineEvents = ref<TimelineEvent[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeTab = ref<'timeline' | 'decisions' | 'insights'>('timeline')
const eventTypeFilter = ref<string>('')
const selectedDate = ref(new Date())
const timelineLoading = ref(false)

const eventTypes = ['scan', 'finding', 'report', 'verdict', 'sync', 'system']

const eventIcons: Record<string, any> = {
  scan: Activity,
  finding: Bug,
  report: FileText,
  verdict: CheckCircle2,
  sync: RefreshCw,
  system: Zap,
}

const eventColors: Record<string, string> = {
  scan: 'text-blue-400',
  finding: 'text-destructive',
  report: 'text-gold',
  verdict: 'text-success',
  sync: 'text-accent',
  system: 'text-muted-foreground',
}

// ── Date helpers ──
const dateStr = computed(() => selectedDate.value.toISOString().split('T')[0])

function goDay(delta: number) {
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + delta)
  selectedDate.value = d
}

function goToday() { selectedDate.value = new Date() }

function formatDate(d: Date) {
  const today = new Date()
  const yesterday = new Date(today.getTime() - 86400000)
  if (d.toDateString() === today.toDateString()) return 'Hoy'
  if (d.toDateString() === yesterday.toDateString()) return 'Ayer'
  return d.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })
}

// ── Filtered events ──
const filteredEvents = computed(() => {
  let events = timelineEvents.value
  if (eventTypeFilter.value) {
    events = events.filter(e => e.event_type === eventTypeFilter.value)
  }
  return events
})

// ── Chart data ──
const activityByType = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of timelineEvents.value) {
    counts[e.event_type] = (counts[e.event_type] || 0) + 1
  }
  return { labels: Object.keys(counts), data: Object.values(counts) }
})

// ── API ──
async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    const [decRes, insRes, statsRes] = await Promise.allSettled([
      api.get<{ decisions: DecisionEntry[]; count: number }>('/system/decisions', { limit: 20 }),
      api.get<{ insights: InsightEntry[]; count: number }>('/system/insights', { limit: 20 }),
      api.get<{ total_executions: number }>('/system/execution-stats'),
    ])
    if (decRes.status === 'fulfilled') decisions.value = decRes.value.decisions || []
    if (insRes.status === 'fulfilled') insights.value = insRes.value.insights || []
    if (statsRes.status === 'fulfilled') stats.value = statsRes.value
  } catch (e: any) { error.value = e?.message || 'Error al cargar el historial' }
  finally { loading.value = false }
}

async function fetchTimeline() {
  timelineLoading.value = true
  try {
    const res = await getTimeline({ limit: 100 })
    timelineEvents.value = res.events || []
  } catch { /* ignore */ }
  finally { timelineLoading.value = false }
}

onMounted(() => {
  fetchAll()
  fetchTimeline()
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">History</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Historial del Sistema</h1>
      <p class="text-sm text-muted-foreground">Timeline cronológico · decisiones · insights · registro completo</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-24 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="fetchAll">Reintentar</Button>
      </div>
    </template>

    <template v-else>
      <!-- Stats bar -->
      <div v-if="stats" class="flex items-center gap-4 text-xs text-muted-foreground animate-in">
        <span>Ejecuciones: <strong class="text-foreground">{{ stats.total_executions }}</strong></span>
        <span>Eventos: <strong class="text-foreground">{{ timelineEvents.length }}</strong></span>
        <span>Decisiones: <strong class="text-foreground">{{ decisions.length }}</strong></span>
        <span>Insights: <strong class="text-foreground">{{ insights.length }}</strong></span>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Actividad por Tipo</p>
          </div>
          <BarChart
            :labels="activityByType.labels"
            :datasets="[{ label: 'Eventos', data: activityByType.data, backgroundColor: '#7c3aed' }]"
            :height="200"
            yLabel="Cantidad"
            :showLegend="false"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Distribución</p>
          </div>
          <DoughnutChart
            :labels="activityByType.labels"
            :data="activityByType.data"
            :height="200"
          />
        </Card>
      </div>

      <!-- Tabs -->
      <div class="flex items-center gap-2 border-b border-border/40">
        <button @click="activeTab = 'timeline'"
          :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === 'timeline' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
        >Timeline</button>
        <button @click="activeTab = 'decisions'"
          :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === 'decisions' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
        >Decisiones ({{ decisions.length }})</button>
        <button @click="activeTab = 'insights'"
          :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === 'insights' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
        >Insights ({{ insights.length }})</button>
      </div>

      <!-- ══ TIMELINE TAB ══ -->
      <div v-if="activeTab === 'timeline'" class="space-y-4 animate-in">
        <!-- Calendar navigation -->
        <div class="flex items-center justify-between rounded-xl border border-border/40 bg-[#131524]/60 p-3">
          <div class="flex items-center gap-2">
            <button @click="goDay(-1)" class="rounded-lg p-1.5 text-muted-foreground hover:bg-surface/30 hover:text-foreground transition-colors">
              <ChevronLeft class="h-4 w-4" />
            </button>
            <div class="flex items-center gap-2 px-2">
              <Calendar class="h-4 w-4 text-primary" />
              <span class="text-sm font-semibold text-foreground capitalize">{{ formatDate(selectedDate) }}</span>
            </div>
            <button @click="goDay(1)" class="rounded-lg p-1.5 text-muted-foreground hover:bg-surface/30 hover:text-foreground transition-colors">
              <ChevronRight class="h-4 w-4" />
            </button>
            <Button variant="ghost" size="sm" @click="goToday" class="text-[10px]">Hoy</Button>
          </div>
          <div class="flex items-center gap-2">
            <div class="flex items-center gap-1 rounded-lg bg-surface/20 px-2 py-1">
              <Filter class="h-3 w-3 text-muted-foreground" />
              <select v-model="eventTypeFilter" class="bg-transparent text-[10px] text-foreground outline-none">
                <option value="">Todos</option>
                <option v-for="t in eventTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <button @click="fetchTimeline" :disabled="timelineLoading" class="rounded-lg p-1.5 text-muted-foreground hover:bg-surface/30 hover:text-foreground transition-colors">
              <RefreshCw :class="['h-3.5 w-3.5', timelineLoading ? 'animate-spin' : '']" />
            </button>
          </div>
        </div>

        <!-- Timeline entries -->
        <div v-if="timelineLoading" class="space-y-2">
          <Skeleton v-for="i in 5" :key="i" class="h-16 rounded-xl" />
        </div>

        <div v-else-if="filteredEvents.length === 0" class="flex flex-col items-center py-16 text-center">
          <Clock class="h-10 w-10 text-muted-foreground/50 mb-3" />
          <p class="text-sm text-foreground">Sin eventos en esta fecha</p>
          <p class="text-xs text-muted-foreground mt-1">Seleccioná otra fecha o cambiá el filtro</p>
        </div>

        <div v-else class="relative space-y-0">
          <!-- Timeline line -->
          <div class="absolute left-[19px] top-2 bottom-2 w-px bg-border/30" />

          <div v-for="(event, i) in filteredEvents" :key="i" class="relative flex gap-4 pb-4 last:pb-0">
            <!-- Dot -->
            <div class="relative z-10 flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full" :class="eventColors[event.event_type]?.replace('text-', 'bg-')?.replace('-400', '-500/15') || 'bg-surface/30'">
              <component :is="eventIcons[event.event_type] || Activity" :class="['h-4 w-4', eventColors[event.event_type] || 'text-muted-foreground']" />
            </div>
            <!-- Content -->
            <div class="flex-1 min-w-0 rounded-xl border border-border/20 bg-[#ffffff08] px-4 py-3">
              <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-2">
                  <Badge variant="outline" class="text-[8px] uppercase">{{ event.event_type }}</Badge>
                  <span class="text-[10px] text-muted-foreground/60">
                    {{ new Date(event.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) }}
                  </span>
                </div>
                <span v-if="event.source" class="text-[9px] text-muted-foreground/40">{{ event.source }}</span>
              </div>
              <p class="mt-1 text-xs text-foreground">{{ event.description }}</p>
              <div v-if="event.target_name" class="mt-1 flex items-center gap-2">
                <Target class="h-3 w-3 text-muted-foreground/60" />
                <span class="text-[10px] text-muted-foreground/60">{{ event.target_name }}</span>
              </div>
              <div v-if="event.confidence !== undefined && event.confidence !== null" class="mt-1">
                <span class="text-[9px] text-muted-foreground/50">Confianza: {{ (event.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ DECISIONS TAB ══ -->
      <div v-if="activeTab === 'decisions'" class="animate-in">
        <Card v-if="decisions.length > 0" class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <History class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Decision Memory ({{ decisions.length }})</p>
          </div>
          <div class="space-y-1">
            <div v-for="d in decisions" :key="d.id"
              class="rounded-lg bg-[#ffffff08] px-3 py-2 transition-all hover:bg-[#ffffff10]"
            >
              <div class="flex items-center justify-between mb-0.5">
                <span class="text-xs font-semibold text-foreground">{{ d.details?.action || d.key }}</span>
                <Badge v-if="d.details?.outcome"
                  :variant="d.details.outcome === 'success' ? 'success' : d.details.outcome === 'error' ? 'destructive' : 'default'"
                  class="text-[10px]"
                >{{ d.details.outcome }}</Badge>
              </div>
              <p v-if="d.details?.reason" class="text-[11px] text-muted-foreground">{{ d.details.reason }}</p>
              <p v-if="d.details?.confidence !== undefined" class="text-[10px] text-muted-foreground/60 mt-0.5">
                confidence: {{ d.details.confidence.toFixed(2) }} · {{ d.details.source || 'system' }}
              </p>
            </div>
          </div>
        </Card>

        <div v-else class="flex flex-col items-center py-16 text-center">
          <History class="h-8 w-8 text-muted-foreground/50 mb-2" />
          <p class="text-xs text-muted-foreground">No decision history yet</p>
        </div>
      </div>

      <!-- ══ INSIGHTS TAB ══ -->
      <div v-if="activeTab === 'insights'" class="animate-in">
        <Card v-if="insights.length > 0" class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Lightbulb class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Insight Archive ({{ insights.length }})</p>
          </div>
          <div class="space-y-1">
            <div v-for="ins in insights" :key="ins.id"
              class="rounded-lg bg-[#ffffff08] px-3 py-2 transition-all hover:bg-[#ffffff10]"
            >
              <div class="flex items-center justify-between mb-0.5">
                <span class="text-xs font-semibold text-foreground">{{ ins.details?.title || ins.key }}</span>
                <Badge v-if="ins.details?.severity"
                  :variant="ins.details.severity === 'critical' ? 'destructive' : ins.details.severity === 'high' ? 'warning' : 'default'"
                  class="text-[10px]"
                >{{ ins.details.severity }}</Badge>
              </div>
              <p v-if="ins.details?.description" class="text-[11px] text-muted-foreground">{{ ins.details.description }}</p>
              <p class="text-[10px] text-muted-foreground/60 mt-0.5">
                {{ ins.details?.insight_type }} · {{ ins.details?.source }}
              </p>
            </div>
          </div>
        </Card>

        <div v-else class="flex flex-col items-center py-16 text-center">
          <Lightbulb class="h-8 w-8 text-muted-foreground/50 mb-2" />
          <p class="text-xs text-muted-foreground">No insights yet</p>
        </div>
      </div>
    </template>
  </div>
</template>
