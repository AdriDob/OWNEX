<script setup lang="ts">
/**
 * TransitionOverlay — Manages splash→dashboard crossfade
 * Applies CSS opacity transition to the splash layer.
 * Emits 'done' when the transition completes.
 */
import { onMounted } from 'vue'

const emit = defineEmits<{
  done: []
}>()

const props = withDefaults(
  defineProps<{
    /** Transition duration in ms */
    duration?: number
  }>(),
  {
    duration: 700,
  },
)

onMounted(() => {
  setTimeout(() => emit('done'), props.duration + 50)
})
</script>

<template>
  <div
    class="fixed inset-0 z-[200] pointer-events-none"
    :style="{ transition: `opacity ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)` }"
  >
    <slot />
  </div>
</template>
