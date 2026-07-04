<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import {
  DollarSign, TrendingUp, Wallet, AlertTriangle, Shield, RefreshCw,
  CheckCircle2, Clock, XCircle, ArrowUpRight, Eye, Database,
  ExternalLink, Activity, PieChart, BarChart3,
} from '@lucide/vue'

interface PlatformState {
  verified: number
  pending: number
  withdrawn: number
  estimated: number
  report_count: number
  sync_health: string
  last_sync: string
}

interface CategoryBreakdown {
  amount: number
  confidence: number
  entry_count: number
  last_updated: string
  entries?: any[]
}

interface FinancialState {
  verified_balance: number
  pending_balance: number
  withdrawn_balance: number
  estimated_balance: number
  manual_balance: number
  disputed_balance: number
  total_balance: number
  real_balance: number
  effective_balance: number
  sync_health: string
  last_sync: string
  last_reconciliation: string
  entry_count: number
  by_platform: Record<string, PlatformState>
  by_category: Record<string, CategoryBreakdown>
  summary: Array<{ label: string; amount: number; category: string; confidence: number; detail: string }>
}

interface SyncHealthEntry {
  id: string
  health: string
  last_sync: number
  last_success: number
  consecutive_failures: number
}

interface WithdrawalEntry {
  id: string
  amount: number
  currency: string
  platform: string
  target_account: string
  method: string
  status: string
  confirmation: string
  confidence: number
  created_at: string
  completed_at: string
  fee: number
  net_amount: number
  tx_hash: string
  error: string
}

const router = useRouter()
const loading = ref(true)
const error = ref('')
const refreshing = ref(false)
const activeTab = ref<'overview' | 'platforms' | 'withdrawals' | 'reconciliation'>('overview')

const financialState = ref<FinancialState | null>(null)
const syncHealth = ref<SyncHealthEntry[]>([])
const withdrawals = ref<WithdrawalEntry[]>([])
const reconciliationState = ref<any>(null)
const reconciliationHistory = ref<any[]>([])

const healthColor = (h: string) => {
  const map: Record<string, string> = {
    healthy: 'text-success',
    degraded: 'text-warning',
    stale: 'text-muted-foreground',
    failed: 'text-destructive',
    never_synced: 'text-muted-foreground/50',
  }
  return map[h] || 'text-muted-foreground'
}

const healthIcon = (h: string) => {
  const map: Record<string, any> = {
    healthy: CheckCircle2,
    degraded: AlertTriangle,
    stale: Clock,
    failed: XCircle,
    never_synced: Clock,
  }
  return map[h] || AlertTriangle
}

const categoryColor = (cat: string) => {
  const map: Record<string, string> = {
    verified_real: 'text-success',
    pending: 'text-warning',
    estimated: 'text-muted-foreground/60',
    manual_input: 'text-primary',
    unknown: 'text-destructive/60',
  }
  return map[cat] || 'text-muted-foreground'
}

const categoryLabel = (cat: string) => {
  const labels: Record<string, string> = {
    verified_real: 'VERIFICADO',
    pending: 'PENDIENTE',
    estimated: 'ESTIMADO',
    manual_input: 'MANUAL',
    unknown: 'SIN DATOS',
  }
  return labels[cat] || cat
}

const categoryBg = (cat: string) => {
  const map: Record<string, string> = {
    verified_real: 'bg-success/10 border-success/20',
    pending: 'bg-warning/10 border-warning/20',
    estimated: 'bg-muted/20 border-border/30',
    manual_input: 'bg-primary/10 border-primary/20',
    unknown: 'bg-destructive/10 border-destructive/20',
  }
  return map[cat] || 'bg-muted/10 border-border/20'
}

const sortedCategories = computed(() => {
  if (!financialState.value) return []
  const order = ['verified_real', 'pending', 'withdrawn', 'estimated', 'manual_input', 'unknown']
  return order
    .filter(c => financialState.value!.by_category[c])
    .map(c => ({ key: c, ...financialState.value!.by_category[c] }))
})

const platformList = computed(() => {
  if (!financialState.value) return []
  return Object.entries(financialState.value.by_platform).map(([id, ps]) => ({ id, ...ps }))
})

const totalWidth = computed(() => {
  if (!financialState.value) return 0
  return financialState.value.verified_balance + financialState.value.pending_balance + financialState.value.estimated_balance
})

