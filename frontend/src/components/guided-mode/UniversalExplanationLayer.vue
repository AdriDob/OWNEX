<script setup lang="ts">
import { computed } from 'vue'
import ConfidenceBadge from './ConfidenceBadge.vue'
import type { ExplanationLayer } from '@/types/guided'

interface Props {
  layer: ExplanationLayer
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
})

const sectionOrder = ['what', 'why', 'how', 'result', 'nextStep'] as const

const sectionLabels: Record<string, { label: string; icon: string; color: string }> = {
  what: { label: 'QUÉ', icon: '📋', color: 'from-blue-500 to-cyan-500' },
  why: { label: 'POR QUÉ', icon: '🎯', color: 'from-green-500 to-emerald-500' },
  how: { label: 'CÓMO', icon: '⚙️', color: 'from-purple-500 to-violet-500' },
  result: { label: 'RESULTADO', icon: '✅', color: 'from-orange-500 to-amber-500' },
  nextStep: { label: 'PRÓXIMO PASO', icon: '➡️', color: 'from-cyan-500 to-blue-500' },
}
</script>

<template>
  <div class="explanation-layer">
    <div v-if="!compact" class="explanation-layer__header">
      <h3 class="explanation-layer__title">Explicación Universal</h3>
      <p class="explanation-layer__subtitle">
        Cada acción de OWNEX tiene: Qué · Por qué · Cómo · Resultado · Próximo paso
      </p>
    </div>

    <div class="explanation-layer__grid">
      <div
        v-for="key in sectionOrder"
        :key="key"
        class="explanation-layer__card"
        :style="{ '--section-color': sectionLabels[key].color }"
      >
        <div class="explanation-layer__card-header">
          <div class="explanation-layer__icon" :style="{ background: `linear-gradient(135deg, ${sectionLabels[key].color})` }">
            {{ sectionLabels[key].icon }}
          </div>
          <h4 class="explanation-layer__section-label">{{ sectionLabels[key].label }}</h4>
        </div>
        <p
          v-if="layer[key]"
          class="explanation-layer__content"
          :class="{ 'explanation-layer__content--empty': !layer[key] }"
        >
          {{ layer[key] }}
        </p>
        <p v-else class="explanation-layer__content explanation-layer__content--empty">
          Sin información disponible
        </p>
      </div>
    </div>

    <div v-if="!compact && layer.confidence" class="explanation-layer__confidence">
      <ConfidenceBadge :level="layer.confidence.level" :detail="layer.confidence.detail" />
    </div>
  </div>
</template>

<style scoped>
.explanation-layer {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
}

.explanation-layer__header {
  margin-bottom: 16px;
}

.explanation-layer__title {
  font-size: 1rem;
  font-weight: 600;
  color: #f0f0f0;
  margin: 0 0 4px;
}

.explanation-layer__subtitle {
  font-size: 0.75rem;
  color: #888;
  margin: 0;
}

.explanation-layer__grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.explanation-layer__card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 16px;
  min-height: 120px;
  display: flex;
  flex-direction: column;
}

.explanation-layer__card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.explanation-layer__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: white;
  box-shadow: 0 2px 8px color-mix(in srgb, var(--section-color) 40%, transparent);
}

.explanation-layer__section-label {
  font-size: 0.625rem;
  font-weight: 600;
  color: #aaa;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.explanation-layer__content {
  font-size: 0.75rem;
  color: #ddd;
  line-height: 1.5;
  margin: 0;
  flex: 1;
}

.explanation-layer__content--empty {
  color: #666;
  font-style: italic;
  font-size: 0.625rem;
}

@media (max-width: 768px) {
  .explanation-layer__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
   .explanation-layer__grid {
    grid-template-columns: 1fr;
  }
}
</style>