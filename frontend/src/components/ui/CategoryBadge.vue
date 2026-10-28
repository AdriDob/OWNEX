<template>
  <span :class="['category-badge', category]" v-text="label" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineProps<{
  category: string
}>()

const label = computed(() => {
  const labels: Record<string, string> = {
    health_degradation: 'Salud',
    error_spike: 'Errores',
    performance_regression: 'Performance',
    test_failure: 'Tests',
    sla_violation: 'SLA',
    resource_exhaustion: 'Recursos',
    config_drift: 'Config',
    dependency_failure: 'Dependencia',
    security_anomaly: 'Seguridad',
    unknown: 'Desconocido',
  }
  return labels[props.category] || props.category
})
</script>

<style scoped>
.category-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  background: rgba(0, 213, 255, 0.1);
  border: 1px solid rgba(0, 213, 255, 0.2);
  color: var(--ownex-accent);
}
</style>