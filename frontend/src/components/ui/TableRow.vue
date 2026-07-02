<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <tr
    :class="cn(
      'border-b border-border/40 transition-colors',
      'hover:bg-surface/30 data-[state=selected]:bg-surface/50',
      props.class,
    )"
  >
    <slot />
  </tr>
</template>
