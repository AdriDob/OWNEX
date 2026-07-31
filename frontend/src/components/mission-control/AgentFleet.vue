<script setup lang="ts">
/**
 * OWNEX Agent Fleet — Visualization of active AI agents with roles
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'

interface Agent {
  id: string
  name: string
  role: string
  model?: string
  status: 'idle' | 'thinking' | 'working' | 'complete' | 'error'
  progress?: number
  currentTask?: string
  lastActivity?: string
  avatar?: string
}

interface Props {
  agents: Agent[]
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  agents: () => [],
  compact: false,
})

const statusConfig = computed(() => ({
  idle: { label: 'Esperando', variant: 'default' as const, icon: 'circle' },
  thinking: { label: 'Analizando', variant: 'primary' as const, icon: 'cpu', pulse: true },
  working: { label: 'Trabajando', variant: 'success' as const, icon: 'activity', pulse: true },
  complete: { label: 'Completado', variant: 'success' as const, icon: 'check-circle' },
  error: { label: 'Error', variant: 'error' as const, icon: 'alert-circle' },
  // Fallback for unknown statuses (e.g., from tests)
  online: { label: 'En línea', variant: 'success' as const, icon: 'wifi', pulse: true },
  local: { label: 'Local', variant: 'default' as const, icon: 'cpu' },
  limited: { label: 'Limitado', variant: 'warning' as const, icon: 'alert-triangle' },
}))

const getRoleColor = (role: string) => {
  const colors: Record<string, string> = {
    'Analista': 'var(--color-cycle-security)',
    'Cazador': 'var(--color-cycle-forge)',
    'Ejecutor': 'var(--color-cycle-pulse)',
    'Validador': 'var(--color-cycle-vault)',
    'Explorador': 'var(--color-cycle-atlas)',
    'Estratega': 'var(--color-cycle-odyssey)',
  }
  return colors[role] || 'var(--ownex-blue)'
}

const formatRelativeTime = (isoString?: string) => {
  if (!isoString) return '—'
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Ahora'
  if (minutes < 60) return `Hace ${minutes}m`
  const hours = Math.floor(minutes / 60)
  return `Hace ${hours}h`
}

const activeCount = computed(() =>
  props.agents.filter(a => a.status === 'working' || a.status === 'thinking').length
)

const roleToCycle = (role: string): 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey' => {
  const mapping: Record<string, any> = {
    'Analista': 'security',
    'Cazador': 'forge',
    'Ejecutor': 'pulse',
    'Validador': 'vault',
    'Explorador': 'atlas',
    'Estratega': 'odyssey',
  }
  return mapping[role] || 'security'
}

const statusDotStyle = (status: string) => {
  const styles: Record<string, any> = {
    idle: { backgroundColor: 'var(--ownex-text-muted)', boxShadow: 'none' },
    thinking: { backgroundColor: 'var(--ownex-blue)', boxShadow: '0 0 8px var(--ownex-blue)' },
    working: { backgroundColor: 'var(--ownex-green)', boxShadow: '0 0 8px var(--ownex-green)' },
    complete: { backgroundColor: 'var(--ownex-green)', boxShadow: '0 0 8px var(--ownex-green)' },
    error: { backgroundColor: 'var(--ownex-red)', boxShadow: '0 0 8px var(--ownex-red)' },
    // Fallback for unknown statuses
    online: { backgroundColor: 'var(--ownex-green)', boxShadow: '0 0 8px var(--ownex-green)' },
    local: { backgroundColor: 'var(--ownex-blue)', boxShadow: '0 0 8px var(--ownex-blue)' },
    limited: { backgroundColor: 'var(--ownex-yellow)', boxShadow: '0 0 8px var(--ownex-yellow)' },
  }
  return styles[status] || styles.idle
}
</script>

<template>
  <div class="ownex-agent-fleet" role="region" aria-label="Flota de agentes activos">
    <div class="ownex-agent-fleet__header">
      <h3 class="ownex-agent-fleet__title">Flota de Agentes</h3>
      <OwnexBadge variant="default" :dot="true" size="sm">
        {{ activeCount }} / {{ props.agents.length }} Activos
      </OwnexBadge>
    </div>

    <div class="ownex-agent-fleet__list">
      <div
        v-for="agent in props.agents"
        :key="agent.id"
        class="ownex-agent-fleet__agent"
        :class="`ownex-agent-fleet__agent--${agent.status}`"
      >
        <!-- Avatar / Status indicator -->
        <div class="ownex-agent-fleet__avatar-wrapper">
          <div
            class="ownex-agent-fleet__avatar"
            :style="{ backgroundColor: getRoleColor(agent.role) }"
          >
            <span v-if="agent.avatar">{{ agent.avatar }}</span>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <span
            class="ownex-agent-fleet__status-dot"
            :class="`ownex-agent-fleet__status-dot--${agent.status}`"
            :style="statusDotStyle(agent.status)"
            aria-hidden="true"
          />
        </div>

        <div class="ownex-agent-fleet__info">
          <div class="ownex-agent-fleet__identity">
            <span class="ownex-agent-fleet__name">{{ agent.name }}</span>
            <OwnexBadge :variant="'cycle'" :cycle="roleToCycle(agent.role)" size="sm">
              {{ agent.role }}
            </OwnexBadge>
          </div>

          <div class="ownex-agent-fleet__status-row">
            <OwnexBadge
              :variant="statusConfig[agent.status].variant"
              :dot="statusConfig[agent.status].pulse"
              size="sm"
            >
              {{ statusConfig[agent.status].label }}
            </OwnexBadge>
            <span v-if="agent.currentTask && !props.compact" class="ownex-agent-fleet__task">
              {{ agent.currentTask }}
            </span>
          </div>

          <!-- Progress bar for working/thinking -->
          <div v-if="(agent.status === 'working' || agent.status === 'thinking') && agent.progress !== undefined"
               class="ownex-agent-fleet__progress"
               role="progressbar"
               :aria-valuenow="agent.progress"
               aria-valuemin="0"
               aria-valuemax="100"
               :aria-label="`Progreso: ${agent.progress}%`"
          >
            <div
              class="ownex-agent-fleet__progress-fill"
              :style="{ width: `${agent.progress}%`, backgroundColor: getRoleColor(agent.role) }"
            />
          </div>

          <!-- Meta info -->
          <div v-if="!props.compact" class="ownex-agent-fleet__meta">
            <span v-if="agent.model" class="ownex-agent-fleet__model">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <rect x="2" y="3" width="20" height="14" rx="2" />
                <path d="M8 21h8M12 17v4" />
              </svg>
              {{ agent.model }}
            </span>
            <span class="ownex-agent-fleet__last-activity">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              {{ formatRelativeTime(agent.lastActivity) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!props.agents.length" class="ownex-agent-fleet__empty">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
        <p>No hay agentes activos</p>
        <span class="ownex-agent-fleet__empty-hint">Los agentes aparecen cuando inician tareas</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ownex-agent-fleet {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.9), rgba(5, 5, 5, 0.7));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.ownex-agent-fleet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.ownex-agent-fleet__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  margin: 0;
}

.ownex-agent-fleet__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-agent-fleet__agent {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--ownex-bg-base);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.ownex-agent-fleet__agent:hover {
  border-color: var(--color-border-light);
}

.ownex-agent-fleet__agent--working {
  border-color: rgba(16, 185, 129, 0.3);
}

.ownex-agent-fleet__agent--thinking {
  border-color: rgba(59, 130, 246, 0.3);
}

.ownex-agent-fleet__agent--error {
  border-color: rgba(239, 68, 68, 0.3);
}

/* Avatar */
.ownex-agent-fleet__avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.ownex-agent-fleet__avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ownex-bg-deep);
  font-weight: var(--font-weight-bold);
  font-size: 14px;
  font-family: var(--font-display);
}

