<script setup lang="ts">
import { X } from '@lucide/vue'
import { useToast } from '@/composables/useToast'

const { toasts, removeToast, iconMap, iconColorMap } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts" :key="t.id"
          class="pointer-events-auto flex items-start gap-3 rounded-xl border border-border/40 bg-surface/95 px-4 py-3 shadow-2xl backdrop-blur-xl w-72"
          :class="'border-l-2 ' + (t.type === 'success' ? 'border-l-success' : t.type === 'error' ? 'border-l-destructive' : t.type === 'warning' ? 'border-l-warning' : 'border-l-primary')"
        >
          <component :is="iconMap[t.type]" :class="['mt-0.5 h-4 w-4 shrink-0', iconColorMap[t.type]]" />
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-foreground">{{ t.title }}</p>
            <p v-if="t.message" class="mt-0.5 text-[10px] text-muted-foreground leading-relaxed">{{ t.message }}</p>
          </div>
          <button @click="removeToast(t.id)" class="shrink-0 rounded p-0.5 text-muted-foreground/40 hover:text-muted-foreground transition-colors">
            <X class="h-3 w-3" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.9);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.9);
}
.toast-move {
  transition: transform 0.2s ease;
}
</style>
