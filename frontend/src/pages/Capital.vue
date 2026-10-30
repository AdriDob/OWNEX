<script setup lang="ts">
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleDot,
  Clock,
  Coins,
  Crown,
  DollarSign,
  ExternalLink,
  Filter,
  Flag,
  Gauge,
  Gem,
  Layers,
  Loader2,
  MoreHorizontal,
  PieChart,
  RefreshCw,
  RotateCcw,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Star,
  Target,
  TrendingDown,
  TrendingUp,
  TriangleAlert,
  Wallet,
  XCircle,
  Zap,
  Zap as Zap2,
  Zap as ZapIcon,
} from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import DataTable from '@/components/ui/DataTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Input from '@/components/ui/Input.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import Modal from '@/components/ui/Modal.vue'
import Select from '@/components/ui/Select.vue'
import { useToast } from '@/composables/useToast'
import type { EVTarget, PlatformStatus, RevenueMetricsData } from '@/lib/api'
import { api, getEVRankedTargets, getPlatformsStatus, getRevenueMetrics } from '@/lib/api'

const { toast } = useToast()

// ── Tabs ──
type Tab = 'overview' | 'progressive-scaling' | 'targets' | 'programs' | 'pipeline' | 'platforms' | 'settings'
const activeTab = ref<Tab>('overview')

// ── State ──
const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)

const capitalData = ref<any>(null)
const revenueData = ref<RevenueMetricsData | null>(null)
const evTargets = ref<EVTarget[]>([])
const evLoading = ref(false)
const platforms = ref<PlatformStatus[]>([])
const platformsLoading = ref(false)

// Filters
const searchQuery = ref('')
const platformFilter = ref('')
const minEV = ref(0)
const sortField = ref<'rank' | 'ev' | 'reward' | 'prob' | 'effort'>('ev')
const sortAsc = ref(false)

// ── Fetch ──
async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    const [capital, revenue, ev, plats] = await Promise.allSettled([
      api.get('/api/revenue/capital-dashboard'),
      getRevenueMetrics(),
      getEVRankedTargets(100),
      getPlatformsStatus(),
    ])
    capitalData.value = capital.status === 'fulfilled' ? capital.value : null
    revenueData.value = revenue.status === 'fulfilled' ? revenue.value : null
    evTargets.value = ev.status === 'fulfilled' ? ev.value.ranked : []
    platforms.value = plats.status === 'fulfilled' ? plats.value.platforms : []
  } catch (e: any) {
    error.value = e?.message || 'Failed to load capital data'
    toast.error('Error', error.value)
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    await fetchAll()
    toast.success('Actualizado', 'Datos de capital refrescados')
  } catch (e: any) {
    toast.error('Error', e?.message || 'No se pudo refrescar')
  } finally {
    refreshing.value = false
  }
}

async function refreshEVTargets() {
  evLoading.value = true
  try {
    const res = await getEVRankedTargets(100)
    evTargets.value = res.ranked
  } catch (e: any) {
    toast.error('Error', e?.message || 'No se pudo refrescar targets')
  } finally {
    evLoading.value = false
  }
}

function toggleSort(field: typeof sortField.value) {
  if (sortField.value === field) sortAsc.value = !sortAsc.value
  else {
    sortField.value = field
    sortAsc.value = false
  }
}

// ── Computed ──
const platformColors: Record<string, string> = {
  hackerone: 'bg-success/20 text-success border-success/30',
  bugcrowd: 'bg-primary/20 text-primary border-primary/30',
  intigriti: 'bg-intigriti/20 text-intigriti border-purple-500/30',
  synack: 'bg-muted/20 text-muted-foreground border-border-light',
  yeswehack: 'bg-destructive/20 text-destructive border-pink-500/30',
  immunefi: 'bg-warning/20 text-warning border-warning/30',
  code4rena: 'bg-destructive/20 text-destructive border-destructive/30',
}

