<script setup lang="ts">
/**
 * Work Cycle Card — Per OWNEX_DESIGN_SYSTEM.md §4.2
 * Cada ciclo = una "app" completa con objetivo, throughput, tareas, ingresos, automatización
 */

import { computed } from 'vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'

interface WorkCycle {
  id: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  name: string
  label: string
  icon: string
  status: 'active' | 'waiting' | 'paused' | 'inactive'
  objective: string
  opportunities: number
  potentialValue: number
  throughput: number // opportunities/day
  weeklyRevenue: number
  projectedRevenue: number
  automation: number // 0-100
  pendingTasks: number
  configAction?: 'configure' | 'activate' | 'view' | 'pause'
}

interface Props {
  cycle: WorkCycle
  onEnter: (cycle: WorkCycle) => void
  onConfigure: (cycle: WorkCycle) => void
  compact?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ enter: [cycle: WorkCycle]; configure: [cycle: WorkCycle] }>()

const statusConfig = {
  active: { label: 'Activo', variant: 'success' as const, dot: true },
  waiting: { label: 'Esperando', variant: 'warn' as const, dot: false },
  paused: { label: 'Pausado', variant: 'default' as const, dot: false },
  inactive: { label: 'Inactivo', variant: 'default' as const, dot: false },
}

const cycleColors = {
  security: 'var(--cycle-security)',
  forge: 'var(--cycle-forge)',
  pulse: 'var(--cycle-pulse)',
  vault: 'var(--cycle-vault)',
  atlas: 'var(--cycle-atlas)',
  odyssey: 'var(--cycle-odyssey)',
}

