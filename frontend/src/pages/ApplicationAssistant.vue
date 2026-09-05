<script setup lang="ts">
/**
 * Application Assistant — plan asistido de postulación a plataformas de ingreso.
 * Backend: core/application_assistant.py vía /api/applications/* (control.py).
 * Plan Combinado + Income Command Center: cores/direct_work_engine/income_plan.py
 * (GET /api/applications/income-plan). Contrato backend SSOT:
 * platform.key / step.id / step.detail / step.fields = Record<label, hint>.
 */

import { CheckCircle2, Circle, ExternalLink, Target } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'

interface PlanStep {
  id: string
  title: string
  detail?: string
  est_minutes?: number
  fields?: Record<string, string>
  done?: boolean
}
interface PlanPlatform {
  key: string
  name: string
  url?: string
  category?: string
  pay_range?: string
  payout?: string
  time_to_first_income?: string
  why?: string
  status?: string
  steps: PlanStep[]
}
interface PlanResponse {
  generated_at?: string
  platforms: PlanPlatform[] | Record<string, PlanPlatform>
}
interface OverviewResponse {
  generated_at?: string
  by_status: Record<string, number>
  progress_pct: number
  next_action: { platform: string; platform_name: string; url?: string; step: string } | null
}

type ActionSource = 'workbank' | 'first_day' | 'applications'
interface PayoffRange {
  low: number
  high: number
}
interface IncomeAction {
  source: ActionSource
  title: string
  detail?: string
  why?: string
  url?: string | null
  human_hours?: number | null
  ev_per_human_hour_usd?: number | null
  payoff_range?: PayoffRange | null
  cash_speed_days?: number | null
  zero_experience?: boolean
  assessment_required?: boolean
  access_probability?: string
  unlocks_stream?: { hourly_rate_usd?: number | null; cash_speed_days?: number | null } | null
}
interface CommandCenter {
  today: PayoffRange
  week: PayoffRange
  fortnight: PayoffRange
  month: PayoffRange
  basis: { availability_hours_per_week: number; note: string; sources: string }
  active_stack: Array<{ key: string; name: string; rate_documented: number | null; status: string }>
  ready_to_deliver_count: number
}
interface IncomePlanResponse {
  philosophy: string
  next_action: IncomeAction | null
  phases: {
    now: IncomeAction[]
    this_week: IncomeAction[]
    waiting: Array<{ key: string; name: string; status: string }>
  }
  tracks: {
    active: { label: string; first_day_progress_pct: number; workbank_ready_to_deliver: number }
    passive: { label: string; progress_pct: number; by_status: Record<string, number> }
  }
  income_command_center: CommandCenter
}

const loading = ref(true)
const error = ref<string | null>(null)
const plan = ref<PlanPlatform[]>([])
const overview = ref<OverviewResponse | null>(null)
const income = ref<IncomePlanResponse | null>(null)
const activePlatform = ref<string>('')
const completing = ref<string>('')

const usd = (n: number): string => `$${Math.round(n).toLocaleString('es-AR')}`
const rangeLabel = (r: PayoffRange): string => (r.low === r.high ? usd(r.low) : `${usd(r.low)}–${usd(r.high)}`)

function fieldsOf(step: PlanStep): Array<{ label: string; value: string }> {
  if (!step.fields) return []
  return Object.entries(step.fields).map(([label, value]) => ({ label, value: String(value ?? '') }))
}

const doneSteps = computed(() => {
  const set = new Set<string>()
  for (const p of plan.value) {
    for (const s of p.steps ?? []) if (s.done) set.add(`${p.key}:${s.id}`)
  }
  return set
})

const active = computed(() => plan.value.find((p) => p.key === activePlatform.value) ?? null)

