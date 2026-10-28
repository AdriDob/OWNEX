<script setup lang="ts">
/**
 * SystemStatePanel — la salud real del sistema, para un supervisor.
 *
 * Por qué existe: `system-state` estaba montado pero sin interfaz, y es la
 * única fuente que dice si lo que OWNEX hace por vos está funcionando.
 * Sus datos son reales (cuento de `cores/system_state.py`), y hoy muestra
 * algo concreto: `health_center` `unhealthy` con 49.822 errores.
 *
 * Regla: si un servicio está caído, se dice. No se suaviza ni se cuenta
 * como "operational" porque el proceso esté vivo.
 */
import { computed, onMounted, ref } from 'vue'
import { Activity, RefreshCw, Server } from '@lucide/vue'
import { api } from '@/lib/api'
import { isUnauthenticated } from '@/lib/errors'
import Button from '@/components/ui/Button.vue'
import DataTable, { type Column } from '@/components/ui/DataTable.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface Service {
  name: string
  state: string
  last_healthy?: number | null
  last_seen?: number
  error_count?: number
  last_error?: string | null
}

interface StatePayload {
  state?: {
    system_state?: string
    uptime_seconds?: number
    services_total?: number
    services_healthy?: number
    services_unhealthy?: number
  }
  services?: Service[]
}

const state = ref<StatePayload>({})
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    state.value = await api.get<StatePayload>('/api/system-state/state')
  } catch (e) {
    if (!isUnauthenticated(e)) error.value = e instanceof Error ? e.message : String(e)
    state.value = {}
  } finally {
    loading.value = false
  }
}

const summary = computed(() => state.value.state ?? {})

const tone = computed(() => {
  const s = (summary.value.system_state ?? '').toUpperCase()
  if (s === 'HEALTHY' || s === 'OK') return 'text-success'
  if (s === 'DEGRADED') return 'text-warning'
  if (s === 'DOWN' || s === 'CRITICAL') return 'text-destructive'
  return 'text-muted-foreground'
})

const columns: Column<Service>[] = [
  { key: 'name', label: 'Servicio', sortable: true },
  { key: 'state', label: 'Estado', sortable: true, width: '120px' },
  { key: 'error_count', label: 'Errores', sortable: true, align: 'right', width: '110px' },
  { key: 'last_error', label: 'Último error', sortable: true },
]

function uptime(sec?: number): string {
  if (sec == null) return 'UNKNOWN'
  const h = Math.floor(sec / 3600)
  const d = Math.floor(h / 24)
  return d > 0 ? `${d}d ${h % 24}h` : `${h}h`
}

onMounted(load)
</script>

<template>
  <OwnexCard class="p-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <Server class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold text-foreground">Salud del sistema</h2>
      </div>
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">
        <RefreshCw class="mr-1 h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" />
      </Button>
    </div>

    <LoadingState v-if="loading" :rows="2" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <div v-else class="mt-3 space-y-3">
      <div class="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Estado</p>
          <p class="font-mono text-sm font-semibold" :class="tone">
            {{ summary.system_state ?? 'UNKNOWN' }}
          </p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Servicios</p>
          <p class="font-mono text-sm text-foreground">
            {{ summary.services_healthy ?? 0 }}/{{ summary.services_total ?? 0 }}
          </p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Caídos</p>
          <p class="font-mono text-sm text-foreground">{{ summary.services_unhealthy ?? 0 }}</p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Uptime</p>
          <p class="font-mono text-sm text-foreground">{{ uptime(summary.uptime_seconds) }}</p>
        </div>
      </div>

      <DataTable
        :columns="columns"
        :items="state.services ?? []"
        dense
        searchable
        row-key="name"
        search-placeholder="Buscar servicio..."
        empty-title="Sin servicios registrados"
        empty-description="El registro de salud está vacío: el sistema no reportó servicios."
      >
        <template #cell-state="{ item }">
          <span
            class="rounded px-1.5 py-0.5 font-mono text-[10px]"
            :class="
              item.state === 'healthy'
                ? 'bg-success/10 text-success'
                : item.state === 'degraded'
                  ? 'bg-warning/10 text-warning'
                  : 'bg-destructive/10 text-destructive'
            "
          >
            {{ item.state }}
          </span>
        </template>
        <template #cell-error_count="{ item }">
          <span class="font-mono" :class="(item.error_count ?? 0) > 0 ? 'text-destructive' : 'text-muted-foreground'">
            {{ item.error_count ?? 0 }}
          </span>
        </template>
        <template #cell-last_error="{ item }">
          <span class="text-muted-foreground">{{ item.last_error ?? '—' }}</span>
        </template>
      </DataTable>
    </div>
  </OwnexCard>
</template>