<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getOrionContext } from '@/lib/api'
import type { OrionContext } from '@/types'
import { useHuntStore } from '@/stores/hunt'
import KPIGrid from '@/components/dashboard/KPIGrid.vue'
import OpportunityTable from '@/components/dashboard/OpportunityTable.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Button from '@/components/ui/Button.vue'
import { Activity, AlertTriangle, ArrowRight, Sparkles, Clock, DollarSign, Target, Zap, Play, Square, Pause } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'

const hunt = useHuntStore()
const ctx = ref<OrionContext | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try { ctx.value = await getOrionContext() }
  catch (e: any) { error.value = e?.message || 'Error al cargar el contexto' }
  finally { loading.value = false }
  hunt.fetchStatus()
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const kpiItems = computed(() => {
  if (!ctx.value) return []
  const c = ctx.value.counts
  return [
    { label: 'Active Targets', value: String(c.targets), icon: 'target' as const, accent: 'blue' as const },
    { label: 'High-Signal Endpoints', value: String(c.endpoints), icon: 'activity' as const, accent: 'purple' as const },
    { label: 'Confirmed Findings', value: String(c.confirmed_findings), icon: 'check' as const, accent: 'green' as const },
    { label: 'Estimated ROI', value: `$${(c.total_estimated_payout || 0).toLocaleString()}`, icon: 'dollar' as const, accent: 'gold' as const },
  ]
})

