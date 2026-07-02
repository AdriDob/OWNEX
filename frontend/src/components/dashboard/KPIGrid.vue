<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import {
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  CheckCircle2,
  DollarSign,
} from '@lucide/vue'

const props = defineProps<{
  items: Array<{
    label: string
    value: string
    icon?: string
    trend?: { direction: 'up' | 'down'; text: string }
    accent?: 'green' | 'gold' | 'blue' | 'purple'
    sublabel?: string
  }>
  systemStatus?: 'healthy' | 'degraded' | 'critical' | null
}>()

const accentMap: Record<string, string> = {
  green: 'text-success border-success/20 bg-success/8',
  gold: 'text-gold border-gold/20 bg-gold/8',
  blue: 'text-accent border-accent/20 bg-accent/8',
  purple: 'text-purple-400 border-purple-400/20 bg-purple-400/8',
}

const iconMap: Record<string, any> = {
  target: Target,
  activity: Activity,
  check: CheckCircle2,
  dollar: DollarSign,
}

const statusColor = computed(() => {
  if (props.systemStatus === 'healthy') return 'bg-success'
  if (props.systemStatus === 'degraded') return 'bg-warning'
  if (props.systemStatus === 'critical') return 'bg-destructive'
  return 'bg-muted-foreground/30'
})

const statusLabel = computed(() => {
  if (props.systemStatus === 'healthy') return 'Sistema operativo'
  if (props.systemStatus === 'degraded') return 'Atención requerida'
  if (props.systemStatus === 'critical') return 'Estado crítico'
  return 'Desconocido'
})
</script>

<template>
  <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <div
      v-for="(item, i) in items"
      :key="i"
      class="animate-in"
      :style="{ animationDelay: `${i * 50}ms` }"
    >
      <div
        :class="cn(
          'glass-card rounded-xl p-4',
          accentMap[item.accent || 'blue'] || accentMap.blue,
        )"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {{ item.label }}
            </p>
            <p class="mt-1.5 text-2xl font-bold tabular-nums text-foreground transition-all duration-300">
              {{ item.value }}
            </p>
            <p v-if="item.sublabel" class="mt-1 text-xs text-muted-foreground truncate">
              {{ item.sublabel }}
            </p>
          </div>
          <div
            v-if="item.icon"
            :class="cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border',
              accentMap[item.accent || 'blue'] || accentMap.blue,
            )"
          >
            <component :is="iconMap[item.icon]" class="h-4 w-4" />
          </div>
        </div>
        <div
          v-if="item.trend"
          class="mt-3 flex items-center gap-1 text-xs"
          :class="item.trend.direction === 'up' ? 'text-success' : 'text-destructive'"
        >
          <TrendingUp v-if="item.trend.direction === 'up'" class="h-3 w-3" />
          <TrendingDown v-else class="h-3 w-3" />
          <span>{{ item.trend.text }}</span>
        </div>
      </div>
    </div>

    <!-- System Status Indicator -->
    <div v-if="systemStatus" class="animate-in col-span-1 sm:col-span-2 lg:col-span-4">
      <div :class="cn('flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs', statusColor === 'bg-success' ? 'bg-success/10 text-success' : statusColor === 'bg-warning' ? 'bg-warning/10 text-warning' : 'bg-destructive/10 text-destructive')">
        <span :class="cn('h-2 w-2 rounded-full', statusColor)" />
        <span>{{ statusLabel }}</span>
      </div>
    </div>
  </div>
</template>
