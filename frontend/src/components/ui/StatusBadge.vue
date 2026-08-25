<script setup lang="ts">
import { computed } from 'vue'

/**
 * StatusBadge — single vocabulary for OWNEX system states (spec §13).
 * Never color-only: dot + label + optional reason (title tooltip).
 */
export type SystemStatus =
  | 'OPERATIONAL'
  | 'STARTING'
  | 'SCANNING'
  | 'PROCESSING'
  | 'WAITING'
  | 'DEGRADED'
  | 'BLOCKED'
  | 'ERROR'
  | 'OFFLINE'

interface Props {
  status: SystemStatus
  /** Optional human explanation shown as tooltip */
  reason?: string
  compact?: boolean
}

const props = withDefaults(defineProps<Props>(), { compact: false })

const SEMANTIC: Record<SystemStatus, { color: string; label: string; pulse: boolean }> = {
  OPERATIONAL: { color: 'var(--color-success)', label: 'Operacional', pulse: false },
  STARTING: { color: 'var(--color-info)', label: 'Iniciando', pulse: true },
  SCANNING: { color: 'var(--color-info)', label: 'Escaneando', pulse: true },
  PROCESSING: { color: 'var(--color-info)', label: 'Procesando', pulse: true },
  WAITING: { color: 'var(--color-warning)', label: 'En espera', pulse: false },
  DEGRADED: { color: 'var(--color-warning)', label: 'Degradado', pulse: false },
  BLOCKED: { color: 'var(--color-danger)', label: 'Bloqueado', pulse: false },
  ERROR: { color: 'var(--color-danger)', label: 'Error', pulse: false },
  OFFLINE: { color: 'var(--color-text-muted)', label: 'Sin conexión', pulse: false },
}

const s = computed(() => SEMANTIC[props.status] ?? SEMANTIC.OFFLINE)
const tooltip = computed(() => (props.reason ? `${s.value.label}: ${props.reason}` : s.value.label))
</script>

<template>
  <span
    class="status-badge inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5"
    :class="compact ? 'text-[10px]' : 'text-xs'"
    :title="tooltip"
    role="status"
    :aria-label="tooltip"
    style="border-color: var(--color-border); background: var(--color-surface)"
  >
    <span
      class="status-dot inline-block h-2 w-2 shrink-0 rounded-full"
      :class="{ 'status-pulse': s.pulse }"
      :style="{ background: s.color }"
      aria-hidden="true"
    />
    <span class="font-medium uppercase tracking-wider" style="color: var(--color-text)">
      {{ s.label }}
    </span>
  </span>
</template>

<style scoped>
.status-pulse {
  animation: statusPulse 2s ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
  .status-pulse {
    animation: none;
  }
}
@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}
</style>
