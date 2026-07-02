<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  decimals?: number
  prefix?: string
  duration?: number
}>(), {
  decimals: 0,
  prefix: '',
  duration: 600,
})

const display = ref(0)
const el = ref<HTMLElement | null>(null)
let rafId = 0

function animate(from: number, to: number) {
  cancelAnimationFrame(rafId)
  const start = performance.now()
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / props.duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = from + (to - from) * eased
    if (progress < 1) rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}

watch(() => props.value, (to, from) => {
  animate(from || 0, to || 0)
})

onMounted(() => {
  display.value = props.value
})
</script>

<template>
  <span ref="el" class="num-transition tabular-nums">{{ prefix }}{{ display.toFixed(decimals) }}</span>
</template>
