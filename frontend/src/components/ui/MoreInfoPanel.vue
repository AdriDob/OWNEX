<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDown, ChevronRight, Info } from '@lucide/vue'
import type { Component } from 'vue'
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{
  title: string
  open?: boolean
  icon?: Component
}>(), {
  open: false,
  icon: Info,
})

const isOpen = ref(props.open)

const emit = defineEmits<{
  toggle: [open: boolean]
}>()

function toggle() {
  isOpen.value = !isOpen.value
  emit('toggle', isOpen.value)
}
</script>

<template>
  <div class="rounded-lg border border-[var(--color-border)]/30 overflow-hidden transition-all duration-200" :class="{ 'border-primary/15': isOpen }">
    <button
      class="flex w-full items-center gap-2 px-3 py-2.5 text-xs font-medium text-foreground/70 hover:text-foreground hover:bg-surface-hover transition-colors"
      @click="toggle"
      :aria-expanded="isOpen"
      aria-label="Toggle more info"
    >
      <component :is="isOpen ? ChevronDown : ChevronRight" class="w-3.5 h-3.5 text-muted shrink-0" />
      <component :is="icon" class="w-3.5 h-3.5 text-muted shrink-0" />
      <span class="flex-1 text-left">{{ title }}</span>
    </button>
    <Transition name="expand">
      <div v-show="isOpen" class="border-t border-[var(--color-border)]/20">
        <div class="px-3 py-2 text-xs text-foreground/70 space-y-1.5">
          <slot />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: opacity 0.2s ease, max-height 0.25s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
