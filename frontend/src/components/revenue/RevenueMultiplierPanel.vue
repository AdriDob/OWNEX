<script setup lang="ts">
/**
 * RevenueMultiplier — el apartado de multiplicación de ingresos, en el panel.
 *
 * Los 8 endpoints de `/api/revenue-multiplier` tenían 0 consumidores en el
 * frontend: el módulo corría y nadie veía sus números. Este panel los expone.
 *
 * Honestidad (regla dura del proyecto: UNKNOWN nunca como cifra):
 * - Los 0 del revenue significan "no medido" hasta que se registre algo real.
 *   El panel NO los muestra como "$0 ganado" ni proyecta nada.
 * - `win_rate` se muestra como "—" cuando no hay trades decididos (es
 *   `0.0` en el payload pero no es 0% real: es "sin datos para calcularlo").
 * - `available: 13/62` se muestra tal cual: 49 herramientas del catálogo no
 *   están instaladas. No se disimula.
 * - El modo `live` se muestra con aviso: aunque hoy el server exige Human
 *   Gate, el panel deja claro que existe y qué bloquea.
 */
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Ban, CheckCircle2, RefreshCw, Zap } from '@lucide/vue'
import { api } from '@/lib/api'

type ToolSummary = { total?: number; available?: number; not_found?: number; error?: number }

type TradingMetrics = { total_trades?: number; win_rate?: number; total_pnl?: string }
type RevenueMetrics = {
  '24h'?: string
  '7d'?: string
  '30d'?: string
  total?: string
  estimated_annual?: string
}
type BountyMetrics = {
  targets_scanned?: number
  findings_total?: number
  findings_by_severity?: Record<string, number>
  avg_cvss?: number
  top_tools?: Record<string, number>
}

type Status = {
  running?: boolean
  session?: string
  mode?: string
  tool_summary?: ToolSummary
  metrics?: { bounty?: BountyMetrics; trading?: TradingMetrics; revenue?: RevenueMetrics }
  config?: { max_concurrent_tools?: number; max_concurrent_trades?: number; auto_report?: boolean; auto_trade?: boolean }
}

type RmTool = {
  name?: string
  category?: string
  binary?: string
  pip_package?: string
  installed?: boolean
  requires_api_key?: boolean
}

