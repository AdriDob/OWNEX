<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { AlertTriangle, DollarSign, ListChecks, RefreshCw, Settings, TrendingUp, Wallet } from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

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
const loadingEligible = ref(true)
interface EligibleSource {
  source_id: string
  name: string
  overall_score: number
  payout_methods: string[]
  ar_compatible: boolean
}

const error = ref('')

// Inicialmente vacío - se poblará desde el API fetchSourceIntel
const eligibleSources = ref<EligibleSource[]>([])

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

async function fetchEligibleSources() {
  loadingEligible.value = true
  try {
    const res = await fetch('/source-intel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    if (res.ok) {
      const data = await res.json()
      // Transform the PlatformAnalysis cards into our EligibleSource format
      eligibleSources.value = (data.sources || []).filter((s: any) => s.argentina_compatibility === 'YES').map((s: any) => ({
        source_id: s.source_id || s.name?.toLowerCase().replace(/ /g, '-') || 'unknown',
        name: s.name,
        overall_score: s.trust_score || 94,
        payout_methods: typeof s.payment_method === 'string' ? [s.payment_method] : (s.payment_method || []),
        ar_compatible: s.argentina_compatibility === 'YES',
      }))
    }
  } catch (e) {
    console.error('Failed to fetch eligible sources:', e)
  } finally {
    loadingEligible.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchEligibleSources()
})

const hasData = () => (summary.value?.total_bets ?? 0) > 0
const profitClass = (v: number | undefined) => v != null ? (v >= 0 ? 'text-success' : 'text-destructive') : ''
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

    <!-- Fuentes elegibles AR -->
    <div v-if="!loading && !error && hasData() && !loadingEligible" class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-card/50 border border-border/20 rounded-lg p-4 mb-6">
      <h3 class="text-sm font-medium text-foreground mb-3">Fuentes Elegibles Argentina</h3>
      <div class="space-y-2 text-xs text-muted-foreground">
        <div v-for="source in eligibleSources" :key="source.source_id" class="flex items-center gap-2">
          <span class="w-6 h-6 rounded bg-primary/10 flex items-center justify-center">
            <svg class="h-3 w-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M12 6v6l4 2"/>
            </svg>
          </span>
          <span class="text-sm font-medium capitalize">{{ source.name }}</span>
          <span class="text-[10px] text-primary/60">{{ source.overall_score }}/100</span>
          <span class="text-[10px] text-success ml-2">✅ AR</span>
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
