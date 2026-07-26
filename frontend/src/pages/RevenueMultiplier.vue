<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import {
  Zap, Activity, Wrench, BarChart3, Clock, DollarSign,
  TrendingUp, Target, Play, Settings2, AlertTriangle, RefreshCw, Rocket,
} from '@lucide/vue'

const loading = ref(true)
const activating = ref(false)
const error = ref<string | null>(null)

const status = ref<any>(null)
const tools = ref<any>(null)
const metrics = ref<any>(null)
const events = ref<any[]>([])
const config = ref<any>(null)

const activeTab = ref<'overview' | 'tools' | 'metrics' | 'events'>('overview')

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    const [s, t, m, e, c] = await Promise.allSettled([
      api.get('/revenue-multiplier/status'),
      api.get('/revenue-multiplier/tools'),
      api.get('/revenue-multiplier/metrics'),
      api.get('/revenue-multiplier/events'),
      api.get('/revenue-multiplier/config'),
    ])
    if (s.status === 'fulfilled') status.value = s.value
    if (t.status === 'fulfilled') tools.value = t.value
    if (m.status === 'fulfilled') metrics.value = m.value
    if (e.status === 'fulfilled') events.value = e.value?.events ?? []
    if (c.status === 'fulfilled') config.value = c.value
  } catch (e: any) {
    error.value = e?.message || 'Failed to load revenue multiplier data'
  } finally {
    loading.value = false
  }
}

async function activateMaxRevenue() {
  activating.value = true
  try {
    const r = await api.post('/revenue-multiplier/activate', { mode: 'dry_run' })
    alert(`MAX REVENUE MODE complete\nSession: ${r.result?.session_id}\nTargets: ${r.result?.bounty?.targets?.length || 0}`)
    await fetchAll()
  } catch (e: any) {
    alert(`Activation failed: ${e?.message}`)
  } finally {
    activating.value = false
  }
}

const runtimeConfig = computed(() => status.value?.status?.config ?? {})
const isRunning = computed(() => status.value?.status?.running ?? false)
const currentMode = computed(() => status.value?.status?.mode ?? '—')

const toolSummary = computed(() => {
  if (!tools.value) return null
  return {
    total: tools.value.total,
    available: tools.value.available,
    unavailable: tools.value.unavailable,
  }
})

const metricCards = computed(() => {
  if (!metrics.value?.metrics) return []
  const m = metrics.value.metrics
  const bounty = m.bounty || {}
  const trading = m.trading || {}
  const revenue = m.revenue || {}
  return [
    { label: 'Total Findings', value: String(bounty.findings_total || 0), icon: Target, color: 'text-blue-400' },
    { label: 'Top Tool', value: Object.keys(bounty.top_tools || {})[0] || '—', icon: Wrench, color: 'text-cyan-400' },
    { label: 'Trades', value: String(trading.total_trades || 0), icon: TrendingUp, color: 'text-emerald-400' },
    { label: 'Win Rate', value: (trading.win_rate ?? 0) + '%', icon: Activity, color: 'text-violet-400' },
    { label: '24h Revenue', value: '$' + (parseFloat(revenue['24h'] || '0')).toFixed(2), icon: DollarSign, color: 'text-green-400' },
    { label: 'Est. Annual', value: '$' + (parseFloat(revenue.estimated_annual || '0')).toFixed(2), icon: BarChart3, color: 'text-yellow-400' },
  ]
})

onMounted(fetchAll)
</script>

