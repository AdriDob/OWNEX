<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  max?: number
  color?: string
  height?: number
  label?: string
  showValue?: boolean
  animated?: boolean
}>(), {
  max: 100,
  color: 'bg-primary',
  height: 6,
  showValue: false,
  animated: true,
})

const innerWidth = ref(0)
const el = ref<HTMLElement | null>(null)
let rafId = 0

function animateWidth(from: number, to: number) {
  cancelAnimationFrame(rafId)
  const duration = 600
  const start = performance.now()
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    innerWidth.value = from + (to - from) * eased
    if (progress < 1) rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}

watch(() => props.value, (to) => {
  if (props.animated) animateWidth(0, (to / props.max) * 100)
  else innerWidth.value = (to / props.max) * 100
})

onMounted(() => {
  innerWidth.value = (props.value / props.max) * 100
})
</script>

<template>
  <div class="space-y-1">
    <div v-if="label || showValue" class="flex items-center justify-between">
      <span v-if="label" class="text-[10px] text-muted-foreground">{{ label }}</span>
      <span v-if="showValue" class="text-[10px] font-medium tabular-nums text-foreground">
        {{ value }}{{ max !== 100 ? '/' + max : '%' }}
      </span>
    </div>
    <div
      ref="el"
      class="overflow-hidden rounded-full bg-surface/50"
      :style="{ height: height + 'px' }"
    >
      <div
        class="h-full rounded-full transition-all duration-300"
        :class="[color]"
        :style="{ width: innerWidth + '%' }"
      >
        <div v-if="animated && innerWidth > 20" class="h-full w-full animate-pulse opacity-20"
          style="background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent); background-size: 200% 100%; animation: shimmerSlide 2s ease-in-out infinite;"
        />
      </div>
    </div>
  </div>
</template>
