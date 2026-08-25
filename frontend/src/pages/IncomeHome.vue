<script setup lang="ts">
/**
 * OWNEX CEO HOME — Income Command Center ('/', 2026-08-25).
 * Responde en <60s sin documentación: ¿cuánto gano? ¿qué hago? ¿por qué?
 * ¿qué hace OWNEX? ¿qué hago yo? ¿cuándo cobro?
 * Datos reales únicamente: /applications/income-plan + /mission/status.
 */

import { computed, onMounted, ref } from 'vue'
import { Bot, CircleUser, ExternalLink } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import NextBestAction from '@/components/mission-control/NextBestAction.vue'
import { fetchIncomePlan, fetchMissionStatus, type IncomePlanAction, type IncomePlanState } from '@/services/ownexData'

const loading = ref(true)
const error = ref<string | null>(null)
const income = ref<IncomePlanState | null>(null)
const system = ref<{ health: number; status: string } | null>(null)

const usd = (n: number): string => `$${Math.round(n).toLocaleString('es-AR')}`
const rangeLabel = (r: { low: number; high: number }): string =>
  r.low === r.high ? usd(r.low) : `${usd(r.low)}–${usd(r.high)}`

const horizons = {
  today: 'HOY',
  week: 'ESTA SEMANA',
  fortnight: 'QUINCENA',
  month: 'MES',
} as const

const statusVariant = computed<'success' | 'warning' | 'error'>(() => {
  const s = system.value?.status.toLowerCase()
  if (!s || s === 'unknown') return 'warning'
  if (['healthy', 'operational', 'ready'].includes(s)) return 'success'
  if (['degraded', 'starting', 'scanning', 'processing', 'waiting'].includes(s)) return 'warning'
  return 'error'
})

/** 🤖 Lo que OWNEX hace solo (estado real del plan, no métricas decorativas). */
const automation = computed(() => {
  const t = income.value?.tracks
  return [
    {
      done: true,
      text: `Descubriendo y rankeando por $/hora humana (${(t?.active.first_day_progress_pct ?? 0) > 0 ? 'guía first-day activa' : 'radar de fuentes curadas'})`,
    },
    {
      done: true,
      text: `Work Bank: ${t?.active.workbank_ready_to_deliver ?? 0} entrega(s) lista(s)`,
    },
    {
      done: (t?.passive.accepted_streams?.length ?? 0) > 0,
      text:
        (t?.passive.accepted_streams?.length ?? 0) > 0
          ? `Streams aprobados: ${t?.passive.accepted_streams?.join(', ')}`
          : 'Postulaciones AI-training en curso (sin stream aprobado aún)',
    },
    {
      done: false,
      text: `Esperando plataforma: ${income.value?.phases.waiting.map((w) => w.name).join(', ') || 'ninguna'}`,
    },
  ]
})

