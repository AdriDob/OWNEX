<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import type { ReportItem } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { DoughnutChart, BarChart } from '@/components/charts'
import { Search, AlertTriangle, RefreshCw, FileText, DollarSign, ChevronLeft, ChevronRight, ArrowUpDown, CalendarDays, Filter } from '@lucide/vue'

interface ReportStats {
  total: number
  status_counts: Record<string, number>
  paid_count: number
  total_rewards: number
  estimated_rewards: number
}

const reports = ref<ReportItem[]>([])
const stats = ref<ReportStats | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const statusFilter = ref<string | null>(null)
const page = ref(1)
const total = ref(0)
const limit = 20
const sortField = ref<string>('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

const statusTabs = [
  { key: null, label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'ready', label: 'Ready' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'triaged', label: 'Triaged' },
  { key: 'paid', label: 'Paid' },
]

async function fetchReports() {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, any> = {
      limit,
      offset: (page.value - 1) * limit,
      sort_by: sortField.value,
      sort_order: sortOrder.value,
    }
    if (statusFilter.value) params.status = statusFilter.value
    if (search.value.trim()) params.search = search.value.trim()

    const [r, s] = await Promise.all([
      api.get<{ items: ReportItem[]; total: number }>('/reports', params),
      api.get<ReportStats>('/reports/stats').catch(() => null),
    ])
    reports.value = r.items || []
    total.value = r.total || 0
    if (s) stats.value = s
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar reportes'
  } finally {
    loading.value = false
  }
}

onMounted(fetchReports)

function setStatus(status: string | null) {
  statusFilter.value = status
  page.value = 1
  fetchReports()
}

function toggleSort(field: string) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'desc'
  }
  fetchReports()
}

function prevPage() { if (page.value > 1) { page.value--; fetchReports() } }
function nextPage() { if (page.value * limit < total.value) { page.value++; fetchReports() } }

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

function statusVariant(status: string) {
  const map: Record<string, 'success' | 'info' | 'warning' | 'destructive' | 'default'> = {
    paid: 'success', submitted: 'info', triaged: 'info', ready: 'info',
    draft: 'default', rejected: 'destructive',
  }
  return map[status.toLowerCase()] || 'default'
}

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success',
  }
  return map[sev?.toLowerCase()] || 'default'
}

function elapsedDays(date: string | null): string {
  if (!date) return '—'
  const days = Math.floor((Date.now() - new Date(date).getTime()) / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return '1 day'
  return `${days} days`
}

const statusChartData = computed(() => {
  if (!stats.value?.status_counts) return { labels: [], data: [] }
  const entries = Object.entries(stats.value.status_counts)
    .sort((a, b) => b[1] - a[1])
  return {
    labels: entries.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1)),
    data: entries.map(([, v]) => v),
  }
})

const monthlyChartData = computed(() => {
  if (!reports.value.length) return { labels: [], datasets: [] }
  const byMonth: Record<string, number> = {}
  for (const r of reports.value) {
    if (!r.created_at) continue
    const month = new Date(r.created_at).toLocaleString('default', { month: 'short', year: '2-digit' })
    byMonth[month] = (byMonth[month] || 0) + 1
  }
  const sorted = Object.entries(byMonth).sort((a, b) => {
    const [ma, ya] = a[0].split(' ')
    const [mb, yb] = b[0].split(' ')
    const months = 'JanFebMarAprMayJunJulAugSepOctNovDec'
    return (months.indexOf(mb) + parseInt(yb) * 12) - (months.indexOf(ma) + parseInt(ya) * 12)
  })
  return {
    labels: sorted.map(([m]) => m),
    datasets: [{
      label: 'Reports',
      data: sorted.map(([, c]) => c),
      backgroundColor: '#ffffff',
    }],
  }
})

