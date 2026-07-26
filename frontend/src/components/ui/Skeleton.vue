<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  variant?: 'shimmer' | 'crt' | 'pulse'
}
const props = withDefaults(defineProps<Props>(), {
  variant: 'shimmer',
})
</script>

<template>
  <div
    :class="cn(
      'relative overflow-hidden rounded-md',
      variant === 'crt' ? 'bg-surface/60 border border-border/30' : 'bg-surface/50',
      props.class,
    )"
  >
    <!-- Shimmer variant -->
    <div
      v-if="variant === 'shimmer'"
      class="absolute inset-0 -translate-x-full"
      style="background: linear-gradient(90deg, transparent, rgba(0,255,65,0.04), transparent); animation: shimmerSlide 1.8s ease-in-out infinite;"
    />
    <!-- CRT flicker variant -->
    <div
      v-if="variant === 'crt'"
      class="absolute inset-0"
      style="background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,65,0.04) 2px, rgba(0,255,65,0.04) 4px); animation: phosphorFlicker 0.1s infinite;"
    />
    <!-- Pulse variant -->
    <div
      v-if="variant === 'pulse'"
      class="absolute inset-0 skeleton-pulse"
    />
  </div>
</template>
