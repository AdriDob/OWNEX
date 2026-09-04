<script setup lang="ts">
import { GripVertical, RefreshCw, Settings, X } from '@lucide/vue'
import GlassCard from '@/components/ui/GlassCard.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { cn } from '@/lib/utils'

interface Props {
  widgetId: string
  title: string
  icon?: string
  variant?: 'default' | 'premium' | 'gold' | 'highlight'
  loading?: boolean
  error?: string | null
  removable?: boolean
  configurable?: boolean
  editable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  loading: false,
  error: null,
  removable: false,
  configurable: false,
  editable: false,
})

const emit = defineEmits<{
  close: []
  configure: []
  refresh: []
}>()
</script>

<template>
  <GlassCard :variant="variant" class="widget-wrapper flex flex-col h-full" :hover="false">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 py-2 border-b border-border/20">
      <div class="flex items-center gap-2 min-w-0">
        <GripVertical v-if="editable" class="h-3 w-3 text-muted-foreground cursor-grab shrink-0 drag-handle" />
        <span class="font-mono text-[9px] font-bold tracking-wider text-muted-foreground uppercase truncate">
          {{ title }}
        </span>
      </div>
      <div class="flex items-center gap-0.5 shrink-0">
        <button
          v-if="!loading && !error"
          @click="emit('refresh')"
          class="h-5 w-5 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
          title="Refresh"
        >
          <RefreshCw class="h-3 w-3" />
        </button>
        <button
          v-if="configurable"
          @click="emit('configure')"
          class="h-5 w-5 flex items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
          title="Configure"
        >
          <Settings class="h-3 w-3" />
        </button>
        <button
          v-if="removable && editable"
          @click="emit('close')"
          class="h-5 w-5 flex items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
          title="Remove"
        >
          <X class="h-3 w-3" />
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 p-3 min-h-0 overflow-hidden">
      <template v-if="loading">
        <div class="space-y-2">
          <Skeleton class="h-4 w-3/4" />
          <Skeleton class="h-4 w-1/2" />
          <Skeleton class="h-8 w-full" />
        </div>
      </template>
      <template v-else-if="error">
        <div class="flex flex-col items-center justify-center h-full py-4 text-center">
          <p class="text-xs text-destructive mb-1">Failed to load</p>
          <p class="text-[10px] text-muted-foreground mb-2">{{ error }}</p>
          <button
            @click="emit('refresh')"
            class="text-[10px] text-primary hover:underline font-mono"
          >
            Retry
          </button>
        </div>
      </template>
      <template v-else>
        <slot />
      </template>
    </div>
  </GlassCard>
</template>
