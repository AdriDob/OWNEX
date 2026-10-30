<script setup lang="ts">
/**
 * SkeletonCard — Animated loading placeholder
 * Replicates the shape of content cards during data loading.
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Height class (Tailwind) */
    height?: string
    /** Width class (Tailwind) */
    width?: string
    /** Number of skeleton lines */
    lines?: number
    /** Show avatar circle */
    avatar?: boolean
    /** Border radius */
    radius?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  }>(),
  {
    height: 'h-4',
    width: 'w-full',
    lines: 3,
    avatar: false,
    radius: 'lg',
  },
)

const radiusClass = computed(() => {
  const map = { sm: 'rounded-sm', md: 'rounded-lg', lg: 'rounded-xl', xl: 'rounded-2xl', full: 'rounded-full' }
  return map[props.radius]
})
</script>

<template>
  <div :class="['glass-panel p-4', radiusClass]">
    <div class="flex gap-3" v-if="avatar">
      <div class="w-10 h-10 rounded-full skeleton-pulse shrink-0" />
      <div class="flex-1 space-y-2">
        <div class="skeleton-pulse h-4 w-1/3 rounded" />
        <div class="skeleton-pulse h-3 w-1/2 rounded" />
      </div>
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="i in lines"
        :key="i"
        :class="[
          'skeleton-pulse rounded',
          props.height,
          i === lines ? 'w-2/3' : i === 1 ? 'w-1/2' : props.width,
        ]"
      />
    </div>
  </div>
</template>
