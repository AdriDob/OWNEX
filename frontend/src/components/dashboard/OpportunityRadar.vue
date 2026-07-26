<script setup lang="ts">
import { Radar } from '@lucide/vue'

interface Opportunity {
  id: string
  title: string
  source: string
  type: string
  reward: number
  confidence: number
  effort: string
  action: string
}

interface Props {
  opportunities?: Opportunity[]
  loading?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  opportunities: () => [
    {
      id: '1',
      title: 'IDOR en endpoint REST',
      source: 'HackerOne',
      type: 'Security',
      reward: 5000,
      confidence: 84,
      effort: 'Bajo',
      action: 'Analizar',
    },
    {
      id: '2',
      title: 'Integración API pública',
      source: 'Algora',
      type: 'Dev',
      reward: 800,
      confidence: 72,
      effort: 'Medio',
      action: 'Aplicar',
    },
    {
      id: '3',
      title: 'Evaluación dataset NLP',
      source: 'DataAnnotation',
      type: 'AI',
      reward: 300,
      confidence: 65,
      effort: 'Bajo',
      action: 'Iniciar',
    },
  ],
  loading: false,
})

const effortColor = (e: string) => {
  const map: Record<string, string> = { Bajo: 'text-success', Medio: 'text-warning', Alto: 'text-destructive' }
  return map[e] || 'text-muted-foreground'
}

const typeIcon: Record<string, string> = {
  Security: '🛡️',
  Dev: '⚒️',
  AI: '🤖',
  Wealth: '💰',
}
</script>

<template>
  <div :class="['panel rounded-xl p-4', className]">
    <div class="flex items-center gap-2 mb-3">
      <Radar class="h-4 w-4 text-primary" />
      <span class="font-mono text-xs font-semibold text-foreground">Opportunity Radar</span>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 3" :key="i" class="h-12 animate-pulse rounded-lg bg-surface/50" />
    </div>

    <div v-else-if="opportunities.length === 0" class="py-6 text-center">
      <p class="font-mono text-xs text-muted-foreground">Sin oportunidades disponibles</p>
    </div>

    <div v-else class="space-y-1.5">
      <div
        v-for="opp in opportunities"
        :key="opp.id"
        class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface/20 transition-colors cursor-pointer"
      >
        <span class="text-base shrink-0">{{ typeIcon[opp.type] || '🔵' }}</span>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-foreground truncate flex items-center gap-1.5">
            {{ opp.title }}
            <span class="text-[8px] text-muted-foreground font-mono">{{ opp.source }}</span>
          </p>
          <div class="flex items-center gap-3 mt-0.5">
            <span class="font-mono text-[10px] text-gold">${{ opp.reward.toLocaleString() }}</span>
            <span class="font-mono text-[10px]" :class="confidence >= 80 ? 'text-success' : confidence >= 60 ? 'text-warning' : 'text-muted-foreground'">
              {{ opp.confidence }}% confianza
            </span>
            <span :class="['font-mono text-[10px]', effortColor(opp.effort)]">{{ opp.effort }}</span>
          </div>
        </div>
        <span class="text-[10px] font-mono text-primary shrink-0">{{ opp.action }}</span>
      </div>
    </div>
  </div>
</template>
