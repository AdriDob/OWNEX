<script setup lang="ts">
import { Copy, ExternalLink, Eye } from '@lucide/vue'
import { onUnmounted, ref, watch } from 'vue'
import { useUIStore } from '@/stores/ui'
import Badge from './Badge.vue'

const store = useUIStore()

const visible = ref(false)
const position = ref({ x: 0, y: 0 })
let showTimeout: ReturnType<typeof setTimeout> | null = null
let hideTimeout: ReturnType<typeof setTimeout> | null = null

watch(
  () => store.miniPreview,
  (preview) => {
    if (!preview) {
      clearTimeout(showTimeout!)
      visible.value = false
      return
    }
    clearTimeout(hideTimeout!)
    showTimeout = setTimeout(() => {
      position.value = { x: preview.x, y: preview.y }
      visible.value = true
    }, 300)
  },
  { deep: true },
)

function handleMouseLeave() {
  hideTimeout = setTimeout(() => {
    visible.value = false
    store.miniPreview = null
  }, 150)
}

function handleMouseEnter() {
  clearTimeout(hideTimeout!)
}

onUnmounted(() => {
  clearTimeout(showTimeout!)
  clearTimeout(hideTimeout!)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible && store.miniPreview"
      class="fixed z-[60] w-72 p-3 rounded-lg glass-terminal shadow-xl animate-in-fast"
      :style="{ left: `${position.x + 12}px`, top: `${position.y + 12}px` }"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
    >
      <!-- Title row -->
      <div class="flex items-start justify-between gap-2 mb-2">
        <div class="min-w-0">
          <p class="text-sm font-semibold text-foreground truncate">{{ store.miniPreview.title }}</p>
          <p v-if="store.miniPreview.subtitle" class="text-[10px] font-mono text-muted truncate">{{ store.miniPreview.subtitle }}</p>
        </div>
        <Badge v-if="store.miniPreview.status" :variant="store.miniPreview.status === 'active' || store.miniPreview.status === 'success' ? 'success' : store.miniPreview.status === 'error' ? 'destructive' : 'default'" class="shrink-0">
          {{ store.miniPreview.status }}
        </Badge>
      </div>

      <!-- Key metrics -->
      <div class="grid grid-cols-2 gap-2 mb-3">
        <div v-for="(metric, key) in store.miniPreview.metrics ?? {}" :key="String(key)" class="px-2 py-1 rounded bg-[var(--color-surface)]/50 border border-[var(--color-border)]/30">
          <p class="text-[9px] font-mono text-muted uppercase">{{ key }}</p>
          <p class="text-xs font-semibold text-foreground">{{ metric }}</p>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="flex items-center gap-1.5">
        <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
          <ExternalLink class="w-3 h-3" />
          Open
        </button>
        <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
          <Eye class="w-3 h-3" />
          Inspect
        </button>
        <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
          <Copy class="w-3 h-3" />
          Copy ID
        </button>
      </div>
    </div>
  </Teleport>
</template>
