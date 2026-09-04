<script setup lang="ts">
/**
 * Button.vue — Backward-compatible re-export of OwnexButton.
 * Many pages import from '@/components/ui/Button.vue'.
 */
import OwnexButton from './OwnexButton.vue'

const props = defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'gold'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  fullWidth?: boolean
  type?: 'button' | 'submit' | 'reset'
}>()
</script>

<template>
  <OwnexButton v-bind="props">
    <slot />
  </OwnexButton>
</template>
