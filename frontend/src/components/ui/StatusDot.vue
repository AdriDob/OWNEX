<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  status: 'online' | 'offline' | 'warning' | 'error' | 'idle' | 'active'
  size?: 'sm' | 'md' | 'lg'
  pulse?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'sm',
  pulse: true,
})

const colorMap: Record<string, string> = {
  online: 'bg-success',
  offline: 'bg-muted',
  warning: 'bg-warning',
  error: 'bg-destructive',
  idle: 'bg-muted-foreground',
  active: 'bg-primary',
}
</script>

<template>
  <span :class="cn('relative inline-flex shrink-0', props.class)">
    <span
      v-if="pulse && (status === 'online' || status === 'active')"
      :class="[
        'absolute inline-flex h-full w-full animate-ping rounded-full opacity-40',
        colorMap[status],
      ]"
    />
    <span
      :class="[
        'relative inline-flex rounded-full',
        size === 'lg' ? 'h-3 w-3' : size === 'md' ? 'h-2 w-2' : 'h-1.5 w-1.5',
        colorMap[status],
      ]"
    />
  </span>
</template>
