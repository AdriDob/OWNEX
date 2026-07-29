<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, getRevenueMetrics, getEVRankedTargets } from '@/lib/api'
import type { RevenueMetricsData, EVTarget } from '@/lib/api'
import {
  DollarSign, TrendingUp, BarChart3, Clock, CheckCircle2,
  XCircle, PieChart, Wallet, Target, RefreshCw,
  ArrowUpRight, ArrowDownRight, CircleDot, Zap, Activity,
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DataTable from '@/components/ui/DataTable.vue'

const loading = ref(true)
const error = ref<string | null>(null)
const data = ref<RevenueMetricsData | null>(null)
const activeTab = ref<'overview' | 'monthly' | 'programs' | 'vulns' | 'pipeline' | 'ev-targets'>('overview')
const evTargets = ref<EVTarget[]>([])
const evLoading = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const resp = await getRevenueMetrics()
    data.value = resp
  } catch (e: any) {
    error.value = e?.message || 'Failed to load revenue data'
  } finally {
    loading.value = false
  }
}

async function fetchEVTargets() {
  evLoading.value = true
  try {
    const resp = await getEVRankedTargets(50)
    evTargets.value = resp.ranked
  } catch (e: any) {
    console.error('Failed to load EV targets:', e)
  } finally {
    evLoading.value = false
  }
}

const platformColors: Record<string, string> = {
  hackerone: 'bg-green-500/20 text-green-400',
  bugcrowd: 'bg-blue-500/20 text-blue-400',
  immunefi: 'bg-purple-500/20 text-purple-400',
  intigriti: 'bg-orange-500/20 text-orange-400',
  synack: 'bg-cyan-500/20 text-cyan-400',
  yeswehack: 'bg-pink-500/20 text-pink-400',
  code4rena: 'bg-red-500/20 text-red-400',
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
  { key: 'action', label: '', width: '80px', align: 'center' as const },
]

