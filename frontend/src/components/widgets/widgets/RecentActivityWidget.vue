<script setup lang="ts">
import { computed } from 'vue'
import { Activity } from '@lucide/vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const events = computed(() => {
  const raw = props.data?.events ?? []
  return raw.slice(0, 6).map((e: any, i: number) => ({
    id: e.id || `act-${i}`,
    message: e.title || e.message || 'Event registered',
    timestamp: e.timestamp || new Date().toISOString(),
    severity: e.severity || 'info',
  }))
})

const severityDot = (s?: string) => {
  if (s === 'high' || s === 'critical') return 'bg-destructive'
  if (s === 'warning') return 'bg-warning'
  return 'bg-primary/40'
}
</script>

<template>
  <div class="flex flex-col gap-1">
    <div v-if="events.length === 0" class="py-4 text-center">
      <p class="font-mono text-[10px] text-muted-foreground">No recent activity</p>
    </div>
    <div v-else class="space-y-0.5">
      <div
        v-for="event in events"
        :key="event.id"
        class="flex items-start gap-2 rounded px-1.5 py-1 hover:bg-surface/20 transition-colors"
      >
        <span :class="['mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full', severityDot(event.severity)]" />
        <div class="flex-1 min-w-0">
          <p class="text-[11px] text-foreground truncate">{{ event.message }}</p>
          <p class="font-mono text-[9px] text-muted-foreground">{{ new Date(event.timestamp).toLocaleTimeString() }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
