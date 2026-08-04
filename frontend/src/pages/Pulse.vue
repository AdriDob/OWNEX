<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import {
  Bot, Star, Clock, TrendingUp, Filter, X, RefreshCw, ExternalLink,
  CheckCircle, AlertCircle, Loader2, ChevronDown, ChevronUp,
  Github, Linkedin, DollarSign, Zap, Brain, Globe, Code2,
  Search, SlidersHorizontal
} from '@lucide/vue'

// ── Types ──────────────────────────────────────────────────────────────
interface PulseOpportunity {
  id: string
  title: string
  platform: string
  platformDisplay: string
  reward: number
  effortHours: number
  confidence: number
  score: number
  url: string
  tags: string[]
  category: string
  description?: string
  postedAt: string
  cycle: 'pulse'
}

interface PlatformInfo {
  id: string
  name: string
  displayName: string
  icon: any
  color: string
  bgColor: string
  connected: boolean
  lastSync?: string
  opportunityCount: number
}

// ── Platform Configuration ─────────────────────────────────────────────
const PULSE_PLATFORMS: PlatformInfo[] = [
  { id: 'outlier', name: 'outlier', displayName: 'Outlier', icon: Brain, color: 'text-intigriti', bgColor: 'bg-intigriti/10', connected: false, opportunityCount: 0 },
  { id: 'mindrift', name: 'mindrift', displayName: 'Mindrift', icon: Zap, color: 'text-warning', bgColor: 'bg-warning/10', connected: false, opportunityCount: 0 },
  { id: 'dataannotation', name: 'dataannotation', displayName: 'DataAnnotation', icon: Globe, color: 'text-primary', bgColor: 'bg-primary/10', connected: false, opportunityCount: 0 },
  { id: 'remotasks', name: 'remotasks', displayName: 'Remotasks', icon: Code2, color: 'text-success', bgColor: 'bg-success/10', connected: false, opportunityCount: 0 },
  { id: 'freelancer_microtask', name: 'freelancer_microtask', displayName: 'Freelancer Microtasks', icon: DollarSign, color: 'text-warning', bgColor: 'bg-warning/10', connected: false, opportunityCount: 0 },
  { id: 'linkedin_easyapply', name: 'linkedin_easyapply', displayName: 'LinkedIn Easy Apply', icon: Linkedin, color: "text-primary", bgColor: "bg-primary/10", connected: false, opportunityCount: 0 },
  { id: 'opyre_microtask', name: 'opyre_microtask', displayName: 'Opyre Microtasks', icon: Github, color: 'text-destructive', bgColor: 'bg-destructive/10', connected: false, opportunityCount: 0 },
]

// ── State ──────────────────────────────────────────────────────────────
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const opportunities = ref<PulseOpportunity[]>([])
const allOpportunities = ref<PulseOpportunity[]>([])
const selectedPlatform = ref('')
const effortFilter = ref('') // 'low', 'medium', 'high'
const minReward = ref(0)
const maxReward = ref(10000)
const sortBy = ref('score') // 'score', 'reward', 'effort', 'confidence', 'date'
const sortOrder = ref('desc')
const viewMode = ref<'cards' | 'table'>('cards')
const showFilters = ref(false)

// ── Computed ───────────────────────────────────────────────────────────
const filteredOpportunities = computed(() => {
  let result = [...allOpportunities.value]

  if (selectedPlatform.value) {
    result = result.filter(o => o.platform === selectedPlatform.value)
  }

  if (effortFilter.value) {
    result = result.filter(o => {
      if (effortFilter.value === 'low') return o.effortHours < 2
      if (effortFilter.value === 'medium') return o.effortHours >= 2 && o.effortHours < 5
      if (effortFilter.value === 'high') return o.effortHours >= 5
      return true
    })
  }

  result = result.filter(o => o.reward >= minReward.value && o.reward <= maxReward.value)

  result.sort((a, b) => {
    let aVal: number | string = a[sortBy.value as keyof PulseOpportunity]
    let bVal: number | string = b[sortBy.value as keyof PulseOpportunity]
    if (sortBy.value === 'date') {
      aVal = new Date(a.postedAt).getTime()
      bVal = new Date(b.postedAt).getTime()
    }
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = bVal.toLowerCase()
    }
    const dir = sortOrder.value === 'asc' ? 1 : -1
    return aVal > bVal ? dir : aVal < bVal ? -dir : 0
  })

  return result
})

