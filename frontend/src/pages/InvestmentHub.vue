<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle, ArrowDown, ArrowUp, BarChart3, DollarSign, Play, Pause,
  RefreshCw, Settings, Shield, Target, TrendingUp, Activity, Fuel,
  List, Zap, Wallet,
} from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Badge from '@/components/ui/Badge.vue'
import {
  getInvestmentStatus, getInvestmentMetrics, getAllocation, getExposure,
  getInvestmentEvents, getInvestmentStrategies, getCcxtInfo,
  deployStrategy, pauseStrategy, resumeStrategy, allocatePayout as apiAllocatePayout,
  updateInvestmentCapital, pauseAllInvestments, resumeAllInvestments,
  activateMaxRevenue, updateInvestmentConfig,
  type InvestmentStatus, type ConsolidateMetrics, type PnLPoint,
} from '@/lib/api'

const router = useRouter()
const activeTab = ref<'overview' | 'strategies' | 'ccxt'>('overview')

const loading = ref(true)
const error = ref('')

const status = ref<InvestmentStatus | null>(null)
const metrics = ref<ConsolidateMetrics | null>(null)
const allocation = ref<any>(null)
const exposure = ref<any>(null)
const events = ref<any[]>([])
const strategies = ref<any[]>([])
const ccxtInfo = ref<any>(null)
const pnlChart = ref<PnLPoint[]>([])

const deployAmount = ref<Record<string, number>>({})
const deployMsg = ref<Record<string, string>>({})
const capitalInput = ref(0)
const payoutInput = ref(0)

const totalCapital = computed(() => status.value?.total_capital ?? 0)
const deployed = computed(() => status.value?.deployed ?? 0)
const available = computed(() => status.value?.available ?? 0)
const totalPnl = computed(() => status.value?.summary?.total_pnl ?? 0)
const totalPnlPct = computed(() => status.value?.summary?.total_pnl_pct ?? 0)
const sharpe = computed(() => status.value?.summary?.sharpe ?? 0)
const maxDd = computed(() => status.value?.summary?.max_drawdown_pct ?? 0)
const winRate = computed(() => status.value?.summary?.win_rate ?? 0)
const totalTrades = computed(() => status.value?.summary?.total_trades ?? 0)
const inDrawdown = computed(() => status.value?.summary?.in_drawdown ?? false)
const isPaused = computed(() => status.value?.paused ?? false)
const hasData = computed(() => totalCapital.value > 0)

