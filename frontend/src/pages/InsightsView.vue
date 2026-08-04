<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import { Lightbulb, AlertTriangle, RotateCw, ChevronDown, ChevronRight, Activity, Layers, BarChart3 } from '@lucide/vue'

interface Explanation {
  id: string
  type: string
  title: string
  description: string
  confidence: number
  reasoning_chain: ReasoningStep[]
  created_at: string
}

interface ReasoningStep {
  step: number
  content: string
  confidence: number
}

interface ExecutionTrace {
  id: string
  action: string
  agent: string
  status: string
  duration_ms: number
  timestamp: string
  details?: string
}

interface InsightsData {
  explanations: Explanation[]
  traces: ExecutionTrace[]
  aggregates: Record<string, number>
}

const data = ref<InsightsData | null>(null)
const loading = ref(true)
const error = ref('')
const expandedExplanations = ref<Set<string>>(new Set())

function toggleExpand(id: string) {
  if (expandedExplanations.value.has(id)) {
    expandedExplanations.value.delete(id)
  } else {
    expandedExplanations.value.add(id)
  }
}

const confidenceLabels = computed(() => ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])
const confidenceData = computed(() => {
  if (!data.value) return [0, 0, 0, 0, 0]
  const buckets = [0, 0, 0, 0, 0]
  for (const exp of data.value.explanations) {
    const idx = Math.min(Math.floor(exp.confidence * 5), 4)
    buckets[idx]++
  }
  return buckets
})

const typeLabels = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value.aggregates)
})
const typeData = computed(() => {
  if (!data.value) return []
  return Object.values(data.value.aggregates)
})

function confidenceColor(score: number) {
  if (score >= 0.8) return 'text-success'
  if (score >= 0.6) return 'text-info'
  if (score >= 0.4) return 'text-warning'
  return 'text-destructive'
}

function traceStatusVariant(s: string): 'default' | 'success' | 'warning' | 'destructive' {
  if (s === 'completed' || s === 'success') return 'success'
  if (s === 'running' || s === 'in_progress') return 'warning'
  if (s === 'failed' || s === 'error') return 'destructive'
  return 'default'
}

async function fetchInsights() {
  loading.value = true
  error.value = ''
  try {
    const [insightsRes, tracesRes] = await Promise.all([
      api.get<InsightsData>('/system/insights'),
      api.get<{ traces: ExecutionTrace[] }>('/system/execution-traces', { limit: 10 }),
    ])
    data.value = {
      explanations: insightsRes.explanations || [],
      traces: tracesRes.traces || [],
      aggregates: insightsRes.aggregates || {},
    }
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar insights'
  } finally {
    loading.value = false
  }
}

onMounted(fetchInsights)
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Sistema</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Insights View</h1>
      <p class="text-sm text-muted-foreground">
        Explicaciones de ejecuciones AI y trazas del sistema
      </p>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Skeleton v-for="i in 4" :key="i" class="h-32 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <!-- Error -->
    <template v-else-if="error && !data">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchInsights">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Empty -->
    <template v-else-if="!data || (!data.explanations.length && !data.traces.length)">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Lightbulb class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin insights disponibles</p>
        <p class="mt-1 text-xs text-muted-foreground">No hay explicaciones o trazas del sistema aún</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchInsights">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Explicaciones por Confianza</p>
          </div>
          <BarChart
            :labels="confidenceLabels"
            :datasets="[{ label: 'Explicaciones', data: confidenceData, backgroundColor: '#7c3aed' }]"
            :height="200"
            yLabel="Cantidad"
            :showLegend="false"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Layers class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Distribución por Tipo</p>
          </div>
          <DoughnutChart
            :labels="typeLabels"
            :data="typeData"
            :height="220"
          />
        </Card>
      </div>

      <!-- Aggregate Counts -->
      <Card v-if="typeLabels.length" class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Activity class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Agregados por Tipo</p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div v-for="(count, type) in data.aggregates" :key="type" class="text-center p-3 rounded-lg bg-surface/30">
            <p class="text-lg font-bold text-foreground">{{ count }}</p>
            <p class="text-[10px] text-muted-foreground capitalize">{{ type }}</p>
          </div>
        </div>
      </Card>

      <!-- Explanations -->
      <div v-if="data.explanations.length" class="space-y-3 animate-in">
        <p class="text-xs font-semibold text-foreground">Explanations ({{ data.explanations.length }})</p>
        <Card v-for="exp in data.explanations" :key="exp.id" class="p-4">
          <div class="flex items-start justify-between cursor-pointer" @click="toggleExpand(exp.id)">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <Lightbulb class="h-4 w-4 text-primary shrink-0" />
                <p class="text-sm font-semibold text-foreground truncate">{{ exp.title }}</p>
                <Badge variant="outline" class="text-[9px]">{{ exp.type }}</Badge>
              </div>
              <p class="text-xs text-muted-foreground line-clamp-2">{{ exp.description }}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0 ml-3">
              <span :class="['text-xs font-bold', confidenceColor(exp.confidence)]">
                {{ (exp.confidence * 100).toFixed(0) }}%
              </span>
              <ChevronRight v-if="!expandedExplanations.has(exp.id)" class="h-4 w-4 text-muted-foreground transition-transform" />
              <ChevronDown v-else class="h-4 w-4 text-muted-foreground transition-transform" />
            </div>
          </div>

          <!-- Reasoning Chain -->
          <div v-if="expandedExplanations.has(exp.id) && exp.reasoning_chain?.length" class="mt-3 pl-6 space-y-2 border-l border-border/40">
            <div v-for="step in exp.reasoning_chain" :key="step.step" class="relative">
              <div class="absolute -left-6 top-1 h-4 w-4 rounded-full bg-surface flex items-center justify-center">
                <span class="text-[8px] font-bold text-muted-foreground">{{ step.step }}</span>
              </div>
              <p class="text-xs text-foreground">{{ step.content }}</p>
              <div class="flex items-center gap-1 mt-0.5">
                <div class="h-1 w-12 rounded-full bg-surface">
                  <div class="h-full rounded-full bg-primary" :style="{ width: `${step.confidence * 100}%` }" />
                </div>
                <span class="text-[9px] text-muted-foreground">{{ (step.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Execution Traces -->
      <div v-if="data.traces.length" class="space-y-3 animate-in">
        <p class="text-xs font-semibold text-foreground">Execution Traces (últimas {{ data.traces.length }})</p>
        <div class="space-y-2">
          <div v-for="trace in data.traces" :key="trace.id"
            class="flex items-center gap-3 rounded-xl border border-border/40 bg-surface/30 p-3 animate-in"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-foreground truncate">{{ trace.action }}</span>
                <Badge :variant="traceStatusVariant(trace.status)" class="text-[9px] capitalize">{{ trace.status }}</Badge>
              </div>
              <p class="text-[10px] text-muted-foreground mt-0.5">
                {{ trace.agent }} • {{ trace.duration_ms }}ms
              </p>
            </div>
            <span class="text-[10px] text-muted-foreground shrink-0">
              {{ new Date(trace.timestamp).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
