<script setup lang="ts">
/**
 * Structured, calm error/connectivity state.
 *
 * Replaces raw `bg-destructive` banners. Per the CALM UX decision
 * (.ai/DECISIONS.md 2026-08-10): connectivity waits are NOT red — they use the
 * accent color and explain what is happening. Real errors render as
 * ERROR / CAUSA / ACCIÓN RECOMENDADA with an optional retry.
 */
import { computed } from 'vue'
import { AlertTriangle, Loader2, RefreshCw, WifiOff } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { backendStatus, retryConnection } from '@/lib/backend'

const props = withDefaults(
  defineProps<{
    /** Short error title (the ERROR line). */
    title?: string
    /** Raw message from the API layer (the CAUSE line). */
    error?: string | null
    /** Optional explicit action hint; derived automatically when absent. */
    action?: string
    /** Called by the retry button; defaults to backend re-discovery. */
    onRetry?: () => void | Promise<void>
  }>(),
  {
    title: 'No se pudo completar la operación',
    error: null,
    action: '',
    onRetry: undefined,
  },
)

/** Backend not ready → this is a connectivity wait, not a hard failure. */
const isConnecting = computed(() => backendStatus.value !== 'ready')

const cause = computed(() => props.error || '')

const recommendedAction = computed(() => {
  if (props.action) return props.action
  if (isConnecting.value)
    return 'OWNEX está localizando el backend local (puertos 8000-8099). Se reconecta solo; no necesitás hacer nada.'
  if (cause.value.includes('Sesión expirada'))
    return 'Reiniciá OWNEX Alpha para regenerar tu sesión local.'
  return 'Verificá tu conexión y probá de nuevo con "Reintentar".'
})

async function retry(): Promise<void> {
  if (props.onRetry) await props.onRetry()
  else retryConnection()
}
</script>

<template>
  <!-- Connecting: calm, informative, NOT destructive -->
  <div
    v-if="isConnecting"
    class="flex flex-col gap-2 rounded-lg border border-accent/30 bg-accent/5 px-4 py-3"
    role="status"
  >
    <div class="flex items-center gap-2 text-sm text-accent">
      <Loader2 class="h-4 w-4 shrink-0 animate-spin" />
      <span>Conectando con el backend de OWNEX…</span>
    </div>
    <p class="pl-6 text-xs leading-relaxed text-muted-foreground">{{ recommendedAction }}</p>
  </div>

  <!-- Hard error: structured ERROR / CAUSA / ACCIÓN -->
  <div
    v-else
    class="flex flex-col gap-1.5 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3"
    role="alert"
  >
    <div class="flex items-center gap-2 text-sm font-medium text-destructive">
      <AlertTriangle class="h-4 w-4 shrink-0" />
      <span>{{ title }}</span>
    </div>
    <p v-if="cause" class="pl-6 font-mono text-xs text-muted-foreground">{{ cause }}</p>
    <p class="pl-6 text-xs leading-relaxed text-foreground/80">
      <WifiOff v-if="isConnecting" class="mr-1 inline h-3 w-3" />
      <span class="font-medium">Acción recomendada:</span> {{ recommendedAction }}
    </p>
    <div class="mt-1 pl-6">
      <Button size="sm" variant="outline" class="h-7 gap-1.5 px-2.5 text-xs" @click="retry">
        <RefreshCw class="h-3 w-3" />
        Reintentar
      </Button>
    </div>
  </div>
</template>
