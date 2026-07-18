<script setup lang="ts">
import { computed } from 'vue'
import { HeartPulse } from '@lucide/vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import StatusDot from '@/components/ui/StatusDot.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const healthScore = computed(() => props.data?.health_score ?? 0)
const status = computed(() => props.data?.status ?? 'unknown')
const checks = computed(() => props.data?.checks ?? [])
const statusColor = computed(() => {
  const s = status.value
  if (s === 'healthy' || s === 'stable') return 'online' as const
  if (s === 'degraded' || s === 'warning') return 'warning' as const
  return 'error' as const
})
</script>

<template>
  <div class="flex flex-col gap-2">
    <KPIBlock
      label="System Health"
      :value="healthScore"
      icon="Activity"
      :color="healthScore >= 90 ? 'success' : healthScore >= 70 ? 'warning' : 'default'"
      format="number"
      size="md"
    />
    <div class="flex items-center gap-2 mt-1">
      <StatusDot :status="statusColor" size="sm" />
      <span class="font-mono text-[10px] text-muted-foreground uppercase">{{ status }}</span>
    </div>
    <div v-if="checks.length > 0" class="space-y-1 mt-1">
      <div v-for="check in checks.slice(0, 4)" :key="check.name || check" class="flex items-center justify-between text-[10px]">
        <span class="text-muted-foreground truncate">{{ check.name || check }}</span>
        <StatusDot
          :status="check.status === 'healthy' || check.status === 'pass' ? 'online' : check.status === 'warning' ? 'warning' : 'error'"
          size="sm"
          :pulse="false"
        />
      </div>
    </div>
  </div>
</template>
