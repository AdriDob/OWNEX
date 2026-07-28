<script setup lang="ts">
/**
 * ReadinessMeter — System Readiness Score display
 * Shows a ProgressRing with animated score + concise status text.
 */
import { computed } from 'vue'
import ProgressRing from '@/shared/components/ProgressRing.vue'

const props = defineProps<{
  score: number
  isReady: boolean
  isPreparing: boolean
}>()

const statusText = computed(() => {
  if (props.isPreparing) return 'Preparando OWNEX…'
  if (props.isReady) return 'Listo para Bug Bounty'
  if (props.score >= 50) return 'Configuración parcial — ejecutá Prepare OWNEX'
  if (props.score >= 20) return 'Se requiere configuración'
  return 'OWNEX sin configurar'
})

const statusColor = computed(() => {
  if (props.isPreparing) return 'text-primary'
  if (props.isReady) return 'text-success'
  if (props.score >= 50) return 'text-warning'
  return 'text-destructive'
})
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <ProgressRing
      :value="score"
      :size="160"
      :stroke-width="10"
    />
    <div class="text-center">
      <div :class="['text-sm font-medium tracking-wide', statusColor]">
        {{ statusText }}
      </div>
      <div class="text-xs text-muted-foreground mt-0.5">
        {{ score }}% · {{ isReady ? 'Listo' : 'Requiere acción' }}
      </div>
    </div>
  </div>
</template>
