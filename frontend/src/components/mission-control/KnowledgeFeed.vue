<script setup lang="ts">
/**
 * OWNEX Knowledge Feed — Learning, insights, and system notifications
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed, defineComponent, h } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'
import OwnexButton from '../ui/OwnexButton.vue'

interface FeedItem {
  id: string
  type: 'insight' | 'learning' | 'pattern' | 'alert' | 'achievement' | 'system'
  title: string
  description: string
  source?: string
  confidence?: number
  tags: string[]
  timestamp: string
  actionable?: boolean
  action?: { label: string; variant: 'primary' | 'secondary' | 'ghost' }
}

interface Props {
  items: FeedItem[]
  maxItems?: number
  groupByDate?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  items: () => [],
  maxItems: 20,
  groupByDate: true,
})

const typeConfig = computed(() => ({
  insight: { label: 'INSIGHT', icon: 'lightbulb', color: 'var(--ownex-blue)', bg: 'rgba(255, 255, 255, 0.1)' },
  learning: { label: 'APRENDIZAJE', icon: 'brain', color: 'var(--color-cycle-forge)', bg: 'rgba(156, 163, 175, 0.1)' },
  pattern: { label: 'PATRÓN', icon: 'git-branch', color: 'var(--color-cycle-pulse)', bg: 'rgba(22, 163, 74, 0.1)' },
  alert: { label: 'ALERTA', icon: 'alert-triangle', color: 'var(--ownex-red)', bg: 'rgba(232, 33, 39, 0.1)' },
  achievement: { label: 'LOGRO', icon: 'trophy', color: 'var(--ownex-gold)', bg: 'rgba(217, 119, 6, 0.1)' },
  system: { label: 'SISTEMA', icon: 'cpu', color: 'var(--ownex-text-muted)', bg: 'rgba(148, 163, 184, 0.1)' },
}))

const formatRelativeTime = (isoString: string) => {
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Ahora'
  if (minutes < 60) return `Hace ${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Hace ${hours}h`
  const days = Math.floor(hours / 24)
  return `Hace ${days}d`
}

const getTypeIcon = (type: string) => {
  const icons: Record<string, string> = {
    insight: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
    learning: 'M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V5a3 3 0 0 0-3-3H12zM12 22H2a1 1 0 0 1-1-1v-1a2 2 0 0 1 2-2h4a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1h-2v-1a1 1 0 0 0-1 1h-2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-1a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1h-2v1a2 2 0 0 1-2 2z',
    pattern: 'M6 3v18M18 3v18M12 3v18M3 12h18M3 6h18M3 18h18',
    alert: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
    achievement: 'M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M18 9a2 2 0 0 0 0-12H6a2 2 0 0 0 0 12',
    system: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  }
  return icons[type] || icons.system
}

const getConfidenceColor = (score: number) => {
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}

const displayedItems = computed(() => props.items.slice(0, props.maxItems))

const groupedItems = computed(() => {
  const groups: Record<string, FeedItem[]> = {}
  for (const item of displayedItems.value) {
    const date = new Date(item.timestamp).toDateString()
    if (!groups[date]) groups[date] = []
    groups[date].push(item)
  }
  return groups
})

const formatDateLabel = (dateString: string) => {
  const date = new Date(dateString)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return 'HOY'
  if (date.toDateString() === yesterday.toDateString()) return 'AYER'
  return date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' }).toUpperCase()
}

// Inner item component for cleaner structure
const KnowledgeFeedItem = defineComponent({
  name: 'KnowledgeFeedItem',
  props: {
    item: {
      type: Object as () => FeedItem,
      required: true,
    },
  },
  setup(props) {
    const config = typeConfig.value[props.item.type] || typeConfig.value.system

    return () => h('div', { class: 'ownex-knowledge-feed__item-inner' }, [
      // Type indicator
      h('div', { class: 'ownex-knowledge-feed__type-indicator', style: { backgroundColor: config.color } }),

      // Content
      h('div', { class: 'ownex-knowledge-feed__item-content' }, [
        // Header
        h('div', { class: 'ownex-knowledge-feed__item-header' }, [
          h('div', { class: 'ownex-knowledge-feed__item-type' }, [
            h('svg', {
              class: 'ownex-knowledge-feed__type-icon',
              width: '12',
              height: '12',
              viewBox: '0 0 24 24',
              fill: 'none',
              stroke: 'currentColor',
              strokeWidth: '2',
              'aria-hidden': 'true',
              style: { color: config.color },
            }, [h('path', { d: getTypeIcon(props.item.type) })]),
            h('span', { class: 'ownex-knowledge-feed__type-label' }, config.label),
          ]),
          h('span', { class: 'ownex-knowledge-feed__item-time' }, formatRelativeTime(props.item.timestamp)),
        ]),

        // Title & Description
        h('h4', { class: 'ownex-knowledge-feed__item-title' }, props.item.title),
        h('p', { class: 'ownex-knowledge-feed__item-description' }, props.item.description),

        // Tags
        h('div', { class: 'ownex-knowledge-feed__item-tags' }, [
          ...props.item.tags.slice(0, 4).map(tag =>
            h('span', { class: 'ownex-knowledge-feed__tag' }, tag)
          ),
        ]),

        // Confidence
        h('div', { class: 'ownex-knowledge-feed__item-confidence', vIf: props.item.confidence !== undefined }, [
          h('span', { class: 'ownex-knowledge-feed__confidence-label' }, 'Confianza'),
          h('div', { class: 'ownex-knowledge-feed__confidence-bar' }, [
            h('div', {
              class: 'ownex-knowledge-feed__confidence-fill',
              style: { width: `${props.item.confidence}%`, backgroundColor: getConfidenceColor(props.item.confidence) },
            }),
          ]),
          h('span', { class: 'ownex-knowledge-feed__confidence-value', style: { color: getConfidenceColor(props.item.confidence) } }, `${props.item.confidence}%`),
        ]),

        // Source
        h('div', { class: 'ownex-knowledge-feed__item-source', vIf: props.item.source }, [
          h('svg', { width: '10', height: '10', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: '2', 'aria-hidden': 'true' }, [
            h('path', { d: 'M12 2L2 7l10 5 10-5-10-5z' }),
            h('path', { d: 'M2 17l10 5 10-5' }),
            h('path', { d: 'M2 12l10 5 10-5' }),
          ]),
          h('span', props.item.source),
        ]),

        // Action
        h('div', { class: 'ownex-knowledge-feed__item-action', vIf: props.item.actionable && props.item.action }, [
          h(OwnexButton, {
            variant: props.item.action.variant,
            size: 'sm',
            onClick: () => { /* action handler */ },
          }, { default: () => props.item.action!.label }),
        ]),
      ]),
    ])
  },
})
</script>

