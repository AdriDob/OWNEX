<template>
  <div class="flex flex-col items-center justify-center py-12 gap-3" role="status" aria-live="polite">
    <!-- Spinner -->
    <div class="relative h-8 w-8">
      <div class="absolute inset-0 rounded-full border-2 border-[var(--ownex-border)]" />
      <div
        class="absolute inset-0 rounded-full border-2 border-transparent border-t-[var(--ownex-accent)] animate-spin"
      />
    </div>
    <!-- Text -->
    <span v-if="text" class="text-sm text-[var(--ownex-text-secondary)]">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  text?: string
}>()
</script>
