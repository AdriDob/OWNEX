<script setup lang="ts">
/**
 * ProgressRing — SVG Circular Progress (radial meter)
 * Used for System Readiness Score, completion percentages.
 * Animates on mount with spring physics.
 */
import { computed, ref, onMounted } from 'vue'
import { animate } from 'motion'
import { useReducedMotion } from '../composables/useReducedMotion'

const props = withDefaults(defineProps<{
  /** Value 0-100 */
  value: number
  /** Size in px */
  size?: number
  /** Stroke width */
  strokeWidth?: number
  /** Color for filled portion */
  color?: string
  /** Show percentage text inside */
  showLabel?: boolean
  /** Label font size (Tailwind) */
  labelSize?: string
}>(), {
  size: 120,
  strokeWidth: 8,
  color: '#3b82f6',
  showLabel: true,
  labelSize: 'text-2xl',
})

const { shouldReduce } = useReducedMotion()
const radius = computed(() => (props.size - props.strokeWidth) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const viewBox = computed(() => `0 0 ${props.size} ${props.size}`)
const center = computed(() => props.size / 2)

const offset = ref(circumference.value) // start at full (empty)

const statusColor = computed(() => {
  if (props.value >= 80) return '#22c55e'  // green
  if (props.value >= 50) return '#f59e0b'  // amber
  if (props.value >= 25) return '#f97316'  // orange
  return '#ef4444'                         // red
})

onMounted(() => {
  if (shouldReduce()) {
    offset.value = circumference.value * (1 - props.value / 100)
    return
  }

  animate(() => offset.value, circumference.value * (1 - props.value / 100), {
    type: 'spring',
    stiffness: 80,
    damping: 14,
    onUpdate: (latest: number) => { offset.value = latest },
  })
})
</script>

<template>
  <div class="relative inline-flex items-center justify-center" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="viewBox" class="transform -rotate-90">
      <!-- Background circle -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        :stroke-width="strokeWidth"
        stroke="rgba(26, 26, 46, 0.4)"
        fill="none"
      />
      <!-- Progress arc -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        :stroke-width="strokeWidth"
        :stroke="color || statusColor"
        fill="none"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        class="gpu-layer"
        style="transition: stroke 0.3s ease"
      />
    </svg>
    <span v-if="showLabel" :class="[labelSize, 'absolute font-bold tabular-nums text-foreground']">
      {{ Math.round(value) }}%
    </span>
  </div>
</template>
