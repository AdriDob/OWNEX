<script setup lang="ts">
import type { EntityType } from '@/composables/useContextMenu'

const props = defineProps<{
  entityType: EntityType
  entity: any
  compact?: boolean
}>()

const emit = defineEmits<{
  action: [actionId: string, entity: any]
}>()

interface QuickAction {
  id: string
  label: string
  icon: string
  shortcut?: string
}

function getActions(type: EntityType): QuickAction[] {
  const common = [
    { id: 'copy-id', label: 'Copiar ID', icon: 'copy', shortcut: 'C' },
  ]
  switch (type) {
    case 'finding':
      return [
        { id: 'validate', label: 'Validar', icon: 'check', shortcut: 'V' },
        { id: 'generate-report', label: 'Reporte', icon: 'file', shortcut: 'R' },
        { id: 'check-duplicate', label: 'Duplicado', icon: 'search', shortcut: 'D' },
        { id: 'estimate-payout', label: 'Payout', icon: 'dollar', shortcut: 'P' },
      ]
    case 'program':
      return [
        { id: 'view-plan', label: 'Plan', icon: 'target' },
        { id: 'scan-surface', label: 'Escaneo', icon: 'scan' },
        { id: 'estimate-payout', label: 'Payout', icon: 'dollar' },
      ]
    case 'report':
      return [
        { id: 'optimize', label: 'Optimizar', icon: 'sparkles', shortcut: 'O' },
        { id: 'check-acceptance', label: 'Aceptación', icon: 'trending' },
        { id: 'export', label: 'Exportar', icon: 'download' },
      ]
    case 'endpoint':
      return [
        { id: 'analyze', label: 'Analizar', icon: 'search' },
        { id: 'scan-surface', label: 'Escaneo', icon: 'scan' },
      ]
    default:
      return common
  }
}

const actions = getActions(props.entityType)

const iconMap: Record<string, string> = {
  check: '✓', file: '📄', search: '🔍', dollar: '💰',
  target: '🎯', scan: '📡', sparkles: '✨', trending: '📈',
  download: '⬇', copy: '📋',
}
</script>

<template>
  <div
    class="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-surface/80 border border-border/40"
    :class="{ 'gap-0.5 px-1.5 py-1': compact }"
    role="toolbar"
    :aria-label="`Acciones rápidas: ${entityType}`"
  >
    <template v-for="(action) in actions" :key="action.id">
      <button
        class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors"
        :class="{ 'px-1.5 py-0.5 text-[9px]': compact }"
        :title="action.label + (action.shortcut ? ` (${action.shortcut})` : '')"
        @click="emit('action', action.id, entity)"
      >
        <span>{{ iconMap[action.icon] || '•' }}</span>
        <span v-if="!compact" class="hidden sm:inline">{{ action.label }}</span>
      </button>
    </template>
  </div>
</template>
