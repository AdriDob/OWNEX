<script setup lang="ts">
import { computed, ref } from 'vue'
import { useGuidedMode } from '@/composables/useGuidedMode'
import ConfidenceBadge from './ConfidenceBadge.vue'

interface FirstDayStep {
  step: number
  title: string
  why: string
  action: string
  effort_hours: number
}

interface FirstDayGuideData {
  generated_at: string
  total_effort_hours: number
  philosophy: string
  principle: string
  steps: FirstDayStep[]
}

interface Props {
  guide: FirstDayGuideData | null
  progress: { completed_steps: number[]; total_steps: number; pct: number }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'step-complete': [step: number]
}>()

const completedSteps = ref<Set<number>>(new Set(props.progress?.completed_steps || []))

const totalHours = computed(() => props.guide?.total_effort_hours || 0)
const completedCount = computed(() => completedSteps.value.size)
const totalSteps = computed(() => props.guide?.steps?.length || 5)

const markComplete = (step: number) => {
  if (completedSteps.value.has(step)) {
    completedSteps.value.delete(step)
  } else {
    completedSteps.value.add(step)
  }
  emit('step-complete', step)
}

const isComplete = (step: number) => completedSteps.value.has(step)

const stepIcon = (step: number) => {
  const icons: Record<number, string> = {
    1: '🔧',
    2: '🎯',
    3: '🐛',
    4: '📝',
    5: '💼',
  }
  return icons[step] || '📋'
}
</script>

<template>
  <div class="first-day-guide" v-if="guide">
    <div class="first-day-guide__header">
      <div class="first-day-guide__title-group">
        <h3 class="first-day-guide__title">Guía de Primer Día</h3>
        <ConfidenceBadge level="high" detail="Diseñado para principiantes sin experiencia" />
      </div>
      <p class="first-day-guide__philosophy">{{ guide.philosophy }}</p>
      <p class="first-day-guide__principle">{{ guide.principle }}</p>
    </div>

    <div class="first-day-guide__progress">
      <div class="first-day-guide__progress-bar">
        <div
          class="first-day-guide__progress-fill"
          :style="{ width: `${progress.pct}%` }"
        ></div>
      </div>
      <div class="first-day-guide__progress-text">
        <span>{{ progress.completed_steps }} / {{ progress.total_steps }} pasos completados</span>
        <span>{{ progress.pct }}%</span>
      </div>
    </div>

    <div class="first-day-guide__effort">
      <span class="first-day-guide__effort-label">Esfuerzo estimado total:</span>
      <span class="first-day-guide__effort-value">{{ totalHours }} horas</span>
    </div>

    <div class="first-day-guide__steps">
      <div
        v-for="step in guide.steps"
        :key="step.step"
        class="first-day-guide__step"
        :class="{ 'first-day-guide__step--complete': isComplete(step.step) }"
      >
        <div class="first-day-guide__step-header">
          <div class="first-day-guide__step-number" :style="{ background: isComplete(step.step) ? 'linear-gradient(135deg, var(--ownex-green), var(--ownex-green))' : 'linear-gradient(135deg, var(--ownex-danger), var(--ownex-accent))' }">
            {{ step.step }}
          </div>
          <div class="first-day-guide__step-icon">{{ stepIcon(step.step) }}</div>
          <div class="first-day-guide__step-title">{{ step.title }}</div>
          <span
            class="first-day-guide__step-effort"
            :style="{ background: isComplete(step.step) ? 'linear-gradient(135deg, var(--ownex-green), var(--ownex-green))' : 'linear-gradient(135deg, rgba(255,255,255,0.1))' }"
          >
            {{ step.effort_hours }}h
          </span>
          <button
            class="first-day-guide__step-toggle"
            @click="markComplete(step.step)"
            :aria-pressed="isComplete(step.step)"
            :aria-label="isComplete(step.step) ? 'Marcar como pendiente' : 'Marcar como completado'"
          >
            <span v-if="isComplete(step.step)" class="first-day-guide__check">✓</span>
            <span v-else class="first-day-guide__circle"></span>
          </button>
        </div>

        <div class="first-day-guide__step-content">
          <div class="first-day-guide__step-why">
            <span class="first-day-guide__step-label">¿Por qué?</span>
            <p>{{ step.why }}</p>
          </div>
          <div class="first-day-guide__step-action">
            <span class="first-day-guide__step-label">Acción</span>
            <p>{{ step.action }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="first-day-guide__principle-box">
      <p class="first-day-guide__principle-text">{{ guide.principle }}</p>
    </div>
  </div>

  <div class="first-day-guide--empty" v-else>
    <div class="first-day-guide__empty">
      <span class="first-day-guide__empty-icon">🚀</span>
      <h4>Primera guía no disponible</h4>
      <p>Ejecuta el daily brief para generar tu plan personalizado.</p>
    </div>
  </div>
</template>

<style scoped>
.first-day-guide {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.first-day-guide__header {
  margin-bottom: 20px;
}

.first-day-guide__title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.first-day-guide__title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--ownex-text-primary);
  margin: 0;
}

.first-day-guide__philosophy {
  font-size: 0.875rem;
  color: var(--ownex-text-secondary);
  margin: 0 0 8px;
  font-style: italic;
}

.first-day-guide__principle {
  font-size: 0.75rem;
  color: var(--ownex-text-muted);
  margin: 0;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border-left: 3px solid var(--ownex-danger);
}

.first-day-guide__progress {
  margin-bottom: 16px;
}

.first-day-guide__progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 8px;
}

.first-day-guide__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--ownex-danger), var(--ownex-accent));
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.first-day-guide__progress-text {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--ownex-text-secondary);
}

.first-day-guide__effort {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border-left: 3px solid var(--ownex-green);
}

.first-day-guide__effort-label {
  font-size: 0.75rem;
  color: var(--ownex-text-secondary);
}

.first-day-guide__effort-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ownex-green);
}

.first-day-guide__steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.first-day-guide__step {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s ease;
}

.first-day-guide__step--complete {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.05);
}

.first-day-guide__step-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  cursor: pointer;
}

.first-day-guide__step-number {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.first-day-guide__step-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.first-day-guide__step-title {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ownex-text-primary);
}

.first-day-guide__step-effort {
  font-size: 0.625rem;
  font-weight: 600;
  color: white;
  padding: 3px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.first-day-guide__step-toggle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.2);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.first-day-guide__step-toggle:hover {
  border-color: var(--ownex-danger);
  background: rgba(59, 130, 246, 0.1);
}

.first-day-guide__step--complete .first-day-guide__step-toggle {
  border-color: var(--ownex-green);
  background: var(--ownex-green);
}

.first-day-guide__check {
  font-size: 0.75rem;
  color: white;
}

.first-day-guide__circle {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.first-day-guide__step-content {
  padding: 0 28px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.first-day-guide__step-why,
.first-day-guide__step-action {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}

.first-day-guide__step-label {
  font-size: 0.625rem;
  font-weight: 600;
  color: var(--ownex-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 6px;
}

.first-day-guide__step-why p,
.first-day-guide__step-action p {
  font-size: 0.75rem;
  color: var(--ownex-text-muted);
  margin: 0;
  line-height: 1.5;
}

.first-day-guide__principle-box {
  margin-top: 20px;
  padding: 16px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
}

.first-day-guide__principle-text {
  font-size: 0.75rem;
  color: var(--ownex-accent);
  margin: 0;
  line-height: 1.5;
  text-align: center;
}

@media (max-width: 480px) {
  .first-day-guide__step-header {
    padding: 12px;
  }
   .first-day-guide__step-content {
    grid-template-columns: 1fr;
  }
}
</style>