<script setup lang="ts">
/**
 * OWNEX Work Cycle Card — Represents a work cycle (Security, Forge, Pulse, Vault, Atlas, Odyssey)
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'
import OwnexButton from '../ui/OwnexButton.vue'
import OwnexKPI from '../ui/OwnexKPI.vue'

interface Props {
  cycle: 'security' | 'forge' | 'pulse' | 'vault' | 'atlas' | 'odyssey'
  title: string
  description: string
  jobsCount: number
  activeJobs: number
  lastRun?: string
  nextRun?: string
  status: 'idle' | 'running' | 'success' | 'warning' | 'error'
  kpis?: Array<{ label: string; value: string | number; trend?: 'up' | 'down' | 'neutral' }>
  actions?: Array<{ label: string; variant: 'primary' | 'secondary' | 'ghost' }>
}

const props = withDefaults(defineProps<Props>(), {
  status: 'idle',
  kpis: () => [],
  actions: () => [],
})

const cycleColors: Record<string, string> = {
  security: 'var(--color-cycle-security)',
  forge: 'var(--color-cycle-forge)',
  pulse: 'var(--color-cycle-pulse)',
  vault: 'var(--color-cycle-vault)',
  atlas: 'var(--color-cycle-atlas)',
  odyssey: 'var(--color-cycle-odyssey)',
}

const cycleIcons: Record<string, string> = {
  security: 'shield',
  forge: 'hammer',
  pulse: 'zap',
  vault: 'vault',
  atlas: 'globe',
  odyssey: 'rocket',
}

const cycleLabels: Record<string, string> = {
  security: 'Security',
  forge: 'Forge',
  pulse: 'Pulse',
  vault: 'Vault',
  atlas: 'Atlas',
  odyssey: 'Odyssey',
}

const statusConfig = computed(() => ({
  idle: { label: 'Inactivo', variant: 'default' as const },
  running: { label: 'Ejecutando', variant: 'primary' as const, dot: true },
  success: { label: 'Completado', variant: 'success' as const },
  warning: { label: 'Advertencia', variant: 'warning' as const },
  error: { label: 'Error', variant: 'error' as const },
})[props.status])

const cycleColor = computed(() => cycleColors[props.cycle])
const cycleIcon = computed(() => cycleIcons[props.cycle])
const cycleLabel = computed(() => cycleLabels[props.cycle])

const statusDotStyle = computed(() => ({
  backgroundColor: props.status === 'running' ? 'var(--ownex-blue)' :
    props.status === 'success' ? 'var(--ownex-green)' :
    props.status === 'warning' ? 'var(--ownex-yellow)' :
    props.status === 'error' ? 'var(--ownex-red)' :
    'var(--ownex-text-muted)',
  boxShadow: props.status === 'running' ? '0 0 8px var(--ownex-blue)' :
    props.status === 'success' ? '0 0 8px var(--ownex-green)' :
    props.status === 'warning' ? '0 0 8px var(--ownex-yellow)' :
    props.status === 'error' ? '0 0 8px var(--ownex-red)' :
    'none',
}))
</script>

<template>
  <div
    class="ownex-cycle-card"
    :class="`ownex-cycle-card--${props.cycle}`"
    :style="{ '--cycle-color': cycleColor }"
    role="region"
    :aria-label="`Ciclo ${cycleLabel}: ${statusConfig.label}`"
  >
    <!-- Header -->
    <div class="ownex-cycle-card__header">
      <div class="ownex-cycle-card__identity">
        <span class="ownex-cycle-card__icon" :style="{ color: cycleColor }" aria-hidden="true">
          <component :is="`icon-${cycleIcon}`" class="ownex-cycle-card__icon-svg" />
        </span>
        <div>
          <h3 class="ownex-cycle-card__title">{{ cycleLabel }}</h3>
          <p class="ownex-cycle-card__subtitle">{{ title }}</p>
        </div>
      </div>

      <OwnexBadge
        :variant="statusConfig.variant"
        :dot="statusConfig.dot"
        class="ownex-cycle-card__status"
      >
        {{ statusConfig.label }}
      </OwnexBadge>
    </div>

    <!-- Description -->
    <p class="ownex-cycle-card__description">{{ description }}</p>

    <!-- Stats row -->
    <div class="ownex-cycle-card__stats">
      <div class="ownex-cycle-card__stat">
        <span class="ownex-cycle-card__stat-value">{{ props.activeJobs }} / {{ props.jobsCount }}</span>
        <span class="ownex-cycle-card__stat-label">Jobs Activos</span>
      </div>
      <div v-if="lastRun" class="ownex-cycle-card__stat">
        <span class="ownex-cycle-card__stat-value">{{ formatTime(lastRun) }}</span>
        <span class="ownex-cycle-card__stat-label">Última Ejecución</span>
      </div>
      <div v-if="nextRun" class="ownex-cycle-card__stat">
        <span class="ownex-cycle-card__stat-value">{{ formatTime(nextRun) }}</span>
        <span class="ownex-cycle-card__stat-label">Próxima Ejecución</span>
      </div>
    </div>

    <!-- Progress bar for running status -->
    <div v-if="props.status === 'running'" class="ownex-cycle-card__progress" role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100" aria-label="Progreso del ciclo">
      <div class="ownex-cycle-card__progress-fill" :style="{ backgroundColor: cycleColor }" />
    </div>

    <!-- KPIs -->
    <div v-if="props.kpis.length" class="ownex-cycle-card__kpis">
      <OwnexKPI
        v-for="kpi in props.kpis"
        :key="kpi.label"
        :label="kpi.label"
        :value="kpi.value"
        :trend="kpi.trend"
        variant="cycle"
        :cycle="props.cycle"
        size="sm"
      />
    </div>

    <!-- Actions -->
    <div v-if="props.actions.length" class="ownex-cycle-card__actions">
      <OwnexButton
        v-for="action in props.actions"
        :key="action.label"
        :variant="action.variant"
        size="sm"
      >
        {{ action.label }}
      </OwnexButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<style scoped>
.ownex-cycle-card {
  background: linear-gradient(135deg, rgba(10, 10, 15, 0.9), rgba(5, 5, 5, 0.7));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.ownex-cycle-card:hover {
  border-color: var(--color-border-light);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

/* Cycle accent border */
.ownex-cycle-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--cycle-color);
  opacity: 0.6;
}

