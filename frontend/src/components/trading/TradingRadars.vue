<script setup lang="ts">
/**
 * TradingRadars — pump.fun, dip y spread CEX/DEX desde el panel.
 *
 * Estos tres radares YA EXISTÍAN en el backend y llamaban APIs reales
 * (DexScreener, RugCheck, Binance, Jupiter — todas keyless) con jobs de
 * scheduler cada 3-7 minutos. Lo que no existía era el consumidor: 9
 * endpoints de trading con 0 renders en el frontend, o sea que el radar
 * corría solo y nadie veía el resultado.
 *
 * Honestidad (regla del proyecto):
 * - `passed_filters: false` se muestra explícito, no se esconde. Un candidato
 *   que no pasó los filtros duros NO es una oportunidad.
 * - `count: 0` se distingue de "no escaneado": el backend devuelve `success`
 *   y `scanned_at`, así que 0 con success=true significa "escaneó y no
 *   encontró", que es información real.
 * - Error de red se dice; nunca se muestra tabla vacía como si fuera limpio.
 * - Ningún botón ejecuta fondos. `/pump/execute` y `/activate` requieren
 *   Human Gate server-side; este panel es sólo lectura.
 */
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Ban, CheckCircle2, RefreshCw } from '@lucide/vue'
import { api } from '@/lib/api'

type Radar = 'pump' | 'dip' | 'spread'

type Candidate = {
  mint?: string
  symbol?: string
  name?: string
  pair?: string
  price_usd?: number
  entry_price?: number
  price_change_h24?: number
  spread_pct?: number
  spread_net_pct?: number
  volume_h24?: number
  liquidity_usd?: number
  dex?: string
  url?: string
  pump_score?: number
  reasons?: string[]
  warnings?: string[]
  passed_filters?: boolean
}

type RadarResponse = {
  success?: boolean
  count?: number
  candidates?: Candidate[]
  opportunities?: Candidate[]
  scanned_at?: number
  error?: string
}

const active = ref<Radar>('pump')
const data = ref<RadarResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const lastScan = ref<number | null>(null)

const TABS: Array<{ id: Radar; label: string; hint: string }> = [
  { id: 'pump', label: 'Pump', hint: 'memes con volumen en Solana · DexScreener + RugCheck' },
  { id: 'dip', label: 'Dip', hint: 'mean-reversion tras caída · cada 7 min' },
  { id: 'spread', label: 'Spread', hint: 'desvío CEX↔DEX · Binance vs Jupiter · cada 3 min' },
]

function rows(): Candidate[] {
  const d = data.value
  if (!d) return []
  return (d.candidates ?? d.opportunities ?? []) as Candidate[]
}

const passedCount = computed(() => rows().filter((c) => c.passed_filters === true).length)
/** Candidatos que pasaron los filtros duros: los únicos accionables. */
const actionable = computed(() => rows().filter((c) => c.passed_filters === true))

function fmtUsd(v: number | undefined | null): string {
  if (v === undefined || v === null) return '—'
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}k`
  return `$${v.toFixed(4)}`
}

function fmtPct(v: number | undefined | null): string {
  if (v === undefined || v === null) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`
}

function fmtAge(ts: number | undefined): string {
  if (!ts) return 'sin timestamp'
  const s = Math.max(0, Math.round(Date.now() / 1000 - ts))
  if (s < 60) return `hace ${s}s`
  if (s < 3600) return `hace ${Math.round(s / 60)}min`
  return `hace ${Math.round(s / 3600)}h`
}

function title(c: Candidate): string {
  return c.symbol || c.pair || c.mint?.slice(0, 6) || '(sin símbolo)'
}

function sub(c: Candidate): string {
  const bits = [c.name, c.dex].filter(Boolean)
  return bits.join(' · ') || '—'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await api.get<RadarResponse>(`/trading/${active.value}/radar`)
    lastScan.value = data.value?.scanned_at ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'no se pudo consultar'
    data.value = null
    lastScan.value = null
  } finally {
    loading.value = false
  }
}

function select(r: Radar) {
  if (active.value === r) return
  active.value = r
  load()
}

onMounted(load)
</script>

