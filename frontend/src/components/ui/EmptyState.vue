<template>
  <div class="flex flex-col items-center justify-center py-16 gap-4 text-center">
    <!-- Icon slot or default -->
    <div class="h-16 w-16 rounded-2xl bg-[var(--ownex-bg-elevated)] flex items-center justify-center">
      <slot name="icon">
        <svg class="h-8 w-8 text-[var(--ownex-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      </slot>
    </div>
    <!-- Title -->
    <h3 class="text-lg font-medium text-[var(--ownex-text-primary)]">{{ title }}</h3>
    <!-- Description -->
    <p v-if="description" class="text-sm text-[var(--ownex-text-secondary)] max-w-sm">{{ description }}</p>
    <!-- Action slot -->
    <slot name="action" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>
