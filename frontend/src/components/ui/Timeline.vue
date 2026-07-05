<script setup lang="ts">
import { cn } from '@/lib/utils'
import Badge from './Badge.vue'

export interface TimelineEvent {
  id: string | number
  timestamp: string
  type: 'success' | 'error' | 'pending' | 'info'
  status: string
  description: string
  detail?: string
}

const props = withDefaults(defineProps<{
  events: TimelineEvent[]
  height?: string
  compact?: boolean
}>(), {
  height: 'full',
  compact: false,
})

const dotColors: Record<string, string> = {
  success: 'bg-success shadow-[0_0_6px_rgba(0,230,118,0.4)]',
  error: 'bg-destructive shadow-[0_0_6px_rgba(255,23,68,0.4)]',
  pending: 'bg-warning shadow-[0_0_6px_rgba(255,171,0,0.4)]',
  info: 'bg-primary shadow-[0_0_6px_rgba(0,255,65,0.4)]',
}
</script>

<template>
  <div
    class="timeline relative"
    :class="[height === 'full' ? 'h-full' : height, compact ? 'text-[10px]' : 'text-xs']"
  >
    <div v-for="(event, i) in events" :key="event.id" class="flex gap-3" :class="{ 'pb-4': i < events.length - 1, 'pb-2': compact && i < events.length - 1 }">
      <div class="flex flex-col items-center shrink-0">
        <div class="w-2.5 h-2.5 rounded-full" :class="dotColors[event.type] || dotColors.info" />
        <div v-if="i < events.length - 1" class="w-px flex-1 bg-[var(--color-border)]/40" />
      </div>
      <div class="flex-1 min-w-0 pt-0.5">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-mono text-muted" :class="compact ? 'text-[9px]' : 'text-[10px]'">{{ event.timestamp }}</span>
          <Badge :variant="event.type === 'success' ? 'success' : event.type === 'error' ? 'destructive' : event.type === 'pending' ? 'warning' : 'info'" class="text-[9px]">
            {{ event.status }}
          </Badge>
        </div>
        <p class="text-foreground/80 mt-0.5 leading-relaxed">{{ event.description }}</p>
        <p v-if="event.detail" class="text-muted mt-0.5 leading-relaxed" :class="compact ? 'text-[10px]' : 'text-xs'">{{ event.detail }}</p>
      </div>
    </div>
    <p v-if="events.length === 0" class="text-xs text-muted text-center py-8">No events</p>
  </div>
</template>
