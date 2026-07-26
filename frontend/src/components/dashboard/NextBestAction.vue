<script setup lang="ts">
import { Zap, Sparkles, ArrowRight } from '@lucide/vue'

interface NextAction {
  title: string
  reason: string
  effort: string
  estimatedReward: number
}

interface Props {
  action?: NextAction | null
  loading?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  action: () => ({
    title: 'Analizar endpoint /api/users/{id}',
    reason: 'Alta probabilidad IDOR en target conocido. 15 min estimados.',
    effort: 'Bajo',
    estimatedReward: 2500,
  }),
  loading: false,
})

const effortColor = (e: string) => {
  const map: Record<string, string> = { Bajo: 'text-success', Medio: 'text-warning', Alto: 'text-destructive' }
  return map[e] || 'text-muted-foreground'
}

function execute() {
  // Placeholder — Future: dispatch action to scheduler
}
</script>

<template>
  <div :class="['panel rounded-xl p-5', className]">
    <div class="flex items-start gap-4">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Zap class="h-5 w-5" />
      </div>
      <div class="flex-1 min-w-0">
        <div v-if="loading" class="space-y-2">
          <div class="h-3 w-24 animate-pulse rounded bg-surface/50" />
          <div class="h-4 w-3/4 animate-pulse rounded bg-surface/50" />
          <div class="h-3 w-1/2 animate-pulse rounded bg-surface/50" />
        </div>
        <template v-else-if="action">
          <div class="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-primary mb-1">
            <Sparkles class="h-3 w-3" />
            <span>Próxima acción recomendada</span>
          </div>
          <h3 class="text-base font-semibold text-foreground">{{ action.title }}</h3>
          <p class="mt-1 text-xs text-muted-foreground">{{ action.reason }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-4">
            <span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
              Esfuerzo:
              <span :class="['font-semibold', effortColor(action.effort)]">{{ action.effort }}</span>
            </span>
            <span v-if="action.estimatedReward" class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
              Recompensa estimada:
              <span class="font-semibold text-gold">${{ action.estimatedReward.toLocaleString() }}</span>
            </span>
          </div>
        </template>
        <div v-else class="py-3 text-center">
          <p class="font-mono text-xs text-muted-foreground">No hay acciones pendientes</p>
        </div>
      </div>
      <button
        v-if="action"
        @click="execute"
        class="shrink-0 flex items-center gap-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 text-xs font-medium transition-colors"
      >
        Ejecutar
        <ArrowRight class="h-3 w-3" />
      </button>
    </div>
  </div>
</template>
