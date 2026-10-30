<script setup lang="ts">
import { Download, RefreshCw, Tag, Trash2, X } from '@lucide/vue'
import { type Component, computed } from 'vue'
import { useUIStore } from '@/stores/ui'
import Separator from './Separator.vue'

const props = withDefaults(
  defineProps<{
    container?: string
  }>(),
  {
    container: '',
  },
)

const store = useUIStore()

const count = computed(() => store.selectedIds.length)

interface Action {
  id: string
  label: string
  icon: Component
  handler: () => void
}

const actions: Action[] = [
  { id: 'export', label: 'Export', icon: Download, handler: () => store.handleMultiSelect('export') },
  { id: 'sync', label: 'Sync', icon: RefreshCw, handler: () => store.handleMultiSelect('sync') },
  { id: 'delete', label: 'Delete', icon: Trash2, handler: () => store.handleMultiSelect('delete') },
  { id: 'tag', label: 'Tag', icon: Tag, handler: () => store.handleMultiSelect('tag') },
]

function clear() {
  store.clearSelection()
}
</script>

<template>
  <Transition name="slide-up">
    <div v-if="count > 0" class="sticky bottom-4 mx-auto w-fit px-4 py-2 rounded-full glass-strong flex items-center gap-3 shadow-lg z-40">
      <span class="text-sm font-mono text-foreground font-medium">{{ count }} selected</span>

      <Separator orientation="vertical" class="h-4" />

      <button
        v-for="action in actions"
        :key="action.id"
        class="flex items-center gap-1 text-xs text-muted hover:text-[var(--color-primary)] transition-colors"
        @click="action.handler"
      >
        <component :is="action.icon" class="w-3.5 h-3.5" />
        <span class="hidden sm:inline">{{ action.label }}</span>
      </button>

      <Separator orientation="vertical" class="h-4" />

      <button
        class="flex items-center gap-1 text-xs text-muted hover:text-foreground transition-colors"
        @click="clear"
        aria-label="Clear selection"
      >
        <X class="w-3.5 h-3.5" />
        Clear
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(12px) scale(0.96);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.96);
}
</style>
