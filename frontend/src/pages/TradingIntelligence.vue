<script setup lang="ts">
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Copy,
  Dna,
  ExternalLink,
  RefreshCw,
  Shield,
  Sparkles,
  TrendingUp,
  XCircle,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'

const TAB_COPY = 'copy'
const TAB_INTEL = 'intel'
const TAB_REASON = 'reason'

type RiskData = {
  max_position_pct?: number
  max_daily_dd_pct?: number
  max_total_dd_pct?: number
  max_open_positions?: number
  allowed_symbols?: string[]
  stop_loss_pct?: number
}

type Master = {
  master_id: string
  name: string
  source: string
  exchange: string
  copy_ratio: number
  max_position_pct: number
  allowed_symbols: string[]
  risk: RiskData
  enabled: boolean
}

type CopyStatus = {
  mode?: string
  emergency_stop?: boolean
  equity_usd?: number
  open_positions?: Record<string, unknown>
  total_pnl_usd?: number
  last_check_at?: string
  [key: string]: unknown
}

type Candidate = {
  trader_id?: string
  name?: string
  source?: string
  score?: number
  tier?: string
  [key: string]: unknown
}

type Alert = {
  severity?: string
  message?: string
  [key: string]: unknown
}

type DnaEntry = {
  edge_id?: string
  antecedent?: string
  consequent?: string
  confidence?: number
  occurrences?: number
  [key: string]: unknown
}

type Proposal = {
  id?: string
  param?: string
  current?: unknown
  suggested?: unknown
  status?: string
  reason?: string
  [key: string]: unknown
}

type Summary = {
  copy: CopyStatus
  masters: Master[]
  intelligence: { discovery: Candidate[]; alerts: Alert[] }
  reasoning: { dna: DnaEntry[]; proposals: Proposal[] }
  generated_at?: string
}

const activeTab = ref(TAB_COPY)
const loading = ref(true)
const error = ref('')
const summary = ref<Summary | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<{ success: boolean; data: Summary }>('/trading/dashboard/summary')
    summary.value = res.data
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar el panel'
  } finally {
    loading.value = false
  }
}

const copyStatus = computed(() => summary.value?.copy ?? {})
const masters = computed(() => summary.value?.masters ?? [])
const candidates = computed(() => summary.value?.intelligence.discovery ?? [])
const alerts = computed(() => summary.value?.intelligence.alerts ?? [])
const dna = computed(() => summary.value?.reasoning.dna ?? [])
const proposals = computed(() => summary.value?.reasoning.proposals ?? [])

const formatMoney = (v?: number) =>
  v === undefined ? '—' : `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })}`
const tierColor = (tier?: string) => {
  switch (tier) {
    case 'ELITE':
      return 'text-success'
    case 'STRONG':
      return 'text-primary'
    case 'AVOID':
      return 'text-warning'
    default:
      return 'text-muted-foreground'
  }
}
const severityColor = (s?: string) => {
  switch (s) {
    case 'CRITICAL':
    case 'danger':
      return 'text-warning'
    case 'warning':
      return 'text-warning'
    default:
      return 'text-muted-foreground'
  }
}

const toggleMaster = async (m: Master) => {
  await api.post<{ success: boolean }>(`/trading/copy/masters/${m.master_id}/toggle`)
  await refresh()
}

const approveProposal = async (id: string) => {
  await api.post<{ success: boolean }>(`/trading/reasoning/approve/${id}`)
  await refresh()
}

const rejectProposal = async (id: string) => {
  await api.post<{ success: boolean }>(`/trading/reasoning/reject/${id}`)
  await refresh()
}

onMounted(refresh)
</script>

