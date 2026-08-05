<script setup lang="ts">
import { computed } from 'vue'
import UniversalExplanationLayer from './UniversalExplanationLayer.vue'
import ConfidenceBadge from './ConfidenceBadge.vue'
import RequirementBadge from './RequirementBadge.vue'
import type { IncomeGuidance } from '@/types/guided'

interface Props {
  opportunity: IncomeGuidance | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'run-cycle'): void
}>()

const explanationLayer = computed(() => {
  if (!props.opportunity) return null
  return props.opportunity.explanation
})

const getDifficultyLabel = (difficulty: string) => {
  const labels: Record<string, string> = {
    beginner: 'Principiante',
    intermediate: 'Intermedio',
    advanced: 'Avanzado',
    expert: 'Experto',
  }
  return labels[difficulty] || difficulty
}

const getDifficultyColor = (difficulty: string) => {
  const colors: Record<string, string> = {
    beginner: 'from-green-500 to-emerald-500',
    intermediate: 'from-blue-500 to-cyan-500',
    advanced: 'from-orange-500 to-amber-500',
    expert: 'from-red-500 to-rose-500',
  }
  return colors[difficulty] || 'from-gray-500 to-gray-400'
}

const getBadgeColor = (required: boolean) => {
  return required ? 'from-red-500 to-rose-500' : 'from-green-500 to-emerald-500'
}

const getBadgeLabel = (required: boolean) => {
  return required ? 'REQUERIDO' : 'NO requerido'
}
</script>

<template>
  <div class="income-guidance" v-if="opportunity">
    <div class="income-guidance__header">
      <div class="income-guidance__title-group">
        <h3 class="income-guidance__title">{{ opportunity.title }}</h3>
        <span
          class="income-guidance__difficulty"
          :style="{ background: `linear-gradient(135deg, ${getDifficultyColor(opportunity.difficulty)})` }"
        >
          {{ getDifficultyLabel(opportunity.difficulty) }}
        </span>
      </div>
      <p class="income-guidance__summary">
        {{ opportunity.summary }}
      </p>
    </div>

    <div class="income-guidance__requirements">
      <h4 class="income-guidance__section-title">Requisitos</h4>
      <div class="income-guidance__req-grid">
        <RequirementBadge
          :label="'Programación'"
          :required="opportunity.required.programming"
        />
        <RequirementBadge
          :label="'Portfolio'"
          :required="opportunity.required.portfolio"
        />
        <RequirementBadge
          :label="'Entrevista'"
          :required="opportunity.required.interview"
        />
      </div>
    </div>

    <div class="income-guidance__preparation">
      <h4 class="income-guidance__section-title">Lo que OWNEX prepara por ti</h4>
      <div class="income-guidance__prep-bar">
        <div class="income-guidance__prep-fill" :style="{ width: `${opportunity.own_prep_pct}%` }"></div>
      </div>
      <p class="income-guidance__prep-text">
        OWNEX puede preparar el <strong>{{ opportunity.own_prep_pct }}%</strong> del trabajo.
      </p>
    </div>

    <div class="income-guidance__action">
      <h4 class="income-guidance__section-title">Tu acción requerida</h4>
      <p class="income-guidance__action-text">
        {{ opportunity.user_action }}
      </p>
    </div>

    <UniversalExplanationLayer :layer="explanationLayer" />

    <ConfidenceBadge
      :level="opportunity.confidence.level"
      :detail="opportunity.confidence.detail"
    />
  </div>

  <div class="income-guidance--empty" v-else>
    <div class="income-guidance__empty">
      <span class="income-guidance__empty-icon">🎯</span>
      <h4>Sin oportunidad seleccionada</h4>
      <p>Corre el daily brief o revisa el work bank para ver oportunidades.</p>
      <button
        class="income-guidance__run-btn"
        @click="$emit('run-cycle')"
      >
        Correr ciclo diario
      </button>
    </div>
  </div>
</template>

<style scoped>
.income-guidance {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(10px);
}

.income-guidance__header {
  margin-bottom: 20px;
}

.income-guidance__title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.income-guidance__title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0;
}

.income-guidance__difficulty {
  font-size: 0.625rem;
  font-weight: 600;
  color: white;
  padding: 4px 10px;
  border-radius: 9999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.income-guidance__summary {
  font-size: 0.875rem;
  color: #aaa;
  margin: 0;
  line-height: 1.5;
}

.income-guidance__section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 20px 0 12px;
}

.income-guidance__req-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.income-guidance__prep-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 8px;
}

.income-guidance__prep-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 9999px;
  transition: width 0.5s ease;
}

.income-guidance__prep-text {
  font-size: 0.75rem;
  color: #aaa;
  margin: 0;
}

.income-guidance__prep-text strong {
  color: #10b981;
}

.income-guidance__action-text {
  font-size: 0.875rem;
  color: #ddd;
  margin: 0;
  line-height: 1.6;
}

.income-guidance__empty {
  text-align: center;
  padding: 40px 20px;
}

.income-guidance__empty-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 12px;
}

.income-guidance__empty h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0 0 8px;
}

.income-guidance__empty p {
  font-size: 0.875rem;
  color: #888;
  margin: 0 0 20px;
}

.income-guidance__run-btn {
  background: linear-gradient(135deg, #3b82f6, #06b6d4);
  border: none;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  padding: 12px 24px;
  border-radius: 9999px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.income-guidance__run-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px color-mix(in srgb, #3b82f6 40%, transparent);
}

@media (max-width: 480px) {
  .income-guidance {
    padding: 16px;
  }
}
</style>