<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  shimmer?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  shimmer: true,
})
</script>

<template>
  <div
    :class="cn('relative overflow-hidden rounded-md bg-surface/50', props.class)"
  >
    <div
      v-if="shimmer"
      class="absolute inset-0 -translate-x-full"
      style="background: linear-gradient(90deg, transparent, rgba(255,255,255,0.03), transparent); animation: shimmerSlide 1.8s ease-in-out infinite;"
    />
  </div>
</template>
