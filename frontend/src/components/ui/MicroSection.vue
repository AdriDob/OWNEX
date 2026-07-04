<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDown, ChevronRight } from '@lucide/vue'

const props = defineProps<{
  title: string
  badge?: string
  badgeVariant?: 'high' | 'medium' | 'low' | 'info'
  defaultOpen?: boolean
  loading?: boolean
  preview?: string
}>()

const emit = defineEmits<{
  toggle: [open: boolean]
}>()

const isOpen = ref(props.defaultOpen ?? false)
const isHovered = ref(false)

const insightBadgeClass = computed(() => {
  const variants: Record<string, string> = {
    high: 'bg-success/20 text-success border-success/30',
    medium: 'bg-warning/20 text-warning border-warning/30',
    low: 'bg-muted/20 text-muted-foreground border-border/40',
    info: 'bg-primary/10 text-primary border-primary/20',
  }
  return variants[props.badgeVariant || 'info'] || variants.info
})

function toggle() {
  isOpen.value = !isOpen.value
  emit('toggle', isOpen.value)
}
</script>

<template>
  <div
    class="border border-border/30 rounded-lg overflow-hidden transition-all duration-150"
    :class="{ 'border-primary/20': isOpen }"
    :aria-expanded="isOpen"
    role="region"
  >
    <button
      class="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-foreground/80 hover:text-foreground hover:bg-surface-hover transition-colors"
      :class="{ 'bg-surface-hover': isHovered }"
      @click="toggle"
      @mouseenter="isHovered = true"
      @mouseleave="isHovered = false"
    >
      <component :is="isOpen ? ChevronDown : ChevronRight" class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <span class="flex-1 text-left">{{ title }}</span>
      <span v-if="badge" class="px-1.5 py-0.5 text-[9px] font-medium rounded border" :class="insightBadgeClass">
        {{ badge }}
      </span>
      <span v-if="loading" class="h-3 w-3 animate-spin rounded-full border border-primary/30 border-t-primary" />
    </button>
    <div
      v-show="isOpen"
      class="px-3 py-2 text-xs text-foreground/70 space-y-1.5 border-t border-border/20"
    >
      <slot />
    </div>
    <div
      v-if="!isOpen && preview"
      class="px-3 pb-2 text-[10px] text-muted-foreground/60 truncate cursor-pointer"
      @click="toggle"
    >
      {{ preview }}
    </div>
  </div>
</template>
