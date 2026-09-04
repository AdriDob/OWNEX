<script setup lang="ts">
defineProps<{
  lines?: number
  type?: 'text' | 'card' | 'avatar' | 'chart'
  class?: string
}>()
</script>

<template>
  <div :class="['animate-pulse space-y-2', $props.class]">
    <!-- Avatar skeleton -->
    <template v-if="type === 'avatar'">
      <div class="flex items-center gap-3">
        <div class="h-10 w-10 rounded-full bg-surface/50" />
        <div class="flex-1 space-y-2">
          <div class="h-3 w-1/3 rounded bg-surface/50" />
          <div class="h-2 w-1/4 rounded bg-surface/30" />
        </div>
      </div>
    </template>

    <!-- Card skeleton -->
    <template v-else-if="type === 'card'">
      <div class="rounded-xl border border-border/30 p-4 space-y-3">
        <div class="h-4 w-1/3 rounded bg-surface/50" />
        <div class="h-3 w-full rounded bg-surface/30" />
        <div class="h-3 w-2/3 rounded bg-surface/30" />
        <div class="flex gap-2 mt-4">
          <div class="h-6 w-16 rounded-full bg-surface/50" />
          <div class="h-6 w-20 rounded-full bg-surface/30" />
        </div>
      </div>
    </template>

    <!-- Chart skeleton -->
    <template v-else-if="type === 'chart'">
      <div class="rounded-xl border border-border/30 p-4 space-y-3">
        <div class="h-4 w-1/4 rounded bg-surface/50" />
        <div class="flex items-end gap-1 h-32">
          <div v-for="i in 12" :key="i" class="flex-1 rounded-t bg-surface/40" :style="{ height: `${20 + Math.random() * 80}%` }" />
        </div>
      </div>
    </template>

    <!-- Text skeleton -->
    <template v-else>
      <div v-for="i in (lines || 3)" :key="i" class="space-y-2">
        <div class="h-3 rounded bg-surface/50" :style="{ width: `${60 + Math.random() * 40}%` }" />
      </div>
    </template>
  </div>
</template>