.ownex-agent-fleet__avatar svg {
  width: 18px;
  height: 18px;
}

.ownex-agent-fleet__status-dot {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--ownex-bg-deep);
}

.ownex-agent-fleet__status-dot--thinking,
.ownex-agent-fleet__status-dot--working {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

/* Info */
.ownex-agent-fleet__info {
  flex: 1;
  min-width: 0;
}

.ownex-agent-fleet__identity {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.ownex-agent-fleet__name {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--ownex-white);
}

.ownex-agent-fleet__status-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ownex-agent-fleet__task {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ownex-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

/* Progress */
.ownex-agent-fleet__progress {
  height: 4px;
  background: var(--ownex-bg-deep);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: var(--space-2);
}

.ownex-agent-fleet__progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-base) cubic-bezier(0.16, 1, 0.3, 1);
}

/* Meta */
.ownex-agent-fleet__meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
}

.ownex-agent-fleet__model,
.ownex-agent-fleet__last-activity {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-body);
  font-size: 10px;
  color: var(--ownex-text-muted);
}

.ownex-agent-fleet__model svg,
.ownex-agent-fleet__last-activity svg {
  color: var(--ownex-text-disabled);
}

/* Empty state */
.ownex-agent-fleet__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
  color: var(--ownex-text-muted);
}

.ownex-agent-fleet__empty svg {
  margin-bottom: var(--space-3);
  opacity: 0.3;
}

.ownex-agent-fleet__empty p {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-1);
}

.ownex-agent-fleet__empty-hint {
  font-size: 11px;
  color: var(--ownex-text-disabled);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-agent-fleet__status-dot--thinking,
  .ownex-agent-fleet__status-dot--working {
    animation: none;
  }
}
</style>