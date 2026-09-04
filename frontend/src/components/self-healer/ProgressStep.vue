<template>
  <div :class="['progress-step', { current, completed, failed }]">
    <span class="step-icon">
      <span v-if="completed" class="icon-done">✓</span>
      <span v-else-if="failed" class="icon-fail">✕</span>
      <span v-else-if="current" class="icon-spin">⟳</span>
      <span v-else class="icon-pending">○</span>
    </span>
    <span class="step-label">{{ label }}</span>
    <span class="step-status">
      <span v-if="completed" class="healthy">Completado</span>
      <span v-else-if="failed" class="unhealthy">Falló</span>
      <span v-else-if="current" class="pending">En progreso...</span>
      <span v-else class="pending">Pendiente</span>
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  completed: boolean
  current: boolean
  healthy?: boolean
}>()

const failed = computed(() => !completed && !current && healthy === false)
</script>

<style scoped>
.progress-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #0a0c11;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.progress-step.current {
  border-left-color: #00d5ff;
  background: rgba(0, 213, 255, 0.05);
}

.progress-step.completed {
  border-left-color: #34d399;
}

.progress-step.failed {
  border-left-color: #f87171;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #13161d;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  font-weight: 600;
  color: #5e6272;
}

.progress-step.completed .step-icon {
  background: rgba(52, 211, 153, 0.15);
  border-color: rgba(52, 211, 153, 0.3);
  color: #34d399;
}

.progress-step.current .step-icon {
  background: rgba(0, 213, 255, 0.15);
  border-color: rgba(0, 213, 255, 0.3);
  color: #00d5ff;
  animation: pulse 1.5s ease-in-out infinite;
}

.progress-step.failed .step-icon {
  background: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.3);
  color: #f87171;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.05); }
}

.icon-done { color: #34d399; }
.icon-fail { color: #f87171; }
.icon-spin {
  color: #00d5ff;
  animation: spin 1s linear infinite;
}
.icon-pending { color: #5e6272; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.step-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #d9dbdf;
}

.step-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.step-healthy {
  color: #34d399;
}

.step-unhealthy {
  color: #f87171;
}

.step-pending {
  color: #fbbf24;
}
</style>