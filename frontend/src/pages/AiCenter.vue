<script setup lang="ts">
/**
 * AI Center — estado real de providers IA + resilience (spec §9, §11, §25).
 * Fuentes: /settings/ai/providers + /settings/ai/config + /oar/status.
 * Nunca muestra como disponible un provider caído (datos del backend).
 *
 * Progressive disclosure: N1 = modo + modelo activo; N2 = providers;
 * N3 = quotas por provider; N4 = JSON crudo expandible.
 */
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { type AiCenterState, fetchAiCenter } from '@/services/ownexData'

const loading = ref(true)
const state = ref<AiCenterState | null>(null)
const showRaw = ref(false)

const resilience = computed(() => state.value?.oar?.resilience)
const modeInfo = computed(() => {
  const raw = resilience.value?.mode
  if (!raw) return null
  const mode = typeof raw === 'string' ? raw : raw.mode
  const reason = typeof raw === 'string' ? '' : (raw.reason ?? '')
  return { mode, reason }
})

const modeVariant = computed<'success' | 'warning' | 'error' | 'default'>(() => {
  switch (modeInfo.value?.mode) {
    case 'normal':
      return 'success'
    case 'degraded':
      return 'warning'
    case 'offline_ai':
      return 'error'
    default:
      return 'default'
  }
})

const modeLabel = computed(() => {
  switch (modeInfo.value?.mode) {
    case 'normal':
      return 'OPERATIVO'
    case 'degraded':
      return 'DEGRADADO'
    case 'offline_ai':
      return 'IA OFFLINE — modo reglas'
    default:
      return '—'
  }
})

const quotaRows = computed(() => {
  const quotas = resilience.value?.quotas ?? {}
  return Object.entries(quotas).map(([id, q]) => ({
    id,
    limitsKnown: q.limits_known,
    rpm: q.rpm_observed,
    tokensToday: q.tokens_today,
    limitLabel: q.limits_known ? `rpm:${q.limits.rpm ?? '—'} rpd:${q.limits.rpd ?? '—'}` : 'UNKNOWN',
  }))
})

async function load(): Promise<void> {
  loading.value = true
  state.value = await fetchAiCenter()
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Centro de IA</h1>
        <p class="text-sm text-muted-foreground">Providers · routing · cuotas · modo degradado</p>
      </div>
      <!-- N1: estado global -->
      <div class="flex items-center gap-2">
        <Badge v-if="modeInfo" :variant="modeVariant" dot>{{ modeLabel }}</Badge>
        <Badge v-if="state?.config" :variant="state.config.available ? 'success' : 'error'" dot>
          {{ state.config.active_provider }} · {{ state.config.available ? 'OK' : 'CAÍDO' }}
        </Badge>
      </div>
    </div>

    <LoadingState v-if="loading" />

    <template v-else-if="state">
      <!-- Motivo de degradación si aplica -->
      <Card v-if="modeInfo && modeInfo.mode !== 'normal'" class="border-warning/30 bg-warning/5 p-4">
        <p class="font-mono text-xs text-warning">{{ modeInfo.reason || 'Sistema en modo reducido' }}</p>
        <p class="mt-1 font-mono text-[10px] text-muted-foreground">OWNEX continúa con reglas deterministas y datos locales mientras tanto.</p>
      </Card>

      <!-- Modelo activo -->
      <Card v-if="state.config" class="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
        <div>
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Provider</p>
          <p class="mt-1 font-mono text-sm font-semibold">{{ state.config.active_provider }}</p>
        </div>
        <div>
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Modelo</p>
          <p class="mt-1 truncate font-mono text-sm">{{ state.config.model || '—' }}</p>
        </div>
        <div>
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Host</p>
          <p class="mt-1 truncate font-mono text-xs text-muted-foreground">{{ state.config.host || state.config.api_base || 'local' }}</p>
        </div>
        <div>
          <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Estado</p>
          <Badge class="mt-1" :variant="state.config.available ? 'success' : 'error'">
            {{ state.config.available ? 'OK' : 'NO DISPONIBLE' }}
          </Badge>
        </div>
      </Card>

      <!-- Providers -->
      <Card class="space-y-1 p-5">
        <p class="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">Providers registrados</p>
        <p v-if="!state.providers.length && !state.errors.length" class="py-4 text-center text-sm text-muted-foreground">
          Sin providers registrados
        </p>
        <div v-for="p in state.providers" :key="p.id" class="flex items-center justify-between py-2">
          <div>
            <span class="text-sm font-medium">{{ p.name || p.id }}</span>
            <span v-if="p.model" class="ml-2 font-mono text-[10px] text-muted-foreground">{{ p.model }}</span>
          </div>
          <Badge :variant="p.available ? 'success' : 'default'" dot>{{ p.available ? 'disponible' : 'sin config' }}</Badge>
        </div>
      </Card>

      <!-- N3: Cuotas observadas -->
      <Card v-if="quotaRows.length" class="space-y-1 p-5">
        <p class="mb-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">Cuotas observadas</p>
        <p class="mb-1 font-mono text-[9px] text-muted-foreground/60">UNKNOWN = el proveedor no informa límites; se penaliza levemente, jamás se asume ilimitado.</p>
        <div v-for="row in quotaRows" :key="row.id" class="flex items-center justify-between py-1.5">
          <span class="font-mono text-xs">{{ row.id }}</span>
          <div class="flex items-center gap-3 font-mono text-xs tabular-nums">
            <span class="text-muted-foreground">{{ row.rpm }}/min hoy {{ row.tokensToday }} tok</span>
            <Badge :variant="row.limitsKnown ? 'success' : 'default'">{{ row.limitLabel }}</Badge>
          </div>
        </div>
      </Card>

      <!-- OAR runtime -->
      <Card v-if="state.oar" class="space-y-3 p-5">
        <button
          class="flex w-full items-center justify-between"
          @click="showRaw = !showRaw"
        >
          <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">OAR Runtime</p>
          <span class="font-mono text-[10px] text-muted-foreground">{{ showRaw ? '[ocultar]' : '[detalles]' }}</span>
        </button>
        <template v-if="state.oar.initialized">
          <!-- Eventos recientes de modo -->
          <div v-if="state.oar.resilience?.recent_events?.length" class="space-y-1">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Eventos recientes</p>
            <div v-for="(ev, i) in state.oar.resilience.recent_events.slice(0, 5)" :key="i" class="flex items-center justify-between rounded border border-border/20 px-2 py-1">
              <span class="font-mono text-[11px]" :class="ev.mode === 'normal' ? 'text-success' : 'text-warning'">{{ ev.mode }}</span>
              <span class="line-clamp-1 font-mono text-[10px] text-muted-foreground">{{ ev.reason }}</span>
            </div>
          </div>
          <!-- N4: JSON crudo bajo demanda -->
          <pre v-if="showRaw" class="max-h-72 overflow-auto rounded-lg border border-border/20 bg-surface/20 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{{ JSON.stringify(state.oar.providers ?? state.oar, null, 2) }}</pre>
        </template>
        <p v-else class="text-sm text-muted-foreground">{{ state.oar.message || 'OAR no inicializado aún' }}</p>
      </Card>

      <!-- Errores honestos -->
      <Card v-if="state.errors.length" class="p-5">
        <p class="font-mono text-[10px] uppercase tracking-wider text-error">Fuentes caídas</p>
        <p class="mt-1 font-mono text-xs text-muted-foreground">{{ state.errors.join(' · ') }} — el resto de la página usa lo que sí respondió.</p>
      </Card>
    </template>
  </div>
</template>