function severityBadge(sev?: string) {
  if (!sev) return 'default' as const
  const map: Record<string, 'destructive' | 'warning' | 'success' | 'info' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

const nextAction = computed(() => ctx.value?.next_action)
const opportunities = computed(() => ctx.value?.opportunities.top || [])
const activityEvents = computed(() => ctx.value?.activity_24h.events || [])

const pipelineStages = computed(() => {
  if (!ctx.value) return []
  const p = ctx.value.pipeline
  return [
    { label: 'Detected', count: p.detected, color: 'bg-muted-foreground/30' },
    { label: 'Validated', count: p.validated, color: 'bg-accent/30' },
    { label: 'Confirmed', count: p.confirmed, color: 'bg-primary/30' },
    { label: 'Reported', count: p.reported, color: 'bg-gold/30' },
  ]
})

const maxPipeline = computed(() => {
  if (!ctx.value) return 1
  const p = ctx.value.pipeline
  return Math.max(p.detected, p.validated, p.confirmed, p.reported, 1)
})

function handleHuntToggle() {
  if (hunt.status === 'idle') hunt.start()
  else if (hunt.status === 'running') hunt.pause()
  else if (hunt.status === 'paused') hunt.resume()
}
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4 animate-in">
        <Skeleton class="h-6 w-64" />
        <Skeleton class="h-4 w-96" />
        <div class="grid grid-cols-4 gap-3">
          <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
        </div>
        <Skeleton class="h-32 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="ctx">
      <div class="flex items-start justify-between gap-4">
        <div class="space-y-1 animate-in">
          <p class="text-xs font-bold uppercase tracking-widest text-primary">{{ greeting }}, OPERADOR</p>
          <h1 class="font-display text-2xl font-bold text-foreground">Mission Control</h1>
          <p class="text-sm text-muted-foreground max-w-xl">
            Sistema {{ ctx.system.status === 'healthy' ? 'operativo' : ctx.system.status === 'degraded' ? 'con atención requerida' : 'en estado crítico' }}.
            Score de salud: {{ ctx.system.health_score }}/100.
            <span v-if="ctx.findings.new_24h"> &middot; {{ ctx.findings.new_24h }} hallazgos nuevos hoy</span>
            <span v-if="ctx.counts.reports_ready > 0"> &middot; {{ ctx.counts.reports_ready }} reporte(s) pendiente(s)</span>
          </p>
        </div>

        <!-- Autonomous Hunt -->
        <div class="shrink-0 animate-in">
          <div class="glass-card rounded-xl p-4 flex items-center gap-4">
            <div>
              <p class="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">Caza Autónoma</p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['h-2 w-2 rounded-full', hunt.status === 'running' ? 'bg-success animate-pulse' : hunt.status === 'paused' ? 'bg-warning' : 'bg-muted-foreground/40']" />
                <span class="text-xs font-semibold" :class="hunt.status === 'running' ? 'text-success' : hunt.status === 'paused' ? 'text-warning' : 'text-muted-foreground'">{{ hunt.label }}</span>
              </div>
              <div v-if="hunt.isActive" class="flex gap-3 mt-1.5 text-[10px] text-muted-foreground">
                <span>{{ hunt.targetsScanned }} targets</span>
                <span>{{ hunt.findingsFound }} findings</span>
              </div>
            </div>
            <div class="flex gap-1.5">
              <Button v-if="hunt.status === 'idle'" size="sm" @click="hunt.start()" :loading="hunt.loading">
                <Play class="h-3.5 w-3.5" />
                Iniciar
              </Button>
              <Button v-if="hunt.status === 'running'" size="sm" variant="secondary" @click="hunt.pause()" :loading="hunt.loading">
                <Pause class="h-3.5 w-3.5" />
                Pausar
              </Button>
              <Button v-if="hunt.status === 'paused'" size="sm" variant="secondary" @click="hunt.resume()" :loading="hunt.loading">
                <Play class="h-3.5 w-3.5" />
                Reanudar
              </Button>
              <Button v-if="hunt.isActive" size="sm" variant="destructive" @click="hunt.stop()" :loading="hunt.loading">
                <Square class="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <KPIGrid :items="kpiItems" />

      <div v-if="nextAction" class="animate-in">
        <div class="glass-card rounded-xl p-5 border-l-2 border-l-primary">
          <div class="flex items-start gap-4">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
              <Zap class="h-5 w-5" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                <Sparkles class="h-3 w-3" />
                <span>Próxima acción recomendada</span>
              </div>
              <h3 class="mt-1 text-base font-semibold text-foreground">{{ nextAction.title }}</h3>
              <p class="mt-1 text-sm text-muted-foreground">{{ nextAction.why_now }}</p>
              <div class="mt-3 flex flex-wrap gap-4">
                <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock class="h-3 w-3" /> Esfuerzo:
                  <span :class="nextAction.effort === 'low' ? 'text-success' : nextAction.effort === 'medium' ? 'text-warning' : 'text-destructive'" class="font-semibold">{{ nextAction.effort }}</span>
                </span>
                <span class="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <DollarSign class="h-3 w-3" /> Recompensa estimada:
                  <span class="font-semibold text-gold">{{ nextAction.estimated_reward }}</span>
                </span>
              </div>
            </div>
            <ArrowRight class="mt-2 h-5 w-5 shrink-0 text-muted-foreground" />
          </div>
        </div>
      </div>

      <div class="space-y-3">
        <h2 class="text-sm font-semibold text-foreground">Pipeline</h2>
        <div class="glass-card rounded-xl p-5">
          <div class="flex items-end gap-2 h-24">
            <div v-for="stage in pipelineStages" :key="stage.label" class="flex-1 flex flex-col items-center gap-2">
              <div class="w-full rounded-t-md transition-all duration-500" :class="stage.color">
                <div class="w-full rounded-t-md transition-all duration-500" :style="{ height: `${(stage.count / maxPipeline) * 100}%`, minHeight: stage.count > 0 ? '8px' : '0' }" />
              </div>
              <span class="text-xs font-semibold tabular-nums text-foreground">{{ stage.count }}</span>
              <span class="text-[10px] text-muted-foreground uppercase tracking-wider">{{ stage.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Estado del Sistema</h3>
        <DoughnutChart
          :labels="['Detected', 'Validated', 'Confirmed', 'Reported']"
          :data="[ctx.pipeline.detected, ctx.pipeline.validated, ctx.pipeline.confirmed, ctx.pipeline.reported]"
          :height="200"
        />
      </Card>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="lg:col-span-2 space-y-3">
          <h2 class="text-sm font-semibold text-foreground">Top Oportunidades</h2>
          <OpportunityTable :opportunities="opportunities" />
        </div>
        <div class="space-y-3">
          <h2 class="text-sm font-semibold text-foreground">Actividad Reciente</h2>
          <div class="glass-card rounded-xl p-4 space-y-3">
            <div v-for="(ev, i) in activityEvents.slice(0, 8)" :key="i" class="animate-in flex items-start gap-3" :style="{ animationDelay: `${i * 30}ms` }">
              <div :class="['mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', ev.type === 'finding' ? 'bg-destructive/15 text-destructive' : 'bg-accent/15 text-accent']">
                <AlertTriangle v-if="ev.type === 'finding'" class="h-3 w-3" />
                <Activity v-else class="h-3 w-3" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-medium text-foreground capitalize">{{ ev.type }} #{{ ev.id }}</p>
                <p v-if="ev.severity" class="text-[11px] text-muted-foreground">
                  <Badge :variant="severityBadge(ev.severity)" class="text-[10px] px-1.5 py-0">{{ ev.severity }}</Badge>
                </p>
              </div>
            </div>
            <div v-if="activityEvents.length === 0" class="py-6 text-center text-xs text-muted-foreground">Sin actividad en las últimas 24h</div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col items-center justify-center py-24 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary shadow-lg shadow-primary/10 mb-6">
          <Target class="h-8 w-8" />
        </div>
        <h2 class="font-display text-xl font-bold text-foreground">Bienvenido a ORION</h2>
        <p class="mt-2 max-w-md text-sm text-muted-foreground">El sistema se está inicializando. Conectá plataformas o importá objetivos para comenzar.</p>
        <div class="mt-6 flex gap-3">
          <Button variant="default">Explorar Programas</Button>
          <Button variant="secondary">Conectar Plataformas</Button>
        </div>
      </div>
    </template>
  </div>
</template>