const filteredReports = computed(() => reports.value)
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">History</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Report History</h1>
      <p class="text-sm text-muted-foreground">Comprehensive report tracking with filtering and analytics</p>
    </div>

    <template v-if="loading && reports.length === 0">
      <div class="flex gap-2"><Skeleton v-for="i in 5" :key="i" class="h-9 w-20 rounded-lg" /></div>
      <Skeleton class="h-10 w-64 rounded-lg" />
      <div class="space-y-2"><Skeleton v-for="i in 5" :key="i" class="h-16 rounded-xl" /></div>
    </template>

    <template v-else-if="error && reports.length === 0">
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">No se pudieron cargar los reportes</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" size="sm" @click="fetchReports">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </Card>
    </template>

    <template v-else>
      <div v-if="stats" class="grid grid-cols-2 gap-3 sm:grid-cols-4 animate-in">
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Total Reports</p>
          <p class="text-2xl font-bold text-foreground mt-1">{{ stats.total }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Paid</p>
          <p class="text-2xl font-bold text-success mt-1">{{ stats.paid_count }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Total Rewards</p>
          <p class="text-2xl font-bold text-gold mt-1">${{ (stats.total_rewards || 0).toLocaleString() }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Est. Rewards</p>
          <p class="text-2xl font-bold text-accent mt-1">${{ (stats.estimated_rewards || 0).toLocaleString() }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Filter class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Status Distribution</p>
          </div>
          <DoughnutChart
            v-if="statusChartData.labels.length"
            :labels="statusChartData.labels"
            :data="statusChartData.data"
            :height="200"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">No data</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <CalendarDays class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Monthly Reports</p>
          </div>
          <BarChart
            v-if="monthlyChartData.labels.length"
            :labels="monthlyChartData.labels"
            :datasets="monthlyChartData.datasets"
            :height="200"
            :showLegend="false"
            yLabel="Count"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">No monthly data</div>
        </Card>
      </div>

      <div class="flex flex-wrap items-center gap-2 animate-in">
        <button v-for="tab in statusTabs" :key="tab.key || 'all'"
          @click="setStatus(tab.key)"
          class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-all"
          :class="statusFilter === tab.key ? 'bg-primary/15 text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-surface/50'"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="relative animate-in">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input v-model="search" placeholder="Buscar por título, vulnerabilidad, target..."
          class="w-full max-w-md rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
          @input="page = 1; fetchReports()"
        />
      </div>

      <Card v-if="filteredReports.length === 0" class="p-6 text-center">
        <FileText class="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
        <p class="text-sm text-muted-foreground">No se encontraron reportes</p>
      </Card>

      <div v-else class="overflow-x-auto animate-in">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-border/40 text-xs text-muted-foreground uppercase tracking-wider">
              <th class="text-left py-3 px-3 font-semibold cursor-pointer hover:text-foreground" @click="toggleSort('title')">
                <span class="flex items-center gap-1">Title <ArrowUpDown class="h-3 w-3" /></span>
              </th>
              <th class="text-left py-3 px-3 font-semibold cursor-pointer hover:text-foreground" @click="toggleSort('status')">
                <span class="flex items-center gap-1">Status <ArrowUpDown class="h-3 w-3" /></span>
              </th>
              <th class="text-left py-3 px-3 font-semibold cursor-pointer hover:text-foreground" @click="toggleSort('severity')">
                <span class="flex items-center gap-1">Severity <ArrowUpDown class="h-3 w-3" /></span>
              </th>
              <th class="text-right py-3 px-3 font-semibold cursor-pointer hover:text-foreground" @click="toggleSort('estimated_reward')">
                <span class="flex items-center gap-1 justify-end">Payout <ArrowUpDown class="h-3 w-3" /></span>
              </th>
              <th class="text-right py-3 px-3 font-semibold cursor-pointer hover:text-foreground" @click="toggleSort('created_at')">
                <span class="flex items-center gap-1 justify-end">Elapsed <ArrowUpDown class="h-3 w-3" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in filteredReports" :key="r.id"
              class="border-b border-border/20 transition-colors hover:bg-surface/20 cursor-pointer"
            >
              <td class="py-3 px-3">
                <div class="flex items-center gap-2">
                  <FileText class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span class="text-xs font-medium text-foreground truncate max-w-[220px]">{{ r.vulnerability || r.target || `#${r.id}` }}</span>
                </div>
              </td>
              <td class="py-3 px-3">
                <Badge :variant="statusVariant(r.status)" class="text-[10px] px-1.5 py-0 capitalize">{{ r.status }}</Badge>
              </td>
              <td class="py-3 px-3">
                <Badge v-if="r.severity" :variant="severityVariant(r.severity)" class="text-[10px] px-1.5 py-0">{{ r.severity }}</Badge>
                <span v-else class="text-xs text-muted-foreground">—</span>
              </td>
              <td class="py-3 px-3 text-right text-xs font-semibold tabular-nums">
                <span v-if="r.estimated_reward" class="text-gold">${{ r.estimated_reward.toLocaleString() }}</span>
                <span v-else class="text-muted-foreground">—</span>
              </td>
              <td class="py-3 px-3 text-right text-xs text-muted-foreground tabular-nums">
                {{ elapsedDays(r.created_at) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > limit" class="flex items-center justify-between animate-in">
        <p class="text-xs text-muted-foreground">
          Mostrando {{ (page - 1) * limit + 1 }}-{{ Math.min(page * limit, total) }} de {{ total }}
        </p>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="prevPage">
            <ChevronLeft class="h-3.5 w-3.5" />
          </Button>
          <div class="flex items-center gap-1">
            <span class="text-xs text-muted-foreground">{{ page }} / {{ totalPages }}</span>
          </div>
          <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="nextPage">
            <ChevronRight class="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </template>
  </div>
</template>
