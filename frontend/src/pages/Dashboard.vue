<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getOrionContext } from '@/lib/api'
import type { OrionContext } from '@/types'
import { useSettingsStore } from '@/stores/settings'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart, DoughnutChart } from '@/components/charts'
import {
  Activity, AlertTriangle, BarChart3, Clock, FileSearch, LayoutDashboard,
  RefreshCw, ShieldCheck, Target, TrendingUp, Zap, Eye, Globe, Crosshair,
  Cpu, Rat, Scan, Bug,
} from '@lucide/vue'

const settings = useSettingsStore()

interface KpiItem {
  label: string
  value: number
  icon: any
  color: string
}

const context = ref<OrionContext | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    context.value = await getOrionContext(true)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar'
  }
  finally { loading.value = false }
}

onMounted(fetchData)

const greeting = computed(() => {
  const h = new Date().getHours()
  const prefix = h < 12 ? 'Buenos días' : h < 18 ? 'Buenas tardes' : 'Buenas noches'
  return `${prefix}, ${settings.data.general.userName || 'Operador'}`
})

const scanInfo = computed(() => {
  const c = context.value?.counts
  if (!c) return null
  return {
    coverage: c.targets > 0 ? Math.min(Math.round((c.endpoints / c.targets) * 100) / 100, 999) : 0,
    // coverage: endpoints/targets (0 if no targets)
    detected: c.findings,
    confirmed: c.confirmed_findings,
    rate: c.findings > 0 ? Math.round((c.confirmed_findings / c.findings) * 100) : 0,
  }
})

const kpis = computed<KpiItem[]>(() => {
  if (!context.value) return []
  const c = context.value.counts
  return [
    { label: 'Targets', value: c.targets, icon: Crosshair, color: '#00b8ff' },
    { label: 'Endpoints', value: c.endpoints, icon: Scan, color: '#00ff41' },
    { label: 'Hallazgos', value: c.findings, icon: Bug, color: '#ffab00' },
    { label: 'Confirmados', value: c.confirmed_findings, icon: ShieldCheck, color: '#00e676' },
  ]
})

const hasTargets = computed(() => (context.value?.counts.targets ?? 0) > 0)

const severityLabels = ['Crítico', 'Alto', 'Medio', 'Bajo', 'Info']
const severityColors = ['#ff1744', '#ff6600', '#ffab00', '#00e676', '#4a5a4a']
const severityData = computed(() => {
  if (!context.value) return [0, 0, 0, 0, 0]
  const s = context.value.findings.by_severity
  return [s.critical || 0, s.high || 0, s.medium || 0, s.low || 0, s.info || 0]
})

const verdictLabels = ['Confirmados', 'Rechazados', 'No concluyentes', 'Pendientes']
const verdictColors = ['#00e676', '#ff1744', '#ffab00', '#4a5a4a']
const verdictData = computed(() => {
  if (!context.value) return [0, 0, 0, 0]
  const v = context.value.verdicts.by_status
  return [v.confirmed || 0, v.rejected || 0, v.inconclusive || 0, v.pending || 0]
})

const systemStatusText = computed(() => {
  const p = scanInfo.value
  if (!p) return 'INITIALIZING'
  if (p.confirmed > 0) return 'ACTIVE'
  if (p.detected > 0) return 'SCANNING'
  return 'MONITORING'
})

