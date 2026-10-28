<script setup lang="ts">
/**
 * BestActionCard — "¿qué hago ahora?"
 *
 * El motor de "una best action" estaba **roto desde el commit 2d74d038**:
 * `_get_default_profile()` llamaba `IntelligentProfileBuilder().build()` sin
 * el argumento que `build(profile)` exige ⇒ `TypeError` ⇒ el endpoint
 * respondía "Sin acción disponible" para siempre. Arreglado el backend; este
 * componente le da la cara en la UI.
 *
 * Muestra la acción con su evidencia completa — ítem, plata esperada,
 * probabilidad de aceptación, horas y URL real — para que la recomendación
 * sea auditable y no una frase motivacional. Con 0 PAID el valor esperado es
 * 0 pero la **probabilidad** no: son cosas distintas y no se mezclan.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AlertTriangle, Compass, RefreshCw } from '@lucide/vue'
import { api } from '@/lib/api'
import { isUnauthenticated } from '@/lib/errors'
import Button from '@/components/ui/Button.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface BestAction {
  action_type: string
  title: string
  description: string
  why_now: string
  platform: string
  work_item_id?: string
  opportunity_id?: string
  expected_value_usd?: number
  acceptance_probability?: number
  estimated_human_hours?: number
  cash_speed_days?: number
  url?: string
  next_step_instruction?: string
  prerequisites?: string[]
}

const router = useRouter()
const action = ref<BestAction | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    action.value = await api.get<BestAction>('/api/unified-income/best-action')
  } catch (e) {
    if (!isUnauthenticated(e)) error.value = e instanceof Error ? e.message : String(e)
    action.value = null
  } finally {
    loading.value = false
  }
}

function openWorkItem() {
  const id = action.value?.work_item_id
  if (id) router.push(`/operations/work-room/${id}`)
}

const prob = computed(() => {
  const p = action.value?.acceptance_probability
  return typeof p === 'number' ? `${Math.round(p * 100)}%` : 'UNKNOWN'
})

onMounted(load)
</script>

<template>
  <OwnexCard class="p-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <Compass class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold text-foreground">La mejor acción ahora</h2>
      </div>
      <Button variant="ghost" size="sm" :disabled="loading" @click="load">
        <RefreshCw class="mr-1 h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" />
      </Button>
    </div>

    <LoadingState v-if="loading" :rows="1" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <p v-else-if="!action" class="mt-2 text-[11px] text-muted-foreground">
      Sin acción disponible todavía. Corré un ciclo del banco para descubrir trabajo.
    </p>

    <div v-else class="mt-3 space-y-2">
      <p class="text-[11px] uppercase tracking-wider text-muted-foreground">{{ action.action_type }}</p>
      <p class="text-sm font-medium text-foreground">{{ action.title }}</p>
      <p class="text-xs text-muted-foreground">{{ action.description }}</p>
      <p v-if="action.why_now" class="text-xs italic text-primary/80">{{ action.why_now }}</p>

      <!-- Evidencia: sin esto la recomendación no es auditable -->
      <div class="grid grid-cols-2 gap-2 pt-1 md:grid-cols-4">
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Valor esperado</p>
          <!-- 0 esperado NO es "ganaste 0": con 0 PAID el esperado es 0 real -->
          <p class="font-mono text-xs text-foreground">
            ${{ Number(action.expected_value_usd ?? 0).toLocaleString('es-AR') }}
          </p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Aceptación</p>
          <p class="font-mono text-xs text-foreground" data-testid="acceptance">{{ prob }}</p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Tiempo humano</p>
          <p class="font-mono text-xs text-foreground">
            {{ action.estimated_human_hours ?? '?' }} h
          </p>
        </div>
        <div class="rounded-md border border-border/30 px-2 py-1.5">
          <p class="text-[10px] text-muted-foreground">Caja en</p>
          <p class="font-mono text-xs text-foreground">{{ action.cash_speed_days ?? '?' }} d</p>
        </div>
      </div>

      <ul v-if="action.prerequisites?.length" class="space-y-0.5 pt-1">
        <li
          v-for="p in action.prerequisites"
          :key="p"
          class="flex items-start gap-1.5 text-[11px] text-muted-foreground"
        >
          <AlertTriangle class="mt-0.5 h-3 w-3 shrink-0 text-warning" />{{ p }}
        </li>
      </ul>

      <div class="flex flex-wrap items-center gap-2 pt-2">
        <Button v-if="action.work_item_id" size="sm" @click="openWorkItem">Abrir el trabajo</Button>
        <span v-if="action.work_item_id" class="font-mono text-[10px] text-muted-foreground/70">
          {{ action.work_item_id }}
        </span>
        <a
          v-if="action.url"
          :href="action.url"
          target="_blank"
          rel="noopener noreferrer"
          class="text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Ver en la plataforma
        </a>
      </div>
    </div>
  </OwnexCard>
</template>