const formatCurrency = (amount: number) => {
  if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`
  if (amount >= 1000) return `$${(amount / 1000).toFixed(1)}k`
  return `$${amount}`
}

const cycleColor = computed(() => cycleColors[props.cycle.id])
</script>

<template>
  <OwnexCard
    :variant="props.cycle.status === 'active' ? 'highlight' : 'cycle'"
    :cycle="props.cycle.id"
    :hoverable="!compact"
    :padded="!compact"
    class="ownex-work-cycle"
    :class="[
      'ownex-work-cycle--' + props.cycle.status,
      { 'ownex-work-cycle--compact': compact }
    ]"
    role="article"
    :aria-label="`Ciclo ${props.cycle.label}: ${statusConfig[props.cycle.status].label}`"
  >
    <div class="ownex-work-cycle__header">
      <div class="ownex-work-cycle__icon" :style="{ background: cycleColor + '20', color: cycleColor }" aria-hidden="true">
        {{ props.cycle.icon }}
      </div>

      <div class="ownex-work-cycle__identity">
        <h3 class="ownex-work-cycle__name">{{ props.cycle.label }}</h3>
        <p class="ownex-work-cycle__objective">{{ props.cycle.objective }}</p>
      </div>

      <OwnexBadge
        :variant="statusConfig[props.cycle.status].variant"
        :dot="statusConfig[props.cycle.status].dot"
        size="sm"
      >
        {{ statusConfig[props.cycle.status].label }}
      </OwnexBadge>
    </div>

    <div v-if="!compact" class="ownex-work-cycle__stats" role="list" aria-label="Estadísticas del ciclo">
      <div class="ownex-work-cycle__stat" role="listitem">
        <span class="ownex-work-cycle__stat-value">{{ props.cycle.opportunities }}</span>
        <span class="ownex-work-cycle__stat-label">Oportunidades</span>
      </div>

      <div class="ownex-work-cycle__stat" role="listitem">
        <span class="ownex-work-cycle__stat-value ownex-work-cycle__stat-value--gold">
          {{ formatCurrency(props.cycle.potentialValue) }}
        </span>
        <span class="ownex-work-cycle__stat-label">Potencial</span>
      </div>

      <div class="ownex-work-cycle__stat" role="listitem">
        <span class="ownex-work-cycle__stat-value">{{ props.cycle.throughput }}/día</span>
        <span class="ownex-work-cycle__stat-label">Throughput</span>
      </div>

      <div class="ownex-work-cycle__stat" role="listitem">
        <span class="ownex-work-cycle__stat-value ownex-work-cycle__stat-value--gold">
          {{ formatCurrency(props.cycle.weeklyRevenue) }}
        </span>
        <span class="ownex-work-cycle__stat-label">Esta semana</span>
      </div>
    </div>

    <div v-if="!compact" class="ownex-work-cycle__progress">
      <div class="ownex-work-cycle__progress-row">
        <span class="ownex-work-cycle__progress-label">Automatización</span>
        <span class="ownex-work-cycle__progress-value">{{ props.cycle.automation }}%</span>
      </div>
      <div class="ownex-work-cycle__progress-bar" role="progressbar" :aria-valuenow="props.cycle.automation" aria-valuemin="0" aria-valuemax="100">
        <div
          class="ownex-work-cycle__progress-fill"
          :style="{ width: props.cycle.automation + '%', background: cycleColor }"
        />
      </div>
    </div>

    <div class="ownex-work-cycle__footer">
      <div class="ownex-work-cycle__tasks" v-if="!compact">
        <span class="ownex-work-cycle__tasks-count">{{ props.cycle.pendingTasks }}</span>
        <span class="ownex-work-cycle__tasks-label">tareas pendientes</span>
      </div>

      <div class="ownex-work-cycle__actions">
        <OwnexButton
          v-if="props.cycle.status === 'active'"
          variant="primary"
          :size="compact ? 'sm' : 'md'"
          :full-width="compact"
          @click="emit('enter', props.cycle)"
        >
          Entrar
        </OwnexButton>

        <OwnexButton
          v-else-if="props.cycle.status === 'waiting'"
          variant="secondary"
          :size="compact ? 'sm' : 'md'"
          :full-width="compact"
          @click="emit('configure', props.cycle)"
        >
          Configurar
        </OwnexButton>

        <OwnexButton
          v-else-if="props.cycle.status === 'paused'"
          variant="ghost"
          :size="compact ? 'sm' : 'md'"
          :full-width="compact"
          @click="emit('enter', props.cycle)"
        >
          Reanudar
        </OwnexButton>

        <OwnexButton
          v-else
          variant="ghost"
          :size="compact ? 'sm' : 'md'"
          :full-width="compact"
          @click="emit('configure', props.cycle)"
        >
          Activar
        </OwnexButton>
      </div>
    </div>
  </OwnexCard>
</template>

<style scoped>
.ownex-work-cycle {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ownex-work-cycle--compact {
  padding: var(--space-3) !important;
}

.ownex-work-cycle__header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.ownex-work-cycle--compact .ownex-work-cycle__header {
  margin-bottom: var(--space-2);
}

.ownex-work-cycle__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  font-size: 1.5rem;
  flex-shrink: 0;
}

.ownex-work-cycle--compact .ownex-work-cycle__icon {
  width: 40px;
  height: 40px;
  font-size: 1.25rem;
}

.ownex-work-cycle__identity {
  flex: 1;
  min-width: 0;
}

.ownex-work-cycle__name {
  margin: 0 0 var(--space-1);
  font-family: var(--font-body);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  line-height: var(--leading-snug);
}

.ownex-work-cycle--compact .ownex-work-cycle__name {
  font-size: var(--text-base);
}

.ownex-work-cycle__objective {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ownex-work-cycle--compact .ownex-work-cycle__objective {
  display: none;
}

/* Stats Grid */
.ownex-work-cycle__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--ownex-bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
}

.ownex-work-cycle__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  text-align: center;
}

.ownex-work-cycle__stat-value {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}

.ownex-work-cycle--compact .ownex-work-cycle__stat-value {
  font-size: var(--text-base);
}

.ownex-work-cycle__stat-value--gold {
  color: var(--ownex-gold);
}

.ownex-work-cycle__stat-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

/* Progress */
.ownex-work-cycle__progress {
  margin-bottom: var(--space-3);
}

.ownex-work-cycle__progress-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.ownex-work-cycle__progress-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-work-cycle__progress-value {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-primary);
}

.ownex-work-cycle__progress-bar {
  height: 6px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.ownex-work-cycle__progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-slow) var(--spring-gentle);
}

/* Footer */
.ownex-work-cycle__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  margin-top: auto;
}

.ownex-work-cycle--compact .ownex-work-cycle__footer {
  padding-top: var(--space-2);
}

.ownex-work-cycle__tasks {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.ownex-work-cycle__tasks-count {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--ownex-blue);
}

.ownex-work-cycle--compact .ownex-work-cycle__tasks-count {
  font-size: var(--text-base);
}

.ownex-work-cycle__tasks-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.ownex-work-cycle__actions {
  flex-shrink: 0;
}

/* Status variants */
.ownex-work-cycle--active {
  border-left-color: var(--status-success);
}

.ownex-work-cycle--waiting {
  border-left-color: var(--status-warn);
}

.ownex-work-cycle--paused {
  border-left-color: var(--text-muted);
}

.ownex-work-cycle--inactive {
  opacity: 0.6;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-work-cycle__progress-fill {
    transition: none;
  }
}
</style>