<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { ListTodo, ExternalLink, ShieldAlert } from '@lucide/vue'

interface HumanAction {
  id: string
  title: string
  platform?: string
  motivo?: string
  url?: string
  instrucciones?: string
  que_hace_ownex?: string
  riesgo?: string
  permisos?: string
  estado: string
  estado_raw: string
}

interface HumanActionsResponse {
  doc: string
  total: number
  blocked_on_user: number
  ready_for_authorization: number
  blocked_on_platform: number
  completed: number
  actions: HumanAction[]
}

const data = ref<HumanActionsResponse | null>(null)
const loading = ref(true)
const error = ref(false)
const expanded = ref<string | null>(null)

const sorted = computed(() => {
  const order: Record<string, number> = {
    BLOCKED_ON_USER: 0,
    READY_FOR_AUTHORIZATION: 1,
    BLOCKED_ON_PLATFORM: 2,
    COMPLETED: 3,
  }
  return [...(data.value?.actions ?? [])].sort(
    (a, b) => (order[a.estado] ?? 9) - (order[b.estado] ?? 9) || a.id.localeCompare(b.id),
  )
})

function statusVariant(estado: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (estado === 'READY_FOR_AUTHORIZATION') return 'default'
  if (estado === 'BLOCKED_ON_PLATFORM') return 'secondary'
  if (estado === 'COMPLETED') return 'outline'
  return 'destructive'
}

function toggle(id: string) {
  expanded.value = expanded.value === id ? null : id
}

onMounted(async () => {
  try {
    data.value = await api.get<HumanActionsResponse>('/human-actions')
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Sistema</p>
      <h1 class="font-display text-2xl font-bold text-foreground flex items-center gap-2">
        <ListTodo class="h-6 w-6" /> Acciones pendientes
      </h1>
      <p class="text-sm text-muted-foreground">
        Todo lo que requiere tu intervención personal: credenciales, consentimientos e identidad.
        Fuente: <code class="text-xs">{{ data?.doc ?? 'docs/FINAL_HUMAN_ACTIONS.md' }}</code>
      </p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-24 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <p class="text-sm text-destructive">Error cargando acciones pendientes</p>
      </Card>
    </template>

    <template v-else-if="data">
      <div class="flex flex-wrap gap-3 text-xs text-muted-foreground animate-in">
        <span>Total: <strong class="text-foreground">{{ data.total }}</strong></span>
        <span>Blocked on you: <strong class="text-destructive">{{ data.blocked_on_user }}</strong></span>
        <span>Ready for authorization: <strong class="text-primary">{{ data.ready_for_authorization }}</strong></span>
        <span>Blocked on platform: <strong class="text-foreground">{{ data.blocked_on_platform }}</strong></span>
      </div>

      <div class="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 animate-in">
        <ShieldAlert class="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          OWNEX no ejecuta ninguna de estas acciones sin tu autorización expresa.
          Los ingresos verificados siguen en USD 0 hasta completar la Fase A.
        </span>
      </div>

      <div class="space-y-2 animate-in">
        <Card
          v-for="action in sorted"
          :key="action.id"
          class="p-4 transition-all hover:border-primary/30 cursor-pointer"
          @click="toggle(action.id)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <span class="text-xs font-mono text-muted-foreground">{{ action.id }}</span>
                <Badge :variant="statusVariant(action.estado)" class="text-[10px]">
                  {{ action.estado }}
                </Badge>
                <span v-if="action.platform" class="text-[10px] text-muted-foreground">
                  {{ action.platform }}
                </span>
              </div>
              <p class="text-sm font-semibold text-foreground">{{ action.title }}</p>
              <p v-if="action.motivo" class="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                {{ action.motivo }}
              </p>
            </div>
            <ExternalLink v-if="action.url" class="h-4 w-4 text-muted-foreground shrink-0" />
          </div>

          <div v-if="expanded === action.id" class="mt-3 space-y-2 border-t border-border pt-3 text-xs">
            <p v-if="action.instrucciones" class="text-muted-foreground whitespace-pre-wrap">
              <span class="font-semibold text-foreground">Instrucciones: </span>{{ action.instrucciones }}
            </p>
            <p v-if="action.que_hace_ownex" class="text-muted-foreground">
              <span class="font-semibold text-foreground">OWNEX después: </span>{{ action.que_hace_ownex }}
            </p>
            <p v-if="action.riesgo" class="text-muted-foreground">
              <span class="font-semibold text-foreground">Riesgo: </span>{{ action.riesgo }}
            </p>
            <p v-if="action.permisos" class="text-muted-foreground">
              <span class="font-semibold text-foreground">Permisos: </span>{{ action.permisos }}
            </p>
            <a
              v-if="action.url"
              :href="action.url"
              target="_blank"
              rel="noopener"
              class="inline-flex items-center gap-1 text-primary hover:underline"
              @click.stop
            >
              {{ action.url }} <ExternalLink class="h-3 w-3" />
            </a>
          </div>
        </Card>
      </div>
    </template>
  </div>
</template>
