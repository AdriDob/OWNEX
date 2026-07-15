<script setup lang="ts">
import { AlertTriangle, RefreshCw } from '@lucide/vue'

interface Props {
  title?: string
  message?: string
  retry?: () => void
}

withDefaults(defineProps<Props>(), {
  title: 'Error de conexión',
  message: 'Ocurrió un error al cargar los datos',
})
</script>

<template>
  <div :class="['flex flex-col items-center py-20 text-center animate-in', $attrs.class as string]">
    <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
      <AlertTriangle class="h-8 w-8 text-destructive" />
    </div>
    <p class="text-sm font-semibold text-foreground">{{ title }}</p>
    <p class="mt-1 text-xs text-muted-foreground max-w-md">{{ message }}</p>
    <button
      v-if="retry"
      @click="retry"
      class="mt-4 inline-flex items-center gap-2 rounded-lg border border-border bg-transparent px-4 py-2 text-xs font-semibold text-foreground hover:bg-surface/50 transition-colors"
    >
      <RefreshCw class="h-3.5 w-3.5" />
      Reintentar
    </button>
  </div>
</template>
