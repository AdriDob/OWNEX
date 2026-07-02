<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

const props = defineProps<Props>()
</script>

<template>
  <td
    :class="cn(
      'p-3 align-middle text-sm',
      '[&:has([role=checkbox])]:pr-0',
      props.class,
    )"
  >
    <slot />
  </td>
</template>
