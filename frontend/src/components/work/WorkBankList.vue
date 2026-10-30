<script setup lang="ts">
/**
 * WorkBankList — la cola de trabajo del sistema, y la puerta al Work Room.
 *
 * Por qué existe: el banco ya producía trabajo real (11 items, ciclo con 1.018
 * oportunidades escaneadas) y `WorkRoom.vue` cerraba el loop completo de
 * entrega… pero **nada en la UI lo listaba**. `/operations/work-room/:id` no
 * tenía entrada: el trabajo encontrado era inalcanzable desde la interfaz.
 *
 * Este componente es esa entrada, y además dispara el ciclo (`workbank/cycle`)
 * que descubre y prepara trabajo nuevo. Sin eso el sistema es un lector.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { FolderTree, Play, RefreshCw, TriangleAlert } from '@lucide/vue'
import { api } from '@/lib/api'
import { isUnauthenticated } from '@/lib/errors'
import Button from '@/components/ui/Button.vue'
import DataTable, { type Column } from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface WorkItem {
  id: string
  title: string
  platform: string
  category: string
  reward: number
  status: string
  access_status: string
  deliverables: string[]
  ready_to_deliver: boolean
  url: string
}

interface BankSummary {
  scanned?: number
  eligible_zero_barrier?: number
  ready_to_deliver?: number
  needs_access?: number
  delivered?: number
  unpaid_evidence?: number
  rejected_reasons?: string[]
  items?: WorkItem[]
}

const router = useRouter()
const items = ref<WorkItem[]>([])
const summary = ref<BankSummary>({})
const loading = ref(true)
const cycling = ref(false)
const error = ref<string | null>(null)
const cycleNote = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const d = await api.get<BankSummary>('/direct-work/workbank')
    summary.value = d ?? {}
    items.value = d?.items ?? []
  } catch (e) {
    if (!isUnauthenticated(e)) error.value = e instanceof Error ? e.message : String(e)
    items.value = []
  } finally {
    loading.value = false
  }
}

/** Descubre + prepara trabajo. Es la acción que convierte viewer en motor. */
async function runCycle() {
  cycling.value = true
  cycleNote.value = null
  try {
    const r = await api.post<BankSummary>('/direct-work/workbank/cycle', {})
    summary.value = { ...summary.value, ...(r ?? {}) }
    cycleNote.value = `Ciclo: ${r?.scanned ?? 0} escaneadas · ${r?.eligible_zero_barrier ?? 0} elegibles · ${
      r?.ready_to_deliver ?? 0
    } listas`
    await load()
  } catch (e) {
    cycleNote.value = `El ciclo falló: ${e instanceof Error ? e.message : String(e)}`
  } finally {
    cycling.value = false
  }
}

/** Sólo lo accionable: lo que no tiene evidencia de pago no entra al banco. */
const actionable = computed(() => items.value.filter((i) => i.status !== 'unpaid_evidence'))
const hiddenCount = computed(() => items.value.length - actionable.value.length)

const columns: Column<WorkItem>[] = [
  { key: 'title', label: 'Trabajo', sortable: true },
  { key: 'platform', label: 'Plataforma', sortable: true, width: '110px' },
  { key: 'reward', label: 'Recompensa', sortable: true, align: 'right', width: '110px' },
  { key: 'status', label: 'Estado', sortable: true, width: '130px' },
  { key: 'deliverables', label: 'Entregables', sortable: true, align: 'right', width: '95px' },
  { key: 'actions', label: '', sortable: false, width: '110px' },
]

function money(v: unknown): string {
  const n = Number(v ?? 0)
  return n > 0 ? `$${n.toLocaleString('es-AR', { maximumFractionDigits: 0 })}` : '—'
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <FolderTree class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold text-foreground">Banco de trabajo</h2>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="mr-1 h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" /> Actualizar
        </Button>
        <Button size="sm" :disabled="cycling" @click="runCycle">
          <Play class="mr-1 h-3.5 w-3.5" :class="cycling ? 'animate-pulse' : ''" />
          {{ cycling ? 'Corriendo ciclo…' : 'Correr ciclo' }}
        </Button>
      </div>
    </div>

    <LoadingState v-if="loading" :rows="3" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <OwnexCard class="p-3">
          <p class="text-[11px] text-muted-foreground">Listas para entregar</p>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ summary.ready_to_deliver ?? 0 }}</p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <p class="text-[11px] text-muted-foreground">Escaneadas en el ciclo</p>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ summary.scanned ?? 0 }}</p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <p class="text-[11px] text-muted-foreground">Accionables</p>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ actionable.length }}</p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <p class="flex items-center gap-1 text-[11px] text-muted-foreground">
            <TriangleAlert class="h-3 w-3 text-warning" /> Sin evidencia de pago
          </p>
          <p class="mt-1 font-mono text-xl font-semibold text-muted-foreground">{{ summary.unpaid_evidence ?? 0 }}</p>
        </OwnexCard>
      </div>

      <p v-if="cycleNote" class="text-[11px] text-muted-foreground" data-testid="cycle-note">
        {{ cycleNote }}
      </p>

      <DataTable
        :columns="columns"
        :items="actionable"
        searchable
        dense
        virtualize-over="40"
        row-key="id"
        search-placeholder="Buscar trabajo o plataforma..."
        empty-title="No hay trabajo en el banco"
        empty-description="Corré un ciclo para descubrir oportunidades y preparar las elegibles."
        :row-click="(i: WorkItem) => router.push(`/operations/work-room/${i.id}`)"
      >
        <template #cell-reward="{ item }">
          <span class="font-mono text-foreground">{{ money(item.reward) }}</span>
        </template>
        <template #cell-status="{ item }">
          <span
            class="rounded px-1.5 py-0.5 font-mono text-[10px]"
            :class="item.status === 'ready_to_deliver' ? 'bg-primary/10 text-primary' : 'bg-surface/60 text-muted-foreground'"
          >
            {{ item.status }}
          </span>
        </template>
        <template #cell-actions="{ item }">
          <Button size="sm" variant="outline" @click.stop="router.push(`/operations/work-room/${item.id}`)">
            Abrir
          </Button>
        </template>
      </DataTable>

      <p class="text-[10px] text-muted-foreground">
        Se ocultan {{ hiddenCount }} ítem(s) sin evidencia de pago: sus repos nunca mergearon un PR,
        así que no son entregables. Se listan aparte, no se mezclan con el trabajo accionable.
      </p>
    </template>
  </div>
</template>
