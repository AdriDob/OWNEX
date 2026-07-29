<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart } from '@/components/charts'
import {
  Target, Search, AlertTriangle, RefreshCw, Globe, TrendingUp,
  BarChart3, ArrowUpDown,
} from '@lucide/vue'

interface Opportunity {
  id: number
  name: string
  domain: string
  platform: string
  opportunity_score: number
  competition_score: number
  freshness_score: number
  endpoint_count: number
}

interface OrionOpp {
  id: number
  name: string
  domain: string
  opportunity_score: number
  endpoints: number
  competition: number
  freshness: number
}

type SortKey = 'opportunity_score' | 'endpoint_count' | 'competition_score' | 'freshness_score'

const items = ref<Opportunity[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const sortKey = ref<SortKey>('opportunity_score')
const sortAsc = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [oppsRes, orionRes] = await Promise.allSettled([
      api.get<{ items: Opportunity[]; total: number }>('/opportunities', { limit: 100 }),
      api.get<{ opportunities: { top: OrionOpp[] } }>('/orion/context', { refresh: true }),
    ])
    const merged: Opportunity[] = []
    if (oppsRes.status === 'fulfilled' && oppsRes.value.items) {
      merged.push(...oppsRes.value.items)
    }
    if (orionRes.status === 'fulfilled') {
      const top = orionRes.value.opportunities?.top
      if (top) {
        for (const o of top) {
          if (!merged.some(m => m.id === o.id)) {
            merged.push({
              id: o.id,
              name: o.name,
              domain: o.domain,
              platform: '',
              opportunity_score: o.opportunity_score,
              competition_score: o.competition ?? 0,
              freshness_score: o.freshness ?? 0,
              endpoint_count: o.endpoints ?? 0,
            })
          }
        }
      }
    }
    items.value = merged
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar oportunidades'
  }
  finally { loading.value = false }
}

onMounted(fetchData)

const filtered = computed(() => {
  let result = items.value
  const q = search.value.toLowerCase()
  if (q) {
    result = result.filter(i =>
      i.name.toLowerCase().includes(q) ||
      i.domain?.toLowerCase().includes(q) ||
      i.platform?.toLowerCase().includes(q)
    )
  }
  result = [...result].sort((a, b) => {
    const mul = sortAsc.value ? 1 : -1
    return (a[sortKey.value] - b[sortKey.value]) * mul
  })
  return result
})

function toggleSort(key: SortKey) {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else { sortKey.value = key; sortAsc.value = false }
}

const chartLabels = computed(() => filtered.value.slice(0, 10).map(o => o.name.length > 16 ? o.name.slice(0, 14) + '…' : o.name))
const chartData = computed(() => filtered.value.slice(0, 10).map(o => o.opportunity_score))
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Discovery</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Opportunities</h1>
      <p class="text-sm text-muted-foreground">Oportunidades de investigación priorizadas por OWNEX</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-10 max-w-md rounded-xl" />
      <Skeleton class="h-52 rounded-xl" />
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-28 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error al cargar oportunidades</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="items.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Target class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay oportunidades disponibles</p>
        <p class="mt-1 text-xs text-muted-foreground">Escaneá nuevos targets para generar oportunidades</p>
      </div>
    </template>

    <template v-else>
      <div class="relative max-w-md">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input v-model="search" placeholder="Buscar oportunidades..."
          class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
        />
      </div>

      <Card class="animate-in p-4">
        <div class="flex items-center gap-2 mb-3">
          <BarChart3 class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Top 10 por Score</p>
        </div>
        <BarChart
          :labels="chartLabels"
          :datasets="[{ label: 'Opportunity Score', data: chartData, backgroundColor: '#3b82f6' }]"
          :height="200"
          xLabel="Oportunidad"
          yLabel="Score"
        />
      </Card>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card v-for="(opp, i) in filtered" :key="opp.id" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-foreground truncate flex items-center gap-1.5">
                <Globe class="h-3.5 w-3.5 shrink-0 text-primary" />
                {{ opp.name }}
              </h3>
              <p v-if="opp.domain" class="mt-0.5 text-[10px] text-muted-foreground truncate">{{ opp.domain }}</p>
            </div>
            <Badge :variant="opp.opportunity_score >= 7 ? 'success' : opp.opportunity_score >= 4 ? 'warning' : 'default'" class="shrink-0">
              {{ opp.opportunity_score.toFixed(1) }}
            </Badge>
          </div>
          <div class="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>{{ opp.endpoint_count }} endpoints</span>
            <span v-if="opp.platform">{{ opp.platform }}</span>
          </div>
          <div class="mt-2 flex items-center gap-2 text-[10px]">
            <span class="text-muted-foreground">Competencia:</span>
            <span :class="opp.competition_score > 70 ? 'text-destructive' : opp.competition_score > 40 ? 'text-warning' : 'text-success'">
              {{ opp.competition_score.toFixed(0) }}
            </span>
            <span class="ml-auto text-muted-foreground">Freshness: {{ opp.freshness_score.toFixed(1) }}</span>
          </div>
        </Card>
      </div>

      <div v-if="filtered.length === 0 && items.length > 0" class="py-12 text-center text-sm text-muted-foreground">
        Sin resultados para "{{ search }}"
      </div>
    </template>
  </div>
</template>
