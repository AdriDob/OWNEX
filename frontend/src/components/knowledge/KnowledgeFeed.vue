<script setup lang="ts">
/**
 * Knowledge Feed Card — Per OWNEX_DESIGN_SYSTEM.md §4.5
 * "Un Cerebro, No Un Log"
 * Cada entrada = aprendizaje accionable, no "se escaneó X"
 */

import { computed } from 'vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'

interface KnowledgeEntry {
  id: string
  type: 'pattern' | 'insight' | 'technique' | 'financial' | 'platform'
  title: string
  description: string
  confidence: number
  evidence: string
  appliedTo?: string
  discoveredAt: Date
  tags: string[]
  actionable: boolean
  actionLabel?: string
  action?: () => void
}

interface Props {
  entries: KnowledgeEntry[]
  compact?: boolean
  maxItems?: number
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
  maxItems: 5,
})

const emit = defineEmits<{ 'apply-pattern': [entry: KnowledgeEntry] }>()

const typeConfig = {
  pattern: { icon: '🧠', label: 'NUEVO PATRÓN', color: 'var(--cycle-security)' },
  insight: { icon: '💡', label: 'INSIGHT', color: 'var(--cycle-forge)' },
  technique: { icon: '⚔️', label: 'TÉCNICA', color: 'var(--cycle-pulse)' },
  financial: { icon: '💰', label: 'INSIGHT FINANCIERO', color: 'var(--cycle-vault)' },
  platform: { icon: '🎯', label: 'PLATAFORMA', color: 'var(--cycle-atlas)' },
} as const

const displayedEntries = computed(() => props.entries.slice(0, props.maxItems))

const formatDate = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - new Date(date).getTime()
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (hours < 1) return 'Hace un momento'
  if (hours < 24) return `Hace ${hours}h`
  if (days < 7) return `Hace ${days}d`
  return new Date(date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
}

const handleAction = (entry: KnowledgeEntry) => {
  if (entry.action) {
    entry.action()
  }
  emit('apply-pattern', entry)
}
</script>

<template>
  <OwnexCard variant="elevated" :padded="!compact">
    <template #default>
      <div class="ownex-knowledge-feed">
        <!-- Header -->
        <div class="ownex-knowledge-feed__header">
          <h3 class="ownex-knowledge-feed__title">
            <span class="ownex-knowledge-feed__icon" aria-hidden="true">🧠</span>
            Aprendizaje Nuevo
          </h3>
          <span class="ownex-knowledge-feed__count" aria-label="Total entradas">
            {{ entries.length }}
          </span>
        </div>

        <!-- Entries -->
        <div class="ownex-knowledge-feed__list" role="feed" aria-label="Feed de conocimiento">
          <div
            v-for="entry in displayedEntries"
            :key="entry.id"
            class="ownex-knowledge-feed__entry"
            :class="[
              'ownex-knowledge-feed__entry--' + entry.type,
              { 'ownex-knowledge-feed__entry--compact': compact }
            ]"
            role="article"
            :aria-labelledby="entry.id + '-title'"
          >
            <!-- Type Badge -->
            <div class="ownex-knowledge-feed__type" :style="{ '--entry-color': typeConfig[entry.type].color }">
              <span class="ownex-knowledge-feed__type-icon" aria-hidden="true">
                {{ typeConfig[entry.type].icon }}
              </span>
              <span class="ownex-knowledge-feed__type-label">
                {{ typeConfig[entry.type].label }}
              </span>
            </div>

            <!-- Content -->
            <div class="ownex-knowledge-feed__content">
              <h4 :id="entry.id + '-title'" class="ownex-knowledge-feed__entry-title">
                {{ entry.title }}
              </h4>
              <p class="ownex-knowledge-feed__entry-description">
                {{ entry.description }}
              </p>

              <!-- Evidence -->
              <div class="ownex-knowledge-feed__evidence">
                <span class="ownex-knowledge-feed__evidence-label">Evidencia:</span>
                <span class="ownex-knowledge-feed__evidence-text">{{ entry.evidence }}</span>
              </div>

              <!-- Meta -->
              <div class="ownex-knowledge-feed__meta">
                <div class="ownex-knowledge-feed__confidence">
                  <span class="ownex-knowledge-feed__confidence-label">Confianza</span>
                  <div class="ownex-knowledge-feed__confidence-bar" role="progressbar" :aria-valuenow="entry.confidence" aria-valuemin="0" aria-valuemax="100">
                    <div class="ownex-knowledge-feed__confidence-fill" :style="{ width: entry.confidence + '%', '--entry-color': typeConfig[entry.type].color }" />
                  </div>
                  <span class="ownex-knowledge-feed__confidence-value">{{ entry.confidence }}%</span>
                </div>

                <div class="ownex-knowledge-feed__applied" v-if="entry.appliedTo">
                  <span class="ownex-knowledge-feed__applied-label">Aplicado a:</span>
                  <span class="ownex-knowledge-feed__applied-value">{{ entry.appliedTo }}</span>
                </div>

                <time class="ownex-knowledge-feed__date" :datetime="entry.discoveredAt.toISOString()">
                  {{ formatDate(entry.discoveredAt) }}
                </time>
              </div>

              <!-- Tags -->
              <div v-if="entry.tags.length" class="ownex-knowledge-feed__tags">
                <OwnexBadge
                  v-for="tag in entry.tags"
                  :key="tag"
                  variant="default"
                  size="sm"
                >
                  {{ tag }}
                </OwnexBadge>
              </div>

              <!-- Action -->
              <div v-if="entry.actionable && entry.actionLabel" class="ownex-knowledge-feed__action">
                <OwnexButton
                  :variant="entry.type === 'financial' ? 'gold' : 'primary'"
                  size="sm"
                  @click="handleAction(entry)"
                >
                  {{ entry.actionLabel }}
                </OwnexButton>
              </div>
            </div>
          </div>
        </div>

        <!-- View All -->
        <div v-if="entries.length > props.maxItems" class="ownex-knowledge-feed__view-all">
          <OwnexButton variant="ghost" size="sm" full-width @click="$emit('view-all')">
            Ver todas las {{ entries.length }} entradas
          </OwnexButton>
        </div>
      </div>
    </template>
  </OwnexCard>
