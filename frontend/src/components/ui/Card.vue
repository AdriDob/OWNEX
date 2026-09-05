<script setup lang="ts">
/**
 * Card.vue — Backward-compatible re-export of OwnexCard.
 * Many pages import from '@/components/ui/Card.vue'.
 */
import OwnexCard from './OwnexCard.vue'

const props = defineProps<{
  variant?: 'base' | 'elevated' | 'highlight' | 'cycle'
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  hoverable?: boolean
  padded?: boolean
}>()
</script>

<template>
  <OwnexCard v-bind="props">
    <slot />
  </OwnexCard>
</template>
