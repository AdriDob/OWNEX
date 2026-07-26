<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Select from '@/components/ui/Select.vue'
import { Radar, Search, Filter, TrendingUp, DollarSign, Clock, RefreshCw, ChevronDown, ChevronUp, ExternalLink, AlertTriangle } from '@lucide/vue'
import BarChart from '@/components/charts/BarChart.vue'

interface MoneyRadarItem {
  id: number
  name: string
  platform: string
  program_url: string | null
  private: boolean
  status: string
  orion_score: number
  priority: string
  max_reward: number | null
  min_reward: number | null
  reward_currency: string
  total_reports: number
  confirmed_reports: number
  total_earned: number
  competition: number
  effort_hours: number
  evh: number
  technologies_summary: string | null
}

const router = useRouter()
const items = ref<MoneyRadarItem[]>([])
const loading = ref(true)
const refreshing = ref(false)
const error = ref<string | null>(null)
const search = ref('')
const minScore = ref(0)
const platformFilter = ref('')
const sortField = ref<'orion_score' | 'evh' | 'max_reward'>('orion_score')
const sortAsc = ref(false)

onMounted(() => { fetchRadar() })

async function fetchRadar() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: 100, sort_order: 'desc' }
    if (minScore.value > 0) params.min_score = minScore.value
    if (platformFilter.value) params.platform = platformFilter.value
    const res = await api.get<{ items: MoneyRadarItem[]; total: number }>('/economic/money-radar', params)
    items.value = res.items || []
  } catch (e: any) { error.value = e?.message || 'Error al cargar el radar'; items.value = [] }
  finally { loading.value = false }
}

async function refreshScores() {
  refreshing.value = true
  try {
    await api.post('/economic/money-radar/refresh')
    await fetchRadar()
  } catch { /* ignore */ }
  finally { refreshing.value = false }
}

function toggleSort(field: typeof sortField.value) {
  if (sortField.value === field) sortAsc.value = !sortAsc.value
  else { sortField.value = field; sortAsc.value = false }
}

const filtered = computed(() => {
  let list = items.value
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(i => i.name.toLowerCase().includes(q) || i.platform.toLowerCase().includes(q))
  }
  const dir = sortAsc.value ? 1 : -1
  return [...list].sort((a, b) => {
    const va = a[sortField.value] ?? 0
    const vb = b[sortField.value] ?? 0
    return (va < vb ? -1 : va > vb ? 1 : 0) * dir
  })
})

const platforms = computed(() => [...new Set(items.value.map(i => i.platform))].sort())

function scoreColor(s: number) {
  if (s >= 0.8) return 'success' as const
  if (s >= 0.6) return 'info' as const
  if (s >= 0.4) return 'warning' as const
  return 'default' as const
}

function priorityBadge(p: string) {
  if (p === 'critical') return 'destructive' as const
  if (p === 'high') return 'warning' as const
  if (p === 'medium') return 'default' as const
  return 'outline' as const
}

function formatMoney(n: number | null) {
  if (!n) return '—'
  return '$' + n.toLocaleString()
}

function competitionLabel(c: number) {
  if (c >= 0.7) return 'Alta'
  if (c >= 0.4) return 'Media'
  return 'Baja'
}

function openProgram(id: number) {
  router.push({ name: 'program-intel', params: { id } })
}
</script>

