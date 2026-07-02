<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  hover?: boolean
  clickable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hover: true,
  clickable: false,
})
</script>

<template>
  <div
    :class="cn(
      'rounded-xl border border-border/60 bg-[#11131f]/60 backdrop-blur-sm',
      hover && 'hover-lift',
      clickable && 'cursor-pointer',
      props.class,
    )"
  >
    <slot />
  </div>
</template>