</template>

<style scoped>
.ownex-knowledge-feed {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-knowledge-feed__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ownex-knowledge-feed__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.ownex-knowledge-feed__icon {
  font-size: var(--text-xl);
}

.ownex-knowledge-feed__count {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-1) var(--space-2);
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
}

.ownex-knowledge-feed__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-knowledge-feed__entry {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--ownex-bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.ownex-knowledge-feed__entry:hover {
  border-color: var(--border-active);
  box-shadow: var(--shadow-1);
}

.ownex-knowledge-feed__entry--compact {
  padding: var(--space-2);
  gap: var(--space-2);
}

/* Type indicator */
.ownex-knowledge-feed__type {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  background: rgba(var(--entry-color-rgb), 0.1);
  border: 1px solid rgba(var(--entry-color-rgb), 0.2);
}

.ownex-knowledge-feed__type-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.ownex-knowledge-feed__type-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* Type-specific colors */
.ownex-knowledge-feed__entry--pattern .ownex-knowledge-feed__type { --entry-color-rgb: 245, 245, 245; }
.ownex-knowledge-feed__entry--insight .ownex-knowledge-feed__type { --entry-color-rgb: 156, 163, 175; }
.ownex-knowledge-feed__entry--technique .ownex-knowledge-feed__type { --entry-color-rgb: 22, 163, 74; }
.ownex-knowledge-feed__entry--financial .ownex-knowledge-feed__type { --entry-color-rgb: 217, 119, 6; }
.ownex-knowledge-feed__entry--platform .ownex-knowledge-feed__type { --entry-color-rgb: 212, 212, 216; }

/* Content */
.ownex-knowledge-feed__content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.ownex-knowledge-feed__entry-title {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  line-height: var(--leading-snug);
}

.ownex-knowledge-feed__entry--compact .ownex-knowledge-feed__entry-title {
  font-size: var(--text-sm);
}

.ownex-knowledge-feed__entry-description {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
}

.ownex-knowledge-feed__entry--compact .ownex-knowledge-feed__entry-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Evidence */
.ownex-knowledge-feed__evidence {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--ownex-bg-base);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.ownex-knowledge-feed__evidence-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.ownex-knowledge-feed__evidence-text {
  color: var(--text-secondary);
  flex: 1;
}

/* Meta */
.ownex-knowledge-feed__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.ownex-knowledge-feed__confidence {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 120px;
}

.ownex-knowledge-feed__confidence-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-knowledge-feed__confidence-bar {
  flex: 1;
  height: 4px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-knowledge-feed__confidence-fill {
  height: 100%;
  background: var(--entry-color);
  border-radius: var(--radius-full);
  transition: width var(--transition-base) var(--spring-gentle);
}

.ownex-knowledge-feed__confidence-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  min-width: 32px;
  text-align: right;
}

.ownex-knowledge-feed__applied {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.ownex-knowledge-feed__applied-label {
  color: var(--text-muted);
}

.ownex-knowledge-feed__applied-value {
  color: var(--text-secondary);
}

.ownex-knowledge-feed__date {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

/* Tags */
.ownex-knowledge-feed__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

/* Action */
.ownex-knowledge-feed__action {
  margin-top: var(--space-1);
}

/* View All */
.ownex-knowledge-feed__view-all {
  margin-top: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-knowledge-feed__confidence-fill {
    transition: none;
  }
}
</style>