<template>
  <div class="ownex-knowledge-feed" role="region" aria-label="Feed de conocimiento">
    <div class="ownex-knowledge-feed__header">
      <h3 class="ownex-knowledge-feed__title">Feed de Conocimiento</h3>
      <OwnexBadge variant="default" size="sm">
        {{ displayedItems.length }} items
      </OwnexBadge>
    </div>

    <div class="ownex-knowledge-feed__list">
      <template v-if="props.groupByDate">
        <div v-for="(group, dateKey) in groupedItems" :key="dateKey" class="ownex-knowledge-feed__date-group">
          <div class="ownex-knowledge-feed__date-label">{{ formatDateLabel(dateKey) }}</div>
          <div
            v-for="item in group"
            :key="item.id"
            class="ownex-knowledge-feed__item"
            :class="`ownex-knowledge-feed__item--${item.type}`"
          >
            <KnowledgeFeedItem :item="item" />
          </div>
        </div>
      </template>
      <template v-else>
        <KnowledgeFeedItem
          v-for="item in displayedItems"
          :key="item.id"
          :item="item"
        />
      </template>

      <!-- Empty state -->
      <div v-if="!props.items.length" class="ownex-knowledge-feed__empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V5a3 3 0 0 0-3-3H12z" />
          <path d="M2 22h20M2 17h20" />
        </svg>
        <p>El feed está vacío</p>
        <span>Los insights aparecen tras ejecuciones de ciclos</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ownex-knowledge-feed {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.9), rgba(5, 5, 5, 0.7));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  max-height: 500px;
  overflow-y: auto;
}

