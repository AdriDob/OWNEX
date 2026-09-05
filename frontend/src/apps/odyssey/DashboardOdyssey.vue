<script setup lang="ts">
import { AlertTriangle, DollarSign, ListChecks, RefreshCw, Settings, TrendingUp, Wallet } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

interface SummaryData {
  total_bets: number
  wins: number
  losses: number
  pending: number
  win_rate: number
}

interface ROI {
  roi: number
  total_staked: number
  total_payout: number
}

interface PerfData {
  profit: number
  avg_odds: number
  avg_ev: number
}

const router = useRouter()
const { toast } = useToast()
const summary = ref<SummaryData | null>(null)
const roi = ref<ROI | null>(null)
const perf = ref<PerfData | null>(null)
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [sumRes, roiRes, perfRes] = await Promise.allSettled([
      fetch('/api/odyssey/analytics/summary'),
      fetch('/api/odyssey/analytics/roi'),
      fetch('/api/odyssey/analytics/performance'),
    ])
    if (sumRes.status === 'fulfilled' && sumRes.value.ok) summary.value = await sumRes.value.json()
    if (roiRes.status === 'fulfilled' && roiRes.value.ok) roi.value = await roiRes.value.json()
    if (perfRes.status === 'fulfilled' && perfRes.value.ok) perf.value = await perfRes.value.json()
    if (!summary.value && !roi.value) {
      error.value = 'No se recibieron datos del servidor'
    }
  } catch (e) {
    error.value = 'Error de conexión con el backend'
    toast.error('Error', 'No se pudo cargar el dashboard de ODYSSEY')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

const hasData = () => (summary.value?.total_bets ?? 0) > 0
const profitClass = (v: number | undefined) => (v != null ? (v >= 0 ? 'text-success' : 'text-destructive') : '')
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">ODYSSEY</h1>
        <p class="text-muted-foreground">Analítica de apuestas</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="fetchData" class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
          Actualizar
        </button>
        <button @click="router.push('/odyssey/settings')" class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors">
          <Settings class="h-3 w-3" />
          Configuración
        </button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Skeleton v-for="i in 4" :key="i" class="h-28 rounded-lg" />
      <Skeleton class="h-48 rounded-lg md:col-span-2" />
      <Skeleton class="h-48 rounded-lg md:col-span-2" />
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="border border-destructive/30 rounded-lg p-6 text-center bg-card">
      <AlertTriangle class="h-8 w-8 text-destructive mx-auto mb-2" />
      <p class="text-sm font-semibold text-foreground">{{ error }}</p>
      <button @click="fetchData" class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/80 transition-colors">
        Reintentar
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
       v-if="!loading && !error && !hasData()"
       title="Sin datos de apuestas"
       description="Importá tu historial de apuestas o conectá una plataforma para ver estadísticas."
       action-label="Configurar conexiones"
       @action="router.push('/odyssey/settings')"
    />

    <!-- KPI Cards -->
    <div v-if="!loading && !error && hasData()" class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <ListChecks class="h-4 w-4" />
          <span>Total apuestas</span>
        </div>
        <div class="text-2xl font-bold">{{ summary?.total_bets ?? 0 }}</div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <TrendingUp class="h-4 w-4" />
          <span>Win rate</span>
        </div>
        <div class="text-2xl font-bold">{{ (summary?.win_rate ?? 0).toFixed(1) }}%</div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <DollarSign class="h-4 w-4" />
          <span>ROI</span>
        </div>
        <div class="text-2xl font-bold" :class="profitClass(roi?.roi)">
          {{ roi?.roi != null ? (roi.roi >= 0 ? '+' : '') + roi.roi.toFixed(2) + '%' : '—' }}
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <Wallet class="h-4 w-4" />
          <span>Ganancia / Pérdida</span>
        </div>
        <div class="text-2xl font-bold" :class="profitClass(perf?.profit)">
          {{ perf?.profit != null ? '$' + (perf.profit >= 0 ? '+' : '') + perf.profit.toLocaleString('es-AR', { minimumFractionDigits: 2 }) : '—' }}
        </div>
      </div>
    </div>

    <!-- Detail metrics -->
    <div v-if="!loading && !error && hasData()" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3">Resumen de apuestas</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-muted-foreground">Ganadas</span>
            <span class="text-success">{{ summary?.wins ?? 0 }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Perdidas</span>
            <span class="text-destructive">{{ summary?.losses ?? 0 }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Pendientes</span>
            <span class="text-warning">{{ summary?.pending ?? 0 }}</span>
          </div>
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3">Métricas avanzadas</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-muted-foreground">Odds promedio</span>
            <span class="font-mono">{{ perf?.avg_odds?.toFixed(2) ?? '—' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Valor esperado (EV) promedio</span>
            <span class="font-mono" :class="(perf?.avg_ev ?? 0) >= 0 ? 'text-success' : 'text-destructive'">
              {{ perf?.avg_ev != null ? (perf.avg_ev * 100).toFixed(2) + '%' : '—' }}
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Total apostado</span>
            <span class="font-mono">${{ roi?.total_staked?.toLocaleString('es-AR', { minimumFractionDigits: 2 }) ?? '—' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="flex gap-4">
      <router-link to="/odyssey/bankroll" class="text-xs text-primary hover:underline">Bankroll</router-link>
      <router-link to="/odyssey/bets" class="text-xs text-primary hover:underline">Historial de apuestas</router-link>
      <router-link to="/odyssey/analytics" class="text-xs text-primary hover:underline">Analítica completa</router-link>
    </div>
  </div>
</template>
