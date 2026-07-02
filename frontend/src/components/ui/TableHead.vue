<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <th
    :class="cn(
      'h-10 px-3 text-left align-middle text-xs font-semibold uppercase tracking-wider text-muted-foreground',
      '[&:has([role=checkbox])]:pr-0',
      props.class,
    )"
  >
    <slot />
  </th>
</template>
