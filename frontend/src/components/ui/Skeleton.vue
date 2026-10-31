<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  rows?: number
  rowHeight?: string
  variant?: 'default' | 'brand' | 'glass'
}
const props = withDefaults(defineProps<Props>(), {
  rows: 3,
  rowHeight: '14px',
  variant: 'default',
})
</script>

<template>
  <div class="space-y-2">
    <!-- Línea de skeleton row -->
    <div
      v-for="row in computed(() => props.rows)"
      :key="row"
      class="ownex-skeleton inline-block animate-pulse"
      :style="{ height: props.rowHeight }"
    >
      <template v-if="props.variant === 'brand'">
        <div class="w-48 h-full rounded-lg bg-primary/20" />
        <div class="w-96 h-full rounded-lg bg-primary/20" />
        <div class="w-64 h-full rounded-lg bg-primary/20" />
      </template>
      <template v-if="props.variant === 'glass'">
        <div class="w-full h-full rounded-lg bg-surface/50" />
        <div class="w-3/4 h-full rounded-lg bg-surface/50" />
        <div class="w-1/2 h-full rounded-lg bg-surface/50" />
      </template>
      <template v-if="props.variant === 'default'">
        <!-- Barras horizontales progresivas -->
        <div class="w-64 h-full rounded-bg border border-border/20" />
        <div class="w-48 h-full rounded-bg border border-border/20" />
        <div class="w-32 h-full rounded-bg border border-border/20" />
      </template>
    </div>

    <!-- Skeletons cuadrados (avatars, cards) -->
    <div
      v-for="row in computed(() => props.rows)"
      :key="`square-${row}`"
      class="ownex-skeleton inline-block animate-pulse"
      :style="{ height: props.rowHeight }"
    >
      <template v-if="props.variant === 'brand'">
        <div class="w-16 h-16 rounded-full bg-primary/20" />
        <div class="w-24 h-24 rounded-full bg-primary/20" />
      </template>
      <template v-if="props.variant === 'glass'">
        <div class="w-16 h-16 rounded-full bg-surface/50" />
        <div class="w-24 h-24 rounded-full bg-surface/50" />
      </template>
      <template v-if="props.variant === 'default'">
        <div class="w-16 h-16 rounded-full bg-surface/50" />
        <div class="w-24 h-24 rounded-full bg-surface/50" />
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Skeleton uses Tailwind's built-in animate-pulse */
</style>