const stratList = computed(() => Object.values(status.value?.strategies ?? {}))

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [s, m, a, e, ev, st] = await Promise.all([
      getInvestmentStatus(),
      getInvestmentMetrics(),
      getAllocation(),
      getExposure(),
      getInvestmentEvents(20),
      getInvestmentStrategies(),
    ])
    if (s.success) status.value = s.status
    if (m.success) { metrics.value = m.metrics; pnlChart.value = m.pnl_chart }
    if (a.success) allocation.value = a
    if (e.success) exposure.value = e.exposure
    if (ev.success) events.value = ev.events
    if (st.success) strategies.value = st.strategies
  } catch (e) {
    error.value = 'Error de conexión con el backend de inversiones'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

async function handleDeploy(sid: string) {
  const amt = deployAmount.value[sid] || 0
  if (amt <= 0) return
  deployMsg.value[sid] = 'Desplegando...'
  try {
    const r = await deployStrategy(sid, amt)
    deployMsg.value[sid] = r.success ? `✓ $${amt} desplegado` : `✗ ${r.result?.error || 'Error'}`
  } catch {
    deployMsg.value[sid] = '✗ Error de conexión'
  }
  setTimeout(() => { deployMsg.value[sid] = '' }, 3000)
  fetchData()
}

async function handlePause(sid: string) {
  await pauseStrategy(sid)
  fetchData()
}

async function handleResume(sid: string) {
  await resumeStrategy(sid)
  fetchData()
}

async function handleAllocatePayout() {
  if (payoutInput.value <= 0) return
  await apiAllocatePayout(payoutInput.value)
  payoutInput.value = 0
  fetchData()
}

async function handleUpdateCapital() {
  if (capitalInput.value <= 0) return
  await updateInvestmentCapital(capitalInput.value)
  capitalInput.value = 0
  fetchData()
}

async function handleMaxRevenue() {
  await activateMaxRevenue()
  fetchData()
}

async function handlePauseAll() {
  await pauseAllInvestments()
  fetchData()
}

async function handleResumeAll() {
  await resumeAllInvestments()
  fetchData()
}

function formatUsd(v: number) {
  return v.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Activity class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">INVESTMENT HUB</span>
          <span class="lamp" :class="isPaused ? 'lamp-amber' : totalPnl > 0 ? 'lamp-green' : 'lamp-red'" />
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Centro de Inversiones</h1>
        <p class="text-xs text-muted-foreground">Operaciones automatizadas de trading, estrategias y monitoreo de capital</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap shrink-0">
        <button @click="fetchData"
          class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
          Actualizar
        </button>
        <button @click="handlePauseAll" v-if="!isPaused"
          class="flex items-center gap-1.5 rounded-lg border border-warning/40 px-3 py-1.5 text-xs font-mono text-warning hover:text-warning/80 transition-colors"
        >
          <Pause class="h-3 w-3" />
          Pausar todo
        </button>
        <button @click="handleResumeAll" v-if="isPaused"
          class="flex items-center gap-1.5 rounded-lg border border-success/40 px-3 py-1.5 text-xs font-mono text-success hover:text-success/80 transition-colors"
        >
          <Play class="h-3 w-3" />
          Reanudar todo
        </button>
        <button @click="handleMaxRevenue"
          class="flex items-center gap-1.5 rounded-lg border border-primary/40 px-3 py-1.5 text-xs font-mono text-primary hover:text-primary/80 transition-colors"
        >
          <Zap class="h-3 w-3" />
          Max Revenue
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-border/30 pb-1 overflow-x-auto">
      <button v-for="tab in [{id:'overview',label:'Resumen',icon:BarChart3},{id:'strategies',label:'Estrategias',icon:Target},{id:'ccxt',label:'CCXT Exchanges',icon:Wallet}]" :key="tab.id"
        @click="activeTab = tab.id"
        :class="[
          'flex items-center gap-1.5 px-3 py-2 font-mono text-xs rounded-t-lg transition-all whitespace-nowrap',
          activeTab === tab.id ? 'bg-primary/10 text-primary border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground',
        ]"
      >
        <component :is="tab.icon" class="h-3.5 w-3.5" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-lg" />
      </div>
      <Skeleton class="h-48 rounded-lg" />
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

    <!-- ════════════ OVERVIEW TAB ════════════ -->
    <template v-if="!loading && !error && activeTab === 'overview'">
      <!-- Capital actions -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="border border-border/50 rounded-lg p-4 bg-card">
          <h3 class="text-xs font-semibold mb-2 flex items-center gap-1.5">
            <DollarSign class="h-3.5 w-3.5 text-primary" />
            Asignar payout
          </h3>
          <div class="flex gap-2">
            <input v-model.number="payoutInput" type="number" placeholder="Monto USD"
              class="flex-1 rounded-lg border border-border/40 bg-surface/30 px-3 py-2 font-mono text-sm focus:outline-none focus:border-primary/50"
            />
            <button @click="handleAllocatePayout"
              class="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/80 transition-colors"
            >
              Asignar
            </button>
          </div>
        </div>
        <div class="border border-border/50 rounded-lg p-4 bg-card">
          <h3 class="text-xs font-semibold mb-2 flex items-center gap-1.5">
            <Settings class="h-3.5 w-3.5 text-primary" />
            Actualizar capital total
          </h3>
          <div class="flex gap-2">
            <input v-model.number="capitalInput" type="number" :placeholder="`Actual: $${totalCapital.toFixed(0)}`"
              class="flex-1 rounded-lg border border-border/40 bg-surface/30 px-3 py-2 font-mono text-sm focus:outline-none focus:border-primary/50"
            />
            <button @click="handleUpdateCapital"
              class="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/80 transition-colors"
            >
              Actualizar
            </button>
          </div>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">CAPITAL TOTAL</span>
            <Wallet class="h-4 w-4 text-primary" />
          </div>
          <p class="font-mono text-xl font-bold phosphor">${{ formatUsd(totalCapital) }}</p>
          <p class="text-[10px] text-muted-foreground mt-1">
            ${{ formatUsd(deployed) }} deployado · ${{ formatUsd(available) }} disponible
          </p>
        </div>
        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">P&L TOTAL</span>
            <TrendingUp class="h-4 w-4" :class="totalPnl >= 0 ? 'text-success' : 'text-destructive'" />
          </div>
          <p class="font-mono text-xl font-bold" :class="totalPnl >= 0 ? 'text-success' : 'text-destructive'">
            {{ totalPnl >= 0 ? '+' : '' }}${{ formatUsd(Math.abs(totalPnl)) }}
          </p>
          <p class="text-[10px] mt-1" :class="totalPnlPct >= 0 ? 'text-success' : 'text-destructive'">
            {{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%
          </p>
        </div>
        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">RIESGO</span>
            <Shield class="h-4 w-4" :class="inDrawdown ? 'text-destructive' : (sharpe > 1 ? 'text-success' : 'text-warning')" />
          </div>
          <p class="font-mono text-xl font-bold" :class="inDrawdown ? 'text-destructive' : (sharpe > 1 ? 'text-success' : 'text-warning')">
            {{ inDrawdown ? '⚠ Drawdown' : (sharpe > 1 ? 'Saludable' : 'Moderado') }}
          </p>
          <p class="text-[10px] text-muted-foreground mt-1">
            Sharpe {{ sharpe.toFixed(2) }} · DD máx {{ maxDd.toFixed(1) }}%
          </p>
        </div>
        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">RENDIMIENTO</span>
            <Activity class="h-4 w-4" :class="winRate > 0.5 ? 'text-success' : 'text-warning'" />
          </div>
          <p class="font-mono text-xl font-bold">{{ (winRate * 100).toFixed(1) }}%</p>
          <p class="text-[10px] text-muted-foreground mt-1">
            {{ totalTrades }} trades · {{ totalCapital > 0 ? ((deployed / totalCapital) * 100).toFixed(0) : 0 }}% utilizado
          </p>
        </div>
      </div>

      <!-- Risk warning -->
      <div v-if="exposure && !exposure.within_limit"
        class="flex items-center gap-2 rounded-lg bg-warning/10 border border-warning/20 px-4 py-2.5"
      >
        <AlertTriangle class="h-4 w-4 text-warning shrink-0" />
        <span class="text-xs text-warning">Límite de alto riesgo alcanzado. No se pueden desplegar más estrategias agresivas/especulativas.</span>
      </div>

      <!-- PnL Chart + Exposure -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="border border-border/50 rounded-lg p-4 bg-card">
          <h3 class="text-xs font-semibold mb-3 flex items-center gap-1.5">
            <BarChart3 class="h-3.5 w-3.5 text-primary" />
            P&L diario
          </h3>
          <div v-if="pnlChart.length === 0" class="text-xs text-muted-foreground py-4 text-center">
            Sin datos de P&L. Empezá a operar para ver el gráfico.
          </div>
          <div v-else class="space-y-1 max-h-64 overflow-y-auto">
            <div v-for="pt in pnlChart.slice(-21)" :key="pt.date"
              class="flex items-center gap-2 text-xs"
            >
              <span class="w-20 text-muted-foreground font-mono shrink-0">{{ pt.date }}</span>
              <div class="flex-1 h-4 rounded bg-surface/30 relative overflow-hidden">
                <div class="h-full rounded transition-all"
                  :class="pt.pnl >= 0 ? 'bg-success/50' : 'bg-destructive/50'"
                  :style="{ width: Math.min(Math.abs(pt.pnl) / Math.max(...pnlChart.slice(-21).map(p => Math.abs(p.pnl)), 1) * 100, 100) + '%' }"
                />
              </div>
              <span class="w-16 text-right font-mono shrink-0" :class="pt.pnl >= 0 ? 'text-success' : 'text-destructive'">
                {{ pt.pnl >= 0 ? '+' : '' }}{{ pt.pnl.toFixed(2) }}
              </span>
            </div>
          </div>
        </div>
        <div class="border border-border/50 rounded-lg p-4 bg-card">
          <h3 class="text-xs font-semibold mb-3 flex items-center gap-1.5">
            <Shield class="h-3.5 w-3.5 text-primary" />
            Exposición y límites
          </h3>
          <div v-if="!exposure" class="text-xs text-muted-foreground py-4 text-center">
            Sin datos de exposición.
          </div>
          <div v-else class="space-y-3">
            <div class="flex justify-between text-xs">
              <span class="text-muted-foreground">High-risk deployado</span>
              <span class="font-mono">${{ (exposure.high_risk_deployed || 0).toFixed(2) }}</span>
            </div>
            <div class="flex justify-between text-xs">
              <span class="text-muted-foreground">Límite máximo</span>
              <span class="font-mono">${{ (exposure.max_allowed || 0).toFixed(2) }}</span>
            </div>
            <div class="h-2 rounded-full bg-surface/30 mt-1">
              <div class="h-full rounded-full transition-all"
                :class="exposure.within_limit ? 'bg-success/60' : 'bg-destructive/60'"
                :style="{ width: Math.min((exposure.high_risk_deployed || 0) / Math.max(exposure.max_allowed || 1, 1) * 100, 100) + '%' }"
              />
            </div>
            <div class="flex justify-between text-xs">
              <span class="text-muted-foreground">Capital total</span>
              <span class="font-mono">${{ (exposure.total_capital || 0).toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent events -->
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-xs font-semibold mb-3 flex items-center gap-1.5">
          <List class="h-3.5 w-3.5 text-primary" />
          Eventos recientes
        </h3>
        <div v-if="events.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          Sin eventos registrados.
        </div>
        <div v-for="(ev, i) in events.slice(0, 15)" :key="i"
          class="flex items-center gap-3 py-1.5 border-b border-border/10 last:border-0 text-xs"
        >
          <span class="text-[10px] font-mono text-muted-foreground w-16 shrink-0">{{ ev.timestamp?.slice(0, 10) || '—' }}</span>
          <Badge size="xs" variant="outline">{{ ev.type || ev.action || 'event' }}</Badge>
          <span class="text-muted-foreground truncate">{{ ev.description || ev.detail || '' }}</span>
          <span v-if="ev.amount" class="font-mono ml-auto shrink-0">${{ ev.amount.toFixed(2) }}</span>
        </div>
      </div>
    </template>

    <!-- ════════════ STRATEGIES TAB ════════════ -->
    <template v-if="!loading && !error && activeTab === 'strategies'">
      <!-- All available strategies -->
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-xs font-semibold mb-3 flex items-center gap-1.5">
          <Target class="h-3.5 w-3.5 text-primary" />
          Estrategias registradas
        </h3>
        <div v-if="strategies.length === 0" class="text-xs text-muted-foreground py-4 text-center">
          No hay estrategias registradas en el sistema.
        </div>
        <div v-for="s in strategies" :key="s.id"
          class="border border-border/20 rounded-lg mb-3 p-4"
        >
          <div class="flex items-start justify-between mb-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold">{{ s.name || s.id }}</span>
                <Badge :variant="s.risk_level === 'aggressive' || s.risk_level === 'speculative' ? 'warning' : (s.risk_level === 'moderate' ? 'default' : 'secondary')" size="xs">
                  {{ s.risk_level }}
                </Badge>
                <Badge variant="outline" size="xs">{{ s.type }}</Badge>
              </div>
              <p v-if="s.description" class="text-xs text-muted-foreground mt-1">{{ s.description }}</p>
            </div>
          </div>

          <!-- Active state -->
          <div v-if="s.id === 'ccxt_spot' || true">
            <div class="flex items-center gap-3 text-xs text-muted-foreground mb-2">
              <span v-if="s.expected_roi_pct">ROI esperado: {{ s.expected_roi_pct }}%</span>
              <span v-if="s.max_drawdown_pct">DD máx: {{ s.max_drawdown_pct }}%</span>
              <span v-if="s.sharpe_target">Sharpe target: {{ s.sharpe_target }}</span>
            </div>

            <!-- Strategy status line -->
            <div class="flex items-center gap-2 text-xs mb-2">
              <div class="h-2 w-2 rounded-full"
                :class="stratList.find(x => x.id === s.id)?.paused ? 'bg-warning' : 'bg-success'"
              />
              <span>{{ stratList.find(x => x.id === s.id)?.paused ? 'Pausada' : 'Activa' }}</span>
              <span class="text-muted-foreground">|</span>
              <span class="text-muted-foreground">Deployado: ${{ (stratList.find(x => x.id === s.id)?.total_deployed || 0).toFixed(0) }}</span>
            </div>

            <!-- Controls -->
            <div class="flex items-center gap-2 flex-wrap">
              <input v-model.number="deployAmount[s.id]" type="number" placeholder="Monto a deployar"
                class="w-28 rounded-lg border border-border/40 bg-surface/30 px-2.5 py-1.5 font-mono text-xs focus:outline-none focus:border-primary/50"
              />
              <button @click="handleDeploy(s.id)"
                class="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-[10px] font-semibold text-primary-foreground hover:bg-primary/80 transition-colors"
              >
                <ArrowUp class="h-3 w-3" />
                Deploy
              </button>
              <button @click="handlePause(s.id)" v-if="!stratList.find(x => x.id === s.id)?.paused"
                class="flex items-center gap-1 rounded-lg border border-warning/40 px-3 py-1.5 text-[10px] font-mono text-warning hover:text-warning/80 transition-colors"
              >
                <Pause class="h-3 w-3" />
                Pausar
              </button>
              <button @click="handleResume(s.id)" v-if="stratList.find(x => x.id === s.id)?.paused"
                class="flex items-center gap-1 rounded-lg border border-success/40 px-3 py-1.5 text-[10px] font-mono text-success hover:text-success/80 transition-colors"
              >
                <Play class="h-3 w-3" />
                Reanudar
              </button>
              <span v-if="deployMsg[s.id]" class="text-xs" :class="deployMsg[s.id].startsWith('✓') ? 'text-success' : 'text-destructive'">
                {{ deployMsg[s.id] }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ════════════ CCXT TAB ════════════ -->
    <template v-if="!loading && !error && activeTab === 'ccxt'">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-xs font-semibold mb-3 flex items-center gap-1.5">
          <Wallet class="h-3.5 w-3.5 text-primary" />
          CCXT — 100+ Exchanges
        </h3>
        <p class="text-xs text-muted-foreground mb-4">
          Conexión unificada via CCXT. Usá las API de inversión para conectarte, consultar balances y operar.
        </p>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div v-for="ex in ['binance', 'coinbase', 'kraken', 'kucoin', 'bybit', 'okx', 'bitfinex', 'gate']" :key="ex"
            class="border border-border/30 rounded-lg p-3 text-center hover:border-primary/30 transition-colors"
          >
            <div class="font-mono text-xs font-semibold">{{ ex }}</div>
            <div class="text-[10px] text-muted-foreground mt-1">spot · futures</div>
          </div>
        </div>
        <div class="mt-4 text-xs text-muted-foreground">
          <p>Endpoint disponible: <code class="font-mono text-primary">GET /api/investment/ccxt/info?exchange=binance</code></p>
          <p class="mt-1">Conectate via <code class="font-mono text-primary">POST /api/investment/ccxt/connect</code></p>
        </div>
      </div>
    </template>

    <!-- ═══ HOW-TO FOOTER ═══ -->
    <div class="border border-border/30 rounded-xl p-4 card-base" v-if="!loading && !error">
      <div class="flex items-center gap-2 mb-3">
        <Zap class="h-4 w-4 text-primary" />
        <h3 class="text-sm font-semibold">Cómo usar este hub</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
        <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
          <p class="font-semibold text-foreground flex items-center gap-1.5">
            <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
            Gestioná capital
          </p>
          <p class="text-muted-foreground leading-relaxed">
            Usá "Asignar payout" para inyectar ganancias y "Actualizar capital" para ajustar el total disponible. Monitoreá P&L y Sharpe en las KPI cards.
          </p>
        </div>
        <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
          <p class="font-semibold text-foreground flex items-center gap-1.5">
            <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
            Desplegá estrategias
          </p>
          <p class="text-muted-foreground leading-relaxed">
            En la pestaña "Estrategias" cada perfil tiene botones Deploy/Pause/Resume. Respetá los límites de riesgo por nivel.
          </p>
        </div>
        <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
          <p class="font-semibold text-foreground flex items-center gap-1.5">
            <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">3</span>
            Conectá exchanges
          </p>
          <p class="text-muted-foreground leading-relaxed">
            En "CCXT Exchanges" conectá tus APIs de Binance, Coinbase, Kraken y más. Todo desde un mismo panel.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