<template>
  <section class="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
    <header class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-[var(--color-border)]">
      <div>
        <h2 class="text-[var(--text-heading)] font-[var(--font-weight-semibold)]">Radares de mercado</h2>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          <template v-if="loading">consultando…</template>
          <template v-else-if="lastScan">último escaneo {{ fmtAge(lastScan) }}</template>
          <template v-else>sin datos</template>
          <template v-if="data && rows().length > 0">
            · {{ rows().length }} candidatos
            <template v-if="actionable.length > 0"> · {{ actionable.length }} pasaron filtros</template>
            <template v-else> · ninguno pasó los filtros duros</template>
          </template>
        </p>
      </div>
      <button
        class="flex items-center gap-1 text-[var(--text-label)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
        :disabled="loading"
        aria-label="Refrescar radar"
        @click="load"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        refrescar
      </button>
    </header>

    <!-- Tabs -->
    <div class="flex gap-1 px-4 pt-3" role="tablist" aria-label="Radar">
      <button
        v-for="t in TABS"
        :key="t.id"
        role="tab"
        :aria-selected="active === t.id"
        class="rounded-[var(--radius-md)] px-3 py-1.5 text-[var(--text-label)]"
        :class="
          active === t.id
            ? 'bg-[var(--color-primary)] text-[var(--color-primary-foreground)] font-[var(--font-weight-semibold)]'
            : 'border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
        "
        @click="select(t.id)"
      >
        {{ t.label }}
      </button>
    </div>
    <p class="px-4 pt-1 pb-2 text-[var(--text-caption)] text-[var(--color-text-muted)]">
      {{ TABS.find((t) => t.id === active)?.hint }}
    </p>

    <!-- Estados honestos -->
    <p v-if="error" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-sys-blocked)]">
      No se pudo consultar el radar: {{ error }}
    </p>

    <p
      v-else-if="!loading && data && rows().length === 0"
      class="px-4 py-6 text-[var(--text-body)] text-[var(--color-text-muted)]"
    >
      Escaneó y no encontró candidatos con estos filtros. Bajá los umbrales de liquidez o volumen en la API si
      esperabas alguno.
    </p>

    <p v-else-if="!loading && !data" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-text-muted)]">
      Sin datos del radar.
    </p>

    <table v-else class="w-full text-[var(--text-label)]">
      <thead>
        <tr class="text-[var(--color-text-muted)] border-t border-[var(--color-border)]">
          <th class="text-left font-normal px-4 py-2">token</th>
          <th class="text-right font-normal px-2 py-2">precio</th>
          <th v-if="active === 'spread'" class="text-right font-normal px-2 py-2">spread</th>
          <th v-else class="text-right font-normal px-2 py-2">24h</th>
          <th class="text-right font-normal px-2 py-2">liquidez</th>
          <th class="text-left font-normal px-4 py-2">filtros</th>
        </tr>
      </thead>
      <tbody class="font-[var(--font-numeric)] tabular-nums">
        <tr
          v-for="(c, i) in rows()"
          :key="c.mint || c.pair || i"
          class="border-t border-[var(--color-border)]"
        >
          <td class="px-4 py-2">
            <span class="text-[var(--color-text)]">{{ title(c) }}</span>
            <span class="block text-[var(--text-caption)] text-[var(--color-text-muted)]">{{ sub(c) }}</span>
          </td>
          <td class="px-2 py-2 text-right text-[var(--color-text)]">{{ fmtUsd(c.price_usd ?? c.entry_price) }}</td>
          <td
            v-if="active === 'spread'"
            class="px-2 py-2 text-right"
            :class="(c.spread_net_pct ?? 0) > 0 ? 'text-[var(--color-sys-healthy)]' : 'text-[var(--color-text-muted)]'"
          >
            {{ fmtPct(c.spread_net_pct ?? c.spread_pct) }}
          </td>
          <td
            v-else
            class="px-2 py-2 text-right"
            :class="(c.price_change_h24 ?? 0) > 0 ? 'text-[var(--color-sys-healthy)]' : 'text-[var(--color-sys-blocked)]'"
          >
            {{ fmtPct(c.price_change_h24) }}
          </td>
          <td class="px-2 py-2 text-right text-[var(--color-text-muted)]">{{ fmtUsd(c.liquidity_usd) }}</td>
          <td class="px-4 py-2">
            <span
              v-if="c.passed_filters === true"
              class="inline-flex items-center gap-1 text-[var(--color-sys-healthy)]"
            >
              <CheckCircle2 :size="12" />
              pasó filtros
            </span>
            <span v-else class="inline-flex items-start gap-1 text-[var(--color-sys-degraded)]">
              <Ban :size="12" class="mt-0.5 shrink-0" />
              <span>
                no apto
                <span v-if="c.reasons?.length" class="block text-[var(--text-caption)] text-[var(--color-text-muted)]">
                  {{ c.reasons.slice(0, 2).join(' · ') }}
                </span>
              </span>
            </span>
            <span
              v-if="c.warnings?.length"
              class="mt-0.5 flex items-start gap-1 text-[var(--text-caption)] text-[var(--color-sys-degraded)]"
            >
              <AlertTriangle :size="11" class="mt-0.5 shrink-0" />
              {{ c.warnings.slice(0, 1).join(' · ') }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>

    <p class="px-4 py-3 border-t border-[var(--color-border)] text-[var(--text-caption)] text-[var(--color-text-muted)]">
      Sólo lectura. Ninguna ejecución de fondos desde acá: <code>/pump/execute</code> y
      <code>/activate</code> exigen Human Gate y kill switch en el servidor.
    </p>
  </section>
</template>
