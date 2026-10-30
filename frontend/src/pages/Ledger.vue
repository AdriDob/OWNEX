<script setup lang="ts">
/**
 * Revenue Ledger — verdad contable del sistema económico.
 * Buckets del ciclo canónico: EXPECTED → COMMITTED → EARNED → PENDING → PAID (→ NET).
 * Solo PAID/NET es caja; el resto es pipeline. Sin dinero simulado.
 */
import { computed, onMounted, ref } from 'vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import MetricCard from '@/components/ui/MetricCard.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import {
  fetchRevenueLedger,
  type RevenueLedger,
  type RevenueLedgerOpportunity,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref<string | null>(null)
const ledger = ref<RevenueLedger | null>(null)
const platformFilter = ref<string>('')

const BUCKET_ORDER = ['expected', 'committed', 'earned', 'pending', 'paid', 'net', 'cancelled', 'failed'] as const

const buckets = computed(() => {
  const b = ledger.value?.buckets_usd ?? {}
  return BUCKET_ORDER.filter((k) => k in b).map((k) => ({ state: k, amount: b[k] ?? 0 }))
})

const projection = computed(() => ledger.value?.projection_usd ?? null)

const filteredOpps = computed<RevenueLedgerOpportunity[]>(() => {
  const items = ledger.value?.opportunities ?? []
  const f = platformFilter.value.trim().toLowerCase()
  if (!f) return items
  return items.filter((o) => o.platform.toLowerCase().includes(f))
})

const stateVariant = (s: string): 'success' | 'warning' | 'error' | 'default' => {
  if (['paid', 'net'].includes(s)) return 'success'
  if (['committed', 'earned', 'pending', 'expected'].includes(s)) return 'warning'
  if (['cancelled', 'failed'].includes(s)) return 'error'
  return 'default'
}

const fmt = (n: number): string =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    ledger.value = await fetchRevenueLedger(undefined, 200)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Revenue Ledger">
    <div class="mb-4">
      <h1 class="text-xl font-semibold">Revenue Ledger</h1>
      <p class="text-sm opacity-70">
        Solo PAID/NET es caja. EXPECTED → COMMITTED → EARNED → PENDING es pipeline, no dinero.
      </p>
    </div>

    <LoadingState v-if="loading" message="Cargando ledger..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="ledger">
      <!-- Proyección honesta -->
      <div v-if="projection" class="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="Pipeline" :value="fmt(projection.pipeline)" variant="warning" />
        <MetricCard label="Ganado no cobrado" :value="fmt(projection.earned_not_paid)" variant="warning" />
        <MetricCard label="Realizado (caja)" :value="fmt(projection.realized)" variant="success" />
        <MetricCard label="Potencial total" :value="fmt(projection.total_potential)" />
      </div>

      <!-- Buckets por estado -->
      <OwnexCard class="mb-4">
        <h2 class="mb-3 text-base font-semibold">Por estado</h2>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div
            v-for="b in buckets"
            :key="b.state"
            class="flex items-center justify-between gap-2 rounded border border-border/60 px-3 py-2"
          >
            <OwnexBadge :variant="stateVariant(b.state)">{{ b.state }}</OwnexBadge>
            <span class="font-mono text-sm">{{ fmt(b.amount) }}</span>
          </div>
        </div>
      </OwnexCard>

      <!-- Oportunidades -->
      <OwnexCard>
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h2 class="text-base font-semibold">Oportunidades ({{ filteredOpps.length }})</h2>
          <input
            v-model="platformFilter"
            type="text"
            placeholder="Filtrar por plataforma..."
            class="ml-auto rounded border border-border bg-background px-2 py-1 text-sm"
          />
        </div>
        <EmptyState
          v-if="filteredOpps.length === 0"
          title="Ledger vacío"
          description="Todavía no hay ejecuciones registradas. El primer submit aprobado aparece acá."
        />
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="opp in filteredOpps"
            :key="opp.id"
            class="flex flex-wrap items-center gap-3 rounded border border-border/60 px-3 py-2"
          >
            <OwnexBadge :variant="stateVariant(opp.revenue_state)">{{ opp.revenue_state }}</OwnexBadge>
            <div class="min-w-52 flex-1">
              <div class="text-sm font-semibold">{{ opp.title }}</div>
              <div class="text-xs opacity-60">{{ opp.platform }} · {{ opp.status }}</div>
            </div>
            <span class="font-mono text-sm">{{ fmt(opp.amount_usd) }}</span>
          </div>
        </div>
      </OwnexCard>
    </template>
  </div>
</template>
