<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <div
    :class="cn('flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface text-sm font-semibold text-muted-foreground', props.class)"
  >
    <slot />
  </div>
</template>