<template>
  <div class="space-y-6 p-6">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Zap class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">REVENUE MULTIPLIER</span>
          <span class="lamp" :class="isRunning ? 'lamp-green' : status ? 'lamp-amber' : 'lamp-off'" />
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Revenue Multiplier</h1>
        <p class="text-xs text-muted-foreground">Bug bounty + crypto trading orquestados — modo maximización de ingresos</p>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <Badge variant="info" class="font-mono text-[10px]">{{ currentMode.toUpperCase() }}</Badge>
        <Button @click="fetchAll" variant="outline" size="sm" :disabled="loading">
          <RefreshCw class="w-3.5 h-3.5 mr-1" :class="{ 'animate-spin': loading }" />
          Refresh
        </Button>
      </div>
    </div>

    <LoadingState v-if="loading && !status" message="Loading revenue multiplier..." />
    <ErrorState v-else-if="error && !status" :message="error" @retry="fetchAll" />
    <template v-else>
      <!-- Quick actions -->
      <div class="flex gap-3">
        <Button @click="activateMaxRevenue" :disabled="activating || isRunning" variant="default" size="lg" class="gap-2">
          <Play class="w-4 h-4" />
          {{ activating ? 'Activating...' : isRunning ? 'Running...' : 'MAX REVENUE MODE' }}
        </Button>
        <Button @click="fetchAll" variant="outline" size="lg" class="gap-2">
          <Settings2 class="w-4 h-4" />
          Refresh Data
        </Button>
      </div>

      <!-- Tool summary -->
      <div v-if="toolSummary" class="grid grid-cols-3 gap-4">
        <div class="tactical-panel rounded-xl p-4 text-center">
          <div class="flex items-center justify-center gap-2 mb-2">
            <Wrench class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">TOTAL TOOLS</span>
          </div>
          <p class="font-mono text-2xl font-bold text-primary">{{ toolSummary.total }}</p>
        </div>
        <div class="tactical-panel rounded-xl p-4 text-center">
          <div class="flex items-center justify-center gap-2 mb-2">
            <CheckCircle2 class="h-4 w-4 text-success" />
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">AVAILABLE</span>
          </div>
          <p class="font-mono text-2xl font-bold text-success">{{ toolSummary.available }}</p>
        </div>
        <div class="tactical-panel rounded-xl p-4 text-center">
          <div class="flex items-center justify-center gap-2 mb-2">
            <XCircle class="h-4 w-4 text-destructive" />
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">UNAVAILABLE</span>
          </div>
          <p class="font-mono text-2xl font-bold text-destructive">{{ toolSummary.unavailable }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 p-1 rounded-lg bg-accent/50 w-fit">
        <button v-for="tab in ([
          { key: 'overview', label: 'Overview', icon: BarChart3 },
          { key: 'tools', label: 'Tools', icon: Wrench },
          { key: 'metrics', label: 'Metrics', icon: Activity },
          { key: 'events', label: 'Events', icon: Clock },
        ] as const)" :key="tab.key"
          @click="activeTab = tab.key"
          class="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
          :class="activeTab === tab.key ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
        >
          <component :is="tab.icon" class="w-3.5 h-3.5" />
          {{ tab.label }}
        </button>
      </div>

      <!-- ── Overview ── -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Card v-for="card in metricCards" :key="card.label" class="card-base">
            <CardContent class="p-4">
              <div class="flex items-center justify-between mb-2">
                <span class="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">{{ card.label }}</span>
                <component :is="card.icon" class="w-3.5 h-3.5" :class="card.color" />
              </div>
              <p class="text-lg font-bold" :class="card.color">{{ card.value }}</p>
            </CardContent>
          </Card>
        </div>

        <!-- Config card -->
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Settings2 class="w-4 h-4" /> Current Config</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <div v-for="(val, key) in runtimeConfig" :key="key" class="p-2 rounded bg-accent/30">
                <p class="text-[10px] text-muted-foreground uppercase tracking-wider">{{ key.replace(/_/g, ' ') }}</p>
                <p class="text-xs font-semibold mt-0.5 font-mono">{{ typeof val === 'object' ? JSON.stringify(val) : String(val) }}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- ── Tools ── -->
      <div v-if="activeTab === 'tools'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Wrench class="w-4 h-4" /> Tool Registry ({{ tools?.total || 0 }})</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="tools?.tools?.length" class="space-y-1">
              <div v-for="t in tools.tools" :key="t.name"
                class="flex items-center justify-between py-2 px-2 rounded hover:bg-accent/30 transition-colors">
                <div class="flex items-center gap-3 min-w-0">
                  <span class="w-2 h-2 rounded-full shrink-0" :class="t.available ? 'bg-green-400' : 'bg-red-400'"></span>
                  <span class="text-sm font-medium truncate">{{ t.name }}</span>
                  <Badge variant="outline" class="text-[9px] font-mono">{{ t.category }}</Badge>
                </div>
                <span class="text-[10px] text-muted-foreground shrink-0 ml-2">{{ t.description }}</span>
              </div>
            </div>
            <EmptyState v-else icon="Wrench" title="No tools registered" description="" class="py-6" />
          </CardContent>
        </Card>
      </div>

      <!-- ── Metrics ── -->
      <div v-if="activeTab === 'metrics'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Target class="w-4 h-4" /> Bounty Metrics</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="metrics?.metrics?.bounty" class="space-y-3">
              <div v-for="(val, key) in metrics.metrics.bounty" :key="key"
                class="flex justify-between py-1.5 border-b border-border/30 last:border-0">
                <span class="text-xs text-muted-foreground">{{ key.replace(/_/g, ' ') }}</span>
                <span class="text-xs font-semibold font-mono">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
              </div>
            </div>
            <EmptyState v-else icon="Target" title="No bounty metrics" description="" class="py-6" />
          </CardContent>
        </Card>
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><TrendingUp class="w-4 h-4" /> Trading Metrics</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="metrics?.metrics?.trading" class="space-y-3">
              <div v-for="(val, key) in metrics.metrics.trading" :key="key"
                class="flex justify-between py-1.5 border-b border-border/30 last:border-0">
                <span class="text-xs text-muted-foreground">{{ key.replace(/_/g, ' ') }}</span>
                <span class="text-xs font-semibold font-mono">{{ val }}</span>
              </div>
            </div>
            <EmptyState v-else icon="TrendingUp" title="No trading metrics" description="" class="py-6" />
          </CardContent>
        </Card>
        <Card class="card-base lg:col-span-2">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><DollarSign class="w-4 h-4" /> Revenue</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="metrics?.metrics?.revenue" class="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div v-for="(val, key) in metrics.metrics.revenue" :key="key"
                class="p-3 rounded-lg bg-accent/30 text-center">
                <p class="text-[10px] text-muted-foreground uppercase">{{ key }}</p>
                <p class="text-sm font-bold font-mono mt-1">${{ (parseFloat(val) || 0).toFixed(2) }}</p>
              </div>
            </div>
            <EmptyState v-else icon="DollarSign" title="No revenue data" description="" class="py-6" />
          </CardContent>
        </Card>
      </div>

      <!-- ── Events ── -->
      <div v-if="activeTab === 'events'">
        <Card class="card-base">
          <CardHeader>
            <CardTitle><div class="flex items-center gap-2"><Clock class="w-4 h-4" /> Revenue Events ({{ events.length }})</div></CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="events.length" class="space-y-2">
              <div v-for="(ev, i) in events" :key="i"
                class="flex items-start gap-3 p-2 rounded hover:bg-accent/30 transition-colors">
                <div class="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  :class="ev.category === 'bug_bounty' ? 'bg-blue-400' : ev.category === 'crypto_trading' ? 'bg-green-400' : 'bg-yellow-400'">
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-medium truncate">{{ ev.description }}</p>
                  <div class="flex gap-2 mt-0.5">
                    <Badge variant="outline" class="text-[9px]">{{ ev.category }}</Badge>
                    <span class="text-[10px] text-muted-foreground font-mono">{{ ev.source }}</span>
                  </div>
                </div>
                <span class="text-[10px] text-muted-foreground shrink-0 font-mono">{{ new Date(ev.timestamp).toLocaleString() }}</span>
              </div>
            </div>
            <EmptyState v-else icon="Clock" title="No events yet" description="Events appear when MAX REVENUE MODE is activated." class="py-6" />
          </CardContent>
        </Card>
      </div>

      <!-- ═══ HOW-TO FOOTER ═══ -->
      <div class="border border-border/30 rounded-xl p-4 card-base">
        <div class="flex items-center gap-2 mb-3">
          <Rocket class="h-4 w-4 text-primary" />
          <h3 class="text-sm font-semibold">Cómo usar Revenue Multiplier</h3>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
              Activá modo máximo
            </p>
            <p class="text-muted-foreground leading-relaxed">
              El botón "MAX REVENUE MODE" orquesta todas las herramientas disponibles para maximizar ingresos en bug bounty y crypto trading.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
              Monitoreá herramientas
            </p>
            <p class="text-muted-foreground leading-relaxed">
              La pestaña "Tools" muestra qué herramientas están disponibles y cuáles necesitan configuración. Cada una tiene un status indicator.
            </p>
          </div>
          <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
            <p class="font-semibold text-foreground flex items-center gap-1.5">
              <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">3</span>
              Revisá métricas
            </p>
            <p class="text-muted-foreground leading-relaxed">
              Las pestañas "Metrics" y "Events" muestran el impacto real de las operaciones: bounties generados, trades ejecutados, y eventos del sistema.
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
