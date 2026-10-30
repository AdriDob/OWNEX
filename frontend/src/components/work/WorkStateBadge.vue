<script setup lang="ts">
/**
 * WorkStateBadge — Mapea estados técnicos backend a 5 estados humanos.
 * REQUIERE VOS / ALTO VALOR / OWNEX TRABAJANDO / ESPERANDO / COMPLETADO
 */

import { computed } from 'vue'
import {
  AlertTriangle,
  Bot,
  CheckCircle,
  CircleDollarSign,
  Clock,
  Zap,
  UserRound,
} from '@lucide/vue'

export type WorkStateHuman =
  | 'requires_you'      // REQUIERE VOS - acción humana necesaria
  | 'high_value'        // ALTO VALOR - mejor oportunidad ahora
  | 'own_ex_working'    // OWNEX TRABAJANDO - sistema ejecutando
  | 'waiting'           // ESPERANDO - bloqueado por externo
  | 'completed'         // COMPLETADO - terminado

interface StateConfig {
  label: string
  shortLabel: string
  icon: any
  variant: 'destructive' | 'success' | 'primary' | 'warning' | 'info' | 'default'
  bg: string
  text: string
  border: string
  pulse?: boolean
}

const STATE_CONFIG: Record<WorkStateHuman, StateConfig> = {
  requires_you: {
    label: 'REQUIERE VOS',
    shortLabel: 'VOS',
    icon: UserRound,
    variant: 'destructive',
    bg: 'bg-destructive/15',
    text: 'text-destructive',
    border: 'border-destructive/30',
    pulse: true,
  },
  high_value: {
    label: 'ALTO VALOR',
    shortLabel: 'TOP',
    icon: CircleDollarSign,
    variant: 'success',
    bg: 'bg-success/15',
    text: 'text-success',
    border: 'border-success/30',
    pulse: true,
  },
  own_ex_working: {
    label: 'OWNEX TRABAJANDO',
    shortLabel: 'AUTO',
    icon: Bot,
    variant: 'primary',
    bg: 'bg-primary/15',
    text: 'text-primary',
    border: 'border-primary/30',
    pulse: true,
  },
  waiting: {
    label: 'ESPERANDO',
    shortLabel: 'WAIT',
    icon: Clock,
    variant: 'warning',
    bg: 'bg-warning/15',
    text: 'text-warning',
    border: 'border-warning/30',
  },
  completed: {
    label: 'COMPLETADO',
    shortLabel: 'DONE',
    icon: CheckCircle,
    variant: 'default',
    bg: 'bg-muted/30',
    text: 'text-muted-foreground',
    border: 'border-border/30',
  },
}

// Mapeo de estados técnicos → estados humanos
// Execution Queue states
const EXEC_STATE_MAP: Record<string, WorkStateHuman> = {
  discovered: 'high_value',
  qualified: 'high_value',
  ready: 'own_ex_working',
  queued: 'own_ex_working',
  executing: 'own_ex_working',
  waiting_human: 'requires_you',
  submitted: 'waiting',
  verification: 'waiting',
  paid: 'completed',
  failed: 'requires_you',
  rejected: 'completed',
  blocked: 'waiting',
  dead_letter: 'requires_you',
}

// WorkBank states
const WORKBANK_STATE_MAP: Record<string, WorkStateHuman> = {
  discovered: 'high_value',
  preparing: 'own_ex_working',
  ready_to_deliver: 'requires_you',
  delivered: 'completed',
  needs_access: 'requires_you',
  rejected: 'completed',
  archived: 'completed',
}

// Direct Work Opportunity states
const OPPORTUNITY_STATE_MAP: Record<string, WorkStateHuman> = {
  pending: 'high_value',
  in_review: 'waiting',
  accepted: 'completed',
  rejected: 'completed',
}

// Pipeline stages
const PIPELINE_STAGE_MAP: Record<string, WorkStateHuman> = {
  recon: 'own_ex_working',
  attack_surface: 'own_ex_working',
  hypothesis: 'own_ex_working',
  validation: 'own_ex_working',
  evidence: 'own_ex_working',
  report: 'own_ex_working',
  learning: 'own_ex_working',
  completed: 'completed',
  failed: 'requires_you',
}

export function useWorkStateHuman() {
  function mapToHuman(state: string, source: 'execution' | 'workbank' | 'opportunity' | 'pipeline' = 'execution'): WorkStateHuman {
    const maps = {
      execution: EXEC_STATE_MAP,
      workbank: WORKBANK_STATE_MAP,
      opportunity: OPPORTUNITY_STATE_MAP,
      pipeline: PIPELINE_STAGE_MAP,
    }
    return maps[source][state] || 'waiting'
  }

  function getConfig(state: WorkStateHuman): StateConfig {
    return STATE_CONFIG[state]
  }

  function getAllStates(): WorkStateHuman[] {
    return ['requires_you', 'high_value', 'own_ex_working', 'waiting', 'completed']
  }

  return { mapToHuman, getConfig, getAllStates }
}

// Composable para usar en componentes
export function useWorkStateBadge(rawState: string, source: 'execution' | 'workbank' | 'opportunity' | 'pipeline' = 'execution') {
  const { mapToHuman, getConfig } = useWorkStateHuman()
  const humanState = computed(() => mapToHuman(rawState, source))
  const config = computed(() => getConfig(humanState.value))

  return { humanState, config }
}
</script>

<template>
  <!-- Componente de badge visual para estado humano -->
  <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold"
    :class="[config.bg, config.text, config.border, config.pulse ? 'animate-pulse' : '']"
  >
    <component :is="config.icon" class="h-3 w-3 shrink-0" />
    <span v-if="$slots.default === undefined">{{ config.shortLabel }}</span>
    <slot>{{ config.label }}</slot>
  </div>
</template>

<style scoped>
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.animate-pulse { animation: pulse 1.5s ease-in-out infinite; }
</style>