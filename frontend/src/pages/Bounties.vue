<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { DoughnutChart, BarChart } from '@/components/charts'
import {
  AlertTriangle, ArrowUpDown, Award, BarChart3, DollarSign, Filter, RefreshCw, Search,
} from '@lucide/vue'

interface BountyItem {
  id: number
  program: string
  platform: string
  vulnerability_type: string
  category: string
  payout: number
  evh: number
  confidence: number
  endpoint_count: number
  priority: string
}

type SortField = 'evh' | 'payout' | 'confidence'

const topBounties = ref<BountyItem[]>([])
const evhBounties = ref<BountyItem[]>([])
const categories = ref<string[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const selectedCategory = ref('')
const sortField = ref<SortField>('evh')
const sortAsc = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [topRes, evhRes, catRes] = await Promise.all([
      api.get<{ items: BountyItem[] }>('/opportunity/top', { limit: 50 }),
      api.get<{ items: BountyItem[] }>('/opportunity/evh', { limit: 50 }),
      api.get<{ categories: string[] }>('/opportunity/categories'),
    ])
    topBounties.value = topRes.items || []
    evhBounties.value = evhRes.items || []
    categories.value = catRes.categories || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar bounties'
  }
  finally { loading.value = false }
}

onMounted(fetchData)

const allItems = computed(() => {
  const map = new Map<number, BountyItem>()
  for (const item of [...topBounties.value, ...evhBounties.value]) {
    if (!map.has(item.id)) map.set(item.id, item)
  }
  return Array.from(map.values())
})

const filtered = computed(() => {
  let result = allItems.value
  const q = search.value.toLowerCase()
  if (q) {
    result = result.filter(i =>
      i.program?.toLowerCase().includes(q) ||
      i.platform?.toLowerCase().includes(q) ||
      i.vulnerability_type?.toLowerCase().includes(q)
    )
  }
  if (selectedCategory.value) {
    result = result.filter(i => i.category === selectedCategory.value)
  }
  result = [...result].sort((a, b) => {
    const mul = sortAsc.value ? 1 : -1
    return (a[sortField.value] - b[sortField.value]) * mul
  })
  return result
})

function toggleSort(field: SortField) {
  if (sortField.value === field) sortAsc.value = !sortAsc.value
  else { sortField.value = field; sortAsc.value = false }
}

const categoryLabels = computed(() => {
  const map: Record<string, number> = {}
  for (const item of allItems.value) {
    const cat = item.category || 'Other'
    map[cat] = (map[cat] || 0) + 1
  }
  return Object.entries(map).sort((a, b) => b[1] - a[1])
})

const evhChartLabels = computed(() => filtered.value.slice(0, 10).map(i => i.program.length > 14 ? i.program.slice(0, 12) + '…' : i.program))
const evhChartData = computed(() => filtered.value.slice(0, 10).map(i => i.evh))

function formatMoney(n: number) {
  if (n >= 1000) return '$' + (n / 1000).toFixed(1) + 'k'
  return '$' + n.toLocaleString()
}

function confidenceVariant(c: number) {
  if (c >= 8) return 'success' as const
  if (c >= 5) return 'warning' as const
  return 'default' as const
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Marketplace</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Bounties</h1>
      <p class="text-sm text-muted-foreground">Oportunidades de bounty priorizadas por valor esperado</p>
    </div>

    <template v-if="loading">
      <div class="flex gap-3">
        <Skeleton v-for="i in 4" :key="i" class="h-8 w-24 rounded-lg" />
      </div>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton class="h-52 rounded-xl" />
        <Skeleton class="h-52 rounded-xl" />
      </div>
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-32 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error al cargar bounties</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4 gap-2" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="allItems.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Award class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay bounties disponibles</p>
        <p class="mt-1 text-xs text-muted-foreground">Conectá plataformas de bug bounty para ver oportunidades</p>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-wrap items-center gap-3 animate-in">
        <div class="relative flex-1 min-w-0 sm:min-w-[200px] max-w-xs">
          <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input v-model="search" placeholder="Buscar bounties..."
            class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
          />
        </div>
        <select v-model="selectedCategory"
          class="rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground outline-none focus:border-primary/30"
        >
          <option value="">Todas las categorías</option>
          <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
        <div class="flex items-center gap-1 text-xs text-muted-foreground">
          <Filter class="h-3.5 w-3.5" />
          <span>{{ filtered.length }} resultados</span>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">EVH por programa (top 10)</p>
          </div>
          <BarChart
            :labels="evhChartLabels"
            :datasets="[{ label: 'EVH', data: evhChartData, backgroundColor: '#22c55e' }]"
            :height="200"
            xLabel="Programa"
            yLabel="EVH"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <DollarSign class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Distribución por categoría</p>
          </div>
          <DoughnutChart
            :labels="categoryLabels.map(([k]) => k)"
            :data="categoryLabels.map(([, v]) => v)"
            :height="200"
          />
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card v-for="(b, i) in filtered" :key="b.id" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-start justify-between mb-2">
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold text-foreground truncate">{{ b.program }}</h3>
              <p class="text-[10px] text-muted-foreground">{{ b.platform }} · {{ b.vulnerability_type }}</p>
            </div>
            <Badge variant="success" class="shrink-0 text-[10px]">${{ formatMoney(b.payout) }}</Badge>
          </div>
          <div class="grid grid-cols-3 gap-2 mb-2">
            <div class="text-center">
              <p class="text-[9px] text-muted-foreground">EVH</p>
              <p class="text-xs font-bold text-success">{{ b.evh.toFixed(1) }}</p>
            </div>
            <div class="text-center">
              <p class="text-[9px] text-muted-foreground">Payout</p>
              <p class="text-xs font-bold text-foreground">{{ formatMoney(b.payout) }}</p>
            </div>
            <div class="text-center">
              <p class="text-[9px] text-muted-foreground">Confianza</p>
              <Badge :variant="confidenceVariant(b.confidence)" class="text-[10px] px-1">
                {{ (b.confidence * 100).toFixed(0) }}%
              </Badge>
            </div>
          </div>
          <div class="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>{{ b.endpoint_count }} endpoints</span>
            <Badge v-if="b.category" variant="default" class="text-[9px]">{{ b.category }}</Badge>
          </div>
        </Card>
      </div>

      <div v-if="filtered.length === 0" class="py-12 text-center text-sm text-muted-foreground">
        Sin resultados para los filtros actuales
      </div>
    </template>
  </div>
</template>
