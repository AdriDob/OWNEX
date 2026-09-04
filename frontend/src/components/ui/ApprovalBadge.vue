<template>
  <span :class="['approval-badge', approval]" v-text="label" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineProps<{
  approval: 'none' | 'low_risk' | 'high_risk' | 'critical'
}>()

const label = computed(() => {
  const labels: Record<string, string> = {
    none: 'Sin Aprobación',
    low_risk: 'Bajo Riesgo',
    high_risk: 'Alto Riesgo',
    critical: 'Crítico',
  }
  return labels[props.approval] || props.approval
})

const classes = computed(() => {
  const base = 'approval-badge'
  const variants: Record<string, string> = {
    none: 'approval-none',
    low_risk: 'approval-low',
    high_risk: 'approval-high',
    critical: 'approval-critical',
  }
  return `${base} ${variants[props.approval] || ''}`
})
</script>

<style scoped>
.approval-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.approval-none {
  background: rgba(139, 141, 152, 0.15);
  border: 1px solid rgba(139, 141, 152, 0.3);
  color: #8b8d98;
}

.approval-low {
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  color: #34d399;
}

.approval-high {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.approval-critical {
  background: rgba(248, 113, 113, 0.15);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: #f87171;
}
</style>