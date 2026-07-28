<script setup lang="ts">
/**
 * StatusDot — Animated status indicator dot.
 * Uses CSS glow matching the status color.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  status: 'success' | 'warning' | 'error' | 'pending' | 'off' | 'active'
  /** Show pulse animation */
  pulse?: boolean
  /** Size: sm (6px) | md (8px) | lg (12px) */
  size?: 'sm' | 'md' | 'lg'
  /** Optional label shown alongside */
  label?: string
}>(), {
  pulse: false,
  size: 'md',
})

const dotClass = computed(() => {
  const sizeClasses = { sm: 'w-1.5 h-1.5', md: 'w-2 h-2', lg: 'w-3 h-3' }
  return [
    'rounded-full inline-block shrink-0',
    sizeClasses[props.size],
    props.status === 'success' || props.status === 'active' ? 'bg-success shadow-[0_0_6px_rgba(34,197,94,0.4)]' : '',
    props.status === 'warning' ? 'bg-warning shadow-[0_0_6px_rgba(245,158,11,0.4)]' : '',
    props.status === 'error' ? 'bg-destructive shadow-[0_0_6px_rgba(239,68,68,0.4)]' : '',
    props.status === 'pending' ? 'bg-muted animate-pulse' : '',
    props.status === 'off' ? 'bg-zinc-700' : '',
    props.pulse ? 'animate-pulse' : '',
  ].filter(Boolean).join(' ')
})
</script>

<template>
  <span class="inline-flex items-center gap-1.5">
    <span :class="dotClass" aria-hidden="true" />
    <span v-if="label" class="text-xs text-muted-foreground">{{ label }}</span>
  </span>
</template>