const systemStatusColor = computed(() => {
  const s = systemStatusText.value
  if (s === 'ACTIVE') return 'text-success'
  if (s === 'SCANNING') return 'text-warning'
  return 'text-muted-foreground'
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header with CATEYE branding -->
    <div class="animate-in space-y-1">
      <div class="flex items-center gap-3">
        <div class="flex h-7 items-center gap-2 rounded-md bg-primary/10 px-2.5 py-1 ring-1 ring-primary/20">
          <Eye class="h-3.5 w-3.5 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">CATEYE</span>
        </div>
        <span class="font-mono text-[10px]" :class="systemStatusColor">
          ● {{ systemStatusText }}
        </span>
        <span v-if="scanInfo" class="font-mono text-[10px] text-muted-foreground">
          COVERAGE {{ scanInfo.coverage }}%
        </span>
      </div>
      <h1 class="font-display text-2xl font-bold text-foreground">{{ greeting }}</h1>
      <p class="text-sm text-muted-foreground">Centro de Inteligencia de Seguridad CATEYE</p>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-28 rounded-xl" />
      </div>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton class="h-64 rounded-xl" />
        <Skeleton class="h-64 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error de conexión</p>
        <p class="mt-1 font-mono text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reconectar
        </Button>
      </div>
    </template>

    <template v-else-if="!hasTargets">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4 ring-1 ring-primary/10">
          <Crosshair class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Ningún target en radar</p>
        <p class="mt-1 font-mono text-xs text-muted-foreground">Agregá un target para iniciar el monitoreo</p>
        <Button variant="outline" size="sm" class="mt-4" @click="$router.push('/targets')">Agregar Target</Button>
      </div>
    </template>

    <template v-else>
      <!-- Intel Summary Bar -->
      <div v-if="scanInfo" class="card-base rounded-xl">
        <div class="grid grid-cols-1 divide-y divide-border/30 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div class="p-4 text-center">
            <p class="font-mono text-[10px] text-muted-foreground tracking-wider">DETECTADOS</p>
            <p class="mt-1 font-mono text-xl sm:text-2xl font-bold text-warning tabular-nums">{{ scanInfo.detected }}</p>
          </div>
          <div class="p-4 text-center">
            <p class="font-mono text-[10px] text-muted-foreground tracking-wider">CONFIRMADOS</p>
            <p class="mt-1 font-mono text-xl sm:text-2xl font-bold text-success tabular-nums">{{ scanInfo.confirmed }}</p>
          </div>
          <div class="p-4 text-center">
            <p class="font-mono text-[10px] text-muted-foreground tracking-wider">TASA ÉXITO</p>
            <p class="mt-1 font-mono text-xl sm:text-2xl font-bold text-accent tabular-nums">{{ scanInfo.rate }}%</p>
          </div>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card v-for="(kpi, i) in kpis" :key="kpi.label" class="p-4 stagger-item card-base" :style="{ '--i': i }">
          <div class="flex items-center justify-between mb-2">
            <p class="font-mono text-[10px] text-muted-foreground tracking-wider">{{ kpi.label }}</p>
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-surface/50" :style="{ color: kpi.color }">
              <component :is="kpi.icon" class="h-3.5 w-3.5" />
            </div>
          </div>
          <p class="font-mono text-2xl font-bold tabular-nums text-foreground" :style="{ color: kpi.color }">{{ kpi.value.toLocaleString() }}</p>
        </Card>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 stagger-item" style="--i: 4">
        <Card class="p-4 card-base">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="font-mono text-xs font-semibold text-foreground">Hallazgos por severidad</p>
          </div>
          <div v-if="severityData.every(v => v === 0)" class="flex items-center justify-center h-48 text-center">
            <p class="font-mono text-xs text-muted-foreground">No se encontraron hallazgos</p>
          </div>
          <BarChart v-else
            :labels="severityLabels"
            :datasets="[{ label: 'Hallazgos', data: severityData, backgroundColor: severityColors }]"
            :height="200"
            showLegend
          />
        </Card>
        <Card class="p-4 card-base">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-accent" />
            <p class="font-mono text-xs font-semibold text-foreground">Distribución de veredictos</p>
          </div>
          <div v-if="verdictData.every(v => v === 0)" class="flex items-center justify-center h-48 text-center">
            <p class="font-mono text-xs text-muted-foreground">Aún no hay veredictos</p>
          </div>
          <DoughnutChart v-else
            :labels="verdictLabels"
            :data="verdictData"
            :height="200"
            :colors="verdictColors"
          />
        </Card>
      </div>

      <!-- Top Opportunities -->
      <Card class="p-4 stagger-item card-base" style="--i: 5">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <Zap class="h-4 w-4 text-primary" />
            <p class="font-mono text-xs font-semibold text-foreground">Oportunidades prioritarias</p>
          </div>
          <Badge variant="info" class="font-mono text-[9px]">{{ context?.opportunities.total ?? 0 }} total</Badge>
        </div>
        <div v-if="!context?.opportunities.top?.length" class="py-6 text-center font-mono text-xs text-muted-foreground">
          Sin oportunidades disponibles
        </div>
        <div v-else class="space-y-2">
          <div v-for="(opp, i) in context!.opportunities.top" :key="opp.id"
            class="flex items-center justify-between rounded-lg bg-surface/20 px-3 py-2.5 transition-all hover:bg-surface/40 hover:border-primary/20 border border-transparent"
            :style="{ '--i': i, animation: 'staggerFadeIn 0.3s ease-out both', animationDelay: (i * 40 + 150) + 'ms' }"
          >
            <div class="flex-1 min-w-0">
              <p class="font-mono text-xs font-semibold text-foreground truncate">{{ opp.name }}</p>
              <p class="font-mono text-[10px] text-muted-foreground">{{ opp.domain }} · {{ opp.endpoints }} endpoints</p>
            </div>
            <div class="flex items-center gap-3 shrink-0 ml-3">
              <span class="font-mono text-[10px] text-muted-foreground">SCORE {{ opp.opportunity_score.toFixed(1) }}</span>
              <div class="flex h-7 w-7 items-center justify-center rounded-md text-[10px] font-bold font-mono"
                :class="opp.opportunity_score >= 7 ? 'bg-success/20 text-success' : opp.opportunity_score >= 4 ? 'bg-warning/20 text-warning' : 'bg-muted/20 text-muted-foreground'"
              >
                {{ opp.opportunity_score.toFixed(0) }}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <!-- System footer -->
      <div class="flex flex-col gap-2 border-t border-border/20 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[9px] text-muted-foreground">
          <span>CATEYE {{ context?._meta?.version || '' }}</span>
          <span>●</span>
          <span>DB: {{ context?.counts.targets || 0 }} targets</span>
          <span>●</span>
          <span>Último scan: {{ context?.scans?.active || context?.counts?.active_scans ? 'En curso' : 'Esperando' }}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
          <span class="font-mono text-[9px] text-muted-foreground">{{ context?.system?.status === 'healthy' ? 'SISTEMA NOMINAL' : 'SISTEMA INICIALIZANDO' }}</span>
        </div>
      </div>
    </template>
  </div>
</template>
