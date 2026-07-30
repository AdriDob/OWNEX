<script setup lang="ts">
/**
 * Global Status Bar — Per OWNEX_DESIGN_SYSTEM.md §3.1
 * Siempre visible: Health + Throughput + Revenue
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'

interface Props {
  healthScore?: number // 0-100
  throughput?: number // opportunities/hour
  revenueToday?: number
  revenueWeek?: number
  revenueProjected?: number
  activeTargets?: number
  activeFindings?: number
  confirmedFindings?: number
  pendingReports?: number
  servicesStatus?: {
    scheduler: 'running' | 'stopped' | 'error'
    eventBus: 'running' | 'stopped' | 'error'
    agentBus: 'running' | 'stopped' | 'error'
    recoveryEngine: 'running' | 'stopped' | 'error'
  }
}

const props = withDefaults(defineProps<Props>(), {
  healthScore: 100,
  throughput: 0,
  revenueToday: 0,
  revenueWeek: 0,
  revenueProjected: 0,
  activeTargets: 0,
  activeFindings: 0,
  confirmedFindings: 0,
  pendingReports: 0,
  servicesStatus: {
    scheduler: 'running',
    eventBus: 'running',
    agentBus: 'running',
    recoveryEngine: 'running',
  },
})

const formatCurrency = (amount: number) => {
  if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`
  if (amount >= 1000) return `$${(amount / 1000).toFixed(1)}k`
  return `$${amount}`
}

const healthVariant = computed(() => {
  const score = props.healthScore
  if (score >= 80) return 'success'
  if (score >= 50) return 'warn'
  return 'error'
})

const healthLabel = computed(() => {
  const score = props.healthScore
  if (score >= 80) return 'Saludable'
  if (score >= 50) return 'Atención'
  return 'Crítico'
})

const serviceStatusConfig = {
  running: { label: 'Activo', variant: 'success' as const },
  stopped: { label: 'Detenido', variant: 'warn' as const },
  error: { label: 'Error', variant: 'error' as const },
}
</script>

<template>
  <header class="ownex-status-bar" role="status" aria-live="polite" aria-label="Barra de estado global">
    <!-- Health Indicator -->
    <div class="ownex-status-bar__section ownex-status-bar__health">
      <div class="ownex-status-bar__health-main">
        <span class="ownex-status-bar__health-label">Health</span>
        <OwnexBadge
          :variant="healthVariant"
          :dot="true"
          size="md"
        >
          {{ healthLabel }} {{ healthScore }}%
        </OwnexBadge>
      </div>

      <div class="ownex-status-bar__health-bar" role="progressbar" :aria-valuenow="healthScore" aria-valuemin="0" aria-valuemax="100">
        <div class="ownex-status-bar__health-fill" :style="{ width: healthScore + '%' }" />
      </div>
    </div>

    <div class="ownex-status-bar__divider" aria-hidden="true" />

    <!-- Throughput -->
    <div class="ownex-status-bar__section ownex-status-bar__throughput">
      <span class="ownex-status-bar__metric-label">Throughput</span>
      <span class="ownex-status-bar__metric-value">{{ throughput }}/hr</span>
      <span class="ownex-status-bar__metric-unit">oportunidades</span>
    </div>

    <div class="ownex-status-bar__divider" aria-hidden="true" />

    <!-- Revenue -->
    <div class="ownex-status-bar__section ownex-status-bar__revenue">
      <span class="ownex-status-bar__metric-label">Revenue</span>
      <span class="ownex-status-bar__metric-value ownex-status-bar__metric-value--gold">
        {{ formatCurrency(revenueToday) }} hoy
      </span>
      <span class="ownex-status-bar__metric-detail">
        {{ formatCurrency(revenueWeek) }} sem • {{ formatCurrency(revenueProjected) }} proj.
      </span>
    </div>

    <div class="ownex-status-bar__divider" aria-hidden="true" />

    <!-- Quick Stats -->
    <div class="ownex-status-bar__section ownex-status-bar__stats">
      <div class="ownex-status-bar__stat" title="Targets activos">
        <span class="ownex-status-bar__stat-value">{{ activeTargets }}</span>
        <span class="ownex-status-bar__stat-label">Targets</span>
      </div>
      <div class="ownex-status-bar__stat" title="Findings activos">
        <span class="ownex-status-bar__stat-value">{{ activeFindings }}</span>
        <span class="ownex-status-bar__stat-label">Findings</span>
      </div>
      <div class="ownex-status-bar__stat" title="Findings confirmados">
        <span class="ownex-status-bar__stat-value">{{ confirmedFindings }}</span>
        <span class="ownex-status-bar__stat-label">Confirmados</span>
      </div>
      <div class="ownex-status-bar__stat" title="Reportes pendientes">
        <span class="ownex-status-bar__stat-value">{{ pendingReports }}</span>
        <span class="ownex-status-bar__stat-label">Pendientes</span>
      </div>
    </div>

    <div class="ownex-status-bar__divider" aria-hidden="true" />

    <!-- Services Status -->
    <div class="ownex-status-bar__section ownex-status-bar__services" aria-label="Estado de servicios">
      <div
        v-for="(status, service) in servicesStatus"
        :key="service"
        class="ownex-status-bar__service"
        :title="formatServiceName(service)"
      >
        <OwnexBadge
          :variant="serviceStatusConfig[status].variant"
          :dot="true"
          size="sm"
        >
          {{ serviceStatusConfig[status].label }}
        </OwnexBadge>
      </div>
    </div>
  </header>
</template>

<style scoped>
.ownex-status-bar {
  display: flex;
  align-items: center;
  height: var(--status-bar-height);
  padding: 0 var(--space-4);
  background: var(--ownex-bg-deep);
  border-bottom: 1px solid var(--border-subtle);
  gap: var(--space-4);
  flex-wrap: nowrap;
  overflow-x: auto;
  position: sticky;
  top: 0;
  z-index: var(--z-status-bar);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.ownex-status-bar__section {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.ownex-status-bar__divider {
  width: 1px;
  height: 16px;
  background: var(--border-subtle);
  flex-shrink: 0;
}

/* Health */
.ownex-status-bar__health {
  min-width: 180px;
}