const filteredTargets = computed(() => {
  let list = [...evTargets.value]
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(
      (t) =>
        t.name.toLowerCase().includes(q) || t.domain.toLowerCase().includes(q) || t.platform.toLowerCase().includes(q),
    )
  }
  if (platformFilter.value) {
    list = list.filter((t) => t.platform === platformFilter.value)
  }
  if (minEV.value > 0) {
    list = list.filter((t) => t.ev >= minEV.value)
  }
  const dir = sortAsc.value ? 1 : -1
  return list.sort((a, b) => {
    const va = a[sortField.value] ?? 0
    const vb = b[sortField.value] ?? 0
    return (va < vb ? -1 : va > vb ? 1 : 0) * dir
  })
})

const platformsList = computed(() => [...new Set(evTargets.value.map((t) => t.platform))].sort())

const kpiCards = computed(() => {
  if (!capitalData.value) return []
  const cap = capitalData.value.capital || {}
  const targets = capitalData.value.targets || {}
  const econ = capitalData.value.economic_memory || {}
  const payout = revenueData.value?.payout_summary || {}
  const pipeline = revenueData.value?.finding_pipeline || {}
  const usdPerHour = capitalData.value.usd_per_hour || 0
  const platformSpeed = capitalData.value.platform_speed_days || {}

  return [
    {
      label: 'Capital Total',
      value: `$${(payout.total_payout || 0).toLocaleString()}`,
      sub: `Pendiente: $${(payout.pending_total || 0).toLocaleString()}`,
      icon: DollarSign,
      color: 'text-success',
      bg: 'bg-success/10',
      trend: '+12%',
      trendIcon: ArrowUpRight,
    },
    {
      label: 'USD / Hora',
      value: `$${usdPerHour.toFixed(2)}`,
      sub: 'Basado en payouts históricos',
      icon: ZapIcon,
      color: 'text-warning',
      bg: 'bg-warning/10',
      trend: '+8%',
      trendIcon: ArrowUpRight,
    },
    {
      label: 'Findings Totales',
      value: String(cap.total_findings || 0),
      sub: `Críticos: ${cap.critical_count || 0} · High: ${cap.high_count || 0}`,
      icon: Target,
      color: 'text-destructive',
      bg: 'bg-destructive/10',
      trend: `${cap.recent_30d_findings || 0} (30d)`,
      trendIcon: Activity,
    },
    {
      label: 'Targets Activos',
      value: String(targets.total || 0),
      sub: `${targets.scanned_last_7d || 0} escaneados (7d)`,
      icon: Zap2,
      color: 'text-muted-foreground',
      bg: 'bg-muted/10',
      trend: `${Math.round(((targets.scanned_last_7d || 0) / Math.max(targets.total || 1, 1)) * 100)}% cobertura`,
      trendIcon: ArrowUpRight,
    },
    {
      label: 'Tasa Aceptación',
      value: `${((pipeline.submissions?.acceptance_rate || 0) * 100).toFixed(1)}%`,
      sub: `${pipeline.submissions?.accepted || 0}/${pipeline.submissions?.total || 0} aceptados`,
      icon: CheckCircle2,
      color: 'text-success',
      bg: 'bg-success/10',
      trend: 'vs mes anterior',
      trendIcon: ArrowUpRight,
    },
    {
      label: 'Programas Rastreados',
      value: String(econ.total_programs || 0),
      sub: `USD/h global: $${(econ.overall_usd_per_hour || 0).toFixed(2)}`,
      icon: Crown,
      color: 'text-intigriti',
      bg: 'bg-intigriti/10',
      trend: `${econ.overall_accepted_rate ? (econ.overall_accepted_rate * 100).toFixed(1) + '% accept' : ''}`,
      trendIcon: Gem,
    },
  ]
})

const hotTargets = computed(() => capitalData.value?.hot_targets || [])
const programRanking = computed(() => capitalData.value?.program_ranking || [])

const monthlyRevenue = computed(() => revenueData.value?.monthly_revenue || [])
const roiByProgram = computed(() => revenueData.value?.roi_by_program || [])
const findingsByType = computed(() => revenueData.value?.findings_by_type || [])

