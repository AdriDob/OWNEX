<script setup lang="ts">
/**
 * Executive Dashboard — CEO view.
 * Responde la única pregunta: "¿Esta semana ganamos plata?"
 * Fuente: GET /api/cycles/security/dashboard (core/cycles/executive_dashboard.py)
 */

import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  DollarSign,
  Gauge,
  RefreshCw,
  Target,
  TrendingUp,
  Wallet,
} from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'

interface CeoView {
  verdict: string
  made_money_this_week: boolean
  weekly: { total_usd: number; count: number; avg_per_payout: number }
  monthly: { total_usd: number; runway_months: number }
  efficiency: { usd_per_hour: number; acceptance_rate: number; time_to_payout_avg_days: number }
  pipeline: { findings_total: number; confirmed: number; submitted: number; accepted: number }
  top_platform: string
  cycles: Record<string, { name: string; status: string; metrics: any }>
  generated_at: string
}

const loading = ref(true)
const error = ref('')
const data = ref<CeoView | null>(null)
let refreshInterval: ReturnType<typeof setInterval> | null = null

const verdictTone = computed(() => (data.value?.made_money_this_week ? 'text-success' : 'text-destructive'))
const verdictBg = computed(() =>
  data.value?.made_money_this_week ? 'bg-success/10 border-success/30' : 'bg-destructive/10 border-destructive/30',
)
const pipelinePercent = computed(() => {
  const p = data.value?.pipeline
  if (!p || p.findings_total === 0) return 0
  return Math.round((p.accepted / p.findings_total) * 100)
})
const activeCycles = computed(() => Object.entries(data.value?.cycles ?? {}).filter(([, c]) => c.status !== 'inactive'))

async function load() {
  try {
    const res = await api.get<CeoView>('/cycles/security/dashboard')
    data.value = res
    error.value = ''
  } catch (e: any) {
    if (!data.value) error.value = e?.message || 'Error al cargar el dashboard ejecutivo'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  refreshInterval = setInterval(load, 60000)
})
onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Activity class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX EXECUTIVE</span>
          <Badge variant="secondary" class="text-xs">CEO View</Badge>
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Dashboard Ejecutivo</h1>
        <p class="text-sm text-muted-foreground">
          Una sola pregunta: ¿esta semana ganamos plata?
        </p>
        <p v-if="data?.generated_at" class="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
          <Clock class="h-3 w-3" />
          {{ new Date(data.generated_at).toLocaleString() }}
        </p>
      </div>
      <Button variant="ghost" size="sm" @click="load" :disabled="loading" class="gap-2">
        <RefreshCw class="h-4 w-4" />
        Refrescar
      </Button>
    </div>

    <!-- Error (structured: ERROR / CAUSA / ACCIÓN, calm during backend wait) -->
    <ErrorState
      v-if="error"
      title="No se pudo cargar el dashboard ejecutivo"
      :error="error"
      :on-retry="load"
    />

    <LoadingState v-if="loading && !data" />

    <template v-else-if="data">
      <!-- Verdict -->
      <div :class="['flex items-center gap-4 rounded-xl border px-6 py-5', verdictBg]">
        <Gauge class="h-8 w-8 shrink-0" :class="verdictTone" />
        <div>
          <div class="text-lg sm:text-2xl font-display font-bold" :class="verdictTone">
            {{ data.verdict }}
          </div>
          <p class="text-xs text-muted-foreground mt-0.5">
            Top plataforma: <span class="font-semibold text-foreground">{{ data.top_platform || '—' }}</span>
          </p>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent class="p-5">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Esta semana</span>
              <Wallet class="h-4 w-4 text-success" />
            </div>
            <div class="text-2xl font-bold font-mono text-success">${{ data.weekly.total_usd.toLocaleString() }}</div>
            <div class="text-[11px] text-muted-foreground mt-1">
              {{ data.weekly.count }} payout{{ data.weekly.count === 1 ? '' : 's' }} · avg ${{ data.weekly.avg_per_payout }}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-5">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Este mes</span>
              <DollarSign class="h-4 w-4 text-primary" />
            </div>
            <div class="text-2xl font-bold font-mono">${{ data.monthly.total_usd.toLocaleString() }}</div>
            <div class="text-[11px] text-muted-foreground mt-1">
              Runway: {{ data.monthly.runway_months }} meses
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-5">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">USD / hora</span>
              <TrendingUp class="h-4 w-4 text-warning" />
            </div>
            <div class="text-2xl font-bold font-mono">${{ data.efficiency.usd_per_hour }}</div>
            <div class="text-[11px] text-muted-foreground mt-1">
              Acceptance: {{ data.efficiency.acceptance_rate }}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent class="p-5">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Tiempo a payout</span>
              <Clock class="h-4 w-4 text-primary" />
            </div>
            <div class="text-2xl font-bold font-mono">{{ data.efficiency.time_to_payout_avg_days }}d</div>
            <div class="text-[11px] text-muted-foreground mt-1">promedio desde envío</div>
          </CardContent>
        </Card>
      </div>

      <!-- Pipeline -->
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center gap-2 mb-4">
            <Target class="h-4 w-4 text-primary" />
            <h2 class="font-display text-base font-semibold">Pipeline de Findings</h2>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div class="rounded-lg bg-muted/40 p-3">
              <div class="text-xl font-bold font-mono">{{ data.pipeline.findings_total }}</div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground">Totales</div>
            </div>
            <div class="rounded-lg bg-muted/40 p-3">
              <div class="text-xl font-bold font-mono text-primary">{{ data.pipeline.confirmed }}</div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground">Confirmados</div>
            </div>
            <div class="rounded-lg bg-muted/40 p-3">
              <div class="text-xl font-bold font-mono text-warning">{{ data.pipeline.submitted }}</div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground">Enviados</div>
            </div>
            <div class="rounded-lg bg-muted/40 p-3">
              <div class="text-xl font-bold font-mono text-success">{{ data.pipeline.accepted }}</div>
              <div class="text-[10px] uppercase tracking-wider text-muted-foreground">Aceptados</div>
            </div>
          </div>
          <div class="w-full bg-muted rounded-full h-2">
            <div
              class="bg-success h-2 rounded-full transition-all duration-500"
              :style="{ width: `${pipelinePercent}%` }"
            ></div>
          </div>
          <p class="text-[11px] text-muted-foreground mt-2">
            {{ pipelinePercent }}% de findings totales aceptados
          </p>
        </CardContent>
      </Card>

      <!-- Cycles -->
      <Card>
        <CardContent class="p-6">
          <div class="flex items-center gap-2 mb-4">
            <Activity class="h-4 w-4 text-primary" />
            <h2 class="font-display text-base font-semibold">Work Cycles</h2>
          </div>
          <div v-if="activeCycles.length === 0" class="text-sm text-muted-foreground">
            Sin ciclos activos.
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="[slug, cycle] in activeCycles" :key="slug"
              class="rounded-lg border border-border/40 p-4 flex items-center justify-between"
            >
              <div>
                <div class="text-sm font-semibold">{{ cycle.name }}</div>
                <div class="text-[11px] text-muted-foreground font-mono">{{ slug }}</div>
              </div>
              <Badge
                :variant="cycle.status === 'completed' ? 'success' : cycle.status === 'running' ? 'primary' : 'secondary'"
              >
                {{ cycle.status }}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <p class="text-[10px] text-muted-foreground flex items-center gap-1">
        <ArrowUpRight class="h-3 w-3" />
        Fuente: GET /api/cycles/security/dashboard · refresco cada 60s
      </p>
    </template>
  </div>
</template>