.ownex-status-bar__health-main {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ownex-status-bar__health-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-status-bar__health-bar {
  height: 3px;
  background: var(--ownex-bg-base);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: 2px;
}

.ownex-status-bar__health-fill {
  height: 100%;
  background: var(--status-success);
  border-radius: var(--radius-full);
  transition: width var(--transition-base) var(--spring-gentle), background var(--transition-fast);
}

/* Throughput & Revenue */
.ownex-status-bar__metric-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ownex-status-bar__metric-value {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.ownex-status-bar__metric-value--gold {
  color: var(--ownex-gold);
}

.ownex-status-bar__metric-unit,
.ownex-status-bar__metric-detail {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Stats */
.ownex-status-bar__stats {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.ownex-status-bar__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.ownex-status-bar__stat-value {
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}

.ownex-status-bar__stat-label {
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

/* Services */
.ownex-status-bar__services {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ownex-status-bar__service {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.ownex-status-bar__service .ownex-badge {
  font-size: var(--text-xs);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-status-bar__health-fill {
    transition: none;
  }
}

/* Mobile responsive */
@media (max-width: 1024px) {
  .ownex-status-bar {
    padding: 0 var(--space-3);
    gap: var(--space-3);
  }

  .ownex-status-bar__health {
    min-width: 140px;
  }

  .ownex-status-bar__stats {
    gap: var(--space-2);
  }

  .ownex-status-bar__metric-value {
    font-size: var(--text-base);
  }
}

@media (max-width: 768px) {
  .ownex-status-bar {
    height: auto;
    padding: var(--space-2) var(--space-3);
    flex-wrap: wrap;
  }

  .ownex-status-bar__health {
    width: 100%;
    order: 1;
  }

  .ownex-status-bar__throughput,
  .ownex-status-bar__revenue {
    order: 2;
  }

  .ownex-status-bar__stats {
    width: 100%;
    order: 3;
    justify-content: space-around;
  }

  .ownex-status-bar__services {
    width: 100%;
    order: 4;
    justify-content: center;
  }

  .ownex-status-bar__divider:nth-child(2),
  .ownex-status-bar__divider:nth-child(4),
  .ownex-status-bar__divider:nth-child(6) {
    display: none;
  }
}
</style>