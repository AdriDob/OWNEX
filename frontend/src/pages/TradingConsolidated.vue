<script setup lang="ts">
/**
 * Trading — Panel accionable (contrato REAL de /api/trading).
 * Automático (jobs scheduler) + accionable fácil (toggle master, emergency stop,
 * approve/reject propuestas) + config pendiente visible (vía Setup Checklist).
 */
import { ref, computed, onMounted } from 'vue'
import { TrendingUp, Brain, FlaskConical, DollarSign, RefreshCw, ShieldAlert, Play, Pause } from '@lucide/vue'
import { api } from '@/lib/api'
import TradingRadars from '@/components/trading/TradingRadars.vue'
import TradingLivePanel from '@/components/trading/TradingLivePanel.vue'

const loading = ref(true)
const error = ref('')
const overview = ref<any>(null)
const setup = ref<any>(null)
const busy = ref(false)

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [oRes, sRes] = await Promise.allSettled([
      api.get<any>('/trading/overview'),
      api.get<any>('/setup/checklist/status'),
    ])
    if (oRes.status === 'fulfilled') overview.value = oRes.value
    if (sRes.status === 'fulfilled') setup.value = sRes.value
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar trading'
  } finally {
    loading.value = false
  }
}

// ── Config pendiente (banner) ──
// El Setup Checklist expone ~31 pendientes de todo el sistema. Acá solo
// importan los que bloquean el trabajo de esta página: trading en vivo y las
// credenciales de discovery/entrega (github, dev bounty, bug bounty). El resto
// (perfumes, Mercor, etc.) no pertenece a Trading y drowniría el banner.
const TRADING_BLOCKERS = new Set(['trading_live', 'bounty_api_key', 'devbounty_api_key', 'github_token'])

const pendingItems = computed<any[]>(() => {
  const fromOverview = overview.value?.pending_config || []
  const fromChecklist = (setup.value?.pending || []).filter((i: any) => TRADING_BLOCKERS.has(i.id))
  const merged = new Map<string, any>()
  for (const p of [...fromChecklist, ...fromOverview]) merged.set(p.id, p)
  return [...merged.values()].sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99))
})

const pendingCount = computed(() => pendingItems.value.length)

// ── Acciones ──
async function toggleMaster(masterId: string, enabled: boolean) {
  busy.value = true
  try {
    const res = await api.post<any>(`/trading/copy/masters/${masterId}/toggle`)
    if (res?.success) await fetchData()
  } catch (e: any) {
    error.value = e?.message || 'No se pudo cambiar el master'
  } finally {
    busy.value = false
  }
}

async function emergencyStop() {
  busy.value = true
  try {
    await api.post<any>('/trading/copy/emergency-stop', { reason: 'user requested (front)' })
    await fetchData()
  } catch (e: any) {
    error.value = e?.message || 'No se pudo activar el stop'
  } finally {
    busy.value = false
  }
}

async function release() {
  busy.value = true
  try {
    await api.post<any>('/trading/copy/release')
    await fetchData()
  } catch (e: any) {
    error.value = e?.message || 'No se pudo liberar'
  } finally {
    busy.value = false
  }
}

async function approveProposal(id: string, approve: boolean) {
  busy.value = true
  try {
    await api.post<any>(`/trading/reasoning/${approve ? 'approve' : 'reject'}/${id}`)
    await fetchData()
  } catch (e: any) {
    error.value = e?.message || 'No se pudo procesar la propuesta'
  } finally {
    busy.value = false
  }
}

const isLive = computed(() => overview.value?.is_live === true)

const modeBadge = computed(() => {
  const m = overview.value?.mode_label || 'DRY RUN'
  const cls = isLive.value ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/30'
    : overview.value?.mode === 'dry_run' ? 'bg-blue-400/10 text-blue-400 border-blue-400/30'
    : 'bg-amber-400/10 text-amber-400 border-amber-400/30'
  return { m, cls }
})

function fmtMetric(v: any): string {
  if (v === null || v === undefined) return '—'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (Number.isNaN(n)) return '—'
  return n.toFixed(2)
}

