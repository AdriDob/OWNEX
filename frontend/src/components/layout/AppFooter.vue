<script setup lang="ts">
import { MessageCircle, HelpCircle } from '@lucide/vue'

const emit = defineEmits<{ 'toggleCopilot': [] }>()
</script>

<template>
  <footer class="border-t border-border/20 bg-background/60 px-6 py-3 backdrop-blur-sm">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <router-link
          to="/faqs"
          class="flex items-center gap-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
        >
          <HelpCircle class="h-3.5 w-3.5" />
          <span class="font-mono">FAQs</span>
        </router-link>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="emit('toggleCopilot')"
          class="flex items-center gap-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
        >
          <MessageCircle class="h-3.5 w-3.5" />
          <span class="font-mono">Asistente</span>
        </button>
      </div>
      <span class="font-mono text-[9px] text-muted-foreground/50">OWNEX v5.1.0</span>
    </div>
  </footer>
</template>