const statusVariant = computed(() => {
  const map: Record<string, 'default' | 'success' | 'warning' | 'info'> = {
    accepted: 'success',
    applied: 'info',
    in_review: 'info',
    pending: 'default',
    paused: 'warning',
    rejected: 'warning',
  }
  return (s?: string) => map[s ?? 'pending'] ?? 'default'
})

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [planRes, ovRes, incRes] = await Promise.all([
      api.get<PlanResponse>('/applications/plan'),
      api.get<OverviewResponse>('/applications/overview'),
      api.get<IncomePlanResponse>('/applications/income-plan'),
    ])
    const raw = planRes.platforms
    plan.value = Array.isArray(raw) ? raw : Object.values(raw ?? {})
    overview.value = ovRes
    income.value = incRes
    if (!activePlatform.value && plan.value.length > 0) {
      const headPlatform = ovRes.next_action?.platform
      activePlatform.value = plan.value.find((p) => p.key === headPlatform)?.key ?? plan.value[0]?.key ?? ''
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function completeStep(platformKey: string, stepId: string): Promise<void> {
  completing.value = `${platformKey}:${stepId}`
  try {
    await api.post(`/applications/${platformKey}/steps/${stepId}/complete`)
    const step = plan.value.find((p) => p.key === platformKey)?.steps.find((s) => s.id === stepId)
    if (step) step.done = true
    ;[overview.value, income.value] = await Promise.all([
      api.get<OverviewResponse>('/applications/overview'),
      api.get<IncomePlanResponse>('/applications/income-plan'),
    ])
  } catch {
    // keep silent-ish: the row stays unchecked; user can retry
  } finally {
    completing.value = ''
  }
}

async function setStatus(platformKey: string, status: string): Promise<void> {
  await api.post(`/applications/${platformKey}/status`, { status })
  const p = plan.value.find((x) => x.key === platformKey)
  if (p) p.status = status
  income.value = await api.get<IncomePlanResponse>('/applications/income-plan')
}

onMounted(load)
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h1 class="text-xl font-semibold tracking-tight">Application Assistant</h1>
        <p class="text-sm text-muted-foreground">
          Postulación asistida a plataformas de ingreso — qué poner en cada campo.
        </p>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="load">Refrescar</Button>
    </div>

    <ErrorState
      v-if="error"
      title="No se pudo cargar el plan de postulación"
      :error="error"
      :on-retry="load"
    />
    <LoadingState v-else-if="loading" />

    <template v-else>
      <!-- ══ Income Command Center (Plan Combinado) ══ -->
      <Card v-if="income" class="space-y-4 p-5">
        <div class="flex items-start justify-between gap-4">
          <div class="space-y-1">
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Income Command Center · plan combinado
            </p>
            <p class="text-sm text-foreground/80">{{ income.philosophy }}</p>
          </div>
          <Badge variant="info">EV/hora humana</Badge>
        </div>

        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div v-for="(label, key) in { today: 'HOY', week: 'SEMANA', fortnight: 'QUINCENA', month: 'MES' } as const" :key="key"
            class="rounded-lg border border-border/20 bg-surface/20 p-3">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{{ label }}</p>
            <p class="mt-1 font-mono text-sm font-semibold">{{ rangeLabel(income.income_command_center[key]) }}</p>
          </div>
        </div>

        <div v-if="income.next_action" class="rounded-lg border border-accent/30 bg-accent/5 p-4">
          <div class="flex items-start gap-3">
            <Target class="mt-0.5 h-5 w-5 shrink-0 text-accent" />
            <div class="min-w-0 flex-1 space-y-1.5">
              <p class="font-mono text-[11px] uppercase tracking-wider text-accent">Tu mejor acción ahora</p>
              <a v-if="income.next_action.url" :href="income.next_action.url" target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
                {{ income.next_action.title }} <ExternalLink class="h-3 w-3" />
              </a>
              <p v-else class="text-sm font-medium">{{ income.next_action.title }}</p>
              <p class="text-xs leading-relaxed text-muted-foreground">{{ income.next_action.detail }}</p>
              <dl class="flex flex-wrap gap-x-4 gap-y-1 pt-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                <span v-if="income.next_action.ev_per_human_hour_usd != null">
                  ${{ income.next_action.ev_per_human_hour_usd }}/h documentado
                </span>
                <span v-if="income.next_action.payoff_range">
                  payoff {{ rangeLabel(income.next_action.payoff_range) }}
                </span>
                <span v-if="income.next_action.human_hours != null">
                  {{ income.next_action.human_hours }} h humanas
                </span>
                <span v-if="income.next_action.cash_speed_days != null">
                  1er pago ~{{ income.next_action.cash_speed_days }}d
                </span>
                <span :class="income.next_action.zero_experience ? 'text-success' : ''">
                  experiencia: {{ income.next_action.zero_experience ? 'NO requerida' : 'requerida' }}
                </span>
                <span>assessment: {{ income.next_action.assessment_required ? 'SÍ' : 'no' }}</span>
              </dl>
            </div>
          </div>
        </div>

        <p class="font-mono text-[10px] leading-relaxed text-muted-foreground/70">
          {{ income.income_command_center.basis.note }} ·
          {{ income.income_command_center.basis.sources }}
        </p>
      </Card>

      <!-- Next action (fallback overview) -->
      <Card
        v-if="!income?.next_action && overview?.next_action"
        class="border-accent/30 bg-accent/5 p-5"
      >
        <div class="flex items-start gap-3">
          <Target class="mt-0.5 h-5 w-5 text-accent" />
          <div class="space-y-1">
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Próxima acción recomendada · progreso {{ overview.progress_pct }}%
            </p>
            <a
              v-if="overview.next_action.url"
              :href="overview.next_action.url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
            >
              {{ overview.next_action.platform_name }}
              <ExternalLink class="h-3 w-3" />
            </a>
            <p class="text-sm text-foreground/90">{{ overview.next_action.step }}</p>
          </div>
        </div>
      </Card>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        <!-- Platform list -->
        <Card class="divide-y divide-border/20 p-0">
          <button
            v-for="p in plan"
            :key="p.key"
            class="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface/40"
            :class="{ 'bg-primary/5': activePlatform === p.key }"
            @click="activePlatform = p.key"
          >
            <span class="space-y-0.5">
              <span class="block font-mono text-sm font-medium">{{ p.name }}</span>
              <span v-if="p.pay_range" class="block font-mono text-[10px] text-muted-foreground">{{ p.pay_range }}</span>
            </span>
            <Badge :variant="statusVariant(p.status)">{{ p.status ?? 'pending' }}</Badge>
          </button>
        </Card>

        <!-- Steps -->
        <Card v-if="active" class="space-y-4 p-5">
          <div class="flex items-center justify-between">
            <h2 class="font-mono text-sm font-semibold">{{ active.name }}</h2>
            <select
              class="rounded-lg border border-border/40 bg-surface/30 px-2 py-1 font-mono text-xs"
              :value="active.status ?? 'pending'"
              @change="setStatus(active.key, ($event.target as HTMLSelectElement).value)"
            >
              <option value="pending">pending</option>
              <option value="applied">applied</option>
              <option value="in_review">in_review</option>
              <option value="accepted">accepted</option>
              <option value="rejected">rejected</option>
              <option value="paused">paused</option>
            </select>
          </div>

          <ol class="space-y-3">
            <li
              v-for="(s, i) in active.steps"
              :key="s.id"
              class="rounded-lg border border-border/20 bg-surface/20 p-3"
              :class="{ 'opacity-60': doneSteps.has(`${active.key}:${s.id}`) }"
            >
              <div class="flex items-start gap-2.5">
                <CheckCircle2 v-if="doneSteps.has(`${active.key}:${s.id}`)" class="mt-0.5 h-4 w-4 shrink-0 text-success" />
                <Circle v-else class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div class="min-w-0 flex-1 space-y-1.5">
                  <p class="font-mono text-xs font-medium">{{ i + 1 }}. {{ s.title }}</p>
                  <p v-if="s.detail" class="text-xs leading-relaxed text-muted-foreground">{{ s.detail }}</p>
                  <dl v-if="fieldsOf(s).length" class="grid grid-cols-1 gap-1 sm:grid-cols-2">
                    <div v-for="f in fieldsOf(s)" :key="f.label" class="rounded border border-border/20 bg-background/40 px-2 py-1">
                      <dt class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{{ f.label }}</dt>
                      <dd class="truncate font-mono text-[11px]" :title="f.value">{{ f.value }}</dd>
                    </div>
                  </dl>
                  <Button
                    v-if="!doneSteps.has(`${active.key}:${s.id}`)"
                    size="sm"
                    variant="outline"
                    class="h-7 px-2 text-[11px]"
                    :disabled="completing === `${active.key}:${s.id}`"
                    @click="completeStep(active.key, s.id)"
                  >
                    Marcar completado
                  </Button>
                </div>
              </div>
            </li>
          </ol>
        </Card>
      </div>
    </template>
  </div>
</template>
