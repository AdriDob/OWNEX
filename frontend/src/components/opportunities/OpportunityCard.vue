<script setup lang="ts">
/**
 * Opportunity Radar Card — Per OWNEX_DESIGN_SYSTEM.md §4.4
 * "NO es una lista de links. Es un ranking por Valor Esperado (EV)."
 */

import { computed } from 'vue'
import OwnexCard from '../ui/OwnexCard.vue'
import OwnexBadge from '../ui/OwnexBadge.vue'
import OwnexButton from '../ui/OwnexButton.vue'

interface Opportunity {
  id: string
  title: string
  type: 'idor' | 'ssrf' | 'xss' | 'rce' | 'bypass' | 'logic' | 'other'
  platform: 'hackerone' | 'bugcrowd' | 'intigriti' | 'synack' | 'yeswehack' | 'private'
  program: string
  reward: number
  probability: number // 0-100
  timeEstimate: number // minutes
  ev: number // Expected Value = reward * probability * (1 - difficulty)
  confidence: number // 0-100
  tags: string[]
  description: string
  foundAt: Date
  status: 'new' | 'investigating' | 'validating' | 'reporting' | 'submitted' | 'discarded'
}

interface Props {
  opportunity: Opportunity
  rank: number
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
})

const emit = defineEmits<{
  start: [opportunity: Opportunity]
  view: [opportunity: Opportunity]
  discard: [opportunity: Opportunity]
}>()

const starRating = computed(() => {
  const stars = Math.round(props.opportunity.probability / 20)
  return '★'.repeat(stars) + '☆'.repeat(5 - stars)
})

const formatReward = (amount: number) => {
  if (amount >= 10000) return `$${(amount / 1000).toFixed(1)}k`
  if (amount >= 1000) return `$${amount.toLocaleString()}`
  return `$${amount}`
}

