<script setup lang="ts">
import { ref } from 'vue'
import { AlertCircle, RefreshCw, Copy, X, ChevronDown, ChevronUp } from '@lucide/vue'
import Button from './Button.vue'

const props = withDefaults(defineProps<{
  error: string
  title?: string
  onRetry?: () => void
  onDismiss?: () => void
  details?: string
}>(), {
  title: 'Error',
})

const showDetails = ref(false)

async function copyError() {
  const text = `${props.title}: ${props.error}${props.details ? `\n\nDetails:\n${props.details}` : ''}`
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
}
</script>

<template>
  <div class="rounded-lg border border-[var(--color-destructive)]/30 bg-[var(--color-destructive)]/5 p-4" role="alert">
    <div class="flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-destructive shrink-0 mt-0.5" />
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-destructive">{{ title }}</p>
        <p class="text-sm text-muted mt-1 leading-relaxed">{{ error }}</p>

        <div v-if="showDetails && details" class="mt-2 p-2 rounded bg-[var(--color-background)] border border-[var(--color-border)]/40">
          <pre class="text-xs font-mono text-foreground/70 whitespace-pre-wrap">{{ details }}</pre>
        </div>

        <div class="flex flex-wrap gap-2 mt-3">
          <Button v-if="onRetry" size="sm" variant="outline" @click="onRetry">
            <RefreshCw class="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
          <Button v-if="details" size="sm" variant="ghost" @click="showDetails = !showDetails">
            <component :is="showDetails ? ChevronUp : ChevronDown" class="w-3.5 h-3.5 mr-1" />
            {{ showDetails ? 'Hide' : 'Details' }}
          </Button>
          <Button size="sm" variant="ghost" @click="copyError">
            <Copy class="w-3.5 h-3.5 mr-1" />
            Copy Error
          </Button>
        </div>
      </div>
      <button
        v-if="onDismiss"
        class="shrink-0 text-muted hover:text-foreground transition-colors p-0.5"
        @click="onDismiss"
        aria-label="Dismiss error"
      >
        <X class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>
