<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle, DollarSign, TrendingUp, PieChart, RefreshCw, Settings,
  Shield, Play, Pause, Activity, BarChart3, Target,
} from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Badge from '@/components/ui/Badge.vue'
import {
  getInvestmentStatus, getInvestmentMetrics, getExposure, getAllocation,
  type InvestmentStatus, type ConsolidateMetrics,
} from '@/lib/api'

const router = useRouter()
const status = ref<InvestmentStatus | null>(null)
const metrics = ref<ConsolidateMetrics | null>(null)
const exposure = ref<any>(null)
const allocation = ref<any>(null)
const pnlChart = ref<{ date: string; pnl: number }[]>([])
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [s, m, e, a] = await Promise.all([
      getInvestmentStatus(),
      getInvestmentMetrics(),
      getExposure(),
      getAllocation(),
    ])
    if (s.success) status.value = s.status
    if (m.success) { metrics.value = m.metrics; pnlChart.value = m.pnl_chart }
    if (e.success) exposure.value = e.exposure
    if (a.success) allocation.value = a
  } catch (e) {
    error.value = 'Error de conexión con el backend de inversiones'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

const totalCapital = computed(() => status.value?.total_capital ?? 0)
const deployed = computed(() => status.value?.deployed ?? 0)
const available = computed(() => status.value?.available ?? 0)
const utilization = computed(() => totalCapital.value > 0 ? (deployed.value / totalCapital.value * 100) : 0)
const totalPnl = computed(() => status.value?.summary?.total_pnl ?? 0)
const totalPnlPct = computed(() => status.value?.summary?.total_pnl_pct ?? 0)
const sharpe = computed(() => status.value?.summary?.sharpe ?? 0)
const totalTrades = computed(() => status.value?.summary?.total_trades ?? 0)
const winRate = computed(() => status.value?.summary?.win_rate ?? 0)
const inDrawdown = computed(() => status.value?.summary?.in_drawdown ?? false)
const maxDrawdown = computed(() => status.value?.summary?.max_drawdown_pct ?? 0)
const hasData = computed(() => totalCapital.value > 0)
const strategies = computed(() => Object.values(status.value?.strategies ?? {}))

const insuficientLimit = computed(() => exposure.value && !exposure.value.within_limit)
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">ATLAS</h1>
        <p class="text-muted-foreground">Gestión de inversiones automatizada</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="fetchData"
          class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
          Actualizar
        </button>
        <button @click="router.push('/atlas/settings')"
          class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <Settings class="h-3 w-3" />
          Configuración
        </button>
        <button @click="router.push('/investments')"
          class="flex items-center gap-1.5 rounded-lg border border-primary/40 px-3 py-1.5 text-xs font-mono text-primary hover:text-primary/80 transition-colors"
        >
          <BarChart3 class="h-3 w-3" />
          Hub completo
        </button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Skeleton v-for="i in 3" :key="i" class="h-28 rounded-lg" />
      <Skeleton class="h-48 rounded-lg md:col-span-2" />
      <Skeleton class="h-48 rounded-lg" />
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="border border-destructive/30 rounded-lg p-6 text-center bg-card">
      <AlertTriangle class="h-8 w-8 text-destructive mx-auto mb-2" />
      <p class="text-sm font-semibold text-foreground">{{ error }}</p>
      <button @click="fetchData"
        class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/80 transition-colors"
      >
        Reintentar
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState v-if="!loading && !error && !hasData"
      title="Sin capital desplegado"
      description="Agregá capital desde Configuración o conectá un payout para empezar a invertir."
      action-label="Configurar inversiones"
      @action="router.push('/atlas/settings')"
    />

    <!-- KPIs -->
    <div v-if="!loading && !error && hasData" class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <DollarSign class="h-3.5 w-3.5" />
          <span>Capital total</span>
        </div>
        <div class="text-xl font-bold">${{ totalCapital.toLocaleString('es-AR', { minimumFractionDigits: 2 }) }}</div>
        <div class="text-[10px] text-muted-foreground mt-0.5">
          {{ deployed.toFixed(2) }} deployado · {{ available.toFixed(2) }} disponible
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <TrendingUp class="h-3.5 w-3.5" />
          <span>P&L total</span>
        </div>
        <div class="text-xl font-bold" :class="totalPnl >= 0 ? 'text-success' : 'text-destructive'">
          {{ totalPnl >= 0 ? '+' : '' }}{{ totalPnl.toFixed(2) }}
        </div>
        <div class="text-[10px]" :class="totalPnlPct >= 0 ? 'text-success' : 'text-destructive'">
          {{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <Shield class="h-3.5 w-3.5" />
          <span>Riesgo</span>
        </div>
        <div class="text-xl font-bold" :class="inDrawdown ? 'text-destructive' : 'text-success'">
          {{ inDrawdown ? 'Drawdown' : 'Normal' }}
        </div>
        <div class="text-[10px] text-muted-foreground mt-0.5">
          Sharpe {{ sharpe.toFixed(2) }} · DD máx {{ maxDrawdown.toFixed(1) }}%
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <Activity class="h-3.5 w-3.5" />
          <span>Rendimiento</span>
        </div>
        <div class="text-xl font-bold">{{ (winRate * 100).toFixed(1) }}%</div>
        <div class="text-[10px] text-muted-foreground mt-0.5">
          {{ totalTrades }} trades · {{ (utilization).toFixed(0) }}% utilizado
        </div>
      </div>
    </div>

    <!-- Risk warning -->
    <div v-if="insuficientLimit && !loading"
      class="flex items-center gap-2 rounded-lg bg-warning/10 border border-warning/20 px-4 py-2.5"
    >
      <AlertTriangle class="h-4 w-4 text-warning shrink-0" />
      <span class="text-xs text-warning">Límite de alto riesgo alcanzado. No se pueden desplegar más estrategias agresivas/especulativas.</span>
    </div>

    <!-- Strategies + PnL chart -->
    <div v-if="!loading && !error && hasData" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Active strategies -->
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
          <Target class="h-4 w-4 text-primary" />
          Estrategias activas
        </h3>
        <div v-if="strategies.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          No hay estrategias activas.
        </div>
        <div v-for="s in strategies.slice(0, 5)" :key="s.id"
          class="flex items-center justify-between py-2 border-b border-border/20 last:border-0"
        >
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full" :class="s.paused ? 'bg-warning' : 'bg-success'" />
            <span class="text-sm">{{ s.id }}</span>
            <Badge :variant="s.risk_level === 'aggressive' || s.risk_level === 'speculative' ? 'warning' : 'default'" size="xs">
              {{ s.risk_level }}
            </Badge>
          </div>
          <div class="text-xs font-mono text-muted-foreground">
            ${{ (s.total_deployed ?? 0).toFixed(0) }}
          </div>
        </div>
        <button @click="router.push('/investments')"
          v-if="strategies.length > 5"
          class="text-xs text-primary hover:underline mt-2"
        >
          Ver todas las estrategias
        </button>
      </div>

      <!-- PnL Chart -->
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3 flex items-center gap-2">
          <BarChart3 class="h-4 w-4 text-primary" />
          P&L diario
        </h3>
        <div v-if="pnlChart.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          Sin datos de P&L todavía.
        </div>
        <div v-else class="space-y-1.5">
          <div v-for="(pt, i) in pnlChart.slice(-14)" :key="pt.date"
            class="flex items-center gap-2 text-xs"
          >
            <span class="w-24 text-muted-foreground font-mono">{{ pt.date }}</span>
            <div class="flex-1 h-4 rounded bg-surface/30 relative overflow-hidden">
              <div class="h-full rounded transition-all"
                :class="pt.pnl >= 0 ? 'bg-success/40' : 'bg-destructive/40'"
                :style="{ width: Math.min(Math.abs(pt.pnl) / 10, 100) + '%' }"
              />
            </div>
            <span class="w-16 text-right font-mono" :class="pt.pnl >= 0 ? 'text-success' : 'text-destructive'">
              {{ pt.pnl >= 0 ? '+' : '' }}{{ pt.pnl.toFixed(2) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick link to full hub -->
    <div v-if="!loading && !error && hasData" class="flex gap-4">
      <router-link to="/investments" class="text-xs text-primary hover:underline">
        Hub completo de inversiones →
      </router-link>
      <router-link to="/atlas/settings" class="text-xs text-muted-foreground hover:text-foreground transition-colors">
        Configuración y conexiones
      </router-link>
    </div>
  </div>
</template>
