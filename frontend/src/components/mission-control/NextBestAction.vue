<script setup lang="ts">
/**
 * OWNEX Next Best Action — Hero card for primary recommended action
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'
import OwnexButton from '../ui/OwnexButton.vue'
import OwnexBadge from '../ui/OwnexBadge.vue'
import { useAudio } from '@/composables/useAudio'

interface Props {
  title: string
  description: string
  primaryAction: {
    label: string
    variant?: 'primary' | 'gold'
  }
  secondaryAction?: {
    label: string
    variant?: 'secondary' | 'ghost'
  }
  confidence?: number
  reasoning?: string
  meta?: Record<string, string | number>
}

const props = withDefaults(defineProps<Props>(), {
  primaryAction: () => ({ label: 'Ejecutar', variant: 'primary' }),
  secondaryAction: () => ({ label: 'Más tarde', variant: 'ghost' }),
  confidence: 0,
  reasoning: '',
  meta: () => ({}),
})

const confidenceColor = computed(() => {
  const c = props.confidence
  if (c >= 80) return 'var(--ownex-green)'
  if (c >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
})

const confidenceLabel = computed(() => {
  const c = props.confidence
  if (c >= 80) return 'ALTA CONFIANZA'
  if (c >= 60) return 'CONFIANZA MEDIA'
  return 'REQUIERE REVISIÓN'
})

const audio = useAudio()

function handlePrimaryAction() {
  audio.play('click')
}

function handleSecondaryAction() {
  audio.play('toggle')
}
</script>

<template>
  <div class="ownex-next-action" role="region" aria-label="Próxima acción recomendada">
    <!-- Header -->
    <div class="ownex-next-action__header">
      <div class="ownex-next-action__badge-group">
        <OwnexBadge variant="gold" dot>
          PRÓXIMA ACCIÓN
        </OwnexBadge>
        <OwnexBadge
          :variant="confidence >= 80 ? 'success' : confidence >= 60 ? 'warning' : 'error'"
          dot
        >
          {{ confidenceLabel }}
        </OwnexBadge>
      </div>
      <div class="ownex-next-action__confidence">
        <span class="ownex-next-action__confidence-label">Confianza</span>
        <div class="ownex-next-action__confidence-bar" role="progressbar" :aria-valuenow="confidence" aria-valuemin="0" aria-valuemax="100">
          <div
            class="ownex-next-action__confidence-fill"
            :style="{ width: `${confidence}%`, backgroundColor: confidenceColor }"
          />
        </div>
        <span class="ownex-next-action__confidence-value" :style="{ color: confidenceColor }">
          {{ confidence }}%
        </span>
      </div>
    </div>

    <!-- Main content -->
    <div class="ownex-next-action__content">
      <h2 class="ownex-next-action__title">{{ title }}</h2>
      <p class="ownex-next-action__description">{{ description }}</p>

      <!-- Meta info -->
      <div v-if="Object.keys(meta).length" class="ownex-next-action__meta">
        <div
          v-for="(value, key) in meta"
          :key="key"
          class="ownex-next-action__meta-item"
        >
          <span class="ownex-next-action__meta-key">{{ key }}</span>
          <span class="ownex-next-action__meta-value">{{ value }}</span>
        </div>
      </div>

      <!-- Reasoning -->
      <div v-if="reasoning" class="ownex-next-action__reasoning">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4M12 8h.01" />
        </svg>
        <span>{{ reasoning }}</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="ownex-next-action__actions">
      <OwnexButton
        :variant="primaryAction.variant"
        size="lg"
        class="ownex-next-action__primary-btn"
        @click="handlePrimaryAction"
      >
        {{ primaryAction.label }}
      </OwnexButton>
      <OwnexButton
        v-if="secondaryAction"
        :variant="secondaryAction.variant"
        size="lg"
        class="ownex-next-action__secondary-btn"
        @click="handleSecondaryAction"
      >
        {{ secondaryAction.label }}
      </OwnexButton>
    </div>
  </div>
</template>

<style scoped>
.ownex-next-action {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.95), rgba(5, 5, 5, 0.85));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  position: relative;
  overflow: hidden;
}

/* Gold accent border top */
.ownex-next-action::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--ownex-gold), transparent);
}

/* Header */
.ownex-next-action__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.ownex-next-action__badge-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ownex-next-action__confidence {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 200px;
}

.ownex-next-action__confidence-label {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ownex-text-muted);
  white-space: nowrap;
}

.ownex-next-action__confidence-bar {
  flex: 1;
  height: 6px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-next-action__confidence-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-slow) cubic-bezier(0.16, 1, 0.3, 1);
}

.ownex-next-action__confidence-value {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  min-width: 40px;
  text-align: right;
}

/* Content */
.ownex-next-action__content {
  margin-bottom: var(--space-5);
}

.ownex-next-action__title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  margin: 0 0 var(--space-2);
  line-height: 1.2;
}

.ownex-next-action__description {
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-4);
  line-height: 1.6;
}

/* Meta */
.ownex-next-action__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3) var(--space-5);
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  background: var(--ownex-bg-base);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.ownex-next-action__meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ownex-next-action__meta-key {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-muted);
}

.ownex-next-action__meta-value {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ownex-white);
  font-variant-numeric: tabular-nums;
}

/* Reasoning */
.ownex-next-action__reasoning {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-md);
  color: var(--ownex-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.ownex-next-action__reasoning svg {
  color: var(--ownex-blue);
  flex-shrink: 0;
  margin-top: 1px;
}

/* Actions */
.ownex-next-action__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.ownex-next-action__primary-btn {
  flex: 1;
}

.ownex-next-action__secondary-btn {
  flex: 1;
  max-width: 140px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-next-action__confidence-fill {
    transition: none;
  }
}
</style>