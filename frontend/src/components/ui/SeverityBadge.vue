<template>
  <span :class="['severity-badge', severity]" v-text="label" />
</template>

<script setup lang="ts">
defineProps<{
  severity: 'critical' | 'high' | 'medium' | 'low'
}>()

const label = computed(() => {
  const labels: Record<string, string> = {
    critical: 'CRÍTICO',
    high: 'ALTO',
    medium: 'MEDIO',
    low: 'BAJO',
  }
  return labels[props.severity] || props.severity.toUpperCase()
})
</script>

<style scoped>
.severity-badge {
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

.severity-critical {
  background: rgba(248, 113, 113, 0.15);
  border: 1px solid rgba(248, 113, 113, 0.3);
  color: var(--ownex-danger);
}

.severity-high {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: var(--ownex-yellow);
}

.severity-medium {
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  color: var(--ownex-green);
}

.severity-low {
  background: rgba(139, 141, 152, 0.15);
  border: 1px solid rgba(139, 141, 152, 0.3);
  color: var(--ownex-text-secondary);
}
</style>