<script setup lang="ts">
/**
 * AnimatedCounter — Spring-driven count-up number display.
 * Animates from start value to target when visible.
 */
import { ref, toRef } from 'vue'
import { useAnimatedCounter } from '../composables/useAnimatedCounter'
import { useInViewport } from '../composables/useInViewport'

const props = withDefaults(defineProps<{
  /** The target numeric value */
  value: number
  /** Start value (default: 0) */
  from?: number
  /** Decimal places */
  decimals?: number
  /** Suffix text (e.g. "%", " GB") */
  suffix?: string
  /** Prefix text (e.g. "$") */
  prefix?: string
  /** Duration in seconds (default: 0.6) */
  duration?: number
  /** Use spring physics (default: true) */
  spring?: boolean
  /** Delay animation until element is in viewport */
  lazy?: boolean
  /** Font size class */
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl'
}>(), {
  from: 0,
  decimals: 0,
  suffix: '',
  prefix: '',
  duration: 0.6,
  spring: true,
  lazy: false,
  size: '2xl',
})

const displayRef = ref<HTMLElement | null>(null)
const valueRef = toRef(props, 'value')
const visible = ref(!props.lazy)

const { isIntersecting } = useInViewport(displayRef, { once: true, threshold: 0.1 })

// When lazy, only animate once visible
if (props.lazy) {
  // watchEffect inside useAnimatedCounter handles this
  import('vue').then(({ watch }) => {
    watch(isIntersecting, (val) => {
      if (val) visible.value = true
    })
  })
}

const { isAnimating } = useAnimatedCounter(displayRef, valueRef, {
  from: props.from,
  duration: props.duration,
  decimals: props.decimals,
  suffix: props.suffix,
  prefix: props.prefix,
  spring: props.spring,
})

const sizeClass: Record<string, string> = {
  xs: 'text-xs',
  sm: 'text-sm',
  base: 'text-base',
  lg: 'text-lg',
  xl: 'text-xl',
  '2xl': 'text-2xl',
  '3xl': 'text-3xl',
  '4xl': 'text-4xl',
}
</script>

<template>
  <span
    ref="displayRef"
    :class="[
      sizeClass[size],
      'font-semibold tabular-nums',
      isAnimating ? 'count-in' : '',
    ]"
  >
    {{ prefix }}{{ Number(value).toFixed(decimals) }}{{ suffix }}
  </span>
</template>