const platformStats = computed(() => {
  const stats: Record<string, { count: number; avgReward: number; avgEffort: number; connected: boolean }> = {}
  for (const opp of allOpportunities.value) {
    if (!stats[opp.platform]) {
      stats[opp.platform] = { count: 0, avgReward: 0, avgEffort: 0, connected: false }
    }
    stats[opp.platform].count++
    stats[opp.platform].avgReward += opp.reward
    stats[opp.platform].avgEffort += opp.effortHours
  }
  for (const key of Object.keys(stats)) {
    stats[key].avgReward = Math.round(stats[key].avgReward / stats[key].count)
    stats[key].avgEffort = Math.round((stats[key].avgEffort / stats[key].count) * 10) / 10
  }
  return stats
})

const totalRewards = computed(() => allOpportunities.value.reduce((sum, o) => sum + o.reward, 0))
const avgConfidence = computed(() => {
  if (!allOpportunities.value.length) return 0
  return Math.round(allOpportunities.value.reduce((sum, o) => sum + o.confidence, 0) / allOpportunities.value.length)
})

// ── Helpers ────────────────────────────────────────────────────────────
function effortLabel(hours: number): string {
  if (hours < 2) return 'Bajo'
  if (hours < 5) return 'Medio'
  return 'Alto'
}

function effortColor(hours: number): string {
  if (hours < 2) return 'bg-success/20 text-success'
  if (hours < 5) return 'bg-warning/20 text-warning'
  return 'bg-destructive/20 text-destructive'
}

function confidenceColor(conf: number): string {
  if (conf >= 80) return 'text-success'
  if (conf >= 60) return 'text-warning'
  return 'text-destructive'
}

function formatReward(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return dateStr
  }
}

function getPlatformInfo(platformId: string): PlatformInfo | undefined {
  return PULSE_PLATFORMS.find(p => p.id === platformId)
}

function toggleSort(field: string) {
  if (sortBy.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortOrder.value = 'desc'
  }
}

function clearFilters() {
  selectedPlatform.value = ''
  effortFilter.value = ''
  minReward.value = 0
  maxReward.value = 10000
}

// ── Data Fetching ──────────────────────────────────────────────────────
async function fetchOpportunities() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<any>('/api/opportunity/top', { limit: 100 })
    const opps = res.opportunities || []

    const pulseOpps: PulseOpportunity[] = opps
      .filter((o: any) => o.category === 'pulse' || o.source_type === 'pulse')
      .map((o: any, idx: number) => ({
        id: o.id || `pulse-${idx}`,
        title: o.name || o.title || 'Untitled',
        platform: o.source_name?.toLowerCase().replace(/\s+/g, '_') || 'unknown',
        platformDisplay: o.source_name || 'Unknown',
        reward: o.reward_info ? parseFloat(o.reward_info.replace(/[^0-9.]/g, '')) || 0 : o.estimated_payout || 0,
        effortHours: o.estimated_effort_hours || 1,
        confidence: o.confidence || Math.round((o.score || 0) * 100),
        score: Math.round((o.score || 0) * 100),
        url: o.public_url || '#',
        tags: o.technology_tags || [],
        category: o.category || 'pulse',
        description: o.scope_summary || '',
        postedAt: o.last_update || o.created_at || new Date().toISOString(),
        cycle: 'pulse' as const,
      }))

    allOpportunities.value = pulseOpps
    opportunities.value = pulseOpps
    updatePlatformConnectionStatus()
  } catch (e: any) {
    error.value = e.message || 'Failed to load Pulse opportunities'
    console.error('[Pulse] Fetch error:', e)
  } finally {
    loading.value = false
  }
}

async function fetchPlatformConnections() {
  try {
    const res = await api.get<any>('/api/opportunity/identity/accounts')
    const accounts = res.accounts || []
    for (const platform of PULSE_PLATFORMS) {
      const acc = accounts.find((a: any) => a.provider === platform.id)
      platform.connected = !!acc
      platform.lastSync = acc?.last_sync
    }
  } catch (e) {
    console.warn('[Pulse] Could not fetch platform connections:', e)
  }
}

