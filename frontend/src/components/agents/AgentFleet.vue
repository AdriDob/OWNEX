<script setup lang="ts">
/**
 * Agent Fleet Card — Per OWNEX_DESIGN_SYSTEM.md §4.3
 * "El usuario NUNCA ve: Qwen, Claude, DeepSeek, GPT, modelos, proveedores, tokens, temperatura, context windows.
 * El usuario SÍ ve: Agentes trabajando."
 */

import { computed, onMounted, ref } from 'vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'

interface Agent {
  id: string
  name: string
  icon: string
  role: string
  status: 'active' | 'idle' | 'learning' | 'queued' | 'error' | 'paused'
  description: string
  detail?: string
  progress?: number
  cycle?: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  lastActivity?: string
}

interface Props {
  agents: Agent[]
  compact?: boolean
  showHeader?: boolean
  onAssignTask?: (agentId: string) => void
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
  showHeader: true,
})

const emit = defineEmits<{ 'assign-task': [agentId: string] }>()

const statusConfig = {
  active: { label: 'Activo', variant: 'success' as const, dot: true },
  idle: { label: 'Disponible', variant: 'default' as const, dot: true },
  learning: { label: 'Aprendiendo', variant: 'cycle' as const, cycle: 'pulse', dot: true },
  queued: { label: 'En cola', variant: 'warn' as const, dot: false },
  error: { label: 'Error', variant: 'error' as const, dot: false },
  paused: { label: 'Pausado', variant: 'default' as const, dot: false },
} as const

const agentIcons = {
  researcher: '🔬',
  executor: '⚡',
  memory: '🧠',
  security: '🛡️',
  analyst: '📊',
  vault: '💰',
  scanner: '🔍',
  reporter: '📝',
}

const getAgentIcon = (name: string, customIcon?: string) => {
  if (customIcon) return customIcon
  const lower = name.toLowerCase()
  for (const [key, icon] of Object.entries(agentIcons)) {
    if (lower.includes(key)) return icon
  }
  return '🤖'
}
</script>

<template>
  <OwnexCard variant="elevated" :padded="!compact">
    <template var(--ownex-accent)ult>
      <div class="ownex-agent-fleet">
        <!-- Header -->
        <div v-if="showHeader" class="ownex-agent-fleet__header">
          <h3 class="ownex-agent-fleet__title">
            <span class="ownex-agent-fleet__icon" aria-hidden="true">🤖</span>
            Agent Fleet
          </h3>
          <OwnexButton
            v-if="!compact"
            variant="ghost"
            size="sm"
            icon="plus"
            @click="$emit('assign-task')"
          >
            Asignar Tarea
          </OwnexButton>
        </div>

        <!-- Agents List -->
        <div class="ownex-agent-fleet__list" role="list" aria-label="Agentes activos">
          <div
            v-for="agent in agents"
            :key="agent.id"
            class="ownex-agent-fleet__item"
            :class="[
              'ownex-agent-fleet__item--' + agent.status,
              { 'ownex-agent-fleet__item--compact': compact }
            ]"
            role="listitem"
          >
            <!-- Status Indicator -->
            <div class="ownex-agent-fleet__status" :data-status="agent.status">
              <span
                class="ownex-agent-fleet__dot"
                :class="statusConfig[agent.status].dot ? 'ownex-agent-fleet__dot--pulse' : ''"
                aria-hidden="true"
              />
            </div>

            <!-- Agent Info -->
            <div class="ownex-agent-fleet__info">
              <div class="ownex-agent-fleet__main">
                <span class="ownex-agent-fleet__avatar" aria-hidden="true">
                  {{ getAgentIcon(agent.name, agent.icon) }}
                </span>
                <div class="ownex-agent-fleet__details">
                  <div class="ownex-agent-fleet__name-row">
                    <span class="ownex-agent-fleet__name">{{ agent.name }}</span>
                    <OwnexBadge
                      :variant="statusConfig[agent.status].variant"
                      :cycle="statusConfig[agent.status].cycle"
                      :dot="statusConfig[agent.status].dot"
                      size="sm"
                    >
                      {{ statusConfig[agent.status].label }}
                    </OwnexBadge>
                  </div>
                  <p class="ownex-agent-fleet__description">{{ agent.description }}</p>
                  <p v-if="agent.detail" class="ownex-agent-fleet__detail">{{ agent.detail }}</p>
                </div>
              </div>

              <!-- Progress Bar -->
              <div v-if="agent.progress !== undefined" class="ownex-agent-fleet__progress">
                <div
                  class="ownex-agent-fleet__progress-bar"
                  role="progressbar"
                  :aria-valuenow="agent.progress"
                  aria-valuemin="0"
                  aria-valuemax="100"
                >
                  <div
                    class="ownex-agent-fleet__progress-fill"
                    :style="{ width: agent.progress + '%' }"
                  />
                </div>
                <span class="ownex-agent-fleet__progress-text">{{ agent.progress }}%</span>
              </div>

              <!-- Actions -->
              <div v-if="!compact" class="ownex-agent-fleet__actions">
                <OwnexButton
                  v-if="agent.status === 'idle' || agent.status === 'queued'"
                  variant="ghost"
                  size="sm"
                  @click="$emit('assign-task', agent.id)"
                >
                  Asignar
                </OwnexButton>
                <OwnexButton
                  v-else-if="agent.status === 'active'"
                  variant="secondary"
                  size="sm"
                  disabled
                >
                  Trabajando
                </OwnexButton>
                <span v-else class="ownex-agent-fleet__last-activity">
                  {{ agent.lastActivity }}
                </span>
              </div>
            </div>

            <!-- Cycle indicator -->
            <div v-if="agent.cycle" class="ownex-agent-fleet__cycle" :data-cycle="agent.cycle" aria-hidden="true" />
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="agents.length === 0" class="ownex-agent-fleet__empty">
          <span class="ownex-agent-fleet__empty-icon" aria-hidden="true">🤖</span>
          <p class="ownex-agent-fleet__empty-text">Sin agentes configurados</p>
          <OwnexButton variant="primary" size="sm" @click="$emit('assign-task')">
            Añadir Agente
          </OwnexButton>
        </div>

        <!-- Keyboard Hint -->
        <div v-if="!compact" class="ownex-agent-fleet__hint">
          <kbd>Ctrl+Space</kbd> para asignar tarea manual
        </div>
      </div>
    </template>
  </OwnexCard>
