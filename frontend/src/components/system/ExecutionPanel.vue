<script setup lang="ts">
/**
 * ExecutionPanel — "¿qué está haciendo OWNEX ahora?"
 *
 * Por qué existe: la auditoría encontró que `execution_queue`, `worker_core`,
 * `auto_submit`, `bounty_pipeline`, `unified_income` y `economic_feedback`
 * tenían **cero** UI. Son las capacidades que dicen si el trabajo automático
 * avanza o se murió — y el rol del dueño es supervisor: sin verlas no puede
 * supervisar nada.
 *
 * Se apoya en el `DataTable` denso (virtualización) porque la cola tiene
 * decenas de items y crece con cada ciclo.
 */
import { computed, onMounted, ref } from 'vue'
import { Activity, AlertTriangle, CheckCircle2, Clock, RefreshCw, Zap } from '@lucide/vue'
import { api } from '@/lib/api'
import { isUnauthenticated } from '@/lib/errors'
import Button from '@/components/ui/Button.vue'
import DataTable, { type Column } from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface QueueItem {
  item_id: string
  state: string
  payload?: Record<string, unknown>
  history?: Array<{ state?: string; at?: string }>
}

interface FeedbackSnapshot {
  total_outcomes?: number
  total_paid?: number
  total_net?: number
  total_hours?: number | null
  global_net_per_hour?: number | null
  generated_at?: string
}

const queue = ref<QueueItem[]>([])
const feedback = ref<FeedbackSnapshot | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const busyId = ref<string | null>(null)
const actionNote = ref<string | null>(null)

/**
 * Transiciones por estado, tomadas de la máquina real
 * (`cores/execution_queue/models.py:38-48`) y NO inventadas.
 *
 * `failed → queued` es el reintento; `failed → dead_letter` es el descarte
 * definitivo. Se ofrecen sólo las que el backend acepta: ofrecer una acción
 * que el servidor rechaza sería un botón de mentira.
 */
const ACTIONS: Record<string, Array<{ target: string; label: string; tone: string }>> = {
  ready: [{ target: 'queued', label: 'Encolar', tone: 'primary' }],
  executing: [
    { target: 'submitted', label: 'Marcar enviado', tone: 'primary' },
    { target: 'failed', label: 'Marcar fallido', tone: 'outline' },
  ],
  waiting_human: [
    { target: 'executing', label: 'Retomar', tone: 'primary' },
    { target: 'submitted', label: 'Enviar', tone: 'primary' },
    { target: 'blocked', label: 'Bloquear', tone: 'outline' },
  ],
  submitted: [{ target: 'verification', label: 'A verificación', tone: 'outline' }],
  verification: [{ target: 'paid', label: 'Marcar pagado', tone: 'primary' }],
  failed: [
    { target: 'queued', label: 'Reintentar', tone: 'primary' },
    { target: 'dead_letter', label: 'A DLQ', tone: 'outline' },
  ],
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const items = await api.get<QueueItem[]>('/api/execution-queue')
    queue.value = Array.isArray(items) ? items : []
  } catch (e) {
    if (!isUnauthenticated(e)) error.value = e instanceof Error ? e.message : String(e)
    queue.value = []
  }
  // El feedback económico es complementario: si falla, el panel igual sirve.
  try {
    feedback.value = await api.get<FeedbackSnapshot>('/api/economic-feedback/snapshot')
  } catch {
    feedback.value = null
  }
  loading.value = false
}

async function transition(item: QueueItem, target: string, label: string) {
  busyId.value = item.item_id
  actionNote.value = null
  try {
    await api.post(`/api/execution-queue/${encodeURIComponent(item.item_id)}/transition`, { target_state: target })
    actionNote.value = `${item.item_id}: ${label}`
    await load()
  } catch (e) {
    // El servidor es la autoridad sobre transiciones válidas: si rechaza,
    // se dice exactamente qué dijo en vez de asumir que funcionó.
    actionNote.value = `${item.item_id}: no se pudo — ${e instanceof Error ? e.message : String(e)}`
  } finally {
    busyId.value = null
  }
}

const byState = computed(() => {
  const acc: Record<string, number> = {}
  for (const i of queue.value) acc[i.state] = (acc[i.state] ?? 0) + 1
  return acc
})

const columns: Column<QueueItem>[] = [
  { key: 'item_id', label: 'Item', sortable: true, width: '180px' },
  { key: 'state', label: 'Estado', sortable: true, width: '110px' },
  { key: 'title', label: 'Trabajo', sortable: true },
  { key: 'platform', label: 'Plataforma', sortable: true, width: '110px' },
  { key: 'reward', label: 'Recompensa', sortable: true, align: 'right', width: '105px' },
  { key: 'steps', label: 'Pasos', sortable: true, align: 'right', width: '70px' },
  { key: 'actions', label: 'Acciones', sortable: false, width: '210px' },
]

