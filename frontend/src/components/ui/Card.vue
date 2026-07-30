<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  variant?: 'default' | 'tactical' | 'glass'
  highlight?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  highlight: false,
})
</script>

<template>
  <div
    :class="cn(
      variant === 'tactical' ? 'tactical-panel' : variant === 'glass' ? 'glass-terminal' : 'card-base',
      'rounded-xl ownex-hover-lift',
      highlight && 'card-highlight',
      props.class,
    )"
  >
    <slot />
  </div>
</template>
