<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
  variant?: 'default' | 'premium' | 'gold' | 'highlight'
  hover?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  hover: true,
})
</script>

<template>
  <div
    :class="cn(
      'rounded-xl transition-all duration-300',
      variant === 'premium' && 'card-premium',
      variant === 'gold' && 'card-base card-gold',
      variant === 'highlight' && 'card-base card-highlight',
      variant === 'default' && 'card-base',
      hover && 'hover-lift',
      props.class,
    )"
  >
    <slot />
  </div>
</template>
