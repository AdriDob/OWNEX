<template>
  <div class="flex flex-col items-center justify-center py-16 gap-4 text-center">
    <!-- Error icon -->
    <div class="h-16 w-16 rounded-2xl bg-[var(--ownex-danger)]/10 flex items-center justify-center">
      <svg class="h-8 w-8 text-[var(--ownex-danger)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    </div>
    <!-- Title -->
    <h3 class="text-lg font-medium text-[var(--ownex-text-primary)]">{{ title }}</h3>
    <!-- Description -->
    <p v-if="description" class="text-sm text-[var(--ownex-text-secondary)] max-w-sm">{{ description }}</p>
    <!-- Retry button -->
    <button
      v-if="onRetry"
      class="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--ownex-bg-elevated)] text-[var(--ownex-text-primary)] border border-[var(--ownex-border)] hover:bg-[var(--ownex-border)] transition-colors"
      @click="onRetry"
    >
      Try Again
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
  onRetry?: () => void
}>()
</script>