const barWidth = (amount: number) => {
  const total = totalWidth.value
  if (total === 0) return 0
  return (amount / total) * 100
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [stateRes, healthRes, wdRes, recStateRes, recHistRes] = await Promise.all([
      api.get('/financial/state'),
      api.get('/financial/state/sync-health'),
      api.get('/financial/withdrawals'),
      api.get('/financial/reconciliation/state'),
      api.get('/financial/reconciliation/history'),
    ])
    financialState.value = (stateRes as any).data
    syncHealth.value = (healthRes as any).data?.platforms || []
    withdrawals.value = (wdRes as any).data
    reconciliationState.value = (recStateRes as any).data
    reconciliationHistory.value = (recHistRes as any).data
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar datos financieros'
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  refreshing.value = true
  await loadAll()
  refreshing.value = false
}

function formatMoney(n: number): string {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatTime(ts: string | number): string {
  if (!ts) return '—'
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  return d.toLocaleString('es-AR')
}

onMounted(loadAll)
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <Database class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">FINANCIAL TRUTH</span>
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Financial Truth Layer</h1>
        <p class="text-xs text-muted-foreground">Fuente única de verdad financiera — todo valor tiene categoría y procedencia</p>
      </div>
      <button
        class="inline-flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs font-medium text-foreground/70 hover:text-foreground hover:border-primary/30 transition-colors"
        :disabled="refreshing"
        @click="refreshAll"
      >
        <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': refreshing }" />
        Actualizar
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
      <div class="flex items-center gap-2 text-destructive">
        <AlertTriangle class="h-4 w-4" />
        <span class="font-mono text-xs">{{ error }}</span>
      </div>
    </div>

    <template v-else-if="financialState">
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div class="rounded-xl border border-success/20 bg-success/5 p-3">
          <p class="font-mono text-[9px] text-success uppercase tracking-wider mb-1">Real verificado</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.verified_balance) }}</p>
          <p class="font-mono text-[9px] text-success/70">1.0 confianza</p>
        </div>
        <div class="rounded-xl border border-warning/20 bg-warning/5 p-3">
          <p class="font-mono text-[9px] text-warning uppercase tracking-wider mb-1">Pendiente</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.pending_balance) }}</p>
          <p class="font-mono text-[9px] text-warning/70">~0.85 confianza</p>
        </div>
        <div class="rounded-xl border border-primary/20 bg-primary/5 p-3">
          <p class="font-mono text-[9px] text-primary uppercase tracking-wider mb-1">Retirado</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.withdrawn_balance) }}</p>
          <p class="font-mono text-[9px] text-primary/70">verificado</p>
        </div>
        <div class="rounded-xl border border-border/30 bg-surface/20 p-3">
          <p class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Estimado</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.estimated_balance) }}</p>
          <p class="font-mono text-[9px] text-muted-foreground/70">~0.3 confianza</p>
        </div>
        <div class="rounded-xl border border-border/30 bg-surface/20 p-3">
          <p class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider mb-1">Manual</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.manual_balance) }}</p>
          <p class="font-mono text-[9px] text-muted-foreground/70">~0.6 confianza</p>
        </div>
        <div class="rounded-xl border border-destructive/20 bg-destructive/5 p-3">
          <p class="font-mono text-[9px] text-destructive uppercase tracking-wider mb-1">En disputa</p>
          <p class="font-display text-lg font-bold text-foreground">${{ formatMoney(financialState.disputed_balance) }}</p>
          <p class="font-mono text-[9px] text-destructive/70">requiere revisión</p>
        </div>
      </div>

      <!-- Proportional bar -->
      <div class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
          <span>Distribución proporcional</span>
          <span>Total: ${{ formatMoney(financialState.total_balance) }}</span>
        </div>
        <div class="flex h-4 rounded-full overflow-hidden">
          <div
            v-if="financialState.verified_balance > 0"
            class="bg-success transition-all duration-500"
            :style="{ width: barWidth(financialState.verified_balance) + '%' }"
            :title="'Verificado: $' + formatMoney(financialState.verified_balance)"
          />
          <div
            v-if="financialState.pending_balance > 0"
            class="bg-warning transition-all duration-500"
            :style="{ width: barWidth(financialState.pending_balance) + '%' }"
            :title="'Pendiente: $' + formatMoney(financialState.pending_balance)"
          />
          <div
            v-if="financialState.estimated_balance > 0"
            class="bg-muted-foreground/30 transition-all duration-500"
            :style="{ width: barWidth(financialState.estimated_balance) + '%' }"
            :title="'Estimado: $' + formatMoney(financialState.estimated_balance)"
          />
        </div>
        <div class="flex gap-4 text-[9px] font-mono">
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-sm bg-success" /> Verificado</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-sm bg-warning" /> Pendiente</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-sm bg-muted-foreground/30" /> Estimado</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 border-b border-border/30 pb-1 overflow-x-auto">
        <button
          v-for="tab in [{ id: 'overview' as const, label: 'Resumen', icon: PieChart },
                          { id: 'platforms' as const, label: 'Plataformas', icon: BarChart3 },
                          { id: 'withdrawals' as const, label: 'Retiros', icon: Wallet },
                          { id: 'reconciliation' as const, label: 'Reconciliación', icon: Activity }]"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'flex items-center gap-1.5 px-3 py-2 font-mono text-xs rounded-t-lg transition-all whitespace-nowrap shrink-0',
            activeTab === tab.id
              ? 'bg-primary/10 text-primary border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground',
          ]"
        >
          <component :is="tab.icon" class="h-3.5 w-3.5" />
          {{ tab.label }}
        </button>
      </div>

      <!-- ── OVERVIEW TAB ── -->
      <div v-if="activeTab === 'overview'" class="space-y-4">
        <!-- Summary items -->
        <div class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-3">Resumen financiero</h3>
          <div
            v-for="item in financialState.summary"
            :key="item.label"
            class="flex items-center justify-between rounded-lg border px-3 py-2"
            :class="categoryBg(item.category)"
          >
            <div class="space-y-0.5">
              <p class="font-mono text-xs text-foreground">{{ item.label }}</p>
              <p class="font-mono text-[9px] text-muted-foreground">{{ item.detail }}</p>
            </div>
            <div class="text-right">
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(item.amount) }}</p>
              <p class="font-mono text-[9px]" :class="categoryColor(item.category)">
                {{ categoryLabel(item.category) }} · {{ (item.confidence * 100).toFixed(0) }}% confianza
              </p>
            </div>
          </div>
        </div>

        <!-- Sync health -->
        <div class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-3">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Activity class="h-3.5 w-3.5 text-primary" />
            Salud de sincronización
          </h3>
          <div class="flex items-center gap-3">
            <component :is="healthIcon(financialState.sync_health)" class="h-5 w-5" :class="healthColor(financialState.sync_health)" />
            <div>
              <p class="font-mono text-xs text-foreground capitalize">{{ financialState.sync_health.replace('_', ' ') }}</p>
              <p class="font-mono text-[9px] text-muted-foreground">
                Último sync: {{ formatTime(financialState.last_sync) }}
                · {{ financialState.entry_count }} entradas en ledger
              </p>
            </div>
          </div>
        </div>

        <!-- By category breakdown -->
        <div class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-3">Por categoría</h3>
          <div
            v-for="cat in sortedCategories"
            :key="cat.key"
            class="flex items-center justify-between rounded-lg border px-3 py-2"
            :class="categoryBg(cat.key)"
          >
            <div class="flex items-center gap-2">
              <span class="h-2 w-2 rounded-full" :class="categoryColor(cat.key).replace('text-', 'bg-').replace('/60', '')" />
              <div>
                <p class="font-mono text-xs font-medium text-foreground">{{ categoryLabel(cat.key) }}</p>
                <p class="font-mono text-[9px] text-muted-foreground">{{ cat.entry_count }} entradas</p>
              </div>
            </div>
            <div class="text-right">
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(cat.amount) }}</p>
              <p class="font-mono text-[9px]" :class="categoryColor(cat.key)">{{ (cat.confidence * 100).toFixed(0) }}% confianza</p>
            </div>
          </div>
        </div>

        <!-- Reconciliation -->
        <div v-if="reconciliationState" class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2">
          <h3 class="font-mono text-xs font-semibold text-foreground flex items-center gap-2">
            <Shield class="h-3.5 w-3.5 text-primary" />
            Reconciliación
          </h3>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full"
                :class="reconciliationState.state === 'consistent' ? 'bg-success' : reconciliationState.state === 'conflict' ? 'bg-destructive' : 'bg-warning'"
              />
              <span class="font-mono text-xs text-foreground capitalize">{{ reconciliationState.state }}</span>
            </div>
            <div class="text-right">
              <p class="font-mono text-[9px] text-muted-foreground">{{ reconciliationState.unresolved || 0 }} sin resolver</p>
              <p class="font-mono text-[9px] text-muted-foreground">{{ reconciliationState.total_discrepancies || 0 }} discrepancias totales</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ── PLATFORMS TAB ── -->
      <div v-if="activeTab === 'platforms'" class="space-y-3">
        <div
          v-for="p in platformList"
          :key="p.id"
          class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-3"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <component :is="healthIcon(p.sync_health)" class="h-4 w-4" :class="healthColor(p.sync_health)" />
              <span class="font-mono text-sm font-semibold text-foreground capitalize">{{ p.id }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-mono text-[9px]" :class="healthColor(p.sync_health)">{{ p.sync_health.replace('_', ' ') }}</span>
              <span class="font-mono text-[9px] text-muted-foreground">{{ formatTime(p.last_sync) }}</span>
            </div>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <div>
              <p class="font-mono text-[9px] text-success uppercase">Verificado</p>
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(p.verified) }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] text-warning uppercase">Pendiente</p>
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(p.pending) }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] text-primary uppercase">Retirado</p>
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(p.withdrawn) }}</p>
            </div>
            <div>
              <p class="font-mono text-[9px] text-muted-foreground uppercase">Estimado</p>
              <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(p.estimated) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ── WITHDRAWALS TAB ── -->
      <div v-if="activeTab === 'withdrawals'" class="space-y-4">
        <div v-if="withdrawals.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-8 text-center">
          <Wallet class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
          <p class="font-mono text-xs text-muted-foreground">No hay retiros registrados</p>
        </div>
        <div
          v-for="w in withdrawals"
          :key="w.id"
          class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full"
                :class="w.status === 'completed' ? 'bg-success' : w.status === 'failed' ? 'bg-destructive' : w.status === 'pending' ? 'bg-warning' : 'bg-muted-foreground/50'"
              />
              <span class="font-mono text-xs font-semibold text-foreground capitalize">{{ w.status }}</span>
              <span class="font-mono text-[9px] text-muted-foreground">#{{ w.id.slice(0, 8) }}</span>
            </div>
            <p class="font-mono text-sm font-bold text-foreground">${{ formatMoney(w.amount) }}</p>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] font-mono text-muted-foreground">
            <span>{{ w.platform }} → {{ w.method }}</span>
            <span>{{ w.target_account }}</span>
            <span>{{ w.currency }}</span>
            <span>{{ formatTime(w.created_at) }}</span>
          </div>
          <div v-if="w.tx_hash" class="text-[9px] font-mono text-muted-foreground/60">
            TX: {{ w.tx_hash.slice(0, 32) }}...
          </div>
          <div v-if="w.error" class="text-[9px] font-mono text-destructive/80">
            Error: {{ w.error }}
          </div>
          <div class="flex items-center gap-2 pt-1">
            <span class="px-1.5 py-0.5 rounded text-[8px] font-mono border"
              :class="w.confirmation === 'api_verified' ? 'border-success/30 text-success bg-success/10' :
                      w.confirmation === 'manual_proof' ? 'border-primary/30 text-primary bg-primary/10' :
                      'border-border/30 text-muted-foreground bg-muted/20'">
              {{ w.confirmation.replace('_', ' ') }}
            </span>
            <span class="text-[9px] font-mono text-muted-foreground">{{ (w.confidence * 100).toFixed(0) }}% confianza</span>
          </div>
        </div>
      </div>

      <!-- ── RECONCILIATION TAB ── -->
      <div v-if="activeTab === 'reconciliation'" class="space-y-4">
        <div v-if="reconciliationHistory.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-8 text-center">
          <Shield class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
          <p class="font-mono text-xs text-muted-foreground">No hay reconciliaciones registradas</p>
        </div>
        <div
          v-for="(rec, i) in reconciliationHistory"
          :key="i"
          class="rounded-xl border border-border/30 bg-surface/20 p-4 space-y-2"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full"
                :class="rec.state === 'consistent' ? 'bg-success' : rec.state === 'conflict' ? 'bg-destructive' : 'bg-warning'"
              />
              <span class="font-mono text-xs font-semibold text-foreground capitalize">{{ rec.platform_id }}</span>
            </div>
            <span class="font-mono text-[9px] text-muted-foreground">{{ formatTime(rec.checked_at) }}</span>
          </div>
          <div class="flex gap-3 text-[10px] font-mono">
            <span class="text-success">{{ rec.auto_resolved_count }} auto-resueltas</span>
            <span v-if="rec.requires_user_count > 0" class="text-destructive">{{ rec.requires_user_count }} requieren atención</span>
            <span v-else class="text-muted-foreground">0 pendientes</span>
          </div>
          <div v-for="(d, j) in rec.discrepancies" :key="j" class="rounded-lg border border-border/20 px-3 py-1.5 text-[10px] font-mono">
            <div class="flex items-center justify-between">
              <span :class="d.auto_resolved ? 'text-muted-foreground' : 'text-destructive'">
                {{ d.type.replace('_', ' ') }}
              </span>
              <span v-if="d.auto_resolved" class="text-success">✓ resuelta</span>
              <span v-else class="text-warning">⚠ pendiente</span>
            </div>
            <p class="text-muted-foreground mt-0.5">{{ d.description }}</p>
            <div v-if="d.external_amount || d.ledger_amount" class="flex gap-3 mt-0.5 text-muted-foreground/70">
              <span v-if="d.external_amount">Externo: ${{ d.external_amount }}</span>
              <span v-if="d.ledger_amount">Ledger: ${{ d.ledger_amount }}</span>
            </div>
            <p v-if="d.resolution" class="text-primary/70 mt-0.5">{{ d.resolution }}</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
