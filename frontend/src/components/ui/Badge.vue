<script setup lang="ts">
/**
 * Badge.vue — Backward-compatible re-export of OwnexBadge.
 * Many pages import from '@/components/ui/Badge.vue'.
 */
import OwnexBadge from './OwnexBadge.vue'

const props = defineProps<{
  variant?: 'default' | 'success' | 'warning' | 'error' | 'cycle' | 'gold' | 'platform'
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  platform?: 'hackerone' | 'bugcrowd' | 'intigriti' | 'synack' | 'yeswehack'
  size?: 'sm' | 'md'
  dot?: boolean
  removable?: boolean
}>()

const emit = defineEmits<{ remove: [] }>()
</script>

<template>
  <OwnexBadge v-bind="props" @remove="emit('remove')">
    <slot />
  </OwnexBadge>
</template>
