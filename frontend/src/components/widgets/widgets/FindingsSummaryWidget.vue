<script setup lang="ts">
import { Bug } from '@lucide/vue'
import { computed } from 'vue'
import Badge from '@/components/ui/Badge.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const severities = computed(() => {
  const items = props.data?.items ?? []
  const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const item of items) {
    const sev = (item.severity || 'info').toLowerCase()
    if (sev in counts) counts[sev]++
  }
  return counts
})

const total = computed(() => Object.values(severities.value).reduce((a, b) => a + b, 0))

const severityConfig: Record<string, { color: string; bg: string }> = {
  critical: { color: 'text-destructive', bg: 'bg-destructive' },
  high: { color: 'text-warning', bg: 'bg-warning' },
  medium: { color: 'text-info', bg: 'bg-info' },
  low: { color: 'text-muted-foreground', bg: 'bg-muted-foreground' },
  info: { color: 'text-primary', bg: 'bg-primary' },
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between">
      <span class="font-mono text-[10px] text-muted-foreground tracking-wider">Findings</span>
      <Badge variant="outline" class="text-[9px]">{{ total }} total</Badge>
    </div>
    <div class="space-y-1.5">
      <div v-for="(count, sev) in severities" :key="sev" class="flex items-center gap-2">
        <span class="text-[10px] text-muted-foreground w-14 truncate capitalize">{{ sev }}</span>
        <div class="flex-1 h-1.5 rounded-full bg-surface/50 overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="severityConfig[sev]?.bg || 'bg-muted'"
            :style="{ width: total > 0 ? `${(count / total) * 100}%` : '0%' }"
          />
        </div>
        <span class="font-mono text-[10px] text-foreground w-6 text-right">{{ count }}</span>
      </div>
    </div>
  </div>
</template>