function updatePlatformConnectionStatus() {
  for (const platform of PULSE_PLATFORMS) {
    const stat = platformStats.value[platform.id]
    platform.opportunityCount = stat?.count || 0
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    await api.post('/api/opportunity/refresh', {})
    await fetchOpportunities()
  } catch (e: any) {
    error.value = e.message || 'Refresh failed'
  } finally {
    refreshing.value = false
  }
}

async function syncPlatform(platformId: string) {
  const platform = PULSE_PLATFORMS.find(p => p.id === platformId)
  if (!platform) return

  platform.connected = true // optimistic
  try {
    await api.post(`/api/connections/sync/${platformId}`, {})
    platform.lastSync = new Date().toISOString()
    await fetchOpportunities()
  } catch (e: any) {
    platform.connected = false
    error.value = `Sync failed for ${platform.displayName}: ${e.message}`
  }
}

function connectPlatform(platformId: string) {
  window.location.href = `/integrations/connections?platform=${platformId}`
}

function openOpportunity(url: string) {
  if (url && url !== '#') {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([fetchOpportunities(), fetchPlatformConnections()])
})

watch([selectedPlatform, effortFilter, minReward, maxReward, sortBy, sortOrder], () => {
  opportunities.value = filteredOpportunities.value
}, { deep: true })
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      <div>
        <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">AI Work</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Pulse Cycle</h1>
        <p class="text-xs text-muted-foreground mt-1">
          Micro-tareas de IA, data labeling, evaluación de modelos · {{ allOpportunities.length }} oportunidades · ${{ totalRewards }} valor total
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" @click="refreshAll" :disabled="refreshing" class="flex items-center gap-1.5">
          <RefreshCw :class="['h-3.5 w-3.5', refreshing ? 'animate-spin' : '']" />
          {{ refreshing ? 'Actualizando...' : 'Actualizar' }}
        </Button>
        <Button variant="outline" size="sm" @click="showFilters = !showFilters" class="flex items-center gap-1.5">
          <Filter class="h-3.5 w-3.5" />
          Filtros
        </Button>
        <Button variant="ghost" size="sm" @click="viewMode = 'cards'" :class="{ 'bg-primary/10 text-primary': viewMode === 'cards' }">
          <div class="grid grid-cols-2 gap-0.5 p-0.5">
            <div class="rounded bg-primary" /><div class="rounded bg-transparent" />
            <div class="rounded bg-transparent" /><div class="rounded bg-transparent" />
          </div>
        </Button>
        <Button variant="ghost" size="sm" @click="viewMode = 'table'" :class="{ 'bg-primary/10 text-primary': viewMode === 'table' }">
          <div class="flex items-center gap-0.5 p-0.5">
            <div class="h-1.5 w-6 rounded bg-primary" /><div class="h-1.5 w-6 rounded bg-transparent" />
            <div class="h-1.5 w-6 rounded bg-transparent" /><div class="h-1.5 w-6 rounded bg-transparent" />
          </div>
        </Button>
      </div>
    </div>

    <!-- Platform Quick Stats -->
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      <Card v-for="platform in PULSE_PLATFORMS" :key="platform.id" class="p-3 hover:border-primary/30 transition-colors cursor-pointer" @click="selectedPlatform = selectedPlatform === platform.id ? '' : platform.id">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div :class="['rounded-lg p-1.5 flex items-center justify-center', platform.bgColor]">
              <component :is="platform.icon" :class="['h-3.5 w-3.5', platform.color]" />
            </div>
            <div>
              <p class="font-mono text-xs font-semibold text-foreground">{{ platform.displayName }}</p>
              <p class="text-[9px] text-muted-foreground">{{ platform.opportunityCount }} ops</p>
            </div>
          </div>
          <div class="flex items-center gap-1.5">
            <span v-if="platform.connected" class="flex items-center gap-1 text-[9px] font-mono text-success">
              <CheckCircle class="h-3 w-3" /> Conectado
            </span>
            <span v-else class="flex items-center gap-1 text-[9px] font-mono text-muted-foreground">
              <AlertCircle class="h-3 w-3" /> Desconectado
            </span>
            <Badge v-if="selectedPlatform === platform.id" variant="outline" class="text-[8px]">Activo</Badge>
          </div>
        </div>
        <div class="mt-2 flex items-center justify-between text-[9px] font-mono">
          <span class="text-muted-foreground">${{ platformStats[platform.id]?.avgReward || 0 }} avg</span>
          <span class="text-muted-foreground">{{ platformStats[platform.id]?.avgEffort || 0 }}h avg</span>
        </div>
      </Card>
    </div>

    <!-- Filters Panel -->
    <div v-if="showFilters" class="glass-fintech rounded-xl p-4 animate-in space-y-4">
      <div class="flex items-center justify-between">
        <span class="font-mono text-xs font-semibold text-foreground">Filtros</span>
        <Button variant="ghost" size="sm" @click="clearFilters">
          <X class="h-3 w-3" /> Limpiar
        </Button>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <label class="block text-[10px] font-medium text-muted-foreground mb-1">Plataforma</label>
          <Select v-model="selectedPlatform" placeholder="Todas las plataformas" class="w-full">
            <option value="">Todas</option>
            <option v-for="p in PULSE_PLATFORMS" :key="p.id" :value="p.id">{{ p.displayName }}</option>
          </Select>
        </div>

        <div>
          <label class="block text-[10px] font-medium text-muted-foreground mb-1">Esfuerzo</label>
          <Select v-model="effortFilter" placeholder="Cualquier esfuerzo" class="w-full">
            <option value="">Cualquiera</option>
            <option value="low">Bajo (< 2h)</option>
            <option value="medium">Medio (2-5h)</option>
            <option value="high">Alto (> 5h)</option>
          </Select>
        </div>

        <div>
          <label class="block text-[10px] font-medium text-muted-foreground mb-1">Recompensa mín.</label>
          <Input v-model.number="minReward" type="number" placeholder="0" class="w-full" />
        </div>

        <div>
          <label class="block text-[10px] font-medium text-muted-foreground mb-1">Recompensa máx.</label>
          <Input v-model.number="maxReward" type="number" placeholder="10000" class="w-full" />
        </div>

        <div>
          <label class="block text-[10px] font-medium text-muted-foreground mb-1">Ordenar por</label>
          <Select v-model="sortBy" class="w-full">
            <option value="score">Score</option>
            <option value="reward">Recompensa</option>
            <option value="effortHours">Esfuerzo</option>
            <option value="confidence">Confianza</option>
            <option value="date">Fecha</option>
          </Select>
        </div>
      </div>

      <div class="flex items-center gap-2 pt-2 border-t border-border/30">
        <span class="text-[10px] text-muted-foreground">{{ filteredOpportunities.length }} de {{ allOpportunities.length }} oportunidades</span>
        <span class="text-[10px] text-muted-foreground">Confianza media: {{ avgConfidence }}%</span>
      </div>
    </div>

    <!-- Loading / Error / Empty States -->
    <template v-if="loading && opportunities.length === 0">
      <div class="space-y-4">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Skeleton class="h-48 rounded-xl" v-for="i in 8" :key="i" />
        </div>
      </div>
    </template>

    <template v-else-if="error && opportunities.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertCircle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error cargando oportunidades</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchOpportunities">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="opportunities.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Bot class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin oportunidades Pulse</p>
        <p class="mt-1 text-xs text-muted-foreground">
          Conecta plataformas en <a href="/integrations/connections" class="text-primary hover:underline">Conexiones</a> y ejecuta discovery
        </p>
        <Button variant="outline" size="sm" class="mt-4" @click="refreshAll">
          <RefreshCw class="h-3.5 w-3.5" /> Ejecutar Discovery
        </Button>
      </div>
    </template>

    <!-- Cards View -->
    <template v-else>
      <div v-if="viewMode === 'cards'" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <div v-for="opp in opportunities" :key="opp.id" class="group">
          <Card class="p-4 h-full flex flex-col transition-all hover:border-primary/30 hover:bg-surface/50">
            <div class="flex items-start justify-between gap-2 mb-2">
              <h4 class="font-mono text-xs font-semibold text-foreground flex-1 min-w-0 truncate">{{ opp.title }}</h4>
              <span class="font-mono text-[9px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{{ opp.platformDisplay }}</span>
            </div>

            <div class="flex items-center gap-3 text-[9px] font-mono mb-2">
              <span class="flex items-center gap-1 text-warning">
                <Star class="h-2.5 w-2.5" />
                {{ formatReward(opp.reward) }}
              </span>
              <span class="flex items-center gap-1" :class="confidenceColor(opp.confidence)">
                <TrendingUp class="h-2.5 w-2.5" />
                {{ opp.confidence }}%
              </span>
              <span class="flex items-center gap-1" :class="effortColor(opp.effortHours)">
                <Clock class="h-2.5 w-2.5" />
                {{ effortLabel(opp.effortHours) }}
              </span>
            </div>

            <div class="flex flex-wrap gap-1 mb-3">
              <Badge v-for="tag in opp.tags.slice(0, 3)" :key="tag" variant="outline" class="text-[8px]">{{ tag }}</Badge>
              <span v-if="opp.tags.length > 3" class="text-[8px] text-muted-foreground">+{{ opp.tags.length - 3 }}</span>
              <span v-if="!opp.tags.length" class="text-muted-foreground text-[8px]">—</span>
            </div>

            <div v-if="opp.description" class="text-[9px] text-muted-foreground mb-3 line-clamp-2">{{ opp.description }}</div>

            <div class="flex items-center justify-between pt-2 border-t border-border/30 mt-auto">
              <span class="text-[9px] text-muted-foreground uppercase">{{ opp.cycle }}</span>
              <div class="flex items-center gap-2">
                <span class="text-[9px] font-bold tabular-nums text-primary">{{ opp.score }}%</span>
                <Button variant="ghost" size="sm" class="p-1" @click.stop="openOpportunity(opp.url)" :disabled="opp.url === '#'">
                  <ExternalLink class="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <!-- Table View -->
      <div v-else class="glass-fintech rounded-xl overflow-hidden animate-in">
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-border/30 bg-surface/20">
                <th class="text-left px-4 py-3 font-semibold text-foreground">Oportunidad</th>
                <th class="text-left px-4 py-3 font-semibold text-foreground">Plataforma</th>
                <th class="text-center px-4 py-3 font-semibold text-foreground">Recompensa</th>
                <th class="text-center px-4 py-3 font-semibold text-foreground">Esfuerzo</th>
                <th class="text-center px-4 py-3 font-semibold text-foreground">Confianza</th>
                <th class="text-center px-4 py-3 font-semibold text-foreground">Score</th>
                <th class="text-left px-4 py-3 font-semibold text-foreground">Tags</th>
                <th class="text-center px-4 py-3 font-semibold text-foreground">Acción</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border/20">
              <tr v-for="opp in opportunities" :key="opp.id" class="hover:bg-surface/10 transition-colors">
                <td class="px-4 py-3">
                  <p class="font-semibold text-foreground whitespace-nowrap truncate max-w-xs">{{ opp.title }}</p>
                  <p class="text-[9px] text-muted-foreground">{{ formatDate(opp.postedAt) }}</p>
                </td>
                <td class="px-4 py-3">
                  <Badge variant="outline" class="text-[8px]">{{ opp.platformDisplay }}</Badge>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="font-bold tabular-nums text-warning">{{ formatReward(opp.reward) }}</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <span :class="effortColor(opp.effortHours)" class="px-2 py-0.5 rounded text-[8px] font-mono">{{ effortLabel(opp.effortHours) }} ({{ opp.effortHours }}h)</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="font-bold tabular-nums" :class="confidenceColor(opp.confidence)">{{ opp.confidence }}%</span>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="font-bold tabular-nums text-primary">{{ opp.score }}%</span>
                </td>
                <td class="px-4 py-3">
                  <div class="flex flex-wrap gap-1">
                    <Badge v-for="tag in opp.tags.slice(0, 3)" :key="tag" variant="outline" class="text-[8px]">{{ tag }}</Badge>
                    <span v-if="opp.tags.length > 3" class="text-[8px] text-muted-foreground">+{{ opp.tags.length - 3 }}</span>
                    <span v-if="!opp.tags.length" class="text-muted-foreground text-[8px]">—</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-center">
                  <Button variant="ghost" size="sm" class="p-1" @click.stop="openOpportunity(opp.url)" :disabled="opp.url === '#'">
                    <ExternalLink class="h-3.5 w-3.5" />
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between p-4 border-t border-border/30">
          <p class="text-[10px] text-muted-foreground">
            Mostrando {{ opportunities.length }} de {{ allOpportunities.length }} oportunidades
          </p>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" :disabled="opportunities.length === allOpportunities.length" @click="clearFilters">
              <Filter class="h-3.5 w-3.5" /> Limpiar filtros
            </Button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>