function fmtCurrency(n: number | null | undefined): string {
  if (n == null) return '-'
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function pct(n: number | null | undefined): string {
  if (n == null) return '-'
  return (n * 100).toFixed(1) + '%'
}

function platformBadge(platform: string) {
  const cls = platformColors[platform] || 'bg-gray-500/20 text-gray-400'
  return `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}">${platform}</span>`
}

async function scanTarget(targetId: number) {
  try {
    await api.post<{ success: boolean }>(`/targets/${targetId}/scan`, { mode: 'quick' })
  } catch (e) {
    console.error('Scan failed:', e)
  }
}

function fmt(n: number | null | undefined): string {
  if (n == null) return '-'
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function days(n: number | null | undefined): string {
  if (n == null) return '-'
  return n.toFixed(1) + ' days'
}

const summaryCards = computed(() => {
  if (!data.value) return []
  const ps = data.value.payout_summary
  const fp = data.value.finding_pipeline
  return [
    { label: 'Total Payout', value: fmt(ps.total_payout), icon: DollarSign, color: 'text-green-400' },
    { label: 'Pending', value: fmt(ps.pending_total), icon: Clock, color: 'text-yellow-400' },
    { label: 'Avg Payout', value: fmt(ps.avg_payout), icon: BarChart3, color: 'text-blue-400' },
    { label: 'Acceptance Rate', value: pct(fp.submissions.acceptance_rate), icon: CheckCircle2, color: 'text-emerald-400' },
    { label: 'Total Submissions', value: String(fp.submissions.total), icon: Target, color: 'text-cyan-400' },
    { label: 'Confirmed Findings', value: String(fp.findings.confirmed), icon: CircleDot, color: 'text-violet-400' },
  ]
})

const maxMonthlyTotal = computed(() => {
  if (!data.value?.monthly_revenue?.length) return 1
  return Math.max(...data.value.monthly_revenue.map(m => m.total), 1)
})

const maxProgramTotal = computed(() => {
  if (!data.value?.roi_by_program?.length) return 1
  return Math.max(...data.value.roi_by_program.map(p => p.total_payout), 1)
})

const maxVulnTotal = computed(() => {
  if (!data.value?.roi_by_vuln_type?.length) return 1
  return Math.max(...data.value.roi_by_vuln_type.map(v => v.total_payout), 1)
})

onMounted(() => {
  fetchData()
  fetchEVTargets()
})
</script>

<template>
  <div class="space-y-6 p-6">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <DollarSign class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">REVENUE DASHBOARD</span>
          <span class="lamp" :class="data?.payout_summary?.total_payout ? 'lamp-green' : 'lamp-amber'" />
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Centro de Ingresos</h1>
        <p class="text-xs text-muted-foreground">Métricas de payout en tiempo real, análisis ROI, e inteligencia de pipeline</p>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <button @click="fetchData" class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent hover:bg-accent/80 text-sm transition-colors" :disabled="loading">
          <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': loading }" />
          Refresh
        </button>
      </div>
    </div>

    <!-- Loading / Error / Empty -->
    <LoadingState v-if="loading && !data" message="Loading revenue data..." />
    <ErrorState v-else-if="error" :message="error" @retry="fetchData" />
    <EmptyState v-else-if="!data" icon="DollarSign" title="No revenue data yet" description="Revenue metrics will appear here once you have payouts, submissions, and findings." />

    <template v-if="data">
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div v-for="card in summaryCards" :key="card.label" class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">{{ card.label.toUpperCase() }}</span>
            <component :is="card.icon" class="h-4 w-4" :class="card.color" />
          </div>
          <p class="font-mono text-xl font-bold" :class="card.color">{{ card.value }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 p-1 rounded-lg bg-accent/50 w-fit">
        <button v-for="tab in ([
          { key: 'overview', label: 'Overview', icon: DollarSign },
          { key: 'monthly', label: 'Monthly', icon: BarChart3 },
          { key: 'programs', label: 'By Program', icon: Target },
          { key: 'vulns', label: 'By Vuln Type', icon: PieChart },
          { key: 'pipeline', label: 'Pipeline', icon: TrendingUp },
          { key: 'ev-targets', label: 'Targets by EV', icon: Zap },
        ] as const)" :key="tab.key"
          @click="activeTab = tab.key"
          class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors"
          :class="activeTab === tab.key ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
        >
          <component :is="tab.icon" class="w-4 h-4" />
          {{ tab.label }}
        </button>
      </div>

      <!-- ── Overview Tab ── -->
      <div v-if="activeTab === 'overview'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Time Metrics -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Clock class="w-4 h-4" /> Time Metrics</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3">
              <div class="flex justify-between items-center py-2 border-b border-border/50">
                <span class="text-sm text-muted-foreground">Avg days to acceptance</span>
                <span class="text-sm font-semibold">{{ days(data.time_metrics.avg_days_to_acceptance) }}</span>
              </div>
              <div class="flex justify-between items-center py-2 border-b border-border/50">
                <span class="text-sm text-muted-foreground">Acceptance samples</span>
                <span class="text-sm font-semibold">{{ data.time_metrics.acceptance_samples }}</span>
              </div>
              <div class="flex justify-between items-center py-2 border-b border-border/50">
                <span class="text-sm text-muted-foreground">Avg days to payout</span>
                <span class="text-sm font-semibold">{{ days(data.time_metrics.avg_days_to_payout) }}</span>
              </div>
              <div class="flex justify-between items-center py-2">
                <span class="text-sm text-muted-foreground">Payout samples</span>
                <span class="text-sm font-semibold">{{ data.time_metrics.payout_samples }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Payout by Platform -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Wallet class="w-4 h-4" /> Payout by Platform</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3" v-if="Object.keys(data.payout_summary.by_platform).length">
              <div v-for="(amount, platform) in data.payout_summary.by_platform" :key="platform"
                class="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                <span v-html="platformBadge(platform)"></span>
                <span class="text-sm font-semibold">{{ fmt(amount) }}</span>
              </div>
            </div>
            <EmptyState v-else icon="Wallet" title="No payouts" description="" class="py-6" />
          </CardContent>
        </Card>

        <!-- Acceptance Rate -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><CheckCircle2 class="w-4 h-4" /> Acceptance Rate by Platform</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3" v-if="Object.keys(data.acceptance_rate).length">
              <div v-for="(rate, platform) in data.acceptance_rate" :key="platform"
                class="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                <div class="flex items-center gap-2">
                  <span v-html="platformBadge(platform)"></span>
                  <span class="text-xs text-muted-foreground">({{ rate.accepted }}/{{ rate.total }})</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="w-20 h-2 rounded-full bg-accent overflow-hidden">
                    <div class="h-full rounded-full transition-all" :class="rate.acceptance_rate >= 0.5 ? 'bg-green-500' : rate.acceptance_rate >= 0.3 ? 'bg-yellow-500' : 'bg-red-500'" :style="{ width: (rate.acceptance_rate * 100) + '%' }"></div>
                  </div>
                  <span class="text-sm font-semibold w-12 text-right">{{ pct(rate.acceptance_rate) }}</span>
                </div>
              </div>
            </div>
            <EmptyState v-else icon="CheckCircle2" title="No submissions yet" description="" class="py-6" />
          </CardContent>
        </Card>

        <!-- Payout by Currency -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><PieChart class="w-4 h-4" /> Payout by Currency</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3" v-if="Object.keys(data.payout_summary.by_currency).length">
              <div v-for="(amount, currency) in data.payout_summary.by_currency" :key="currency"
                class="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                <span class="text-sm font-medium">{{ currency }}</span>
                <span class="text-sm font-semibold">{{ fmt(amount) }}</span>
              </div>
            </div>
            <EmptyState v-else icon="PieChart" title="No currency data" description="" class="py-6" />
          </CardContent>
        </Card>
      </div>

      <!-- ── Monthly Tab ── -->
      <div v-if="activeTab === 'monthly'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><BarChart3 class="w-4 h-4" /> Monthly Revenue</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="data.monthly_revenue.length" class="space-y-1">
              <div v-for="month in data.monthly_revenue" :key="month.month"
                class="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
                <span class="text-sm font-medium w-16">{{ month.month }}</span>
                <div class="flex-1 h-5 rounded bg-accent overflow-hidden">
                  <div class="h-full rounded bg-gradient-to-r from-blue-500 to-blue-400 transition-all" :style="{ width: (month.total / maxMonthlyTotal * 100) + '%' }"></div>
                </div>
                <span class="text-sm font-semibold w-28 text-right">{{ fmt(month.total) }}</span>
                <span class="text-xs text-muted-foreground w-12 text-right">{{ month.count }}</span>
              </div>
            </div>
            <EmptyState v-else icon="BarChart3" title="No monthly data" description="Payouts with payment dates will populate this chart." class="py-8" />
          </CardContent>
        </Card>
      </div>

      <!-- ── By Program Tab ── -->
      <div v-if="activeTab === 'programs'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Target class="w-4 h-4" /> ROI by Program</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="data.roi_by_program.length" class="space-y-1">
              <div v-for="prog in data.roi_by_program" :key="prog.program"
                class="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate">{{ prog.program }}</p>
                  <div class="flex gap-1 mt-1">
                    <span v-for="p in prog.platforms" :key="p" v-html="platformBadge(p)"></span>
                  </div>
                </div>
                <div class="flex-1 h-5 rounded bg-accent overflow-hidden">
                  <div class="h-full rounded bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all" :style="{ width: (prog.total_payout / maxProgramTotal * 100) + '%' }"></div>
                </div>
                <div class="text-right w-28">
                  <p class="text-sm font-semibold">{{ fmt(prog.total_payout) }}</p>
                  <p class="text-xs text-muted-foreground">{{ prog.count }} payout{{ prog.count !== 1 ? 's' : '' }}</p>
                </div>
              </div>
            </div>
            <EmptyState v-else icon="Target" title="No program data" description="Payouts linked to programs will appear here." class="py-8" />
          </CardContent>
        </Card>
      </div>

      <!-- ── By Vuln Type Tab ── -->
      <div v-if="activeTab === 'vulns'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><PieChart class="w-4 h-4" /> ROI by Vulnerability Type</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="data.roi_by_vuln_type.length" class="space-y-1">
              <div v-for="vuln in data.roi_by_vuln_type" :key="vuln.vuln_type"
                class="flex items-center gap-4 py-3 border-b border-border/50 last:border-0">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium">{{ vuln.vuln_type }}</p>
                  <p class="text-xs text-muted-foreground">{{ vuln.total_programs }} program{{ vuln.total_programs !== 1 ? 's' : '' }}</p>
                </div>
                <div class="flex-1 h-5 rounded bg-accent overflow-hidden">
                  <div class="h-full rounded bg-gradient-to-r from-violet-500 to-violet-400 transition-all" :style="{ width: (vuln.total_payout / maxVulnTotal * 100) + '%' }"></div>
                </div>
                <div class="text-right w-28">
                  <p class="text-sm font-semibold">{{ fmt(vuln.total_payout) }}</p>
                  <p class="text-xs text-muted-foreground">{{ vuln.count }} payout{{ vuln.count !== 1 ? 's' : '' }}</p>
                </div>
                <div class="text-right w-24">
                  <p class="text-sm text-muted-foreground">{{ fmt(vuln.avg_payout) }}</p>
                  <p class="text-xs text-muted-foreground">avg</p>
                </div>
              </div>
            </div>
            <EmptyState v-else icon="PieChart" title="No vulnerability data" description="Findings linked to payouts will populate this view." class="py-8" />
          </CardContent>
        </Card>
      </div>

      <!-- ── EV Targets Tab ── -->
      <div v-if="activeTab === 'ev-targets'" class="space-y-6">
        <Card class="card-base">
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <Zap class="w-5 h-5 text-yellow-400" />
              Targets Ranked by Expected Value (USD/hour)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="evLoading" class="flex justify-center py-8">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
            <DataTable v-else-if="evTargets.length > 0"
              :columns="evColumns"
              :items="evTargets"
              :searchable="true"
              :pageSize="10"
            >
              <template #cell-target_name="{ value }">
                <span class="font-medium text-primary">{{ value }}</span>
              </template>
              <template #cell-priority_score="{ value }">
                <Badge :variant="value >= 100 ? 'success' : value >= 50 ? 'warning' : value >= 20 ? 'info' : 'outline'">
                  ${{ value.toFixed(2) }}/hr
                </Badge>
              </template>
              <template #cell-estimated_reward="{ value }">
                <span class="text-green-400 font-medium">${{ value.toLocaleString() }}</span>
              </template>
              <template #cell-acceptance_probability="{ value }">
                <span :class="value >= 0.7 ? 'text-green-400' : value >= 0.4 ? 'text-yellow-400' : 'text-red-400'">
                  {{ (value * 100).toFixed(0) }}%
                </span>
              </template>
              <template #cell-attack_plan="{ value }">
                <span class="text-xs text-muted-foreground" v-if="value">
                  {{ value.phases.join(' → ') }} ({{ value.estimated_hours }}h)
                </span>
                <span class="text-xs text-muted-foreground" v-else>—</span>
              </template>
            </DataTable>
            <EmptyState v-else icon="Zap" title="No targets ranked yet" description="Add targets and run the AI Bounty Auto-Hunter to populate EV rankings." class="py-8" />
          </CardContent>
        </Card>
      </div>

      <!-- ── Pipeline Tab ── -->
      <div v-if="activeTab === 'pipeline'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Findings Pipeline -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><CircleDot class="w-4 h-4" /> Findings Pipeline</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-blue-400">{{ data.finding_pipeline.findings.total }}</p>
                <p class="text-xs text-muted-foreground mt-1">Total Findings</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-green-400">{{ data.finding_pipeline.findings.confirmed }}</p>
                <p class="text-xs text-muted-foreground mt-1">Confirmed</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-red-400">{{ data.finding_pipeline.findings.rejected }}</p>
                <p class="text-xs text-muted-foreground mt-1">Rejected</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-yellow-400">{{ data.finding_pipeline.findings.open }}</p>
                <p class="text-xs text-muted-foreground mt-1">Open</p>
              </div>
            </div>
            <div class="flex items-center justify-between py-2 border-t border-border/50">
              <span class="text-sm text-muted-foreground">Confirmation rate</span>
              <span class="text-sm font-semibold">{{ pct(data.finding_pipeline.findings.confirmation_rate) }}</span>
            </div>
          </CardContent>
        </Card>

        <!-- Submissions Pipeline -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><TrendingUp class="w-4 h-4" /> Submissions Pipeline</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-cyan-400">{{ data.finding_pipeline.submissions.total }}</p>
                <p class="text-xs text-muted-foreground mt-1">Total Submissions</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-green-400">{{ data.finding_pipeline.submissions.accepted }}</p>
                <p class="text-xs text-muted-foreground mt-1">Accepted</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-red-400">{{ data.finding_pipeline.submissions.rejected }}</p>
                <p class="text-xs text-muted-foreground mt-1">Rejected</p>
              </div>
              <div class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-2xl font-bold text-yellow-400">{{ data.finding_pipeline.submissions.pending }}</p>
                <p class="text-xs text-muted-foreground mt-1">Pending</p>
              </div>
            </div>
            <div class="flex items-center justify-between py-2 border-t border-border/50">
              <span class="text-sm text-muted-foreground">Acceptance rate</span>
              <span class="text-sm font-semibold">{{ pct(data.finding_pipeline.submissions.acceptance_rate) }}</span>
            </div>
          </CardContent>
        </Card>

        <!-- Findings by Type -->
        <Card class="card-base lg:col-span-2">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><PieChart class="w-4 h-4" /> Findings by Vulnerability Type</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="data.findings_by_type.length" class="space-y-1">
              <div v-for="ft in data.findings_by_type" :key="ft.vuln_type"
                class="flex items-center gap-4 py-2 border-b border-border/50 last:border-0">
                <span class="text-sm font-medium w-32">{{ ft.vuln_type }}</span>
                <div class="flex gap-3 text-xs">
                  <span class="text-blue-400">{{ ft.total }} total</span>
                  <span class="text-green-400">{{ ft.confirmed }} confirmed</span>
                  <span class="text-red-400">{{ ft.rejected }} rejected</span>
                </div>
                <div class="flex-1 h-4 rounded bg-accent overflow-hidden flex">
                  <div v-if="ft.total > 0" class="h-full bg-green-500/60 transition-all" :style="{ width: (ft.confirmed / ft.total * 100) + '%' }"></div>
                  <div v-if="ft.total > 0" class="h-full bg-red-500/40 transition-all" :style="{ width: (ft.rejected / ft.total * 100) + '%' }"></div>
                </div>
                <span class="text-xs font-medium w-14 text-right">{{ pct(ft.confirmation_rate) }}</span>
              </div>
            </div>
            <EmptyState v-else icon="PieChart" title="No findings by type" description="" class="py-6" />
          </CardContent>
        </Card>
      </div>

      <!-- ── Targets by EV Tab ── -->
      <div v-if="activeTab === 'ev-targets'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Zap class="w-4 h-4" /> Targets Ranked by Expected Value (USD/hour)</div></CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              :columns="evColumns"
              :items="[]"
              :loading="evLoading"
              searchable
              :pageSize="10"
            >
              <template #cell-rank="{ value, item }">
                <span class="text-lg font-bold text-primary">{{ value }}</span>
              </template>
              <template #cell-ev="{ value, item }">
                <span class="text-sm font-semibold text-green-400">{{ fmtCurrency(item.ev) }}/h</span>
              </template>
              <template #cell-reward="{ value, item }">
                <span class="text-sm">{{ fmtCurrency(item.reward) }}</span>
              </template>
              <template #cell-prob="{ value, item }">
                <span :class="item.prob >= 0.5 ? 'text-green-400' : item.prob >= 0.3 ? 'text-yellow-400' : 'text-red-400'">
                  {{ pct(item.prob) }}
                </span>
              </template>
              <template #cell-effort="{ value, item }">
                <span class="text-sm">{{ item.effort }}h</span>
              </template>
              <template #cell-platform="{ value, item }">
                <span v-if="item.platform" v-html="platformBadge(item.platform)"></span>
                <span v-else class="text-muted-foreground">—</span>
              </template>
              <template #cell-action="{ item }">
                <button
                  @click="scanTarget(item.id)"
                  class="inline-flex items-center justify-center w-8 h-8 rounded bg-accent hover:bg-accent/80 text-sm transition-colors"
                  title="Scan this target"
                >
                  <Activity class="w-4 h-4" />
                </button>
              </template>
            </DataTable>
            <div v-if="!evLoading" class="text-center py-4 text-sm text-muted-foreground">
              No targets with EV ranking yet. Run recon to populate targets.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
    <!-- ═══ HOW-TO FOOTER ═══ -->
    <Card>
      <div class="p-4">
        <div class="flex items-center gap-2 mb-3">
          <DollarSign class="h-4 w-4 text-primary" />
          <h3 class="text-sm font-semibold">Cómo usar este dashboard</h3>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
              Monitoreá métricas
            </p>
            <p class="text-muted-foreground leading-relaxed">
              Las KPI cards muestran payout total, tasa de aceptación, y pipeline de submissions. Revisá las pestañas para desglose por programa, mes, y tipo de vulnerabilidad.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
              Identificá tendencias
            </p>
            <p class="text-muted-foreground leading-relaxed">
              Los charts mensuales y por programa muestran qué plataformas y tipos de vulnerabilidad generan más ROI. Priorizá esfuerzos donde el payout es más alto.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">3</span>
              Accioná targets
            </p>
            <p class="text-muted-foreground leading-relaxed">
              En la pestaña "Targets by EV" cada target tiene un botón de scan. Los targets con mayor Expected Value (EV) aparecen primero.
            </p>
          </div>
        </div>
      </div>
    </Card>
  </template>