function flat(i: QueueItem): Record<string, unknown> {
  return (i.payload ?? {}) as Record<string, unknown>
}

/** El denominador ausente es UNKNOWN, nunca $0: se muestra el texto tal cual. */
function netPerHour(s: FeedbackSnapshot | null): string {
  const v = s?.global_net_per_hour
  if (v == null) return 'UNKNOWN'
  return `$${Number(v).toFixed(2)}/h`
}

function money(v: unknown): string {
  const n = Number(v ?? 0)
  return n > 0 ? `$${n.toLocaleString('es-AR', { maximumFractionDigits: 0 })}` : '—'
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <!-- Cabecera -->
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <Activity class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold text-foreground">Supervisión de la ejecución</h2>
      </div>
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">
        <RefreshCw class="mr-1 h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" /> Actualizar
      </Button>
    </div>

    <LoadingState v-if="loading" :rows="3" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else>
      <!-- Estado por fase: lo primero que un supervisor necesita ver -->
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <OwnexCard class="p-3">
          <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Clock class="h-3.5 w-3.5" /> Listos
          </div>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ byState.ready ?? 0 }}</p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Activity class="h-3.5 w-3.5" /> Enviados
          </div>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ byState.submitted ?? 0 }}</p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <AlertTriangle class="h-3.5 w-3.5 text-warning" /> Fallidos
          </div>
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">
            {{ (byState.failed ?? 0) + (byState.dead_letter ?? 0) }}
          </p>
        </OwnexCard>
        <OwnexCard class="p-3">
          <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <CheckCircle2 class="h-3.5 w-3.5 text-success" /> Neto / hora
          </div>
          <!-- UNKNOWN si no hay horas registradas: nunca $0 (KNOWN_DEBT #34) -->
          <p class="mt-1 font-mono text-xl font-semibold text-foreground">{{ netPerHour(feedback) }}</p>
        </OwnexCard>
      </div>

      <!-- La cola, densa -->
      <DataTable
        :columns="columns"
        :items="queue"
        searchable
        dense
        virtualize-over="40"
        row-key="item_id"
        search-placeholder="Buscar por id, plataforma o título..."
        empty-title="La cola de ejecución está vacía"
        empty-description="Nada encolado todavía. Corré un ciclo del WorkBank para poblarla."
      >
        <template #cell-state="{ item }">
          <span
            class="rounded px-1.5 py-0.5 font-mono text-[10px]"
            :class="
              item.state === 'ready'
                ? 'bg-primary/10 text-primary'
                : item.state === 'submitted'
                  ? 'bg-success/10 text-success'
                  : item.state === 'failed' || item.state === 'dead_letter'
                    ? 'bg-destructive/10 text-destructive'
                    : 'bg-surface/60 text-muted-foreground'
            "
          >
            {{ item.state }}
          </span>
        </template>
        <template #cell-title="{ item }">
          <span class="text-foreground">{{ flat(item).title ?? '—' }}</span>
        </template>
        <template #cell-platform="{ item }">
          <span class="font-mono text-[11px] text-muted-foreground">{{ flat(item).platform ?? '—' }}</span>
        </template>
        <template #cell-reward="{ item }">
          <span class="font-mono text-foreground">{{ money(flat(item).reward) }}</span>
        </template>
        <template #cell-steps="{ item }">
          <span class="font-mono text-muted-foreground">{{ item.history?.length ?? 0 }}</span>
        </template>
        <!-- Sólo las transiciones que el backend acepta para ese estado:
             un botón que el servidor rechaza sería un botón de mentira. -->
        <template #cell-actions="{ item }">
          <div class="flex flex-wrap items-center gap-1">
            <Button
              v-for="a in ACTIONS[item.state] ?? []"
              :key="a.target"
              size="sm"
              :variant="a.tone as never"
              :disabled="busyId === item.item_id"
              @click.stop="transition(item, a.target, a.label)"
            >
              <Zap v-if="busyId === item.item_id" class="mr-1 h-3 w-3 animate-spin" />
              {{ a.label }}
            </Button>
            <span v-if="!(ACTIONS[item.state] ?? []).length" class="text-[10px] text-muted-foreground/60">—</span>
          </div>
        </template>
      </DataTable>

      <!-- Resultado de la última acción: dice lo que pasó, incluido el rechazo. -->
      <p
        v-if="actionNote"
        class="rounded-md border border-border/40 bg-surface/40 px-3 py-2 text-[11px] text-muted-foreground"
        data-testid="action-note"
      >
        {{ actionNote }}
      </p>

      <p class="text-[10px] text-muted-foreground">
        Neto/hora sale de <span class="font-mono">economic-feedback</span>: con 0 PAID es
        <span class="font-mono">UNKNOWN</span>, no $0. Sólo PAID cuenta como caja.
      </p>
    </template>
  </div>
</template>
