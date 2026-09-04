<script setup lang="ts">
import { Clock } from '@lucide/vue'
import { computed } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import StatusDot from '@/components/ui/StatusDot.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const running = computed(() => props.data?.watchdog?.running ?? false)
const uptime = computed(() => {
  const sec = props.data?.uptime_seconds ?? 0
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h`
  return `${Math.floor(sec / 86400)}d`
})
const memory = computed(() => props.data?.system?.memory_percent ?? 0)
const cpu = computed(() => props.data?.system?.cpu_percent ?? 0)
const version = computed(() => props.data?.version ?? '—')
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <StatusDot :status="running ? 'online' : 'offline'" size="sm" />
        <span class="font-mono text-[10px] text-muted-foreground">
          {{ running ? 'Scheduler Active' : 'Scheduler Idle' }}
        </span>
      </div>
      <Badge variant="outline" class="text-[8px]">v{{ version }}</Badge>
    </div>
    <div class="grid grid-cols-2 gap-2 mt-1">
      <div class="rounded-lg bg-surface/30 p-2 text-center">
        <p class="font-mono text-[9px] text-muted-foreground">Uptime</p>
        <p class="font-mono text-sm font-bold text-foreground">{{ uptime }}</p>
      </div>
      <div class="rounded-lg bg-surface/30 p-2 text-center">
        <p class="font-mono text-[9px] text-muted-foreground">CPU / RAM</p>
        <p class="font-mono text-sm font-bold text-foreground">{{ cpu.toFixed(0) }}/{{ memory.toFixed(0) }}%</p>
      </div>
    </div>
  </div>
</template>