const formatTime = (minutes: number) => {
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

const getTypeConfig = (type: Opportunity['type']) => {
  const configs: Record<Opportunity['type'], { label: string; color: string }> = {
    idor: { label: 'IDOR', color: 'var(--ownex-blue)' },
    ssrf: { label: 'SSRF', color: 'var(--cycle-forge)' },
    xss: { label: 'XSS', color: 'var(--cycle-pulse)' },
    rce: { label: 'RCE', color: 'var(--status-error)' },
    bypass: { label: 'Bypass', color: 'var(--cycle-odyssey)' },
    logic: { label: 'Logic', color: 'var(--cycle-atlas)' },
    other: { label: 'Other', color: 'var(--text-muted)' },
  }
  return configs[type]
}
</script>

<template>
  <OwnexCard
    variant="highlight"
    :hoverable="!compact"
    :padded="!compact"
    class="ownex-opportunity"
    :class="{ 'ownex-opportunity--compact': compact }"
    role="article"
    :aria-label="`Oportunidad ${rank}: ${opportunity.title}`"
  >
    <!-- Header with rank and type -->
    <div class="ownex-opportunity__header">
      <div class="ownex-opportunity__rank" :aria-label="`Rank ${rank}`">
        #{{ rank }}
      </div>

      <div class="ownex-opportunity__type-row">
        <OwnexBadge
          variant="default"
          :style="{ borderColor: typeConfig.color, color: typeConfig.color }"
          size="sm"
        >
          {{ typeConfig.label }}
        </OwnexBadge>

        <OwnexBadge
          v-if="opportunity.platform !== 'private'"
          :variant="'platform'"
          :platform="opportunity.platform"
          size="sm"
          dot
        />
      </div>
    </div>

    <!-- Title & Program -->
    <div class="ownex-opportunity__main">
      <h4 class="ownex-opportunity__title">{{ opportunity.title }}</h4>
      <p class="ownex-opportunity__program">{{ opportunity.program }}</p>

      <p v-if="!compact" class="ownex-opportunity__description">{{ opportunity.description }}</p>
    </div>

    <!-- Metrics Grid -->
    <div class="ownex-opportunity__metrics" role="list" aria-label="Métricas de la oportunidad">
      <div class="ownex-opportunity__metric" role="listitem">
        <span class="ownex-opportunity__metric-label">REWARD</span>
        <span class="ownex-opportunity__metric-value ownex-opportunity__metric-value--gold">
          {{ formatReward(opportunity.reward) }}
        </span>
      </div>

      <div class="ownex-opportunity__metric" role="listitem">
        <span class="ownex-opportunity__metric-label">TIEMPO</span>
        <span class="ownex-opportunity__metric-value">
          {{ formatTime(opportunity.timeEstimate) }}
        </span>
      </div>

      <div class="ownex-opportunity__metric" role="listitem">
        <span class="ownex-opportunity__metric-label">PROB</span>
        <span class="ownex-opportunity__metric-value" :style="{ color: probabilityColor }">
          {{ opportunity.probability }}%
        </span>
      </div>

      <div class="ownex-opportunity__metric ownex-opportunity__metric--ev" role="listitem">
        <span class="ownex-opportunity__metric-label">EV</span>
        <span class="ownex-opportunity__metric-value ownex-opportunity__metric-value--ev">
          {{ formatReward(opportunity.ev) }}
        </span>
      </div>
    </div>

    <!-- Confidence & Stars -->
    <div v-if="!compact" class="ownex-opportunity__confidence">
      <div class="ownex-opportunity__stars" aria-label="Confianza">
        <span v-for="i in 5" :key="i" class="ownex-opportunity__star" :class="{ filled: i <= Math.round(opportunity.probability / 20) }">
          ★
        </span>
        <span class="ownex-opportunity__confidence-value">{{ opportunity.confidence }}%</span>
      </div>

      <div class="ownex-opportunity__tags" aria-label="Tags">
        <OwnexBadge
          v-for="tag in opportunity.tags.slice(0, 3)"
          :key="tag"
          variant="default"
          size="sm"
        >
          {{ tag }}
        </OwnexBadge>
        <OwnexBadge
          v-if="opportunity.tags.length > 3"
          variant="default"
          size="sm"
        >
          +{{ opportunity.tags.length - 3 }}
        </OwnexBadge>
      </div>
    </div>

    <!-- Actions -->
    <div class="ownex-opportunity__actions">
      <OwnexButton
        variant="primary"
        size="sm"
        :full-width="compact"
        @click="emit('start', opportunity)"
        :disabled="opportunity.status !== 'new' && opportunity.status !== 'investigating'"
      >
        <span v-if="opportunity.status === 'new'">Iniciar Ciclo</span>
        <span v-else-if="opportunity.status === 'investigating'">Continuar</span>
        <span v-else>Ver</span>
      </OwnexButton>

      <OwnexButton
        v-if="!compact"
        variant="ghost"
        size="sm"
        @click="emit('view', opportunity)"
      >
        Detalles
      </OwnexButton>

      <OwnexButton
        v-if="!compact && (opportunity.status === 'new' || opportunity.status === 'investigating')"
        variant="ghost"
        size="sm"
        @click="emit('discard', opportunity)"
      >
        Descartar
      </OwnexButton>
    </div>
  </OwnexCard>
</template>

<style scoped>
.ownex-opportunity {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-opportunity--compact {
  gap: var(--space-2);
  padding: var(--space-3) !important;
}

.ownex-opportunity__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.ownex-opportunity__rank {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-muted);
  line-height: 1;
  flex-shrink: 0;
}

.ownex-opportunity__type-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ownex-opportunity__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.ownex-opportunity__title {
  font-family: var(--font-body);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
  line-height: var(--leading-snug);
}

.ownex-opportunity__program {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin: 0;
}

.ownex-opportunity__description {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: var(--leading-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ownex-opportunity__metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  padding: var(--space-3);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
}

.ownex-opportunity--compact .ownex-opportunity__metrics {
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
  padding: var(--space-2);
}

.ownex-opportunity__metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: center;
}

.ownex-opportunity__metric--ev {
  grid-column: 1 / -1;
}

.ownex-opportunity--compact .ownex-opportunity__metric--ev {
  grid-column: auto;
}

.ownex-opportunity__metric-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-opportunity__metric-value {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}

.ownex-opportunity--compact .ownex-opportunity__metric-value {
  font-size: var(--text-base);
}

.ownex-opportunity__metric-value--gold {
  color: var(--ownex-gold);
}

.ownex-opportunity__metric-value--ev {
  color: var(--status-success);
  font-size: var(--text-xl);
}

.ownex-opportunity--compact .ownex-opportunity__metric-value--ev {
  font-size: var(--text-lg);
}

.ownex-opportunity__confidence {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.ownex-opportunity__stars {
  display: flex;
  align-items: center;
  gap: 2px;
}

.ownex-opportunity__star {
  font-size: var(--text-sm);
  color: var(--border-subtle);
  line-height: 1;
}

.ownex-opportunity__star.filled {
  color: var(--ownex-gold);
}

.ownex-opportunity__confidence-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-left: var(--space-2);
}

.ownex-opportunity__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.ownex-opportunity__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  flex-wrap: wrap;
}

.ownex-opportunity--compact .ownex-opportunity__actions {
  padding-top: 0;
  border-top: none;
  justify-content: flex-end;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-opportunity__metric-value {
    transition: none;
  }
}
</style>