<script setup lang="ts">
/**
 * Agenda View — calendario unificado corto/mediano/largo plazo.
 * Conecta WorkBank + IncomeTarget + Career + Capital en una vista.
 */
import { onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { type AgendaItem, fetchAgenda, type UnifiedAgendaState } from '@/services/ownexData'

const loading = ref(true)
const agenda = ref<UnifiedAgendaState | null>(null)

const columns = [
  { key: 'today' as const, label: 'HOY', color: 'text-gold' },
  { key: 'short_term' as const, label: 'ESTA SEMANA', color: 'text-accent' },
  { key: 'medium_term' as const, label: 'MES–TRIMESTRE', color: 'text-muted-foreground' },
  { key: 'long_term' as const, label: 'AÑO+', color: 'text-muted-foreground/60' },
]

const sourceIcon = (s: string): string => {
  const map: Record<string, string> = {
    work: '🎯',
    capital: '💰',
    career: '🧠',
    personal: '👤',
  }
  return map[s] || '📋'
}

const usd = (n: number | undefined | null): string => (n ? `$${Math.round(n).toLocaleString('es-AR')}` : '')

async function load(): Promise<void> {
  loading.value = true
  try {
    agenda.value = await fetchAgenda()
  } catch {
    /* degradación silenciosa */
  }
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Agenda Unificada</h1>
        <p class="text-sm text-muted-foreground">Tareas · objetivos · metas — corto, mediano y largo plazo</p>
      </div>
      <Badge v-if="agenda" variant="default">{{ agenda.total_items }} items</Badge>
    </div>

    <LoadingState v-if="loading" />

    <template v-else-if="agenda">
      <!-- Best action -->
      <Card v-if="agenda.best_action" class="border-gold/30 bg-gold/5 p-5">
        <p class="font-mono text-[10px] uppercase tracking-wider text-gold">🔥 Mejor acción global</p>
        <p class="mt-1 text-sm font-semibold">{{ agenda.best_action.title }}</p>
        <div class="mt-2 flex items-center gap-3">
          <span v-if="agenda.best_action.reward" class="font-mono text-lg font-semibold tabular-nums text-success">
            {{ usd(agenda.best_action.reward) }}
          </span>
          <Badge variant="default" class="capitalize">{{ agenda.best_action.source }}</Badge>
          <span class="font-mono text-xs text-muted-foreground">{{ agenda.best_action.action }}</span>
        </div>
      </Card>

      <!-- Calendar grid: 4 horizontes -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div v-for="col in columns" :key="col.key" class="space-y-3">
          <div class="flex items-center justify-between px-1">
            <p class="font-mono text-[10px] uppercase tracking-wider" :class="col.color">{{ col.label }}</p>
            <span class="font-mono text-[10px] text-muted-foreground/50">{{ agenda[col.key]?.length ?? 0 }}</span>
          </div>

          <Card
            v-for="(item, i) in agenda[col.key]"
            :key="i"
            class="space-y-2 p-3.5"
          >
            <div class="flex items-start gap-2">
              <span class="shrink-0 text-sm">{{ sourceIcon(item.source) }}</span>
              <p class="line-clamp-2 text-sm leading-snug">{{ item.title }}</p>
            </div>
            <div v-if="item.reward" class="flex items-center justify-between">
              <span class="font-mono text-sm font-semibold tabular-nums text-success">{{ usd(item.reward) }}</span>
              <Badge variant="default" class="text-[9px] capitalize">{{ item.source }}</Badge>
            </div>
            <p v-if="item.action && !item.reward" class="font-mono text-[10px] text-muted-foreground">{{ item.action }}</p>
            <a
              v-if="item.url"
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="block font-mono text-[10px] text-accent hover:underline"
            >
              Abrir →
            </a>
          </Card>

          <p
            v-if="!agenda[col.key]?.length"
            class="rounded-lg border border-dashed border-border/20 p-6 text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground/40"
          >
            vacío
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
