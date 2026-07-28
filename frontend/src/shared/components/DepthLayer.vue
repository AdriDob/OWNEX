<script setup lang="ts">
/**
 * DepthLayer — CSS z-index and shadow elevation layer.
 * Wraps content with a specific depth level (0-3)
 * that maps to background opacity and shadow intensity.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** Depth level: 0 (transparent) | 1 | 2 | 3 (most elevated) */
  level?: 0 | 1 | 2 | 3
  /** Whether to add will-change GPU hint */
  gpu?: boolean
  /** Position mode */
  position?: 'relative' | 'absolute' | 'fixed'
  /** Custom z-index (overrides default level mapping) */
  zIndex?: number
}>(), {
  level: 1,
  gpu: false,
  position: 'relative',
})

const zValues: Record<number, string> = {
  0: 'z-0',
  1: 'z-10',
  2: 'z-30',
  3: 'z-50',
}

const shadowValues: Record<number, string> = {
  0: '',
  1: 'shadow-depth-1',
  2: 'shadow-depth-2',
  3: 'shadow-depth-3',
}

const classes = computed(() => [
  `depth-layer depth-${props.level}`,
  shadowValues[props.level],
  props.zIndex != null ? `z-${props.zIndex}` : zValues[props.level],
  props.position === 'fixed' ? 'fixed' : props.position === 'absolute' ? 'absolute' : 'relative',
  props.gpu ? 'gpu-layer' : '',
].filter(Boolean).join(' '))
</script>

<template>
  <div :class="classes">
    <slot />
  </div>
</template>
