<script setup lang="ts">
/**
 * ServiceCheck — Single row showing one service status
 * Color-coded by status, with icon, name, version, and action hint.
 */
import { computed } from 'vue'
import type { ServiceCheck as ServiceCheckType } from '@/shared/types'

const props = defineProps<{
  check: ServiceCheckType
}>()

const statusMeta = computed(() => {
  const map: Record<string, { icon: string; color: string; label: string }> = {
    pending: { icon: '○', color: 'text-muted', label: 'Pendiente' },
    checking: { icon: '◎', color: 'text-primary', label: 'Verificando' },
    installing: { icon: '◉', color: 'text-warning', label: 'Instalando' },
    configuring: { icon: '◉', color: 'text-warning', label: 'Configurando' },
    passed: { icon: '●', color: 'text-success', label: props.check.version || 'OK' },
    warning: { icon: '◐', color: 'text-warning', label: 'Advertencia' },
    error: { icon: '○', color: 'text-destructive', label: 'Error' },
  }
  return map[props.check.status] || map.pending
})

const categoryLabel = computed(() => {
  const map: Record<string, string> = {
    infrastructure: 'Infraestructura',
    tools: 'Herramientas',
    ai: 'Inteligencia',
    security: 'Seguridad',
    config: 'Configuración',
    data: 'Datos',
  }
  return map[props.check.category] || props.check.category
})
</script>

<template>
  <div
    class="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors duration-200"
    :class="check.status === 'passed' ? 'bg-success/5' : check.status === 'error' ? 'bg-destructive/5' : 'hover:bg-surface-hover'"
  >
    <!-- Status icon -->
    <span :class="['text-lg leading-none', statusMeta.color]" aria-hidden="true">
      {{ statusMeta.icon }}
    </span>

    <!-- Name + category -->
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <span class="text-sm font-medium text-foreground truncate">{{ check.name }}</span>
        <span v-if="check.version" class="text-xs text-muted-foreground font-mono">{{ check.version }}</span>
      </div>
      <div class="text-xs text-muted-foreground">{{ categoryLabel }}</div>
    </div>

    <!-- Status message -->
    <div
      :class="[
        'text-xs font-medium',
        check.status === 'passed' ? 'text-success' : 
        check.status === 'error' ? 'text-destructive' : 
        check.status === 'warning' ? 'text-warning' : 'text-muted-foreground',
      ]"
    >
      <template v-if="check.status === 'checking'">
        <span class="inline-flex gap-0.5">
          <span class="w-1 h-1 rounded-full bg-primary/60 dot-pulse" />
          <span class="w-1 h-1 rounded-full bg-primary/60 dot-pulse" />
          <span class="w-1 h-1 rounded-full bg-primary/60 dot-pulse" />
        </span>
      </template>
      <template v-else>
        {{ statusMeta.label }}
      </template>
    </div>
  </div>
</template>
