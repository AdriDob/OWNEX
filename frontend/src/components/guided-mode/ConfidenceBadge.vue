<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  level: 'high' | 'medium' | 'low'
  detail?: string
}

const props = defineProps<Props>()

const confidenceConfig = {
  high: {
    label: 'ALTA CONFIANZA',
    color: 'from-green-500 to-emerald-500',
    icon: '✅',
    text: 'Verificado desde múltiples fuentes',
  },
  medium: {
    label: 'CONFIANZA MEDIA',
    color: 'from-yellow-500 to-amber-500',
    icon: '⚠️',
    text: 'Probable, pero requiere verificación',
  },
  low: {
    label: 'BAJA CONFIANZA',
    color: 'from-cyan-500 to-blue-500',
    icon: '🔍',
    text: 'Opción posible, necesita confirmación',
  },
}

const config = computed(() => confidenceConfig[props.level] || confidenceConfig.medium)
</script>

<template>
  <div class="confidence-badge" :style="{ '--confidence-color': config.color }">
    <div class="confidence-badge__main">
      <span class="confidence-badge__icon">{{ config.icon }}</span>
      <div class="confidence-badge__text">
        <span class="confidence-badge__label">{{ config.label }}</span>
        <span class="confidence-badge__detail">{{ config.text }}</span>
      </div>
    </div>
    <div v-if="detail" class="confidence-badge__detail-text">
      {{ detail }}
    </div>
  </div>
</template>

<style scoped>
.confidence-badge {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(10px);
}

.confidence-badge__main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.confidence-badge__icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.confidence-badge__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.confidence-badge__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--confidence-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.confidence-badge__detail {
  font-size: 0.75rem;
  color: #aaa;
}

.confidence-badge__detail-text {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.75rem;
  color: #888;
  font-style: italic;
}
</style>