<script setup lang="ts">
/**
 * ProviderHealthPanel — estado real por provider de IA (OAR).
 *
 * Renderiza GET /oar/doctor: status por provider, latencia, error rate,
 * ultimo error y circuit breaker. Cierra el hueco de que ese endpoint no
 * tenia ningun consumidor: los datos se descargaban y se descartaban.
 *
 * Honesty (regla del proyecto):
 * - UNKNOWN se renderiza como "desconocido", nunca como OK ni como $0.
 * - `needs_key` solo se afirma cuando el backend dijo `last_error` con
 *   "missing"/"api key"/"base url"; no se infiere del status.
 * - Sin providers: empty state honesto, no "todo bien" por defecto.
 * - Circuit breaker abierto se muestra aunque el status sea healthy.
 */
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Ban, CircleAlert, CircleCheck, CircleHelp, RefreshCw } from '@lucide/vue'
import { api } from '@/lib/api'

type OarHealth = {
  status?: string
  latency_ms?: number
  error_rate?: number
  success_count?: number
  error_count?: number
  last_error?: string | null
  uptime_seconds?: number
}

type OarDoctor = {
  overall?: string
  providers?: { healthy?: string[]; degraded?: string[]; unhealthy?: string[]; total?: number }
  health_details?: Record<string, OarHealth>
  circuit_breakers?: Record<string, boolean>
}

const doctor = ref<OarDoctor | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const STATUS_LABEL: Record<string, string> = {
  healthy: 'ok',
  degraded: 'degradado',
  unhealthy: 'caído',
  auth_failed: 'sin credencial',
  quota_exceeded: 'cuota agotada',
  unknown: 'desconocido',
}

function isNeedsKey(h: OarHealth): boolean {
  const e = (h.last_error ?? '').toLowerCase()
  return e.includes('missing') || e.includes('api key') || e.includes('base url')
}

const rows = computed(() => {
  const details = doctor.value?.health_details ?? {}
  const breakers = doctor.value?.circuit_breakers ?? {}
  return Object.entries(details)
    .map(([id, h]) => ({
      id,
      status: h.status ?? 'unknown',
      label: STATUS_LABEL[h.status ?? 'unknown'] ?? (h.status ?? 'desconocido'),
      latencyMs: h.latency_ms ?? null,
      errorRate: h.error_rate ?? null,
      lastError: h.last_error ?? null,
      needsKey: isNeedsKey(h),
      breakerOpen: breakers[id] === true,
    }))
    .sort((a, b) => {
      const rank = (r: string) => (r === 'healthy' ? 0 : r === 'degraded' ? 1 : r === 'unknown' ? 2 : 3)
      return rank(a.status) - rank(b.status) || a.id.localeCompare(b.id)
    })
})

/** Providers que aportan capacidad real: contactados y sin error. */
const usable = computed(() => rows.value.filter((r) => r.status === 'healthy' && !r.breakerOpen).length)
/** Providers activados pero inertes por falta de credencial. */
const needKey = computed(() => rows.value.filter((r) => r.needsKey))
const breakerOpen = computed(() => rows.value.filter((r) => r.breakerOpen))

function statusClass(status: string): string {
  if (status === 'healthy') return 'text-[var(--color-sys-healthy)]'
  if (status === 'degraded') return 'text-[var(--color-sys-degraded)]'
  if (status === 'unknown') return 'text-[var(--color-text-muted)]'
  return 'text-[var(--color-sys-blocked)]'
}

function fmtLatency(ms: number | null): string {
  if (ms === null) return '—'
  if (ms <= 0) return 'sin contactar'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`
}

function fmtRate(rate: number | null): string {
  if (rate === null) return '—'
  return `${(rate * 100).toFixed(0)}%`
}

async function load() {
  loading.value = true
  error.value = null
  try {
    doctor.value = await api.get<OarDoctor>('/oar/doctor')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'no se pudo leer'
    doctor.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
    <header class="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
      <div>
        <h2 class="text-[var(--text-heading)] font-[var(--font-weight-semibold)]">Providers de IA</h2>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          <template v-if="loading">consultando…</template>
          <template v-else-if="rows.length === 0">sin providers registrados</template>
          <template v-else>
            {{ usable }}/{{ rows.length }} aportan capacidad
            <template v-if="needKey.length"> · {{ needKey.length }} sin credencial</template>
          </template>
        </p>
      </div>
      <button
        class="flex items-center gap-1 text-[var(--text-label)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
        :disabled="loading"
        aria-label="Refrescar estado de providers"
        @click="load"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        refrescar
      </button>
    </header>

    <!-- empty honesto: nunca "todo bien" por defecto -->
    <p v-if="!loading && !error && rows.length === 0" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-text-muted)]">
      El runtime de IA no está inicializado. Sin providers registrados no hay capacidad de inference.
    </p>

    <p v-else-if="error" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-sys-blocked)]">
      No se pudo consultar el estado: {{ error }}
    </p>

    <table v-else class="w-full text-[var(--text-label)]">
      <thead>
        <tr class="text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
          <th class="text-left font-normal px-4 py-2">provider</th>
          <th class="text-left font-normal px-2 py-2">estado</th>
          <th class="text-right font-normal px-2 py-2">latencia</th>
          <th class="text-right font-normal px-2 py-2">errores</th>
          <th class="text-left font-normal px-4 py-2">detalle</th>
        </tr>
      </thead>
      <tbody class="font-[var(--font-numeric)] tabular-nums">
        <tr v-for="r in rows" :key="r.id" class="border-b border-[var(--color-border)] last:border-0">
          <td class="px-4 py-2 text-[var(--color-text)]">{{ r.id }}</td>
          <td class="px-2 py-2" :class="statusClass(r.status)">
            <span class="inline-flex items-center gap-1">
              <CircleCheck v-if="r.status === 'healthy' && !r.breakerOpen" :size="12" />
              <CircleAlert v-else-if="r.status === 'degraded' || r.breakerOpen" :size="12" />
              <CircleHelp v-else-if="r.status === 'unknown'" :size="12" />
              <Ban v-else :size="12" />
              {{ r.label }}
            </span>
          </td>
          <td class="px-2 py-2 text-right text-[var(--color-text-muted)]">{{ fmtLatency(r.latencyMs) }}</td>
          <td class="px-2 py-2 text-right text-[var(--color-text-muted)]">{{ fmtRate(r.errorRate) }}</td>
          <td class="px-4 py-2 text-[var(--color-text-muted)]">
            <span v-if="r.breakerOpen" class="inline-flex items-center gap-1 text-[var(--color-sys-blocked)]">
              <AlertTriangle :size="12" /> circuit breaker abierto — failando al siguiente
            </span>
            <span v-else-if="r.needsKey">
              sin credencial — exportá la key del provider para activarlo
            </span>
            <span v-else-if="r.lastError">{{ r.lastError }}</span>
            <span v-else>—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
