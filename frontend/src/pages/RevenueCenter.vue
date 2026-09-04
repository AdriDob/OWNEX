<script setup lang="ts">
/**
 * Revenue Center — dinero esperado vs pendiente vs cobrado (spec §6).
 * Fuentes: /revenue/summary + /revenue/submissions + /payment-tracker.
 */
import { computed, onMounted, ref } from 'vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'
import {
  fetchRevenueSubmissions,
  fetchRevenueSummary,
  type RevenueSubmission,
  type RevenueSummary,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref<string | null>(null)
const summary = ref<RevenueSummary | null>(null)
const submissions = ref<RevenueSubmission[]>([])
const tracker = ref<{ confirmed?: number; pending?: number } | null>(null)

const usd = (n: number | undefined | null): string => `$${Math.round(n ?? 0).toLocaleString('es-AR')}`

const statusVariant = (s?: string): 'success' | 'warning' | 'error' | 'default' => {
  const v = (s || '').toLowerCase()
  if (['paid', 'verified'].includes(v)) return 'success'
  if (['pending', 'submitted', 'reviewing', 'accepted'].includes(v)) return 'warning'
  if (['rejected', 'cancelled', 'failed'].includes(v)) return 'error'
  return 'default'
}

const byPlatform = computed(() => summary.value?.by_platform?.slice().sort((a, b) => b.earned - a.earned) ?? [])

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  const [sumRes, subRes, trkRes] = await Promise.allSettled([
    fetchRevenueSummary(),
    fetchRevenueSubmissions(),
    api.get<{ confirmed?: number; pending?: number }>('/payment-tracker'),
  ])
  if (sumRes.status === 'fulfilled') summary.value = sumRes.value
  else error.value = sumRes.reason instanceof Error ? sumRes.reason.message : String(sumRes.reason)
  if (subRes.status === 'fulfilled') submissions.value = subRes.value
  if (trkRes.status === 'fulfilled') tracker.value = trkRes.value
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Centro de Ingresos</h1>
        <p class="text-sm text-muted-foreground">Esperado ≠ Pendiente ≠ Cobrado</p>
      </div>
      <Badge variant="default">revenue</Badge>
    </div>

    <ErrorState v-if="error && !summary" title="No se pudo cargar el resumen de ingresos" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading && !summary" />

    <template v-else-if="summary">
      <!-- N1: tres números -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card class="p-5">
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Cobrado</p>
          <p class="mt-1 font-mono text-2xl font-semibold tabular-nums text-success">{{ usd(summary.total_earned) }}</p>
          <p class="font-mono text-[9px] text-muted-foreground/60">30d: {{ usd(summary.earnings_30d) }}</p>
        </Card>
        <Card class="p-5">
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Pendiente</p>
          <p class="mt-1 font-mono text-2xl font-semibold tabular-nums">{{ usd(summary.pending_amount) }}</p>
          <p v-if="tracker" class="font-mono text-[9px] text-muted-foreground/60">tracker: {{ usd(tracker.pending) }}</p>
        </Card>
        <Card class="p-5">
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Envíos</p>
          <p class="mt-1 font-mono text-2xl font-semibold tabular-nums">{{ submissions.length }}</p>
          <p class="font-mono text-[9px] text-muted-foreground/60">historial completo abajo</p>
        </Card>
      </div>

      <!-- N2: fuentes -->
      <Card v-if="byPlatform.length" class="space-y-3 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">De dónde viene mi dinero</p>
        <div v-for="row in byPlatform" :key="row.platform" class="flex items-center justify-between border-b border-border/10 pb-2 last:border-0">
          <span class="text-sm capitalize">{{ row.platform }}</span>
          <span class="font-mono text-sm tabular-nums">
            <span class="text-success">{{ usd(row.earned) }}</span>
            <span v-if="row.pending" class="ml-2 text-muted-foreground">+{{ usd(row.pending) }} pend.</span>
          </span>
        </div>
      </Card>

      <!-- N3: submissions -->
      <Card v-if="submissions.length" class="space-y-1 p-5">
        <p class="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">Historial de envíos</p>
        <div v-for="s in submissions.slice(0, 25)" :key="s.id" class="flex items-center justify-between py-1.5">
          <span class="line-clamp-1 max-w-[50%] text-sm">{{ s.title || s.id }}</span>
          <div class="flex items-center gap-3">
            <span v-if="s.amount" class="font-mono text-xs tabular-nums">{{ usd(s.amount) }}</span>
            <Badge :variant="statusVariant(s.status)">{{ s.status || '—' }}</Badge>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>
