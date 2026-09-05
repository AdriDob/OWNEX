<script setup lang="ts">
/**
 * GlassPanel — Glassmorphism container with backdrop blur.
 * Represents depth layer surfaces in the OWNEX design system.
 */
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Glass strength: light | default | strong */
    variant?: 'light' | 'default' | 'strong'
    /** Whether to add border highlight */
    highlight?: boolean
    /** Rounded size: sm | md | lg | xl | full | none */
    radius?: 'sm' | 'md' | 'lg' | 'xl' | 'full' | 'none'
    /** Padding size (Tailwind scale) */
    padding?: 'none' | 'sm' | 'md' | 'lg'
    /** Tag to render as */
    tag?: string
  }>(),
  {
    variant: 'default',
    highlight: false,
    radius: 'md',
    padding: 'md',
    tag: 'div',
  },
)

const classes = computed(() => {
  const map = {
    variant: {
      light: 'glass-panel-light',
      default: 'glass-panel',
      strong: 'glass-panel-strong',
    },
    radius: {
      none: '',
      sm: 'rounded-sm',
      md: 'rounded-lg',
      lg: 'rounded-xl',
      xl: 'rounded-2xl',
      full: 'rounded-full',
    },
    padding: {
      none: '',
      sm: 'p-2',
      md: 'p-4',
      lg: 'p-6',
    },
  }

  return [
    map.variant[props.variant],
    map.radius[props.radius],
    map.padding[props.padding],
    props.highlight ? 'border-l-2 border-l-primary' : '',
    'gpu-layer',
  ]
    .filter(Boolean)
    .join(' ')
})
</script>

<template>
  <component :is="tag" :class="classes">
    <slot />
  </component>
</template>
