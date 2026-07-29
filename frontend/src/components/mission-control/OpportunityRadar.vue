<script setup lang="ts">
/**
 * OWNEX Opportunity Radar — Ranked opportunities with context
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'
import OwnexButton from '../ui/OwnexButton.vue'

interface Opportunity {
  id: string
  title: string
  platform: 'hackerone' | 'bugcrowd' | 'intigriti' | 'synack' | 'yeswehack' | 'custom'
  type: 'bug-bounty' | 'vdp' | 'ctf' | 'freelance' | 'research'
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  reward?: string
  roiScore?: number
  confidence: number
  tags: string[]
  target?: string
  postedAt: string
  sourceUrl?: string
}

interface Props {
  opportunities: Opportunity[]
  maxItems?: number
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  opportunities: () => [],
  maxItems: 10,
  showActions: true,
})

const severityConfig = computed(() => ({
  critical: { label: 'CRÍTICO', variant: 'error' as const, color: 'var(--ownex-red)' },
  high: { label: 'ALTO', variant: 'warning' as const, color: 'var(--ownex-yellow)' },
  medium: { label: 'MEDIO', variant: 'default' as const, color: 'var(--ownex-blue)' },
  low: { label: 'BAJO', variant: 'default' as const, color: 'var(--ownex-text-muted)' },
  info: { label: 'INFO', variant: 'default' as const, color: 'var(--ownex-text-muted)' },
}))

const platformConfig = computed(() => ({
  hackerone: { label: 'HackerOne', color: 'var(--color-hackerone)' },
  bugcrowd: { label: 'Bugcrowd', color: 'var(--color-bugcrowd)' },
  intigriti: { label: 'Intigriti', color: 'var(--color-intigriti)' },
  synack: { label: 'Synack', color: 'var(--color-synack)' },
  yeswehack: { label: 'YesWeHack', color: 'var(--color-yeswehack)' },
  custom: { label: 'Custom', color: 'var(--ownex-text-muted)' },
}))

const formatRelativeTime = (isoString: string) => {
  const diff = Date.now() - new Date(isoString).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return 'Hace < 1h'
  if (hours < 24) return `Hace ${hours}h`
  const days = Math.floor(hours / 24)
  return `Hace ${days}d`
}

const getRoiColor = (score?: number) => {
  if (!score) return 'var(--ownex-text-muted)'
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  if (score >= 40) return 'var(--ownex-blue)'
  return 'var(--ownex-text-muted)'
}
</script>

<template>
  <div class="ownex-opportunity-radar" role="region" aria-label="Radar de oportunidades">
    <div class="ownex-opportunity-radar__header">
      <h3 class="ownex-opportunity-radar__title">Radar de Oportunidades</h3>
      <OwnexBadge variant="default" size="sm">
        {{ displayedOpportunities.length }} oportunidades
      </OwnexBadge>
    </div>

    <div class="ownex-opportunity-radar__list">
      <div
        v-for="(opp, index) in displayedOpportunities"
        :key="opp.id"
        class="ownex-opportunity-radar__item"
        :style="{ '--index': index }"
      >
        <!-- Rank indicator -->
        <div class="ownex-opportunity-radar__rank">
          <span class="ownex-opportunity-radar__rank-number">{{ index + 1 }}</span>
          <div class="ownex-opportunity-radar__rank-bar" :style="{ height: `${(displayedOpportunities.length - index) / displayedOpportunities.length * 100}%` }" />
        </div>

        <!-- Main content -->
        <div class="ownex-opportunity-radar__content">
          <div class="ownex-opportunity-radar__title-row">
            <h4 class="ownex-opportunity-radar__title">{{ opp.title }}</h4>
            <OwnexBadge
              :variant="severityConfig[opp.severity].variant"
              size="sm"
              class="ownex-opportunity-radar__severity"
            >
              {{ severityConfig[opp.severity].label }}
            </OwnexBadge>
          </div>

          <div class="ownex-opportunity-radar__meta">
            <OwnexBadge
              :variant="'platform'"
              :platform="opp.platform"
              size="sm"
            >
              {{ platformConfig[opp.platform].label }}
            </OwnexBadge>
            <OwnexBadge variant="default" size="sm">
              {{ formatType(opp.type) }}
            </OwnexBadge>
            <span v-if="opp.target" class="ownex-opportunity-radar__target">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              {{ opp.target }}
            </span>
            <span class="ownex-opportunity-radar__time">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              {{ formatRelativeTime(opp.postedAt) }}
            </span>
          </div>

          <!-- Tags -->
          <div v-if="opp.tags.length" class="ownex-opportunity-radar__tags">
            <span
              v-for="tag in opp.tags.slice(0, 4)"
              :key="tag"
              class="ownex-opportunity-radar__tag"
            >
              {{ tag }}
            </span>
          </div>

          <!-- Confidence & ROI -->
          <div class="ownex-opportunity-radar__scores">
            <div class="ownex-opportunity-radar__score">
              <span class="ownex-opportunity-radar__score-label">Confianza</span>
              <div class="ownex-opportunity-radar__score-bar">
                <div
                  class="ownex-opportunity-radar__score-fill"
                  :style="{ width: `${opp.confidence}%`, backgroundColor: getConfidenceColor(opp.confidence) }"
                />
              </div>
              <span class="ownex-opportunity-radar__score-value" :style="{ color: getConfidenceColor(opp.confidence) }">
                {{ opp.confidence }}%
              </span>
            </div>
            <div v-if="opp.roiScore !== undefined" class="ownex-opportunity-radar__score">
              <span class="ownex-opportunity-radar__score-label">ROI</span>
              <div class="ownex-opportunity-radar__score-bar">
                <div
                  class="ownex-opportunity-radar__score-fill"
                  :style="{ width: `${opp.roiScore}%`, backgroundColor: getRoiColor(opp.roiScore) }"
                />
              </div>
              <span class="ownex-opportunity-radar__score-value" :style="{ color: getRoiColor(opp.roiScore) }">
                {{ opp.roiScore }}%
              </span>
            </div>
            <div v-if="opp.reward" class="ownex-opportunity-radar__reward">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <line x1="12" y1="1" x2="12" y2="23" />
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
              </svg>
              <span class="ownex-opportunity-radar__reward-value">{{ opp.reward }}</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div v-if="props.showActions" class="ownex-opportunity-radar__actions">
          <OwnexButton
            variant="secondary"
            size="sm"
            @click="$emit('investigate', opp)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            Investigar
          </OwnexButton>
          <OwnexButton
            v-if="opp.sourceUrl"
            variant="ghost"
            size="sm"
            @click="window.open(opp.sourceUrl, '_blank')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            Ver
          </OwnexButton>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!props.opportunities.length" class="ownex-opportunity-radar__empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        <p>No hay oportunidades</p>
        <span>Ejecuta el ciclo Atlas para descubrir nuevas</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts>
import { computed } from 'vue'

const displayedOpportunities = computed(() =>
  props.opportunities.slice(0, props.maxItems)
)

const formatType = (type: string) => {
  const labels: Record<string, string> = {
    'bug-bounty': 'Bug Bounty',
    'vdp': 'VDP',
    'ctf': 'CTF',
    'freelance': 'Freelance',
    'research': 'Research',
  }
  return labels[type] || type
}

const getConfidenceColor = (score: number) => {
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}
</script>

<style scoped>
.ownex-opportunity-radar {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.9), rgba(5, 5, 5, 0.7));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.ownex-opportunity-radar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.ownex-opportunity-radar__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  margin: 0;
}

.ownex-opportunity-radar__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-opportunity-radar__item {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  gap: var(--space-4);
  align-items: start;
  padding: var(--space-3);
  background: var(--ownex-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  animation: staggerFadeIn 0.3s ease-out both;
  animation-delay: calc(var(--index, 0) * 40ms);
}

.ownex-opportunity-radar__item:hover {
  border-color: var(--color-border-light);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.3);
}

/* Rank */
.ownex-opportunity-radar__rank {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding-top: var(--space-2);
}

