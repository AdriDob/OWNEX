<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { MessageCircle, X, Sparkles } from '@lucide/vue'

const props = defineProps<{
  message: string | null
}>()

const emit = defineEmits<{ dismiss: [] }>()
const visible = ref(false)

onMounted(() => {
  setTimeout(() => { visible.value = true }, 100)
})

onUnmounted(() => {
  visible.value = false
})
</script>

<template>
  <Transition name="bubble">
    <div v-if="message && visible" class="fixed bottom-20 right-6 z-[90] max-w-xs">
      <div class="relative rounded-2xl border border-primary/20 bg-surface shadow-xl p-3.5">
        <div class="absolute -top-1.5 right-4 h-3 w-3 rotate-45 border-l border-t border-primary/20 bg-surface" />
        <button class="absolute top-1.5 right-1.5 text-muted-foreground/40 hover:text-foreground transition-colors" @click="emit('dismiss')">
          <X class="h-3 w-3" />
        </button>
        <div class="flex items-start gap-2 pr-4">
          <Sparkles class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <p class="text-xs text-foreground leading-relaxed">{{ message }}</p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.bubble-enter-active, .bubble-leave-active { transition: all 0.25s ease; }
.bubble-enter-from, .bubble-leave-to { opacity: 0; transform: translateY(8px); }
</style>
