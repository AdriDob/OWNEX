<script setup lang="ts">
/**
 * Work Queue — cola de ejecución unificada (spec FEATURE-PARITY §5).
 * NOW / NEXT / WAITING / DONE sobre /api/execution-queue.
 * Acciones reales: transition según estados válidos del backend.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorState from '@/components/shared/ErrorState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import {
  EXEC_QUEUE_COLUMNS,
  type ExecState,
  type ExecutionQueueItem,
  fetchExecutionQueue,
  transitionExecutionItem,
} from '@/services/ownexData'

const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const items = ref<ExecutionQueueItem[]>([])
const busyId = ref<string | null>(null)

const stateVariant = (s: string): 'success' | 'warning' | 'error' | 'default' => {
  if (s === 'paid') return 'success'
  if (['executing', 'queued', 'ready'].includes(s)) return 'warning'
  if (['failed', 'rejected', 'blocked', 'dead_letter'].includes(s)) return 'error'
  return 'default'
}

const byColumn = computed(() => {
  const map: Record<string, ExecutionQueueItem[]> = {}
  for (const col of EXEC_QUEUE_COLUMNS) {
    map[col.key] = items.value.filter((i) => col.states.includes(i.state))
  }
  return map
})

function itemTitle(item: ExecutionQueueItem): string {
  const p = item.payload ?? {}
  return String(p.title || p.name || p.opportunity_id || p.item_id || item.item_id)
}
function itemReward(item: ExecutionQueueItem): number | null {
  const p = item.payload ?? {}
  const r = p.reward ?? p.payment ?? p.amount
  return typeof r === 'number' ? r : null
}

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    items.value = await fetchExecutionQueue()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function advance(item: ExecutionQueueItem): Promise<void> {
  // Siguiente estado válido según la máquina canónica
  const nextByState: Partial<Record<ExecState, ExecState>> = {
    discovered: 'qualified',
    qualified: 'ready',
    ready: 'queued',
    queued: 'executing',
    executing: 'submitted',
    waiting_human: 'submitted',
    submitted: 'verification',
    verification: 'paid',
    failed: 'queued',
  }
  const target = nextByState[item.state]
  if (!target) return
  busyId.value = item.item_id
  try {
    const updated = await transitionExecutionItem(item.item_id, target)
    const idx = items.value.findIndex((i) => i.item_id === item.item_id)
    if (idx !== -1) items.value[idx] = updated
  } catch (e) {
    console.error('transition failed', e)
  } finally {
    busyId.value = null
  }
}

async function reject(item: ExecutionQueueItem): Promise<void> {
  busyId.value = item.item_id
  try {
    const updated = await transitionExecutionItem(item.item_id, 'rejected')
    const idx = items.value.findIndex((i) => i.item_id === item.item_id)
    if (idx !== -1) items.value[idx] = updated
  } catch (e) {
    console.error('reject failed', e)
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-4 p-4 sm:space-y-6 sm:p-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Cola de Trabajo</h1>
        <p class="text-sm text-muted-foreground">Ejecución · DISCOVERED → PAID</p>
      </div>
      <OwnexBadge variant="default">{{ items.length }} ítems</OwnexBadge>
    </div>

    <ErrorState v-if="error && !items.length" title="No se pudo cargar la cola" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading && !items.length" />
    <EmptyState v-else-if="!loading && !items.length" title="Sin trabajos en cola" description="WorkerCore descubre y prepara oportunidades automáticamente. Cuando haya trabajo disponible, aparecerá aquí.">
      <template #action>
        <button @click="load" class="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--ownex-bg-elevated)] text-[var(--ownex-text-primary)] border border-[var(--ownex-border)] hover:bg-[var(--ownex-border)] transition-colors">
          Actualizar
        </button>
      </template>
    </EmptyState>

    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <div v-for="col in EXEC_QUEUE_COLUMNS" :key="col.key" class="space-y-3">
        <div class="flex items-center gap-2 px-1">
          <h2 class="font-mono text-xs uppercase tracking-wider text-muted-foreground">{{ col.label }}</h2>
          <span class="font-mono text-[10px] text-muted-foreground/60">{{ byColumn[col.key].length }}</span>
        </div>
        <OwnexCard
          v-for="item in byColumn[col.key]"
          :key="item.item_id"
          class="space-y-2 p-4"
        >
          <div class="flex items-start justify-between gap-2">
            <p class="line-clamp-2 text-sm font-medium leading-snug">{{ itemTitle(item) }}</p>
            <OwnexBadge :variant="stateVariant(item.state)">{{ item.state }}</OwnexBadge>
          </div>
          <p v-if="itemReward(item) !== null" class="font-mono text-sm font-semibold tabular-nums text-success">
            ${{ itemReward(item)!.toLocaleString('es-AR') }}
          </p>
          <p class="font-mono text-[10px] text-muted-foreground/60">{{ item.payload?.platform || '—' }}</p>
          <div v-if="!['paid', 'rejected', 'blocked', 'dead_letter'].includes(item.state)" class="flex gap-2 pt-1">
            <button
              class="flex-1 rounded-md border border-border/30 px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide hover:bg-surface/40 disabled:opacity-40 min-h-[36px]"
              :disabled="busyId === item.item_id"
              @click="advance(item)"
            >
              {{ busyId === item.item_id ? '…' : 'Avanzar' }}
            </button>
            <button
              v-if="item.state === 'waiting_human'"
              class="rounded-md border border-border/30 px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground hover:bg-surface/40 disabled:opacity-40 min-h-[36px]"
              :disabled="busyId === item.item_id"
              @click="reject(item)"
            >
              Rechazar
            </button>
          </div>
          <button
            class="w-full rounded-md border border-border/30 px-2 py-1.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground hover:bg-surface/40 min-h-[36px]"
            @click="router.push(`/operations/work-room/${item.item_id}`)"
          >
            Ver detalles
          </button>
        </OwnexCard>
        <p
          v-if="!byColumn[col.key].length"
          class="rounded-lg border border-dashed border-border/20 p-6 text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground/50"
        >
          vacío
        </p>
      </div>
    </div>
  </div>
</template>
