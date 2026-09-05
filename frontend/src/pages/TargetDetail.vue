<script setup lang="ts">
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Globe,
  Lightbulb,
  List,
  RefreshCw,
  Shield,
  Target,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BarChart, DoughnutChart } from '@/components/charts'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface TargetDetail {
  id: number
  name: string
  domain: string
  risk_score: number
  roi: number
  finding_count: number
  confirmed_findings: number
  estimated_payout: number
  endpoint_count: number
  surfaces: string[]
  risk_distribution?: Record<string, number>
  created_at: string | null
}

interface EndpointItem {
  id: number
  path: string
  method: string
  risk_score: number
  finding_count: number
  created_at: string | null
}

const route = useRoute()
const router = useRouter()
const targetId = Number(route.params.id)

const target = ref<TargetDetail | null>(null)
const endpoints = ref<EndpointItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const epPage = ref(1)
const epTotal = ref(0)
const epLimit = 20
const generating = ref(false)

async function fetchTarget() {
  loading.value = true
  error.value = null
  try {
    const [t, e] = await Promise.all([
      api.get<TargetDetail>(`/targets/${targetId}`),
      api.get<{ items: EndpointItem[]; total: number }>(`/endpoints`, {
        target_id: targetId,
        skip: (epPage.value - 1) * epLimit,
        limit: epLimit,
      }),
    ])
    target.value = t
    endpoints.value = e.items || []
    epTotal.value = e.total || 0
  } catch (e: any) {
    if (e?.status === 404) target.value = null
    else error.value = e?.message || 'Error al cargar target'
  } finally {
    loading.value = false
  }
}

onMounted(fetchTarget)

async function fetchEndpoints() {
  try {
    const e = await api.get<{ items: EndpointItem[]; total: number }>(`/endpoints`, {
      target_id: targetId,
      skip: (epPage.value - 1) * epLimit,
      limit: epLimit,
    })
    endpoints.value = e.items || []
    epTotal.value = e.total || 0
  } catch {
    /* ignore */
  }
}

function prevEpPage() {
  if (epPage.value > 1) {
    epPage.value--
    fetchEndpoints()
  }
}
function nextEpPage() {
  if (epPage.value * epLimit < epTotal.value) {
    epPage.value++
    fetchEndpoints()
  }
}

async function generateHypotheses() {
  if (!target.value) return
  generating.value = true
  try {
    await api.post(`/zap/hypotheses/${targetId}`, { target_url: target.value.domain })
  } catch {
    /* ignore */
  } finally {
    generating.value = false
  }
}

const epTotalPages = computed(() => Math.max(1, Math.ceil(epTotal.value / epLimit)))

function riskColor(score: number) {
  if (score >= 70) return 'destructive' as const
  if (score >= 40) return 'warning' as const
  if (score >= 20) return 'info' as const
  return 'default' as const
}

const riskChartData = computed(() => {
  if (!target.value?.risk_distribution) return { labels: [], data: [] }
  const dist = target.value.risk_distribution
  const order = ['critical', 'high', 'medium', 'low', 'info']
  const labels: string[] = []
  const data: number[] = []
  for (const key of order) {
    if (dist[key] !== undefined) {
      labels.push(key.charAt(0).toUpperCase() + key.slice(1))
      data.push(dist[key])
    }
  }
  return { labels, data }
})