.ownex-knowledge-feed__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.9), rgba(5, 5, 5, 0.7));
  backdrop-filter: blur(16px);
  z-index: 1;
}

.ownex-knowledge-feed__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  margin: 0;
}

.ownex-knowledge-feed__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* Date groups */
.ownex-knowledge-feed__date-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ownex-knowledge-feed__date-label {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ownex-text-disabled);
  padding: var(--space-1) 0;
}

/* Items */
.ownex-knowledge-feed__item {
  position: relative;
  padding: var(--space-3);
  background: var(--ownex-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  animation: slideIn 0.3s ease-out both;
}

.ownex-knowledge-feed__item:hover {
  border-color: var(--color-border-light);
}

.ownex-knowledge-feed__item--insight   { border-left: 3px solid var(--ownex-blue); }
.ownex-knowledge-feed__item--learning  { border-left: 3px solid var(--color-cycle-forge); }
.ownex-knowledge-feed__item--pattern   { border-left: 3px solid var(--color-cycle-pulse); }
.ownex-knowledge-feed__item--alert     { border-left: 3px solid var(--ownex-red); }
.ownex-knowledge-feed__item--achievement { border-left: 3px solid var(--ownex-gold); }
.ownex-knowledge-feed__item--system    { border-left: 3px solid var(--ownex-text-muted); }

/* Type indicator bar */
.ownex-knowledge-feed__type-indicator {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}

.ownex-knowledge-feed__item-inner {
  display: flex;
  gap: var(--space-3);
  padding-left: var(--space-3);
}

/* Item content */
.ownex-knowledge-feed__item-content {
  flex: 1;
  min-width: 0;
}

.ownex-knowledge-feed__item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.ownex-knowledge-feed__item-type {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ownex-knowledge-feed__type-icon {
  flex-shrink: 0;
}

.ownex-knowledge-feed__type-label {
  font-family: var(--font-body);
  font-size: 9px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-knowledge-feed__item-time {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ownex-text-muted);
}

.ownex-knowledge-feed__item-title {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--ownex-white);
  margin: 0 0 var(--space-1);
  line-height: 1.4;
}

.ownex-knowledge-feed__item-description {
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-2);
  line-height: 1.5;
}

/* Tags */
.ownex-knowledge-feed__item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.ownex-knowledge-feed__tag {
  font-family: var(--font-mono);
  font-size: 8px;
  color: var(--ownex-text-muted);
  background: var(--ownex-bg-deep);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

/* Confidence */
.ownex-knowledge-feed__item-confidence {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.ownex-knowledge-feed__confidence-label {
  font-family: var(--font-body);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-disabled);
}

.ownex-knowledge-feed__confidence-bar {
  flex: 1;
  max-width: 120px;
  height: 3px;
  background: var(--ownex-bg-deep);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-knowledge-feed__confidence-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-base) cubic-bezier(0.16, 1, 0.3, 1);
}

.ownex-knowledge-feed__confidence-value {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  min-width: 28px;
}

/* Source */
.ownex-knowledge-feed__item-source {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-size: 10px;
  color: var(--ownex-text-disabled);
}

.ownex-knowledge-feed__item-source svg {
  color: var(--ownex-text-disabled);
}

/* Action */
.ownex-knowledge-feed__item-action {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

/* Empty state */
.ownex-knowledge-feed__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  text-align: center;
  color: var(--ownex-text-muted);
}

.ownex-knowledge-feed__empty svg {
  margin-bottom: var(--space-3);
  opacity: 0.3;
}

.ownex-knowledge-feed__empty p {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-1);
}

.ownex-knowledge-feed__empty span {
  font-size: 11px;
  color: var(--ownex-text-disabled);
}

/* Animations */
@keyframes slideIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-knowledge-feed__item {
    animation: none;
  }
  .ownex-knowledge-feed__confidence-fill {
    transition: none;
  }
}
</style>