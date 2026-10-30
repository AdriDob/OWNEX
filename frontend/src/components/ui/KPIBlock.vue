<script setup lang="ts">
import { Activity, DollarSign, TrendingUp } from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  label: string
  value: string | number
  icon?: string
  trend?: number
  format?: 'number' | 'currency' | 'percent'
  color?: 'default' | 'primary' | 'gold' | 'success' | 'warning' | 'info'
  size?: 'sm' | 'md' | 'lg'
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  format: 'number',
  color: 'default',
  size: 'md',
})

const displayValue = ref(0)
const targetValue = ref(0)

const iconMap: Record<string, any> = {
  DollarSign,
  TrendingUp,
  Activity,
}

const colorMap: Record<string, string> = {
  default: 'text-foreground',
  primary: 'text-primary',
  gold: 'text-gold',
  success: 'text-success',
  warning: 'text-warning',
  info: 'text-info',
}

const iconColorMap: Record<string, string> = {
  default: 'text-muted-foreground',
  primary: 'text-primary',
  gold: 'text-gold',
  success: 'text-success',
  warning: 'text-warning',
  info: 'text-info',
}

const iconComponent = computed(() => {
  if (!props.icon) return null
  return iconMap[props.icon] || null
})

function animateValue(start: number, end: number, duration = 600) {
  const startTime = performance.now()
  function tick(now: number) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - (1 - progress) ** 3
    displayValue.value = start + (end - start) * eased
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

function parseValue(val: string | number): number {
  if (typeof val === 'number') return val
  return parseFloat(String(val).replace(/[^0-9.-]/g, '')) || 0
}

watch(
  () => props.value,
  (val) => {
    targetValue.value = parseValue(val)
  },
  { immediate: true },
)

watch(
  targetValue,
  (end) => {
    animateValue(displayValue.value || 0, end)
  },
  { immediate: false },
)

onMounted(() => {
  targetValue.value = parseValue(props.value)
})

function formatted(val: number): string {
  if (props.format === 'currency') {
    if (val >= 1_000_000) return '$' + (val / 1_000_000).toFixed(1) + 'M'
    if (val >= 1_000) return '$' + (val / 1_000).toFixed(1) + 'k'
    return '$' + Math.round(val).toLocaleString()
  }
  if (props.format === 'percent') return val.toFixed(1) + '%'
  if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M'
  if (val >= 1_000) return (val / 1_000).toFixed(1) + 'k'
  return Math.round(val).toLocaleString()
}
</script>

<template>
  <div :class="cn('flex flex-col gap-1', props.class)">
    <div class="flex items-center justify-between">
      <span class="font-mono text-[10px] font-medium tracking-wider text-muted-foreground">{{ label }}</span>
      <component :is="iconComponent" v-if="iconComponent" :class="['h-3.5 w-3.5', iconColorMap[color]]" />
    </div>
    <div class="flex items-baseline gap-2">
      <span :class="[
        size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-base' : 'text-xl',
        'font-bold font-mono tabular-nums num-transition',
        colorMap[color],
      ]">
        {{ formatted(displayValue) }}
      </span>
      <span v-if="trend !== undefined" :class="[
        'flex items-center gap-0.5 font-mono text-[11px]',
        trend >= 0 ? 'text-success' : 'text-destructive',
      ]">
        <TrendingUp v-if="trend >= 0" class="h-3 w-3" />
        <TrendingUp v-else class="h-3 w-3 rotate-180" />
        {{ Math.abs(trend).toFixed(1) }}%
      </span>
    </div>
  </div>
</template>
