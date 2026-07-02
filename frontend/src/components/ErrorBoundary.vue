<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { AlertTriangle, RefreshCw, ArrowLeft } from '@lucide/vue'
import { useRouter } from 'vue-router'

defineProps<{
  title?: string
}>()

const router = useRouter()
const error = ref<Error | null>(null)
const errorInfo = ref<string>('')

onErrorCaptured((err, instance, info) => {
  error.value = err as Error
  errorInfo.value = info
  console.error('[ErrorBoundary]', err, info)
  return false
})

function retry() {
  error.value = null
  errorInfo.value = ''
}

function goBack() {
  error.value = null
  errorInfo.value = ''
  router.back()
}
</script>

<template>
  <div v-if="error" class="flex flex-col items-center justify-center py-20 animate-in">
    <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10">
      <AlertTriangle class="h-7 w-7 text-destructive" />
    </div>
    <h2 class="text-base font-semibold text-foreground">
      {{ title || 'Algo salió mal' }}
    </h2>
    <p class="mt-1 max-w-xs text-center text-xs text-muted-foreground">
      {{ error.message || 'Ocurrió un error inesperado al cargar esta sección.' }}
    </p>
    <p v-if="errorInfo" class="mt-2 max-w-md text-center text-[9px] text-muted-foreground/50 font-mono">
      {{ errorInfo }}
    </p>
    <div class="mt-5 flex items-center gap-2">
      <button
        @click="retry"
        class="flex items-center gap-1.5 rounded-lg bg-primary/10 px-3.5 py-2 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
      >
        <RefreshCw class="h-3.5 w-3.5" />
        Reintentar
      </button>
      <button
        @click="goBack"
        class="flex items-center gap-1.5 rounded-lg bg-surface/30 px-3.5 py-2 text-xs font-medium text-muted-foreground hover:bg-surface/50 transition-colors"
      >
        <ArrowLeft class="h-3.5 w-3.5" />
        Volver
      </button>
    </div>
  </div>
  <slot v-else />
</template>

<style scoped>
.animate-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
