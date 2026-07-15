<script setup lang="ts">
import { Lightbulb, X } from '@lucide/vue'

defineProps<{
  title: string
  message: string
}>()

const emit = defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div class="flex items-start gap-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3">
    <Lightbulb class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
    <div class="flex-1 min-w-0">
      <p class="font-mono text-[11px] font-semibold text-foreground uppercase tracking-wider">{{ title }}</p>
      <p class="text-xs text-muted-foreground mt-0.5 leading-relaxed">{{ message }}</p>
    </div>
    <button class="shrink-0 text-muted-foreground/50 hover:text-foreground transition-colors" @click="emit('dismiss')">
      <X class="h-3.5 w-3.5" />
    </button>
  </div>
</template>