const status = ref<Status | null>(null)
const tools = ref<RmTool[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const mode = computed(() => (status.value?.mode ?? 'unknown').toLowerCase())
const trading = computed(() => status.value?.metrics?.trading ?? {})
const revenue = computed(() => status.value?.metrics?.revenue ?? {})
const bounty = computed(() => status.value?.metrics?.bounty ?? {})
const toolsSummary = computed(() => status.value?.tool_summary ?? {})

/** El win_rate del payload es 0.0 también cuando no hay datos. Lo tratamos como
 *  "—" si no hay trades decididos, para no pintar 0% como si fuera un dato. */
const winRateLabel = computed(() => {
  const t = trading.value.total_trades ?? 0
  const wr = trading.value.win_rate
  if (!t) return '—'
  if (wr === undefined || wr === null) return '—'
  return `${wr.toFixed(1)}%`
})

/** Revenue 0 con 0 trades y 0 findings = sin medir, no $0 real. */
const hasAnyActivity = computed(
  () => (trading.value.total_trades ?? 0) > 0 || (bounty.value.findings_total ?? 0) > 0 || (status.value?.running ?? false),
)

function fmtUsd(v: string | number | undefined): string {
  if (v === undefined || v === null) return '—'
  const n = typeof v === 'string' ? Number(v) : v
  if (!Number.isFinite(n)) return '—'
  if (n === 0) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}k`
  return `$${n.toFixed(2)}`
}

function modeLabel(m: string): string {
  if (m === 'live') return 'LIVE — mueve fondos reales'
  if (m === 'paper') return 'paper'
  if (m === 'dry_run') return 'dry run (simula, no mueve fondos)'
  return m
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [s, t] = await Promise.allSettled([
      api.get<Status>('/revenue-multiplier/status'),
      api.get<{ tools?: RmTool[] }>('/revenue-multiplier/tools'),
    ])
    if (s.status === 'fulfilled') status.value = s.value
    else error.value = 'status'
    if (t.status === 'fulfilled') tools.value = t.value.tools ?? []
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'no se pudo consultar'
    status.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
    <header class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-[var(--color-border)]">
      <div>
        <h2 class="flex items-center gap-2 text-[var(--text-heading)] font-[var(--font-weight-semibold)]">
          <Zap :size="16" />
          Multiplicador de ingresos
        </h2>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          <template v-if="loading">consultando…</template>
          <template v-else-if="status">
            modo <span :class="mode === 'live' ? 'text-[var(--color-sys-blocked)]' : 'text-[var(--color-text-muted)]'">{{ modeLabel(mode) }}</span>
            · {{ status.running ? 'corriendo' : 'inactivo' }}
            · {{ toolsSummary.available ?? 0 }}/{{ toolsSummary.total ?? 0 }} herramientas instaladas
          </template>
          <template v-else>sin datos</template>
        </p>
      </div>
      <button
        class="flex items-center gap-1 text-[var(--text-label)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
        :disabled="loading"
        aria-label="Refrescar"
        @click="load"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        refrescar
      </button>
    </header>

    <p v-if="error" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-sys-blocked)]">
      No se pudo consultar el multiplicador ({{ error }}).
    </p>

    <p v-else-if="!loading && !status" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-text-muted)]">
      Sin estado del multiplicador.
    </p>

    <div v-else class="p-4 grid gap-4 md:grid-cols-3">
      <!-- Bounty -->
      <div class="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">
        <h3 class="text-[var(--text-label)] text-[var(--color-text-muted)] uppercase tracking-wide">Bug bounty</h3>
        <p class="mt-1 font-[var(--font-numeric)] tabular-nums text-[var(--text-heading)] text-[var(--color-text)]">
          {{ bounty.findings_total ?? 0 }} <span class="text-[var(--text-caption)] text-[var(--color-text-muted)]">hallazgos</span>
        </p>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          {{ bounty.targets_scanned ?? 0 }} targets escaneados
          <template v-if="bounty.avg_cvss"> · CVSS medio {{ bounty.avg_cvss.toFixed(1) }}</template>
        </p>
      </div>

      <!-- Trading -->
      <div class="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">
        <h3 class="text-[var(--text-label)] text-[var(--color-text-muted)] uppercase tracking-wide">Trading</h3>
        <p class="mt-1 font-[var(--font-numeric)] tabular-nums text-[var(--text-heading)] text-[var(--color-text)]">
          {{ trading.total_trades ?? 0 }} <span class="text-[var(--text-caption)] text-[var(--color-text-muted)]">trades</span>
        </p>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          win rate {{ winRateLabel }} · PnL {{ fmtUsd(trading.total_pnl) }}
        </p>
      </div>

      <!-- Revenue -->
      <div class="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">
        <h3 class="text-[var(--text-label)] text-[var(--color-text-muted)] uppercase tracking-wide">Revenue</h3>
        <p class="mt-1 font-[var(--font-numeric)] tabular-nums text-[var(--text-heading)] text-[var(--color-text)]">
          {{ fmtUsd(revenue.total) }}
        </p>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          24h {{ fmtUsd(revenue['24h']) }} · 30d {{ fmtUsd(revenue['30d']) }}
        </p>
        <p
          v-if="!hasAnyActivity"
          class="mt-1 text-[var(--text-caption)] text-[var(--color-sys-degraded)]"
        >
          <AlertTriangle :size="11" class="inline" /> sin actividad registrada todavía — estos 0 son "sin medir", no $0 real
        </p>
      </div>
    </div>

    <!-- Aviso live -->
    <p
      v-if="mode === 'live'"
      class="mx-4 mb-4 flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-sys-blocked)] p-3 text-[var(--text-label)] text-[var(--color-sys-blocked)]"
    >
      <Ban :size="14" class="mt-0.5 shrink-0" />
      <span>
        Modo LIVE activo. Aunque el panel no ejecuta nada, cada trade real requiere Human Gate
        (<code>approval_token</code>) y el kill switch global debe estar apagado — ambas cosas las
        valida el servidor, no este panel.
      </span>
    </p>

    <!-- Tools -->
    <details v-if="tools.length" class="border-t border-[var(--color-border)]">
      <summary class="cursor-pointer px-4 py-2 text-[var(--text-label)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
        {{ tools.length }} herramientas del catálogo ({{ toolsSummary.available ?? 0 }} instaladas)
      </summary>
      <ul class="max-h-48 overflow-y-auto px-4 pb-3 text-[var(--text-caption)]">
        <li
          v-for="t in tools.slice(0, 60)"
          :key="t.name"
          class="flex items-center gap-2 border-b border-[var(--color-border)] last:border-0 py-1"
        >
          <CheckCircle2 v-if="t.installed" :size="12" class="text-[var(--color-sys-healthy)] shrink-0" />
          <Ban v-else :size="12" class="text-[var(--color-text-muted)] shrink-0" />
          <span class="text-[var(--color-text)]">{{ t.name }}</span>
          <span class="text-[var(--color-text-muted)]">{{ t.category }}</span>
        </li>
      </ul>
    </details>
  </section>
</template>
