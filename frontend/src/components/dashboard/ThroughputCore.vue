<script setup lang="ts">
import { TrendingUp } from '@lucide/vue'

interface ThroughputStage {
  label: string
  value: number
  color: string
}

interface Props {
  stages?: ThroughputStage[]
  efficiency?: number
  trend?: 'up' | 'down' | 'stable'
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  stages: () => [
    { label: 'Oportunidades detectadas', value: 42, color: 'text-accent' },
    { label: 'Analizadas', value: 18, color: 'text-primary' },
    { label: 'Priorizadas', value: 7, color: 'text-warning' },
    { label: 'En ejecución', value: 3, color: 'text-primary' },
    { label: 'Completadas', value: 1, color: 'text-success' },
  ],
  efficiency: 87,
  trend: 'up',
})
</script>

<template>
  <div :class="['panel rounded-xl p-5', className]">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <TrendingUp class="h-4 w-4 text-primary" />
        <span class="font-mono text-[10px] font-bold tracking-widest text-primary uppercase">Throughput</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="font-mono text-[10px] text-muted-foreground">Efficiency</span>
        <span class="font-mono text-sm font-bold" :class="efficiency >= 80 ? 'text-success' : efficiency >= 50 ? 'text-warning' : 'text-destructive'">
          {{ efficiency }}%
        </span>
        <span v-if="trend === 'up'" class="text-success text-xs">↑</span>
        <span v-else-if="trend === 'down'" class="text-destructive text-xs">↓</span>
      </div>
    </div>

    <div class="space-y-2.5">
      <div
        v-for="(stage, i) in stages"
        :key="stage.label"
        class="flex items-center gap-3"
      >
        <!-- Arrow connector (except last) -->
        <div class="flex flex-col items-center w-4 shrink-0">
          <div class="h-2 w-0.5 rounded-full" :class="stage.color.replace('text-', 'bg-')" />
          <div v-if="i < stages.length - 1" class="h-4 w-0.5 rounded-full bg-border/30" />
        </div>

        <!-- Label -->
        <span class="flex-1 font-mono text-[11px] text-muted-foreground">{{ stage.label }}</span>

        <!-- Value -->
        <span :class="['font-mono text-sm font-bold tabular-nums', stage.color]">
          {{ stage.value }}
        </span>
      </div>
    </div>
  </div>
</template>