<template>
  <div class="space-y-6">
    <!-- ═══ HEADER ═══ -->
    <div class="space-y-1 animate-in">
      <div class="flex items-center gap-2">
        <Radar class="h-4 w-4 text-primary" />
        <span class="font-mono text-[10px] font-bold tracking-widest text-primary">MONEY RADAR</span>
        <span class="lamp" :class="items.length ? 'lamp-green' : 'lamp-off'" />
      </div>
      <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Money Radar</h1>
      <p class="text-xs text-muted-foreground">
        Todos los programas rankeados por ORION SCORE — el mejor retorno económico primero
      </p>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3 animate-in">
      <div class="relative max-w-xs">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="search" placeholder="Buscar programa..." class="pl-10" />
      </div>
      <Select
        :options="[{ value: '', label: 'Todas las plataformas' }, ...platforms.map(p => ({ value: p, label: p }))]"
        :model-value="platformFilter"
        @update:model-value="platformFilter = $event as string"
        class="w-40"
      />
      <Select
        :options="[
          { value: '0', label: 'Score ≥ 0.0' },
          { value: '0.4', label: 'Score ≥ 0.4' },
          { value: '0.6', label: 'Score ≥ 0.6' },
          { value: '0.8', label: 'Score ≥ 0.8' },
        ]"
        :model-value="String(minScore)"
        @update:model-value="minScore = Number($event)"
        class="w-36"
      />
      <Button variant="outline" size="sm" :disabled="refreshing" @click="refreshScores">
        <RefreshCw class="mr-1 h-3 w-3" :class="{ 'animate-spin': refreshing }" />
        {{ refreshing ? 'Calculando...' : 'Recalcular Scores' }}
      </Button>
    </div>

    <!-- Summary bar -->
    <div v-if="!loading && items.length" class="grid grid-cols-2 gap-4 sm:grid-cols-4 animate-in">
      <div class="tactical-panel rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider">PROGRAMAS</span>
          <Filter class="h-4 w-4 text-primary" />
        </div>
        <p class="font-mono text-xl font-bold text-primary">{{ items.length }}</p>
      </div>
      <div class="tactical-panel rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider">MEJOR SCORE</span>
          <TrendingUp class="h-4 w-4 text-success" />
        </div>
        <p class="font-mono text-xl font-bold text-success">{{ bestScore }}</p>
      </div>
      <div class="tactical-panel rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider">MEJOR EVH</span>
          <DollarSign class="h-4 w-4 text-warning" />
        </div>
        <p class="font-mono text-xl font-bold text-warning">{{ bestEVH }}</p>
      </div>
      <div class="tactical-panel rounded-xl p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider">REWARD MÁX</span>
          <Clock class="h-4 w-4 text-gold" />
        </div>
        <p class="font-mono text-xl font-bold text-gold">{{ maxReward }}</p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 5" :key="i" class="h-16 rounded-xl" />
    </div>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="fetchRadar">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="filtered.length">
      <!-- EVH Chart -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">EVH Scores</h3>
        <BarChart
          :labels="filtered.slice(0, 10).map(i => i.name)"
          :datasets="[{ label: 'EVH ($/h)', data: filtered.slice(0, 10).map(i => i.evh) }]"
          :height="200"
        />
      </Card>

      <!-- Table -->
      <div class="animate-in space-y-2">
      <div class="hidden grid-cols-12 gap-2 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground lg:grid">
        <button class="col-span-3 flex items-center gap-1 text-left hover:text-foreground" @click="toggleSort('orion_score')">
          Programa
          <ChevronUp v-if="sortField === 'orion_score' && sortAsc" class="h-3 w-3" />
          <ChevronDown v-else-if="sortField === 'orion_score'" class="h-3 w-3" />
        </button>
        <div class="col-span-1">Score</div>
        <div class="col-span-1">EVH</div>
        <button class="col-span-2 flex items-center gap-1 text-left hover:text-foreground" @click="toggleSort('max_reward')">
          Recompensa
          <ChevronUp v-if="sortField === 'max_reward' && sortAsc" class="h-3 w-3" />
          <ChevronDown v-else-if="sortField === 'max_reward'" class="h-3 w-3" />
        </button>
        <div class="col-span-1">Competencia</div>
        <div class="col-span-2">Plataforma</div>
        <div class="col-span-1">Reportes</div>
        <div class="col-span-1"></div>
      </div>

      <button
        v-for="item in filtered"
        :key="item.id"
        class="grid w-full grid-cols-12 items-center gap-2 rounded-xl border border-border/40 bg-[#11131f]/40 px-4 py-3 text-left text-sm transition-all hover:border-primary/30 hover:bg-[#11131f]/80 animate-in"
        @click="openProgram(item.id)"
      >
        <div class="col-span-3 min-w-0">
          <p class="truncate font-semibold text-foreground">{{ item.name }}</p>
          <p v-if="item.technologies_summary" class="truncate text-xs text-muted-foreground">{{ item.technologies_summary }}</p>
        </div>
        <div class="col-span-1">
          <Badge :variant="scoreColor(item.orion_score)">{{ item.orion_score.toFixed(3) }}</Badge>
        </div>
        <div class="col-span-1">
          <span class="font-mono text-xs" :class="item.evh >= 500 ? 'text-success' : item.evh >= 100 ? 'text-foreground' : 'text-muted-foreground'">
            ${{ item.evh.toFixed(0) }}/h
          </span>
        </div>
        <div class="col-span-2">
          <span class="font-mono text-xs text-foreground">{{ formatMoney(item.max_reward) }}</span>
          <span v-if="item.min_reward" class="text-xs text-muted-foreground"> – {{ formatMoney(item.min_reward) }}</span>
        </div>
        <div class="col-span-1">
          <span class="text-xs" :class="item.competition >= 0.7 ? 'text-destructive' : item.competition >= 0.4 ? 'text-warning' : 'text-success'">
            {{ competitionLabel(item.competition) }}
          </span>
        </div>
        <div class="col-span-2 flex items-center gap-1">
          <span class="text-xs capitalize text-muted-foreground">{{ item.platform }}</span>
          <Badge v-if="item.private" variant="outline" class="text-[10px]">Privado</Badge>
        </div>
        <div class="col-span-1 text-xs text-muted-foreground">
          {{ item.total_reports }} ({{ item.confirmed_reports }} ok)
        </div>
        <div class="col-span-1 flex justify-end">
          <ExternalLink class="h-3 w-3 text-muted-foreground" />
        </div>
      </button>

      <p class="pt-2 text-center text-xs text-muted-foreground">
        {{ filtered.length }} programa{{ filtered.length !== 1 ? 's' : '' }}
      </p>
    </div>

    </template>

    <!-- Empty -->
    <div v-else class="flex flex-col items-center py-20 text-center">
      <Radar class="mb-4 h-10 w-10 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No hay programas disponibles</p>
      <p class="mt-1 text-xs text-muted-foreground">Agregá programas desde Settings o esperá el primer escaneo</p>
    </div>

    <!-- ═══ HOW-TO FOOTER ═══ -->
    <Card class="animate-in">
      <div class="p-4">
        <div class="flex items-center gap-2 mb-3">
          <Radar class="h-4 w-4 text-primary" />
          <h3 class="text-sm font-semibold">Cómo usar Money Radar</h3>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
              Filtrame
            </p>
            <p class="text-muted-foreground leading-relaxed">
              Usá los filtros de búsqueda, plataforma y score mínimo para encontrar los programas con mejor relación retorno/esfuerzo.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
              Clasificá
            </p>
            <p class="text-muted-foreground leading-relaxed">
              El ORION SCORE rankea programas por Expected Value. EVH ($/h) muestra el retorno estimado por hora invertida.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">3</span>
              Accioná
            </p>
            <p class="text-muted-foreground leading-relaxed">
              Hacé click en un programa para ver inteligencia detallada, targets activos y plan de ataque personalizado.
            </p>
          </div>
        </div>
      </div>
    </Card>
  </div>
</template>