<template>
  <div class="mx-auto max-w-6xl px-4 py-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-white">Copy Trading</h1>
        <p class="text-sm text-muted-foreground">
          Replica traders verificados en paper trading y razona la lógica ganadora
        </p>
      </div>
      <Button variant="outline" size="sm" @click="refresh">
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
      </Button>
    </div>

    <div class="mb-6 flex gap-2 border-b border-white/10">
      <button
        v-for="tab in [
          { id: TAB_COPY, label: 'Copy Trading', icon: Copy },
          { id: TAB_INTEL, label: 'Inteligencia', icon: BarChart3 },
          { id: TAB_REASON, label: 'Razonamiento OWNEX', icon: Dna },
        ]"
        :key="tab.id"
        class="flex items-center gap-2 border-b-2 px-4 py-2 text-sm transition-colors"
        :class="activeTab === tab.id ? 'border-white text-white' : 'border-transparent text-muted-foreground hover:text-white'"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" class="h-4 w-4" />
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="py-12">
      <LoadingState text="Cargando panel de trading…" />
    </div>

    <div v-else-if="error" class="py-12">
      <ErrorState :title="'No se pudo cargar el panel'" :message="error" />
    </div>

    <template v-else>
      <!-- ═══ TAB COPY ═══ -->
      <div v-if="activeTab === TAB_COPY">
        <div class="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
              <Activity class="h-3 w-3" /> Modo
            </div>
            <p class="mt-1 text-xl font-semibold text-white">{{ copyStatus.mode ?? '—' }}</p>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
              <Shield class="h-3 w-3" /> Equity paper
            </div>
            <p class="mt-1 text-xl font-semibold text-white">{{ formatMoney(copyStatus.equity_usd) }}</p>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
              <TrendingUp class="h-3 w-3" /> PnL
            </div>
            <p class="mt-1 text-xl font-semibold text-white">{{ formatMoney(copyStatus.total_pnl_usd) }}</p>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
              <Zap class="h-3 w-3" /> Posiciones
            </div>
            <p class="mt-1 text-xl font-semibold text-white">
              {{ Object.keys(copyStatus.open_positions ?? {}).length }}
            </p>
          </Card>
        </div>

        <Card class="p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-medium text-white">Traders seguidos</h2>
            <Badge v-if="masters.length" variant="outline">{{ masters.length }}</Badge>
          </div>
          <EmptyState
            v-if="!masters.length"
            title="Sin traders seguidos"
            description="Agregá un trader vía la API POST /api/trading/copy/masters"
          />
          <div v-else class="space-y-2">
            <div
              v-for="m in masters"
              :key="m.master_id"
              class="flex items-center justify-between rounded-lg border border-white/10 px-4 py-3"
            >
              <div class="flex items-center gap-3">
                <div>
                  <p class="font-medium text-white">{{ m.name }}</p>
                  <p class="text-xs text-muted-foreground">
                    {{ m.source }} · {{ m.exchange }} · ratio {{ m.copy_ratio }} · máx
                    {{ m.max_position_pct }}%
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <Badge
                  :variant="m.enabled ? 'default' : 'outline'"
                  class="text-xs"
                >
                  {{ m.enabled ? 'ACTIVO' : 'PAUSADO' }}
                </Badge>
                <Button variant="outline" size="sm" @click="toggleMaster(m)">
                  {{ m.enabled ? 'Pausar' : 'Activar' }}
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- ═══ TAB INTEL ═══ -->
      <div v-if="activeTab === TAB_INTEL" class="space-y-4">
        <Card class="p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-medium text-white">Candidatos descubiertos</h2>
            <Badge v-if="candidates.length" variant="outline">{{ candidates.length }}</Badge>
          </div>
          <EmptyState
            v-if="!candidates.length"
            title="Sin candidatos"
            description="El job de discovery (06:30) llena esta lista; probá POST /api/trading/intelligence/discover"
          />
          <div v-else class="space-y-2">
            <div
              v-for="c in candidates"
              :key="String(c.trader_id ?? c.name ?? '')"
              class="flex items-center justify-between rounded-lg border border-white/10 px-4 py-3"
            >
              <div>
                <p class="font-medium text-white">{{ c.name ?? '—' }}</p>
                <p class="text-xs text-muted-foreground">{{ String(c.source ?? '') }}</p>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-sm font-semibold" :class="tierColor(c.tier)">
                  {{ Number(c.score ?? 0).toFixed(1) }}
                </span>
                <Badge :variant="c.tier === 'AVOID' ? 'destructive' : 'default'" class="text-xs">
                  {{ c.tier ?? '—' }}
                </Badge>
              </div>
            </div>
          </div>
        </Card>

        <Card class="p-4">
          <div class="mb-3 flex items-center gap-2">
            <AlertTriangle class="h-4 w-4 text-warning" />
            <h2 class="text-sm font-medium text-white">Alertas de monitoreo</h2>
          </div>
          <EmptyState v-if="!alerts.length" title="Sin alertas" description="El monitor no detectó anomalías" />
          <div v-else class="space-y-2">
            <div
              v-for="(a, i) in alerts"
              :key="i"
              class="flex items-start gap-2 rounded-lg border border-white/10 px-4 py-2 text-sm"
            >
              <span class="mt-0.5" :class="severityColor(a.severity)">
                {{ a.severity === 'CRITICAL' ? '●' : '○' }}
              </span>
              <span class="text-muted-foreground">{{ a.message ?? JSON.stringify(a) }}</span>
            </div>
          </div>
        </Card>
      </div>

      <!-- ═══ TAB REASON ═══ -->
      <div v-if="activeTab === TAB_REASON" class="space-y-4">
        <Card class="p-4">
          <div class="mb-3 flex items-center gap-2">
            <Dna class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-medium text-white">Strategy DNA — reglas que ganan</h2>
          </div>
          <EmptyState
            v-if="!dna.length"
            title="DNA vacío"
            description="Corré POST /api/trading/reasoning/correlate para extraer reglas del decision journal"
          />
          <div v-else class="space-y-2">
            <div
              v-for="e in dna"
              :key="String(e.edge_id ?? '')"
              class="rounded-lg border border-white/10 px-4 py-2 text-sm"
            >
              <p class="text-muted-foreground">
                <span class="text-white">{{ e.antecedent ?? '—' }}</span>
                <span class="mx-1 text-primary">→</span>
                <span class="text-white">{{ e.consequent ?? '—' }}</span>
              </p>
              <p class="mt-1 text-xs text-muted-foreground">
                confianza {{ Number(e.confidence ?? 0).toFixed(2) }} · {{ e.occurrences ?? 0 }} ocurrencias
              </p>
            </div>
          </div>
        </Card>

        <Card class="p-4">
          <div class="mb-3 flex items-center gap-2">
            <Sparkles class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-medium text-white">Propuestas de auto-optimización</h2>
          </div>
          <EmptyState
            v-if="!proposals.length"
            title="Sin propuestas"
            description="Se generan al correlacionar el journal con trades perdedores"
          />
          <div v-else class="space-y-2">
            <div
              v-for="p in proposals"
              :key="String(p.id ?? '')"
              class="flex items-center justify-between rounded-lg border border-white/10 px-4 py-3"
            >
              <div class="text-sm">
                <p class="text-white">
                  {{ p.param ?? '—' }}: {{ String(p.current ?? '') }} → {{ String(p.suggested ?? '') }}
                </p>
                <p class="text-xs text-muted-foreground">{{ String(p.reason ?? '') }}</p>
              </div>
              <div class="flex items-center gap-2">
                <Badge v-if="p.status === 'pending'" variant="outline">pendiente</Badge>
                <Button v-if="p.status === 'pending'" variant="outline" size="sm" @click="approveProposal(String(p.id))">
                  <CheckCircle2 class="h-3 w-3" /> Aprobar
                </Button>
                <Button v-if="p.status === 'pending'" variant="ghost" size="sm" @click="rejectProposal(String(p.id))">
                  <XCircle class="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </template>

    <p v-if="summary?.generated_at" class="mt-6 text-right text-xs text-muted-foreground">
      actualizado {{ summary.generated_at }}
    </p>
  </div>
</template>