/* Header */
.ownex-cycle-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.ownex-cycle-card__identity {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}

.ownex-cycle-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(var(--cycle-color-rgb), 0.1);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.ownex-cycle-card__icon-svg {
  width: 20px;
  height: 20px;
}

.ownex-cycle-card__title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--ownex-white);
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ownex-cycle-card__subtitle {
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ownex-text-muted);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-cycle-card__status {
  flex-shrink: 0;
  font-size: 10px;
}

/* Description */
.ownex-cycle-card__description {
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--ownex-text-secondary);
  margin: 0 0 var(--space-4);
  line-height: 1.5;
}

/* Stats */
.ownex-cycle-card__stats {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-3);
}

.ownex-cycle-card__stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ownex-cycle-card__stat-value {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--ownex-white);
}

.ownex-cycle-card__stat-label {
  font-family: var(--font-body);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-disabled);
}

/* Progress */
.ownex-cycle-card__progress {
  height: 4px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-3);
}

.ownex-cycle-card__progress-fill {
  height: 100%;
  width: 65%;
  border-radius: var(--radius-full);
  animation: progressPulse 2s ease-in-out infinite;
}

@keyframes progressPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* KPIs */
.ownex-cycle-card__kpis {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

/* Actions */
.ownex-cycle-card__actions {
  display: flex;
  gap: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
}

.ownex-cycle-card__actions .ownex-btn {
  flex: 1;
}

/* Cycle RGB values */
.ownex-cycle-card--security { --cycle-color-rgb: 59, 130, 246; }
.ownex-cycle-card--forge    { --cycle-color-rgb: 168, 85, 247; }
.ownex-cycle-card--pulse    { --cycle-color-rgb: 16, 185, 129; }
.ownex-cycle-card--vault    { --cycle-color-rgb: 245, 158, 11; }
.ownex-cycle-card--atlas    { --cycle-color-rgb: 226, 232, 240; }
.ownex-cycle-card--odyssey  { --cycle-color-rgb: 249, 115, 22; }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-cycle-card__progress-fill {
    animation: none;
  }
}
</style>