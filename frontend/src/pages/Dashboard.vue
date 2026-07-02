<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, getOrionContext } from '@/lib/api'
import type { OrionContext } from '@/types'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart, DoughnutChart } from '@/components/charts'
import {
  Activity, AlertTriangle, BarChart3, Clock, FileSearch, LayoutDashboard,
  RefreshCw, ShieldCheck, Target, TrendingUp, Zap,
} from '@lucide/vue'

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
    error.value = e?.message || 'Error al cargar el dashboard'
  }
  finally { loading.value = false }
}

onMounted(fetchData)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const kpis = computed<KpiItem[]>(() => {
  if (!context.value) return []
  const c = context.value.counts
  return [
    { label: 'Targets', value: c.targets, icon: Target, color: '#3b82f6' },
    { label: 'Endpoints', value: c.endpoints, icon: Activity, color: '#22c55e' },
    { label: 'Findings', value: c.findings, icon: FileSearch, color: '#eab308' },
    { label: 'Confirmados', value: c.confirmed_findings, icon: ShieldCheck, color: '#a855f7' },
  ]
})

const hasTargets = computed(() => (context.value?.counts.targets ?? 0) > 0)

const severityLabels = ['Critical', 'High', 'Medium', 'Low', 'Info']
const severityColors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#6b7280']
const severityData = computed(() => {
  if (!context.value) return [0, 0, 0, 0, 0]
  const s = context.value.findings.by_severity
  return [s.critical || 0, s.high || 0, s.medium || 0, s.low || 0, s.info || 0]
})

const verdictLabels = ['Confirmed', 'Rejected', 'Inconclusive', 'Pending']
const verdictData = computed(() => {
  if (!context.value) return [0, 0, 0, 0]
  const v = context.value.verdicts.by_status
  return [v.confirmed || 0, v.rejected || 0, v.inconclusive || 0, v.pending || 0]
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Dashboard</p>
      <h1 class="font-display text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
      <p class="text-sm text-muted-foreground">Estado actual del sistema Orion</p>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton class="h-60 rounded-xl" />
        <Skeleton class="h-60 rounded-xl" />
      </div>
      <Skeleton class="h-40 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error al cargar el dashboard</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!hasTargets">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <LayoutDashboard class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay targets configurados</p>
        <p class="mt-1 text-xs text-muted-foreground">Agregá un target para comenzar a monitorear</p>
        <Button variant="outline" size="sm" class="mt-4">Agregar Target</Button>
      </div>
    </template>

    <template v-else>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card v-for="(kpi, i) in kpis" :key="kpi.label" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-center justify-between mb-2">
            <p class="text-xs text-muted-foreground">{{ kpi.label }}</p>
            <component :is="kpi.icon" class="h-4 w-4" :style="{ color: kpi.color }" />
          </div>
          <p class="text-2xl font-bold tabular-nums text-foreground">{{ kpi.value.toLocaleString() }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 stagger-item" style="--i: 4">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Hallazgos por severidad</p>
          </div>
          <BarChart
            :labels="severityLabels"
            :datasets="[{ label: 'Hallazgos', data: severityData, backgroundColor: severityColors }]"
            :height="200"
            showLegend
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <TrendingUp class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Distribución de veredictos</p>
          </div>
          <DoughnutChart
            :labels="verdictLabels"
            :data="verdictData"
            :height="200"
          />
        </Card>
      </div>

      <Card class="p-4 stagger-item" style="--i: 5">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <Zap class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Top Oportunidades</p>
          </div>
          <Badge variant="info">{{ context?.opportunities.total ?? 0 }} total</Badge>
        </div>
        <div v-if="!context?.opportunities.top?.length" class="py-6 text-center text-xs text-muted-foreground">
          Sin oportunidades disponibles
        </div>
        <div v-else class="space-y-2">
          <div v-for="(opp, i) in context!.opportunities.top" :key="opp.id"
            class="flex items-center justify-between rounded-lg bg-surface/20 px-3 py-2 transition-colors hover:bg-surface/40 hover-scale"
            :style="{ '--i': i, animation: 'staggerFadeIn 0.3s ease-out both', animationDelay: (i * 40 + 150) + 'ms' }"
          >
            <div class="flex-1 min-w-0">
              <p class="text-xs font-semibold text-foreground truncate">{{ opp.name }}</p>
              <p class="text-[10px] text-muted-foreground">{{ opp.domain }} · {{ opp.endpoints }} endpoints</p>
            </div>
            <div class="flex items-center gap-3 shrink-0 ml-3">
              <span class="text-[10px] text-muted-foreground">Score {{ opp.opportunity_score.toFixed(1) }}</span>
              <Badge :variant="opp.opportunity_score >= 7 ? 'success' : opp.opportunity_score >= 4 ? 'warning' : 'default'" class="text-[10px]">
                {{ opp.opportunity_score.toFixed(1) }}
              </Badge>
            </div>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>
