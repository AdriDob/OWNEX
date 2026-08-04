<script setup lang="ts">
/**
 * OWNEX Status Bar — Top persistent system status (40px)
 * Based on OWNEX_DESIGN_SYSTEM.md §3.2
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import OwnexBadge from '../ui/OwnexBadge.vue'

interface Props {
  systemStatus?: 'healthy' | 'degraded' | 'critical' | 'offline'
  activeCycles?: string[]
  pendingApprovals?: number
  runningWorkflows?: number
  version?: string
}

const props = withDefaults(defineProps<Props>(), {
  systemStatus: 'healthy',
  activeCycles: () => [],
  pendingApprovals: 0,
  runningWorkflows: 0,
  version: '5.0.0',
})

const time = ref(new Date())
const isConnected = ref(true)

let intervalId: ReturnType<typeof setInterval>

onMounted(() => {
  intervalId = setInterval(() => {
    time.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  clearInterval(intervalId)
})

const statusConfig = computed(() => ({
  healthy: { label: 'SISTEMA OPERATIVO', variant: 'success' as const, dot: true },
  degraded: { label: 'DEGRADADO', variant: 'warning' as const, dot: true },
  critical: { label: 'CRÍTICO', variant: 'error' as const, dot: true },
  offline: { label: 'DESCONECTADO', variant: 'default' as const, dot: false },
})[props.systemStatus])

const formattedTime = computed(() =>
  time.value.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
)

const formattedDate = computed(() =>
  time.value.toLocaleDateString('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
)
</script>

<template>
  <header
    class="ownex-status-bar"
    role="banner"
    aria-label="Barra de estado del sistema"
  >
    <div class="ownex-status-bar__left">
      <!-- System status -->
      <OwnexBadge
        :variant="statusConfig.variant"
        :dot="statusConfig.dot"
        class="ownex-status-bar__system"
      >
        {{ statusConfig.label }}
      </OwnexBadge>

      <!-- Active cycles -->
      <div class="ownex-status-bar__cycles" aria-label="Ciclos activos">
        <OwnexBadge
          v-for="cycle in props.activeCycles"
          :key="cycle"
          variant="cycle"
          :cycle="cycle"
          size="sm"
        >
          {{ cycle.toUpperCase() }}
        </OwnexBadge>
      </div>
    </div>

    <div class="ownex-status-bar__center">
      <!-- App title -->
      <span class="ownex-status-bar__title">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="ownex-status-bar__logo"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" stroke-width="1.5" opacity="0.3"/>
          <path
            d="M12 2l0 4M12 18l0 4M2 12l4 0M18 12l4 0M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"
            stroke="#2D7FF9"
            stroke-width="1.5"
          />
        </svg>
        OWNEX
      </span>

      <!-- Live metrics -->
      <div class="ownex-status-bar__metrics" role="status" aria-live="polite">
        <span class="ownex-status-bar__metric" :data-count="props.runningWorkflows">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
          {{ props.runningWorkflows }}
        </span>
        <span class="ownex-status-bar__metric" :data-count="props.pendingApprovals">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" />
          </svg>
          {{ props.pendingApprovals }}
        </span>
      </div>
    </div>

    <div class="ownex-status-bar__right">
      <!-- Version -->
      <span class="ownex-status-bar__version" :title="`v${props.version}`">
        v{{ props.version }}
      </span>

      <!-- Date/Time -->
      <div class="ownex-status-bar__datetime" aria-live="off">
        <span class="ownex-status-bar__time">{{ formattedTime }}</span>
        <span class="ownex-status-bar__date">{{ formattedDate }}</span>
      </div>

      <!-- Connection status -->
      <div
        class="ownex-status-bar__connection"
        :class="{ 'ownex-status-bar__connection--connected': isConnected }"
        :aria-label="isConnected ? 'Conectado' : 'Desconectado'"
      >
        <span class="ownex-status-bar__connection-dot" aria-hidden="true" />
        <span class="ownex-status-bar__connection-text">
          {{ isConnected ? 'ONLINE' : 'OFFLINE' }}
        </span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.ownex-status-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-status-bar);
  height: var(--status-bar-height);
  background: rgba(5, 5, 5, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  font-family: var(--font-body);
  font-size: 11px;
  color: var(--ownex-text-secondary);
}

.ownex-status-bar__left,
.ownex-status-bar__center,
.ownex-status-bar__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.ownex-status-bar__center {
  flex: 1;
  justify-content: center;
  gap: var(--space-5);
}

/* System status badge */
.ownex-status-bar__system {
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Cycles */
.ownex-status-bar__cycles {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* Title */
.ownex-status-bar__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.1em;
  color: var(--ownex-white);
  text-transform: uppercase;
}

.ownex-status-bar__logo {
  color: var(--ownex-blue);
}

/* Metrics */
.ownex-status-bar__metrics {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.ownex-status-bar__metric {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--ownex-text-secondary);
  font-variant-numeric: tabular-nums;
}

.ownex-status-bar__metric svg {
  color: var(--ownex-blue);
  opacity: 0.7;
}

.ownex-status-bar__metric[data-count]:not([data-count="0"]) {
  color: var(--ownex-yellow);
}

.ownex-status-bar__metric[data-count]:not([data-count="0"]) svg {
  color: var(--ownex-yellow);
}

/* Right section */
.ownex-status-bar__version {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ownex-text-muted);
  padding: 2px 6px;
  background: var(--ownex-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.ownex-status-bar__datetime {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.2;
}

.ownex-status-bar__time {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--ownex-white);
}

.ownex-status-bar__date {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-muted);
}

/* Connection */
.ownex-status-bar__connection {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: var(--font-weight-medium);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ownex-text-muted);
}

.ownex-status-bar__connection-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ownex-text-muted);
  box-shadow: 0 0 6px var(--ownex-text-muted);
}

.ownex-status-bar__connection--connected .ownex-status-bar__connection-dot {
  background: var(--ownex-green);
  box-shadow: 0 0 8px var(--ownex-green);
}

.ownex-status-bar__connection--connected .ownex-status-bar__connection-text {
  color: var(--ownex-green);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .ownex-status-bar {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}
</style>