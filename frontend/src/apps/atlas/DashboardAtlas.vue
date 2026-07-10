<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { AlertTriangle, DollarSign, PieChart, RefreshCw, Settings, TrendingUp } from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

interface PortfolioData {
  total_value: number
  cash: number
  positions: Array<{
    symbol: string
    name: string
    asset_type: string
    quantity: number
    value: number
    pnl_percent: number | null
  }>
}

interface RiskData {
  top_concentration: number
  diversification_score: number
  crypto_exposure: number
  stock_exposure: number
  warnings: string[]
}

interface PerformanceData {
  total_pnl_percent: number
  current_value: number
}

const router = useRouter()
const { toast } = useToast()
const portfolio = ref<PortfolioData | null>(null)
const risk = ref<RiskData | null>(null)
const perf = ref<PerformanceData | null>(null)
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [portRes, riskRes, perfRes] = await Promise.allSettled([
      fetch('/api/atlas/portfolio'),
      fetch('/api/atlas/risk'),
      fetch('/api/atlas/performance'),
    ])
    if (portRes.status === 'fulfilled' && portRes.value.ok) portfolio.value = await portRes.value.json()
    if (riskRes.status === 'fulfilled' && riskRes.value.ok) risk.value = await riskRes.value.json()
    if (perfRes.status === 'fulfilled' && perfRes.value.ok) perf.value = await perfRes.value.json()
    if (!portfolio.value && !risk.value) {
      error.value = 'No se recibieron datos del servidor'
    }
  } catch (e) {
    error.value = 'Error de conexión con el backend'
    toast.error('Error', 'No se pudo cargar el dashboard de ATLAS')
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

function pnlClass(pct: number | null): string {
  if (pct === null || pct === undefined) return ''
  return pct >= 0 ? 'text-success' : 'text-destructive'
}

const hasData = () => portfolio.value && (portfolio.value.total_value > 0 || portfolio.value.positions.length > 0)
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">ATLAS</h1>
        <p class="text-muted-foreground">Gestión de inversiones</p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="fetchData" class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors">
          <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" />
          Actualizar
        </button>
        <button @click="router.push('/atlas/settings')" class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors">
          <Settings class="h-3 w-3" />
          Configuración
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
      <button @click="fetchData" class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white hover:bg-primary/80 transition-colors">
        Reintentar
      </button>
    </div>

    <!-- Empty state -->
    <EmptyState
       v-if="!loading && !error && portfolio && !hasData()"
       title="Sin datos de portfolio"
       description="Agregá activos o conectá un exchange para empezar a trackear tu portfolio."
       action-label="Configurar conexiones"
       @action="router.push('/atlas/settings')"
    />

    <!-- KPI Cards -->
    <div v-if="!loading && !error && hasData()" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <DollarSign class="h-4 w-4" />
          <span>Valor total</span>
        </div>
        <div class="text-2xl font-bold">${{ (portfolio?.total_value ?? 0).toLocaleString('es-AR', { minimumFractionDigits: 2 }) }}</div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <TrendingUp class="h-4 w-4" />
          <span>Retorno total</span>
        </div>
        <div class="text-2xl font-bold" :class="pnlClass(perf?.total_pnl_percent ?? null)">
          {{ perf?.total_pnl_percent != null ? (perf.total_pnl_percent >= 0 ? '+' : '') + perf.total_pnl_percent.toFixed(2) + '%' : '—' }}
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <div class="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <PieChart class="h-4 w-4" />
          <span>Activos</span>
        </div>
        <div class="text-2xl font-bold">{{ portfolio?.positions?.length || 0 }}</div>
      </div>
    </div>

    <!-- Risk & Diversification -->
    <div v-if="!loading && !error && hasData()" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3">Métricas de riesgo</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-muted-foreground">Diversificación</span>
            <span :class="(risk?.diversification_score ?? 0) > 60 ? 'text-success' : 'text-warning'">
              {{ risk?.diversification_score?.toFixed(1) ?? '—' }}/100
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Concentración máxima</span>
            <span :class="(risk?.top_concentration ?? 0) > 40 ? 'text-destructive' : 'text-success'">
              {{ risk?.top_concentration?.toFixed(1) ?? '—' }}%
            </span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Exposición crypto</span>
            <span>{{ risk?.crypto_exposure?.toFixed(1) ?? '—' }}%</span>
          </div>
          <div v-if="risk?.warnings?.length" class="mt-3 space-y-1">
            <div v-for="w in risk.warnings" :key="w" class="flex items-center gap-1.5 text-xs text-warning">
              <AlertTriangle class="h-3 w-3 shrink-0" />
              <span>{{ w }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="border border-border/50 rounded-lg p-4 bg-card">
        <h3 class="text-sm font-semibold mb-3">Distribución por tipo</h3>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-muted-foreground">Acciones</span>
            <span>{{ risk?.stock_exposure?.toFixed(1) ?? '—' }}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Crypto</span>
            <span>{{ risk?.crypto_exposure?.toFixed(1) ?? '—' }}%</span>
          </div>
          <div class="flex justify-between">
            <span class="text-muted-foreground">Efectivo</span>
            <span>{{ portfolio ? ((portfolio.cash / portfolio.total_value) * 100).toFixed(1) : '—' }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Top positions -->
    <div v-if="!loading && !error && hasData()">
      <h3 class="text-sm font-semibold mb-3">Principales posiciones</h3>
      <div class="border border-border/50 rounded-lg overflow-hidden">
        <div v-for="(pos, i) in portfolio?.positions?.slice(0, 10)" :key="pos.symbol"
          class="flex items-center justify-between px-4 py-2.5 text-sm"
          :class="i % 2 === 0 ? 'bg-card' : 'bg-surface/30'"
        >
          <div class="flex items-center gap-3">
            <span class="font-semibold">{{ pos.symbol }}</span>
            <span v-if="pos.name" class="text-muted-foreground text-xs">{{ pos.name }}</span>
            <span class="text-xs text-muted-foreground/60 uppercase">{{ pos.asset_type }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="font-mono">${{ pos.value.toLocaleString('es-AR', { minimumFractionDigits: 2 }) }}</span>
            <span v-if="pos.pnl_percent != null" class="font-mono text-xs" :class="pnlClass(pos.pnl_percent)">
              {{ pos.pnl_percent >= 0 ? '+' : '' }}{{ pos.pnl_percent.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="flex gap-4">
      <router-link to="/atlas/portfolio" class="text-xs text-primary hover:underline">Ver portfolio completo</router-link>
      <router-link to="/atlas/assets" class="text-xs text-primary hover:underline">Gestionar activos</router-link>
      <router-link to="/atlas/transactions" class="text-xs text-primary hover:underline">Transacciones</router-link>
    </div>
  </div>
</template>