const methodChartData = computed(() => {
  const counts: Record<string, number> = {}
  for (const ep of endpoints.value) {
    const m = ep.method?.toUpperCase() || 'UNKNOWN'
    counts[m] = (counts[m] || 0) + 1
  }
  return {
    labels: Object.keys(counts),
    datasets: [
      {
        label: 'Endpoints',
        data: Object.values(counts),
        backgroundColor: ['var(--ownex-text-primary)', 'var(--ownex-green)', 'var(--ownex-gold)', 'var(--ownex-accent)', 'var(--ownex-text-secondary)', 'var(--ownex-text-secondary)'],
      },
    ],
  }
})
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <button class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground animate-in" aria-label="Back to Target Radar" @click="router.push({ name: 'radar' })">
      <ArrowLeft class="h-3 w-3" />
      Volver al Radar
    </button>

    <template v-if="loading">
      <Skeleton class="h-8 w-64 rounded-lg" />
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-40 rounded-xl" />
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">Error al cargar el target</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" size="sm" @click="fetchTarget">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </Card>
    </template>

    <template v-else-if="!target">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Target class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Target no encontrado</p>
        <p class="mt-1 text-xs text-muted-foreground">El target con ID {{ targetId }} no existe o fue eliminado</p>
        <Button class="mt-4" size="sm" variant="outline" aria-label="Back to Target Radar" @click="router.push({ name: 'radar' })">
          Volver al Radar
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="animate-in space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <h1 class="font-display text-2xl font-bold text-foreground">{{ target.name }}</h1>
              <Badge :variant="riskColor(target.risk_score)" class="text-[10px]">Risk {{ target.risk_score }}</Badge>
            </div>
            <div class="flex items-center gap-3 text-xs text-muted-foreground">
              <span class="flex items-center gap-1"><Globe class="h-3 w-3" /> {{ target.domain }}</span>
              <span v-if="target.roi !== undefined" class="flex items-center gap-1">
                <DollarSign class="h-3 w-3" /> ROI {{ target.roi }}%
              </span>
            </div>
          </div>
          <Button :disabled="generating" @click="generateHypotheses">
            <Lightbulb v-if="!generating" class="h-4 w-4" />
            <span v-else class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            {{ generating ? 'Generando...' : 'Generate Hypotheses' }}
          </Button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 animate-in">
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Findings</p>
          <p class="text-2xl font-bold text-foreground mt-1">{{ target.finding_count }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Confirmed</p>
          <p class="text-2xl font-bold text-success mt-1">{{ target.confirmed_findings }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Est. Payout</p>
          <p class="text-2xl font-bold text-gold mt-1">${{ (target.estimated_payout || 0).toLocaleString() }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Endpoints</p>
          <p class="text-2xl font-bold text-accent mt-1">{{ target.endpoint_count }}</p>
        </Card>
      </div>

      <div v-if="target.surfaces?.length" class="animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Activity class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Attack Surfaces</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge v-for="s in target.surfaces" :key="s" variant="outline">{{ s }}</Badge>
          </div>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Shield class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Risk Distribution</p>
          </div>
          <DoughnutChart
            v-if="riskChartData.labels.length"
            :labels="riskChartData.labels"
            :data="riskChartData.data"
            :height="220"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">No risk distribution data</div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <List class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Endpoint Methods</p>
          </div>
          <BarChart
            v-if="methodChartData.labels.length"
            :labels="methodChartData.labels"
            :datasets="methodChartData.datasets"
            :height="220"
            :showLegend="false"
            yLabel="Count"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">No endpoint data</div>
        </Card>
      </div>

      <div class="space-y-3 animate-in">
        <h2 class="text-sm font-semibold text-foreground flex items-center gap-2">
          <List class="h-4 w-4 text-muted-foreground" />
          Endpoints
          <span class="text-xs text-muted-foreground font-normal">({{ epTotal }})</span>
        </h2>

        <div v-if="endpoints.length === 0" class="py-8 text-center text-sm text-muted-foreground">
          No hay endpoints registrados para este target
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border/40 text-xs text-muted-foreground uppercase tracking-wider">
                <th class="text-left py-3 px-3 font-semibold">Path</th>
                <th class="text-left py-3 px-3 font-semibold">Method</th>
                <th class="text-right py-3 px-3 font-semibold">Risk</th>
                <th class="text-right py-3 px-3 font-semibold">Findings</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ep in endpoints" :key="ep.id"
                class="border-b border-border/20 transition-colors hover:bg-surface/20 cursor-pointer"
                @click="router.push({ name: 'endpoint-detail', params: { id: ep.id } })"
              >
                <td class="py-3 px-3">
                  <div class="flex items-center gap-2">
                    <Globe class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span class="text-xs font-mono text-foreground truncate max-w-[300px]">{{ ep.path }}</span>
                  </div>
                </td>
                <td class="py-3 px-3">
                  <Badge variant="outline" class="text-[10px] font-mono px-1.5 py-0">{{ ep.method }}</Badge>
                </td>
                <td class="py-3 px-3 text-right">
                  <span class="text-xs font-semibold tabular-nums" :class="ep.risk_score >= 70 ? 'text-destructive' : ep.risk_score >= 40 ? 'text-warning' : 'text-muted-foreground'">
                    {{ ep.risk_score }}
                  </span>
                </td>
                <td class="py-3 px-3 text-right text-xs text-muted-foreground tabular-nums">
                  {{ ep.finding_count }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="epTotal > epLimit" class="flex items-center justify-between">
          <p class="text-xs text-muted-foreground">
            {{ (epPage - 1) * epLimit + 1 }}-{{ Math.min(epPage * epLimit, epTotal) }} de {{ epTotal }}
          </p>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" :disabled="epPage <= 1" @click="prevEpPage">
              <ChevronLeft class="h-3.5 w-3.5" />
            </Button>
            <span class="text-xs text-muted-foreground">{{ epPage }} / {{ epTotalPages }}</span>
            <Button variant="outline" size="sm" :disabled="epPage >= epTotalPages" @click="nextEpPage">
              <ChevronRight class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