function usd(n: any): string {
  const num = typeof n === 'string' ? parseFloat(n) : (n || 0)
  return `$${Number.isFinite(num) ? num.toLocaleString('es-AR') : '0'}`
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <div class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold text-foreground">Trading</h1>
        <span class="rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider" :class="modeBadge.cls">
          {{ modeBadge.m }}
        </span>
        <span v-if="overview?.emergency_stop" class="rounded-full border border-red-400/30 bg-red-400/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-red-400">
          Emergency Stop
        </span>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Refrescar" @click="fetchData"
      >
        <RefreshCw class="h-3 w-3" /> Refresh
      </button>
    </div>

    <p v-if="error" class="mb-4 rounded-lg border border-red-400/20 bg-red-400/5 p-3 text-xs text-red-400">{{ error }}</p>

    <!-- Config pendiente -->
    <div v-if="!loading && pendingCount" class="mb-5 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
      <p class="mb-2 text-xs font-semibold text-amber-300">Config pendiente ({{ pendingCount }})</p>
      <ul class="space-y-1.5 text-xs text-amber-200/80">
        <li v-for="p in pendingItems" :key="p.id">
          <span class="font-medium">{{ p.title }}</span>
          <p class="text-amber-200/60">{{ p.why }} {{ p.how_to }}</p>
        </li>
      </ul>
    </div>

    <div v-if="loading" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div v-for="i in 4" :key="i" class="h-24 animate-pulse rounded-xl bg-surface/30" />
    </div>

    <div v-else-if="overview" class="space-y-5">
      <!-- Estado del sistema -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
          <p class="font-mono text-[10px] uppercase text-muted-foreground">Jobs automáticos</p>
          <p class="mt-1 font-mono text-xl font-bold">{{ overview.jobs?.enabled || 0 }}<span class="text-xs text-muted-foreground">/{{ overview.jobs?.total || 0 }}</span></p>
        </div>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
          <p class="font-mono text-[10px] uppercase text-muted-foreground">Trades paper</p>
          <p class="mt-1 font-mono text-xl font-bold">{{ overview.metrics?.trade_count || 0 }}</p>
          <p class="mt-0.5 text-[10px] text-muted-foreground">verdict: {{ overview.metrics?.verdict || 'NO_DATA' }}</p>
        </div>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
          <p class="font-mono text-[10px] uppercase text-muted-foreground">Win rate</p>
          <p class="mt-1 font-mono text-xl font-bold">{{ overview.metrics?.win_rate ? (overview.metrics.win_rate * 100).toFixed(0) + '%' : '—' }}</p>
          <p class="mt-0.5 text-[10px]" :class="(overview.metrics?.profit_factor || 0) >= 1.2 ? 'text-emerald-400' : 'text-muted-foreground'">
            PF {{ fmtMetric(overview.metrics?.profit_factor) }}
          </p>
        </div>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
          <p class="font-mono text-[10px] uppercase text-muted-foreground">Masters</p>
          <p class="mt-1 font-mono text-xl font-bold">{{ overview.copy?.masters || 0 }}</p>
          <p class="mt-0.5 text-[10px] text-muted-foreground">equity {{ usd(overview.copy?.equity_usd) }}</p>
        </div>
      </div>

      <!-- Masters (accionable) -->
      <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-foreground">Copy Trading</h3>
          <button
            v-if="!overview.emergency_stop"
            class="rounded-lg border border-red-400/30 px-3 py-1 text-xs text-red-400 hover:bg-red-400/10 transition-colors"
            @click="emergencyStop"
          >
            <ShieldAlert class="mr-1 inline h-3 w-3" /> Emergency Stop
          </button>
          <button
            v-else
            class="rounded-lg border border-emerald-400/30 px-3 py-1 text-xs text-emerald-400 hover:bg-emerald-400/10 transition-colors"
            @click="release"
          >
            <Play class="mr-1 inline h-3 w-3" /> Liberar
          </button>
        </div>

        <div v-if="overview.masters?.length" class="space-y-2">
          <div
            v-for="m in overview.masters"
            :key="m.master_id"
            class="flex items-center justify-between rounded-lg border border-border/20 p-3"
          >
            <div>
              <p class="font-mono text-sm font-medium">{{ m.name }}</p>
              <p class="text-[10px] text-muted-foreground">{{ m.master_id }} · {{ m.source }} · ratio {{ (m.copy_ratio || 0) * 100 }}%</p>
            </div>
            <button
              class="flex items-center gap-1.5 rounded-lg border px-3 py-1 text-xs transition-colors"
              :class="m.enabled
                ? 'border-emerald-400/30 text-emerald-400 hover:bg-emerald-400/10'
                : 'border-border/30 text-muted-foreground hover:bg-surface'"
              :disabled="busy"
              @click="toggleMaster(m.master_id, !m.enabled)"
            >
              <Pause v-if="m.enabled" class="h-3 w-3" /> {{ m.enabled ? 'Pausar' : 'Activar' }}
            </button>
          </div>
        </div>
        <p v-else class="py-6 text-center text-sm text-muted-foreground">Sin masters seguidos. El looop papel corre solo; agregá un master vía API para copy.</p>
      </div>

      <!-- Propuestas advisor (Human Gate) -->
      <div v-if="overview.reasoning?.proposals?.length" class="rounded-xl border border-border/30 bg-surface/50 p-5">
        <h3 class="mb-3 text-sm font-semibold text-foreground">Propuestas del Advisor</h3>
        <div class="space-y-2">
          <div
            v-for="p in overview.reasoning.proposals"
            :key="p.proposal_id"
            class="flex items-center justify-between rounded-lg border border-border/20 p-3"
          >
            <div class="text-xs">
              <p class="font-medium text-foreground">{{ p.param }}: {{ p.current_value }} → <span class="text-amber-300">{{ p.proposed_value }}</span></p>
              <p class="text-muted-foreground">{{ p.reason }} · conf {{ p.confidence }}</p>
            </div>
            <div class="flex gap-2">
              <button class="rounded-lg border border-emerald-400/30 px-3 py-1 text-xs text-emerald-400 hover:bg-emerald-400/10" :disabled="busy" @click="approveProposal(p.proposal_id, true)">Aprobar</button>
              <button class="rounded-lg border border-border/30 px-3 py-1 text-xs text-muted-foreground hover:bg-surface" :disabled="busy" @click="approveProposal(p.proposal_id, false)">Rechazar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Radares de mercado: pump.fun, dip, spread CEX/DEX -->
      <TradingRadars />

      <!-- Live trading panel: MT5 + Meme Copy -->
      <TradingLivePanel />
    </div>
  </div>
</template>