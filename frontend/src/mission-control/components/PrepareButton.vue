<script setup lang="ts">
/**
 * PrepareButton — The main "Prepare OWNEX" action button
 * Big, centered, primary call-to-action with pulse animation.
 * Changes state based on readiness phase.
 */
import { computed } from 'vue'
import type { ReadinessPhase } from '@/shared/types'

const props = defineProps<{
  phase: ReadinessPhase
  score: number
  disabled?: boolean
}>()

const emit = defineEmits<{
  'prepare': []
  'cancel': []
  'rescan': []
}>()

const buttonText = computed(() => {
  switch (props.phase) {
    case 'scanning': return 'Escaneando sistema…'
    case 'preparing': return 'Preparando OWNEX…'
    case 'ready': return '✓ Sistema listo'
    default: return props.score >= 80 ? 'Verificar de nuevo' : '🚀 Prepare OWNEX'
  }
})

const isActive = computed(() => props.phase === 'idle' || props.phase === 'ready')
const isLoading = computed(() => props.phase === 'scanning' || props.phase === 'preparing')

function handleClick() {
  if (!isActive.value) return
  if (props.phase === 'ready') {
    emit('rescan')
  } else {
    emit('prepare')
  }
}
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <button
      :disabled="!isActive && !(phase === 'preparing')"
      class="relative px-10 py-4 rounded-xl font-bold text-base tracking-wide transition-all duration-300"
      :class="[
        isActive && !disabled ? 'bg-primary text-primary-foreground hover:brightness-110 hover:shadow-[0_0_30px_rgba(59,130,246,0.3)] active:scale-[0.98]' : '',
        !isActive && phase !== 'preparing' ? 'bg-muted/30 text-muted-foreground cursor-not-allowed' : '',
        phase === 'preparing' ? 'bg-primary/50 text-primary-foreground cursor-wait' : '',
        phase === 'ready' ? 'bg-success/20 text-success border border-success/30 hover:bg-success/30' : '',
        isActive ? 'prepare-pulse' : '',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
      ]"
      @click="handleClick"
    >
      <span v-if="isLoading" class="inline-flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-current dot-pulse" />
        <span class="w-2 h-2 rounded-full bg-current dot-pulse" />
        <span class="w-2 h-2 rounded-full bg-current dot-pulse" />
      </span>
      <span v-else>{{ buttonText }}</span>
    </button>

    <button
      v-if="phase === 'preparing'"
      class="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
      @click="$emit('cancel')"
    >
      Cancelar
    </button>

    <p v-if="phase === 'idle' && score < 80" class="text-xs text-muted-foreground max-w-sm text-center">
      OWNEC detectará y configurará automáticamente las herramientas necesarias para bug bounty
    </p>
  </div>
</template>