.ownex-opportunity-radar__rank-number {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-blue);
  line-height: 1;
}

.ownex-opportunity-radar__rank-bar {
  width: 3px;
  height: 40px;
  background: linear-gradient(180deg, var(--ownex-blue), transparent);
  border-radius: var(--radius-full);
}

/* Content */
.ownex-opportunity-radar__content {
  min-width: 0;
}

.ownex-opportunity-radar__title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.ownex-opportunity-radar__title {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--ownex-white);
  margin: 0;
  line-height: 1.4;
  flex: 1;
}

.ownex-opportunity-radar__severity {
  flex-shrink: 0;
  font-size: 9px;
}

.ownex-opportunity-radar__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.ownex-opportunity-radar__target,
.ownex-opportunity-radar__time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-size: 10px;
  color: var(--ownex-text-muted);
}

.ownex-opportunity-radar__target svg,
.ownex-opportunity-radar__time svg {
  color: var(--ownex-text-disabled);
}

/* Tags */
.ownex-opportunity-radar__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}

.ownex-opportunity-radar__tag {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--ownex-text-muted);
  background: var(--ownex-bg-deep);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

/* Scores */
.ownex-opportunity-radar__scores {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.ownex-opportunity-radar__score {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ownex-opportunity-radar__score-label {
  font-family: var(--font-body);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-disabled);
}

.ownex-opportunity-radar__score-bar {
  width: 60px;
  height: 4px;
  background: var(--ownex-bg-deep);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-opportunity-radar__score-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-base) cubic-bezier(0.16, 1, 0.3, 1);
}

.ownex-opportunity-radar__score-value {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  min-width: 32px;
}

.ownex-opportunity-radar__reward {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: var(--radius-md);
}

.ownex-opportunity-radar__reward svg {
  color: var(--ownex-gold);
}

.ownex-opportunity-radar__reward-value {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-gold);
}

/* Actions */
.ownex-opportunity-radar__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-left: var(--space-3);
  border-left: 1px solid var(--color-border);
}

.ownex-opportunity-radar__actions .ownex-btn {
  justify-content: center;
}

/* Empty state */
.ownex-opportunity-radar__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
  color: var(--ownex-text-muted);
}

.ownex-opportunity-radar__empty svg {
  margin-bottom: var(--space-3);
  opacity: 0.3;
}

.ownex-opportunity-radar__empty p {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-1);
}

.ownex-opportunity-radar__empty span {
  font-size: 11px;
  color: var(--ownex-text-disabled);
}

/* Animations */
@keyframes staggerFadeIn {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-opportunity-radar__item {
    animation: none;
  }
  .ownex-opportunity-radar__score-fill {
    transition: none;
  }
}
</style>