/** 👤 Tus acciones humanas concretas (cola this_week del plan). */
const humanActions = computed<Array<IncomePlanAction>>(
  () => income.value?.phases.this_week.slice(0, 5) ?? [],
)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  // Promise.allSettled: un backend caído no borra lo que sí respondió.
  const [planRes, sysRes] = await Promise.allSettled([fetchIncomePlan(), fetchMissionStatus()])
  if (planRes.status === 'fulfilled') income.value = planRes.value
  else error.value = planRes.reason instanceof Error ? planRes.reason.message : String(planRes.reason)
  if (sysRes.status === 'fulfilled') system.value = { health: sysRes.value.health, status: sysRes.value.status }
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">OWNEX Command Center</h1>
        <p class="text-sm text-muted-foreground">Autonomous Work Operating System</p>
      </div>
      <Badge v-if="system" :variant="statusVariant" dot>
        {{ system.status.toUpperCase() }} · salud {{ Math.round(system.health) }}%
      </Badge>
    </div>

    <ErrorState v-if="error && !income" title="No se pudo cargar el plan de ingresos" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading && !income" />

    <template v-else-if="income">
      <!-- N1: NEXT ACTION dominante -->
      <NextBestAction
        v-if="income.next_action"
        :title="income.next_action.title"
        :description="income.next_action.detail || ''"
        :href="income.next_action.url || '/operations/applications'"
        :primary-action="{ label: income.next_action.url ? 'Abrir y ejecutar' : 'Ver plan completo', variant: 'primary' }"
        :secondary-action="{ label: 'Posponer', variant: 'ghost' }"
        :reasoning="income.next_action.why || income.philosophy"
        :ev-per-hour="income.next_action.ev_per_human_hour_usd ?? null"
        :payoff-range="income.next_action.payoff_range ?? null"
        :cash-speed-days="income.next_action.cash_speed_days ?? null"
        :assessment-required="income.next_action.assessment_required ?? null"
        :zero-experience="income.next_action.zero_experience ?? null"
      />

      <!-- N1: potencial económico -->
      <Card class="space-y-3 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">💰 Ingreso potencial</p>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div v-for="(label, key) in horizons" :key="key" class="rounded-lg border border-border/20 bg-surface/20 p-4">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{{ label }}</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums">
              {{ rangeLabel(income.income_command_center[key]) }}
            </p>
          </div>
        </div>
        <p class="font-mono text-[10px] leading-relaxed text-muted-foreground/70">
          {{ income.income_command_center.basis.note }} · {{ income.income_command_center.basis.sources }}
        </p>
      </Card>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- N1b: qué hace OWNEX vs qué hacés vos -->
        <Card class="space-y-3 p-5">
          <div class="flex items-center gap-2">
            <Bot class="h-4 w-4 text-accent" aria-hidden="true" />
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">🤖 OWNEX está haciendo</p>
          </div>
          <ul class="space-y-2">
            <li v-for="(a, i) in automation" :key="i" class="flex items-start gap-2 text-sm">
              <span :class="a.done ? 'text-success' : 'text-warning'" class="mt-0.5 font-mono">{{ a.done ? '✓' : '…' }}</span>
              <span class="text-foreground/90">{{ a.text }}</span>
            </li>
          </ul>
        </Card>

        <Card class="space-y-3 p-5">
          <div class="flex items-center gap-2">
            <CircleUser class="h-4 w-4 text-gold" aria-hidden="true" />
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">👤 Tus próximas acciones</p>
          </div>
          <ol v-if="humanActions.length" class="space-y-2">
            <li v-for="(a, i) in humanActions" :key="a.title" class="flex items-start gap-2.5 rounded-lg border border-border/20 bg-surface/20 p-2.5">
              <span class="mt-0.5 font-mono text-[10px] text-muted-foreground">{{ i + 1 }}</span>
              <div class="min-w-0 flex-1">
                <a v-if="a.url" :href="a.url" target="_blank" rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 truncate font-mono text-xs font-medium text-accent hover:underline">
                  {{ a.title }} <ExternalLink class="h-3 w-3 shrink-0" />
                </a>
                <p v-else class="truncate font-mono text-xs font-medium">{{ a.title }}</p>
                <p v-if="a.ev_per_human_hour_usd != null" class="font-mono text-[10px] text-muted-foreground">
                  ${{ a.ev_per_human_hour_usd }}/h documentado
                  <template v-if="a.human_hours != null"> · {{ a.human_hours }} h</template>
                </p>
              </div>
            </li>
          </ol>
          <p v-else class="text-sm text-muted-foreground">
            Sin cola pendiente. OWNEX sigue buscando; esta lista se llena sola.
          </p>
        </Card>
      </div>

      <!-- N2: stack activo -->
      <Card class="space-y-2 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">📈 Stack activo (tarifas documentadas)</p>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <div v-for="s in income.income_command_center.active_stack" :key="s.key"
            class="rounded-lg border border-border/20 bg-surface/20 p-3">
            <p class="truncate font-mono text-xs font-medium">{{ s.name }}</p>
            <p class="font-mono text-[11px]" :class="s.rate_documented ? 'text-success' : 'text-muted-foreground'">
              {{ s.rate_documented ? `$${s.rate_documented}/h` : 'tarifa n/d' }}
            </p>
            <Badge :variant="s.status === 'accepted' ? 'success' : s.status === 'in_review' ? 'info' : 'default'" class="mt-1">
              {{ s.status }}
            </Badge>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>
