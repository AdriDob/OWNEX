<script setup lang="ts">
/**
 * AI Center — estado real de providers IA (spec §9).
 * Fuentes: /settings/ai/providers + /settings/ai/config + /oar/status.
 * Nunca muestra como disponible un provider caído (datos del backend).
 */
import { onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { fetchAiCenter, type AiCenterState } from '@/services/ownexData'

const loading = ref(true)
const state = ref<AiCenterState | null>(null)

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
        <p class="text-sm text-muted-foreground">Providers · modelo activo · OAR runtime</p>
      </div>
      <Badge v-if="state?.config" :variant="state.config.available ? 'success' : 'error'" dot>
        {{ state.config.active_provider }} · {{ state.config.available ? 'disponible' : 'caído' }}
      </Badge>
    </div>

    <LoadingState v-if="loading" />

    <template v-else-if="state">
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

      <!-- OAR runtime -->
      <Card v-if="state.oar" class="space-y-3 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">OAR Runtime</p>
        <template v-if="state.oar.initialized">
          <pre class="max-h-72 overflow-auto rounded-lg border border-border/20 bg-surface/20 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{{ JSON.stringify(state.oar.providers ?? state.oar, null, 2) }}</pre>
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
