<template>
  <div class="rounded-lg border border-[var(--ownex-border)] bg-[var(--ownex-bg-surface)] p-4">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-xs text-[var(--ownex-text-secondary)]">{{ label }}</span>
    </div>
    <div class="text-lg font-mono font-semibold" :class="variantClass">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: string
  icon?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
}>()

const variantClass = computed(() => {
  switch (props.variant) {
    case 'success': return 'text-[var(--ownex-green)]'
    case 'warning': return 'text-[var(--ownex-yellow)]'
    case 'error': return 'text-[var(--ownex-danger)]'
    default: return 'text-[var(--ownex-text-primary)]'
  }
})
</script>
