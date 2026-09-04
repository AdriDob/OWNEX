<script setup lang="ts">
const props = defineProps<{
  value: number // 0-100
  max?: number
  color?: 'primary' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  label?: string
}>()

const percentage = computed(() => {
  const max = props.max || 100
  return Math.min(100, Math.max(0, (props.value / max) * 100))
})

const colorClass = computed(() => {
  const colors = {
    primary: 'bg-primary',
    success: 'bg-emerald-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
  }
  return colors[props.color || 'primary']
})

const heightClass = computed(() => {
  const heights = { sm: 'h-1', md: 'h-1.5', lg: 'h-2.5' }
  return heights[props.size || 'md']
})

import { computed } from 'vue'
</script>

<template>
  <div class="w-full">
    <div v-if="showLabel || label" class="mb-1 flex items-center justify-between">
      <span class="text-[10px] font-mono text-muted-foreground">{{ label }}</span>
      <span class="text-[10px] font-mono text-muted-foreground">{{ Math.round(percentage) }}%</span>
    </div>
    <div :class="['w-full overflow-hidden rounded-full bg-surface/50', heightClass]">
      <div
        :class="['rounded-full transition-all duration-500 ease-out', colorClass, heightClass]"
        :style="{ width: `${percentage}%` }"
      />
    </div>
  </div>
</template>
