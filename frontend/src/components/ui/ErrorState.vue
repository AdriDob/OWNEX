<script setup lang="ts">
/**
 * ErrorState — explains WHAT happened, WHY, and WHAT to do next.
 * Never shows raw technical errors as sole explanation.
 */

import { AlertTriangle, RefreshCw } from '@lucide/vue'
import OwnexButton from './OwnexButton.vue'

interface Props {
  title?: string
  message: string
  details?: string
  retryLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Something went wrong',
  details: '',
  retryLabel: 'Retry',
})

const emit = defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-6 text-center">
    <!-- Icon -->
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 mb-4">
      <AlertTriangle class="h-6 w-6 text-destructive" />
    </div>

    <!-- Title -->
    <h3 class="text-sm font-semibold text-foreground mb-1">{{ title }}</h3>

    <!-- Message -->
    <p class="text-xs text-muted-foreground max-w-xs mb-2">{{ message }}</p>

    <!-- Details (technical, collapsed) -->
    <details v-if="details" class="mb-4">
      <summary class="text-[10px] text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
        Technical details
      </summary>
      <pre class="mt-2 text-[10px] text-muted-foreground bg-muted/20 rounded p-2 max-w-xs text-left overflow-x-auto">{{ details }}</pre>
    </details>

    <!-- Retry -->
    <OwnexButton variant="outline" size="sm" @click="emit('retry')">
      <RefreshCw class="h-3 w-3 mr-1.5" />
      {{ retryLabel }}
    </OwnexButton>
  </div>
</template>