</template>

<style scoped>
.ownex-agent-fleet {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-agent-fleet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.ownex-agent-fleet__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.ownex-agent-fleet__icon {
  font-size: var(--text-xl);
}

.ownex-agent-fleet__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.ownex-agent-fleet__item {
  display: grid;
  grid-template-columns: 12px 1fr auto;
  gap: var(--space-3);
  align-items: start;
  padding: var(--space-3);
  background: var(--ownex-bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.ownex-agent-fleet__item:hover {
  border-color: var(--border-active);
  box-shadow: var(--shadow-1);
}

.ownex-agent-fleet__item--compact {
  grid-template-columns: 12px 1fr;
  padding: var(--space-2);
}

.ownex-agent-fleet__status {
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.ownex-agent-fleet__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success);
  flex-shrink: 0;
}

.ownex-agent-fleet__dot--pulse {
  animation: ownex-agent-pulse 2s ease-in-out infinite;
}

@keyframes ownex-agent-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.9); }
}

.ownex-agent-fleet__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.ownex-agent-fleet__main {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.ownex-agent-fleet__avatar {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.ownex-agent-fleet__details {
  flex: 1;
  min-width: 0;
}

.ownex-agent-fleet__name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.ownex-agent-fleet__name {
  font-family: var(--font-body);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.ownex-agent-fleet__description {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ownex-agent-fleet__detail {
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ownex-agent-fleet__progress {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
}

.ownex-agent-fleet__progress-bar {
  flex: 1;
  height: 4px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-agent-fleet__progress-fill {
  height: 100%;
  background: var(--ownex-blue);
  border-radius: var(--radius-full);
  transition: width var(--transition-base) var(--spring-gentle);
}

.ownex-agent-fleet__progress-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-width: 36px;
  text-align: right;
}

.ownex-agent-fleet__actions {
  margin-top: var(--space-1);
}

.ownex-agent-fleet__last-activity {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ownex-agent-fleet__cycle {
  width: 4px;
  border-radius: var(--radius-full);
  background: var(--cycle-color);
  opacity: 0.5;
}

.ownex-agent-fleet__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
  gap: var(--space-3);
  color: var(--text-muted);
}

.ownex-agent-fleet__empty-icon {
  font-size: 3rem;
  opacity: 0.3;
}

.ownex-agent-fleet__empty-text {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-base);
}

.ownex-agent-fleet__hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: var(--space-3);
  margin-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ownex-agent-fleet__hint kbd {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  background: var(--ownex-bg-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: inherit;
  color: var(--text-secondary);
  margin-right: var(--space-2);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-agent-fleet__dot--pulse {
    animation: none;
  }

  .ownex-agent-fleet__progress-fill {
    transition: none;
  }
}
</style>