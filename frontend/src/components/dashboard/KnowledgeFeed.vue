<script setup lang="ts">
import { BookOpen } from '@lucide/vue'

interface KnowledgeItem {
  id: string
  type: 'pattern' | 'decision' | 'learning' | 'alert'
  typeLabel: string
  message: string
  timestamp: string
}

interface Props {
  items?: KnowledgeItem[]
  loading?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  items: () => [
    {
      id: '1',
      type: 'pattern',
      typeLabel: 'Patrón detectado',
      message: 'Fallo de autorización recurrente en endpoints REST multi-tenant',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: '2',
      type: 'decision',
      typeLabel: 'Decisión',
      message: 'Priorizar flujo Security Cycle sobre investigación manual',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
    },
    {
      id: '3',
      type: 'learning',
      typeLabel: 'Aprendizaje',
      message: 'Endpoint scoring mejorado con datos de USD/hora reales',
      timestamp: new Date(Date.now() - 14400000).toISOString(),
    },
  ],
  loading: false,
})

const typeColor: Record<string, string> = {
  pattern: 'bg-blue-500/20 text-blue-400',
  decision: 'bg-amber-500/20 text-amber-400',
  learning: 'bg-green-500/20 text-green-400',
  alert: 'bg-destructive/20 text-destructive',
}
</script>

<template>
  <div :class="['panel rounded-xl p-4', className]">
    <div class="flex items-center gap-2 mb-3">
      <BookOpen class="h-4 w-4 text-primary" />
      <span class="font-mono text-xs font-semibold text-foreground">Knowledge Feed</span>
    </div>

    <div v-if="loading" class="space-y-2">
      <div v-for="i in 3" :key="i" class="h-10 animate-pulse rounded-lg bg-surface/50" />
    </div>

    <div v-else-if="items.length === 0" class="py-6 text-center">
      <p class="font-mono text-xs text-muted-foreground">Sin actividad registrada</p>
    </div>

    <div v-else class="space-y-1.5">
      <div
        v-for="item in items"
        :key="item.id"
        class="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-surface/20 transition-colors"
      >
        <div class="flex flex-col items-center gap-1 shrink-0 pt-0.5">
          <div class="h-1.5 w-1.5 rounded-full" :class="typeColor[item.type]?.split(' ')[0].replace('bg-', 'bg-').replace('/20', '')" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span :class="['text-[8px] font-mono px-1 py-0.5 rounded', typeColor[item.type]]">
              {{ item.typeLabel }}
            </span>
            <span class="font-mono text-[9px] text-muted-foreground">
              {{ new Date(item.timestamp).toLocaleTimeString() }}
            </span>
          </div>
          <p class="text-xs text-foreground mt-0.5">{{ item.message }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
