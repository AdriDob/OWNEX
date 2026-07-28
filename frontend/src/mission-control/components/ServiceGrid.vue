<script setup lang="ts">
/**
 * ServiceGrid — Grid of all service checks, grouped by category
 */
import { computed } from 'vue'
import type { ServiceCheck as ServiceCheckType } from '@/shared/types'
import ServiceCheckComp from './ServiceCheck.vue'
import GlassPanel from '@/shared/components/GlassPanel.vue'

const props = defineProps<{
  checks: ServiceCheckType[]
}>()

const grouped = computed(() => {
  const order = ['infrastructure', 'ai', 'security', 'tools', 'config', 'data'] as const
  const labels: Record<string, string> = {
    infrastructure: 'Infraestructura',
    ai: 'Inteligencia Artificial',
    security: 'Seguridad',
    tools: 'Herramientas',
    config: 'Configuración',
    data: 'Datos',
  }

  const groups: { label: string; checks: ServiceCheckType[] }[] = []
  for (const cat of order) {
    const items = props.checks.filter(c => c.category === cat)
    if (items.length > 0) {
      groups.push({ label: labels[cat] || cat, checks: items })
    }
  }
  return groups
})

const totals = computed(() => ({
  total: props.checks.length,
  passed: props.checks.filter(c => c.status === 'passed').length,
  errors: props.checks.filter(c => c.status === 'error').length,
  checking: props.checks.filter(c => c.status === 'checking' || c.status === 'installing' || c.status === 'configuring').length,
}))
</script>

<template>
  <div class="space-y-3">
    <!-- Quick stats -->
    <div class="flex gap-4 text-xs text-muted-foreground mb-1">
      <span>{{ totals.total }} servicios</span>
      <span class="text-success">{{ totals.passed }} OK</span>
      <span v-if="totals.errors" class="text-destructive">{{ totals.errors }} errores</span>
      <span v-if="totals.checking" class="text-primary">{{ totals.checking }} procesando</span>
    </div>

    <!-- Category groups -->
    <div v-for="group in grouped" :key="group.label" class="space-y-1">
      <div class="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
        {{ group.label }}
        <span class="ml-1 font-normal opacity-60">· {{ group.checks.length }}</span>
      </div>
      <GlassPanel variant="default" padding="sm">
        <ServiceCheckComp
          v-for="check in group.checks"
          :key="check.id"
          :check="check"
        />
      </GlassPanel>
    </div>
  </div>
</template>