function fmtCurrency(n: number | null | undefined): string {
  if (n == null) return '—'
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function fmtCurrency2(n: number | null | undefined): string {
  if (n == null) return '—'
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function pct(n: number | null | undefined): string {
  if (n == null) return '—'
  return (n * 100).toFixed(1) + '%'
}

function platformBadge(platform: string) {
  const cls = platformColors[platform] || 'bg-muted/20 text-muted-foreground border-border-light/30'
  return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}">${platform}</span>`
}

function scanButtonHtml(id: string) {
  return `<button class="text-primary hover:underline text-sm" data-scan="${id}">Scan</button>`
}

const evColumns = [
  { key: 'rank', label: '#', width: '50px', align: 'center' as const },
  { key: 'name', label: 'Target', sortable: true },
  { key: 'domain', label: 'Domain', sortable: true },
  { key: 'ev', label: 'EV (USD/h)', sortable: true, align: 'right' as const },
  { key: 'reward', label: 'Est. Reward', sortable: true, align: 'right' as const },
  { key: 'prob', label: 'Accept %', sortable: true, align: 'right' as const },
  { key: 'effort', label: 'Effort (h)', sortable: true, align: 'right' as const },
  { key: 'platform', label: 'Platform' },
  { key: 'action', label: '', width: '90px', align: 'center' as const },
]

const programColumns = [
  { key: 'rank', label: '#', width: '50px', align: 'center' as const },
  { key: 'name', label: 'Program', sortable: true },
  { key: 'platform', label: 'Platform' },
  { key: 'orion_score', label: 'Orion Score', sortable: true, align: 'right' as const },
  { key: 'accepted_rate', label: 'Accept %', sortable: true, align: 'right' as const },
  { key: 'avg_payout', label: 'Avg Payout', sortable: true, align: 'right' as const },
  { key: 'usd_per_hour', label: 'USD/h', sortable: true, align: 'right' as const },
  { key: 'total_payout', label: 'Total', sortable: true, align: 'right' as const },
]

const pipelineColumns = [
  { key: 'stage', label: 'Etapa' },
  { key: 'total', label: 'Total', align: 'right' as const },
  { key: 'confirmed', label: 'Confirmados', align: 'right' as const },
  { key: 'rejected', label: 'Rechazados', align: 'right' as const },
  { key: 'pending', label: 'Pendientes', align: 'right' as const },
  { key: 'rate', label: 'Tasa', align: 'right' as const },
]

const platformSpeedColumns = [
  { key: 'platform', label: 'Plataforma' },
  { key: 'status', label: 'Estado' },
  { key: 'avg_days', label: 'Días Prom. Payout', align: 'right' as const },
  { key: 'last_sync', label: 'Último Sync' },
  { key: 'earnings', label: 'Earnings', align: 'right' as const },
]

const platformSpeedData = computed(() => {
  const speed = capitalData.value?.platform_speed_days || {}
  return platforms.value.map((p) => ({
    platform: p.name,
    status: p.connected ? '🟢 Conectado' : '🔴 Desconectado',
    avg_days: speed[p.name] ? speed[p.name].toFixed(1) : '—',
    last_sync: p.last_sync ? new Date(p.last_sync).toLocaleDateString() : 'Nunca',
    earnings: p.earnings ? fmtCurrency(p.earnings) : '—',
  }))
})

onMounted(fetchAll)

// ── Actions ──
async function scanTarget(targetId: number) {
  try {
    await api.post<{ success: boolean }>(`/targets/${targetId}/scan`, { mode: 'quick' })
    toast.success('Scan iniciado', `Target ${targetId} en cola`)
  } catch (e: any) {
    toast.error('Error', e?.message || 'No se pudo iniciar scan')
  }
}

async function openProgram(programId: number) {
  // Navigate to program detail
  window.location.href = `/programs/${programId}`
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  toast.success('Copiado', 'Enlace copiado al portapapeles')
}
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-2">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-foreground">Capital Dashboard</h1>
        <p class="text-muted-foreground text-sm">
          Unified view: Payouts · EV Targets · Programs · Pipeline · Platform Speed · Economic Memory
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" @click="refreshAll" :disabled="refreshing" class="gap-1">
          <RotateCcw :class="refreshing ? 'animate-spin' : ''" class="h-4 w-4" />
          Refrescar Todo
        </Button>
        <Button variant="outline" size="sm" @click="refreshEVTargets" :disabled="evLoading" class="gap-1">
          <Loader2 :class="evLoading ? 'animate-spin' : ''" class="h-4 w-4" />
          Targets EV
        </Button>
      </div>
    </div>

    <!-- ═══ TABS ═══ -->
    <div class="flex flex-wrap gap-1 border-b border-border/40 pb-1">
      <button
        v-for="tab in ['overview', 'runway', 'risk', 'allocation', 'forecasting', 'diversification', 'progressive-scaling', 'targets', 'programs', 'pipeline', 'platforms', 'settings']"
        :key="tab"
        aria-label="Activetab = Tab As Tab" @click="activeTab = tab as Tab"
        class="px-3 py-1.5 text-sm font-medium rounded-t-md transition-colors border-b-2 border-transparent
          hover:text-foreground/80 focus:outline-none focus:ring-2 focus:ring-ring"
        :class="activeTab === tab
          ? 'text-primary border-primary bg-primary/5'
          : 'text-muted-foreground hover:bg-accent/30'"
      >
        {{ tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' ') }}
      </button>
    </div>

    <!-- ═══ ERROR STATE ═══ -->
    <ErrorState v-if="error && !capitalData.value" :message="error" @retry="fetchAll" />

    <!-- ═══ LOADING STATE ═══ -->
    <div v-if="loading" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <Skeleton v-for="i in 6" :key="i" class="h-24" />
      </div>
      <Skeleton class="h-64" />
    </div>

    <!-- ═══ CONTENT ═══ -->
    <div v-else class="space-y-6">

      <!-- ═══ OVERVIEW TAB ═══ -->
      <div v-if="activeTab === 'overview'" class="space-y-6 animate-fade-in">
        <!-- KPI Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <KPIBlock
            v-for="kpi in kpiCards"
            :key="kpi.label"
            :label="kpi.label"
            :value="kpi.value"
            :sub="kpi.sub"
            :icon="kpi.icon"
            :color="kpi.color"
            :bg="kpi.bg"
            :trend="kpi.trend"
            :trend-icon="kpi.trendIcon"
          />
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Monthly Revenue -->
          <Card>
            <CardHeader class="flex flex-row items-center justify-between">
              <CardTitle class="flex items-center gap-2">
                <BarChart3 class="h-4 w-4" /> Ingresos Mensuales
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="h-64" v-if="monthlyRevenue.length > 0">
                <canvas ref="monthlyChart"></canvas>
              </div>
              <EmptyState v-else icon="BarChart3" title="Sin datos mensuales" description="Ejecuta hunts para generar historial" />
            </CardContent>
          </Card>

          <!-- Findings by Type -->
          <Card>
            <CardHeader class="flex flex-row items-center justify-between">
              <CardTitle class="flex items-center gap-2">
                <TriangleAlert class="h-4 w-4" /> Findings por Tipo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="h-64" v-if="findingsByType.length > 0">
                <canvas ref="findingsChart"></canvas>
              </div>
              <EmptyState v-else icon="TriangleAlert" title="Sin findings" description="No hay findings registrados aún" />
            </CardContent>
          </Card>
        </div>

        <!-- Hot Targets + Program Ranking -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Hot Targets -->
          <Card>
            <CardHeader class="flex flex-row items-center justify-between">
              <CardTitle class="flex items-center gap-2">
                <Zap class="h-4 w-4 text-warning" /> Targets Calientes (Top EV)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                v-if="hotTargets.length > 0"
                :columns="[
                  { key: 'rank', label: '#', width: '40px', align: 'center' },
                  { key: 'name', label: 'Target' },
                  { key: 'ev', label: 'EV (USD/h)', align: 'right' },
                  { key: 'expected_value', label: 'Expected $', align: 'right' },
                  { key: 'probability', label: 'Prob %', align: 'right' },
                  { key: 'effort_hours', label: 'Esfuerzo (h)', align: 'right' },
                ]"
                :rows="hotTargets.map((t, i) => ({ ...t, rank: i + 1 }))"
                :empty-message="''"
              />
              <EmptyState v-else icon="Zap" title="Sin targets calientes" description="Añade targets y ejecuta --hunt" />
            </CardContent>
          </Card>

          <!-- Top Programs -->
          <Card>
            <CardHeader class="flex flex-row items-center justify-between">
              <CardTitle class="flex items-center gap-2">
                <Crown class="h-4 w-4 text-warning" /> Top Programas por ROI
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                v-if="programRanking.length > 0"
                :columns="programColumns"
                :rows="programRanking.map((p, i) => ({ ...p, rank: i + 1 }))"
                :empty-message="''"
                :max-rows="10"
              />
              <EmptyState v-else icon="Crown" title="Sin programas" description="Añade programas en Inteligencia Económica" />
            </CardContent>
          </Card>
        </div>

        <!-- Platform Speed -->
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2">
              <Clock class="h-4 w-4" /> Velocidad de Payout por Plataforma
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              v-if="platformSpeedData.length > 0"
              :columns="platformSpeedColumns"
              :rows="platformSpeedData"
              :empty-message="''"
            />
            <EmptyState v-else icon="Clock" title="Sin datos de velocidad" description="Conecta plataformas y registra payouts" />
            </CardContent>
          </Card>
      </div>

      <!-- ═══ RUNWAY TAB ═══ -->
      <div v-else-if="activeTab === 'runway'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2"><Gauge class="h-4 w-4 text-warning" /> Runway Engine</CardTitle>
            <Badge variant="outline">P10 / P50 / P90</Badge>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">Cargando datos de runway desde /api/capital/runway...</p>
          </CardContent>
        </Card>
      </div>

      <!-- ═══ RISK TAB ═══ -->
      <div v-else-if="activeTab === 'risk'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2"><ShieldCheck class="h-4 w-4 text-destructive" /> Risk Engine</CardTitle>
            <Badge variant="outline">Score 0-100</Badge>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">Cargando datos de riesgo desde /api/capital/risk...</p>
          </CardContent>
        </Card>
      </div>

      <!-- ═══ ALLOCATION TAB ═══ -->
      <div v-else-if="activeTab === 'allocation'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2"><PieChart class="h-4 w-4 text-primary" /> Capital Allocation</CardTitle>
            <Badge variant="outline">Recommendations</Badge>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">Cargando recomendaciones desde /api/capital/allocation...</p>
          </CardContent>
        </Card>
      </div>

      <!-- ═══ FORECASTING TAB ═══ -->
      <div v-else-if="activeTab === 'forecasting'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2"><BarChart3 class="h-4 w-4 text-primary" /> Capital Forecasting</CardTitle>
            <Badge variant="outline">Monte Carlo P10/P50/P90</Badge>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">Cargando proyecciones desde /api/capital/forecasting...</p>
          </CardContent>
        </Card>
      </div>

      <!-- ═══ DIVERSIFICATION TAB ═══ -->
      <div v-else-if="activeTab === 'diversification'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2"><Layers class="h-4 w-4 text-success" /> Income Diversification</CardTitle>
            <Badge variant="outline">HHI + Top Source %</Badge>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">Cargando análisis de diversificación desde /api/capital/diversification...</p>
          </CardContent>
        </Card>
      </div>

      <!-- ═══ TARGETS TAB (EV Ranked) ═══ -->
      <div v-else-if="activeTab === 'targets'" class="space-y-4 animate-fade-in">
        <div class="flex flex-wrap gap-3 items-center">
          <div class="relative flex-1 min-w-[200px]">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              placeholder="Buscar target, dominio, plataforma..."
              class="pl-10"
            />
          </div>
          <Select v-model="platformFilter" :options="[{ value: '', label: 'Todas' }, ...platformsList.map(p => ({ value: p, label: p }))]" placeholder="Plataforma" class="w-40" />
          <Input v-model.number="minEV" type="number" placeholder="Min EV" class="w-28" step="1" min="0" />
          <Button variant="outline" size="sm" @click="refreshEVTargets" :disabled="evLoading" class="gap-1">
            <Loader2 :class="evLoading ? 'animate-spin' : ''" class="h-4 w-4" />
            Refrescar
          </Button>
        </div>

        <Card>
          <CardContent class="p-0">
            <DataTable
              v-if="filteredTargets.length > 0"
              :columns="evColumns"
              :rows="filteredTargets.map((t, i) => ({
                ...t,
                rank: i + 1,
                reward: fmtCurrency(t.reward),
                ev: fmtCurrency(t.ev),
                prob: pct(t.prob),
                platform: platformBadge(t.platform),
                action: scanButtonHtml(t.id)
              }))"
              :empty-message="''"
              :sortable="true"
              :sort-field="sortField"
              :sort-asc="sortAsc"
              @sort="toggleSort"
            />
            <EmptyState v-else icon="Target" title="Sin targets" description="Ajusta filtros o añade targets" />
          </CardContent>
        </Card>

        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>{{ filteredTargets.length }} de {{ evTargets.length }} targets</span>
        </div>
      </div>

      <!-- ═══ PROGRAMS TAB ═══ -->
      <div v-else-if="activeTab === 'programs'" class="space-y-4 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle>Programas Rastreados (Economic Memory)</CardTitle>
          </CardHeader>
          <CardContent class="p-0">
            <DataTable
              v-if="programRanking.length > 0"
              :columns="programColumns"
              :rows="programRanking.map((p, i) => ({
                ...p,
                rank: i + 1,
                orion_score: (p.orion_score * 100).toFixed(1) + '%',
                accepted_rate: pct(p.accepted_rate),
                avg_payout: fmtCurrency(p.avg_payout),
                usd_per_hour: fmtCurrency(p.usd_per_hour),
                total_payout: fmtCurrency(p.total_payout),
              }))"
              :empty-message="''"
              :max-rows="20"
            />
            <EmptyState v-else icon="Crown" title="Sin programas" description="Añade programas en /program-catalog" />
          </CardContent>
        </Card>
      </div>

      <!-- ═══ PIPELINE TAB ═══ -->
      <div v-else-if="activeTab === 'pipeline'" class="space-y-4 animate-fade-in">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Finding Pipeline -->
          <Card>
            <CardHeader>
              <CardTitle class="flex items-center gap-2">
                <Target class="h-4 w-4" /> Pipeline de Findings
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                v-if="revenueData.value?.finding_pipeline"
                :columns="pipelineColumns"
                :rows="[
                  { stage: 'Findings', ...revenueData.value.finding_pipeline.findings, rate: pct(revenueData.value.finding_pipeline.findings.confirmation_rate) },
                  { stage: 'Submissions', ...revenueData.value.finding_pipeline.submissions, rate: pct(revenueData.value.finding_pipeline.submissions.acceptance_rate) },
                ]"
                :empty-message="''"
              />
            </CardContent>
          </Card>

          <!-- ROI by Program -->
          <Card>
            <CardHeader>
              <CardTitle class="flex items-center gap-2">
                <PieChart class="h-4 w-4" /> ROI por Programa
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DataTable
                v-if="roiByProgram.length > 0"
                :columns="[
                  { key: 'program', label: 'Programa' },
                  { key: 'platforms', label: 'Plataformas' },
                  { key: 'total_payout', label: 'Total Payout', align: 'right' },
                  { key: 'count', label: 'Reportes', align: 'right' },
                ]"
                :rows="roiByProgram.map(r => ({
                  ...r,
                  platforms: r.platforms.join(', '),
                  total_payout: fmtCurrency(r.total_payout),
                }))"
                :empty-message="''"
              />
              <EmptyState v-else icon="PieChart" title="Sin ROI" description="Registra payouts para ver ROI" />
            </CardContent>
          </Card>
        </div>

        <!-- Findings by Vuln Type -->
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <TriangleAlert class="h-4 w-4" /> Findings por Tipo de Vulnerabilidad
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              v-if="findingsByType.length > 0"
              :columns="[
                { key: 'vuln_type', label: 'Tipo' },
                { key: 'total', label: 'Total', align: 'right' },
                { key: 'confirmed', label: 'Confirmados', align: 'right' },
                { key: 'rejected', label: 'Rechazados', align: 'right' },
                { key: 'confirmation_rate', label: 'Tasa Confirmación', align: 'right' },
              ]"
              :rows="findingsByType.map(f => ({
                ...f,
                confirmation_rate: pct(f.confirmation_rate),
              }))"
              :empty-message="''"
            />
            <EmptyState v-else icon="TriangleAlert" title="Sin findings" description="Ejecuta validaciones para poblar" />
          </CardContent>
        </Card>
      </div>

      <!-- ═══ PLATFORMS TAB ═══ -->
      <div v-else-if="activeTab === 'platforms'" class="space-y-4 animate-fade-in">
        <Card>
          <CardHeader class="flex flex-row items-center justify-between">
            <CardTitle class="flex items-center gap-2">
              <Link2 class="h-4 w-4" /> Plataformas de Bug Bounty
            </CardTitle>
            <Button variant="outline" size="sm" @click="fetchAll" :disabled="platformsLoading">
              <RotateCcw :class="platformsLoading ? 'animate-spin' : ''" class="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent class="p-0">
            <DataTable
              v-if="platforms.length > 0"
              :columns="[
                { key: 'name', label: 'Plataforma' },
                { key: 'connected', label: 'Estado' },
                { key: 'username', label: 'Usuario' },
                { key: 'earnings', label: 'Earnings', align: 'right' },
                { key: 'pending', label: 'Pendiente', align: 'right' },
                { key: 'last_sync', label: 'Último Sync' },
              ]"
              :rows="platforms.map(p => ({
                ...p,
                connected: p.connected ? '🟢 Conectado' : '🔴 Desconectado',
                earnings: fmtCurrency(p.earnings),
                pending: fmtCurrency(p.pending),
                last_sync: p.last_sync ? new Date(p.last_sync).toLocaleString() : 'Nunca',
              }))"
              :empty-message="''"
            />
            <EmptyState v-else icon="Link2" title="Sin plataformas" description="Conecta HackerOne, Bugcrowd, Intigriti en Settings" />
          </CardContent>
        </Card>

        <!-- Platform Speed Detail -->
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <Clock class="h-4 w-4" /> Velocidad de Payout (días promedio)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              v-if="platformSpeedData.length > 0"
              :columns="platformSpeedColumns"
              :rows="platformSpeedData"
              :empty-message="''"
            />
            <EmptyState v-else icon="Clock" title="Sin datos de velocidad" description="Registra payouts confirmados con fechas" />
          </CardContent>
        </Card>
      </div>

      <!-- ═══ PROGRESSIVE SCALING TAB ═══ -->
      <div v-else-if="activeTab === 'progressive-scaling'" class="space-y-6 animate-fade-in">
        <router-view />
      </div>

      <!-- ═══ SETTINGS TAB ═══ -->
      <div v-else-if="activeTab === 'settings'" class="space-y-6 animate-fade-in">
        <Card>
          <CardHeader>
            <CardTitle>Configuración de Capital Dashboard</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="space-y-2">
                <label class="text-sm font-medium">Umbral EV Mínimo (USD/h)</label>
                <Input v-model.number="minEV" type="number" step="1" min="0" placeholder="0" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium">Targets por página</label>
                <Select v-model="evTargets.length" :options="[25, 50, 100, 200].map(n => ({ value: n, label: String(n) }))" />
              </div>
            </div>
            <div class="flex items-center gap-4">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" class="rounded border-border" />
                <span class="text-sm">Auto-refresh cada 5 min</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" class="rounded border-border" />
                <span class="text-sm">Notificaciones de payouts nuevos</span>
              </label>
            </div>
          </CardContent>
        </Card>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* Chart containers */
canvas {
  max-height: 300px;
}

/* Fade in animation */
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* DataTable overrides */
:deep(.datatable-cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}
:deep(.datatable-cell.platform) {
  max-width: 120px;
}
</style>