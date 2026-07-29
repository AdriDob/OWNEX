<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { LineChart } from '@/components/charts'
import {
  Target, AlertTriangle, RefreshCw, Clock, DollarSign,
  Lightbulb, ListChecks, Zap, Brain, ArrowRight,
} from '@lucide/vue'

interface NextAction {
  target_id: number
  title: string
  why_now: string
  effort: string
  estimated_reward: string
  type: string
  steps?: string[]
}

interface AnalysisResult {
  analysis: string
  recommended_steps: string[]
  estimated_effort_hours: number
  estimated_value: number
  risk_level: string
}

const nextAction = ref<NextAction | null>(null)
const analysis = ref<AnalysisResult | null>(null)
const loading = ref(true)
const analyzing = ref(false)
const error = ref<string | null>(null)

async function fetchData() {
  loading.value = true
  error.value = null
  analysis.value = null
  try {
    nextAction.value = await api.get<NextAction>('/orion/next-action')
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar la próxima acción'
  }
  finally { loading.value = false }
}

async function runAnalysis() {
  if (!nextAction.value) return
  analyzing.value = true
  try {
    analysis.value = await api.post<AnalysisResult>(`/orion/analyze-opportunity/${nextAction.value.target_id}`)
  } catch { /* ignore */ }
  finally { analyzing.value = false }
}

onMounted(fetchData)

const effortColor = computed(() => {
  const e = nextAction.value?.effort?.toLowerCase() || ''
  if (e.includes('bajo') || e.includes('low')) return 'success'
  if (e.includes('medio') || e.includes('medium')) return 'warning'
  return 'destructive'
})

const typeIcon = computed(() => {
  const t = nextAction.value?.type?.toLowerCase() || ''
  if (t.includes('scan') || t.includes('recon')) return Zap
  if (t.includes('analy') || t.includes('research')) return Brain
  return Lightbulb
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">OWNEX</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Next Action</h1>
      <p class="text-sm text-muted-foreground">Próxima acción recomendada por OWNEX</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-32 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error al cargar la próxima acción</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!nextAction">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Target class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay próxima acción</p>
        <p class="mt-1 text-xs text-muted-foreground">OWNEX no tiene recomendaciones en este momento</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Actualizar
        </Button>
      </div>
    </template>

    <template v-else>
      <Card class="p-5 animate-in border-l-2" :class="nextAction.type === 'scan' ? 'border-l-primary' : 'border-l-accent'">
        <div class="flex items-start gap-4">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <component :is="typeIcon" class="h-5 w-5" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h2 class="text-lg font-bold text-foreground">{{ nextAction.title }}</h2>
              <Badge :variant="effortColor" class="text-[10px]">{{ nextAction.type }}</Badge>
            </div>
            <div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span class="flex items-center gap-1">
                <Clock class="h-3 w-3" /> Esfuerzo: {{ nextAction.effort }}
              </span>
              <span class="flex items-center gap-1">
                <DollarSign class="h-3 w-3" /> Recompensa estimada: {{ nextAction.estimated_reward }}
              </span>
            </div>
          </div>
        </div>
      </Card>

      <Card class="p-5 animate-in">
        <div class="flex items-start gap-3">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <Lightbulb class="h-4 w-4" />
          </div>
          <div class="flex-1">
            <h3 class="text-sm font-semibold text-foreground mb-2">¿Por qué ahora?</h3>
            <p class="text-sm text-muted-foreground leading-relaxed">{{ nextAction.why_now }}</p>
          </div>
        </div>
      </Card>

      <div class="flex animate-in">
        <Button :disabled="analyzing" @click="runAnalysis" class="gap-2">
          <Zap v-if="!analyzing" class="h-4 w-4" />
          <span v-if="analyzing" class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          {{ analyzing ? 'Analizando...' : 'Analizar Oportunidad' }}
        </Button>
      </div>

      <template v-if="analysis">
        <Card class="p-5 animate-in border-l-2 border-l-success">
          <div class="flex items-start gap-3">
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-success/15 text-success">
              <Brain class="h-4 w-4" />
            </div>
            <div class="flex-1">
              <h3 class="text-sm font-semibold text-foreground mb-2">Análisis detallado</h3>
              <p class="whitespace-pre-wrap text-sm text-muted-foreground leading-relaxed">{{ analysis.analysis }}</p>
            </div>
          </div>
        </Card>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 animate-in">
          <Card class="p-4 text-center">
            <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Esfuerzo estimado</p>
            <p class="text-xl font-bold text-foreground mt-1">{{ analysis.estimated_effort_hours }}h</p>
          </Card>
          <Card class="p-4 text-center">
            <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Valor estimado</p>
            <p class="text-xl font-bold text-success mt-1">${{ analysis.estimated_value.toLocaleString() }}</p>
          </Card>
          <Card class="p-4 text-center">
            <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Nivel de riesgo</p>
            <Badge :variant="analysis.risk_level === 'high' ? 'destructive' : analysis.risk_level === 'medium' ? 'warning' : 'success'" class="mt-1">
              {{ analysis.risk_level }}
            </Badge>
          </Card>
        </div>

        <Card v-if="analysis.recommended_steps?.length" class="p-5 animate-in">
          <div class="flex items-center gap-2 mb-3">
            <ListChecks class="h-4 w-4 text-primary" />
            <h3 class="text-xs font-semibold text-foreground">Pasos recomendados</h3>
          </div>
          <div class="space-y-2">
            <div v-for="(step, i) in analysis.recommended_steps" :key="i"
              class="flex items-start gap-3 rounded-lg bg-surface/20 p-3"
            >
              <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary">
                {{ i + 1 }}
              </div>
              <p class="text-sm text-foreground">{{ step }}</p>
            </div>
          </div>
        </Card>
      </template>
    </template>
  </div>
</template>
