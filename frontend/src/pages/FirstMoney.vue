<script setup lang="ts">
/**
 * First Money — tracker visible del funnel Zero-to-Earning ($0 → primer ingreso).
 * Backend: /first-money/* (progreso, next-action, stage start/complete, first-revenue).
 * Freelance es un canal OPCIONAL: solo los canales ACTIVE participan.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import {
  completeFirstMoneyStage,
  fetchAggressivePlan,
  fetchEvolutionLearning,
  fetchFirstMoneyNextAction,
  fetchFirstMoneyProgress,
  fetchFreelanceChannels,
  fetchMilestoneTracker,
  recordFirstRevenue,
  setFreelanceChannel,
  startFirstMoneyStage,
  type AggressiveEnginePlan,
  type AggressivePlanState,
  type DailyAction,
  type EngineProximity,
  type EvolutionCalibration,
  type FirstMoneyNextAction,
  type FirstMoneyProgress,
  type FirstMoneyStageStatus,
  type FreelanceChannelInfo,
  type MilestoneProgressItem,
  type MilestoneTrackerState,
  type RepeatableRow,
} from '@/services/ownexData'

const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const progress = ref<FirstMoneyProgress | null>(null)
const nextAction = ref<FirstMoneyNextAction | null>(null)
const channels = ref<Record<string, FreelanceChannelInfo>>({})
const busyStage = ref<string | null>(null)
const busyChannel = ref<string | null>(null)

const revenueAmount = ref<string>('')
const revenuePlatform = ref<string>('hackerone')
const revenueNotes = ref<string>('')
const revenueBusy = ref(false)
const revenueDone = ref<string | null>(null)
const calibration = ref<EvolutionCalibration | null>(null)
const repeatable = ref<RepeatableRow[]>([])

// Milestone Tracker
const milestoneTracker = ref<MilestoneTrackerState | null>(null)
const busyMilestone = ref(false)

// Aggressive Plan (EOY Targets)
const aggressivePlan = ref<AggressivePlanState | null>(null)
const aggressiveTarget = ref<5000 | 10000>(5000)
const busyAggressive = ref(false)

const statusVariant = (s: FirstMoneyStageStatus): 'success' | 'warning' | 'error' | 'default' => {
  if (s === 'completed') return 'success'
  if (s === 'in_progress') return 'warning'
  if (s === 'blocked') return 'error'
  return 'default'
}

const statusLabel = (s: FirstMoneyStageStatus): string => {
  switch (s) {
    case 'completed':
      return 'Completada'
    case 'in_progress':
      return 'En curso'
    case 'blocked':
      return 'Bloqueada'
    case 'skipped':
      return 'Omitida'
    default:
      return 'Pendiente'
  }
}

const currentStage = computed(() => progress.value?.stages.find((s) => s.is_current) ?? null)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [p, n, c, m, a] = await Promise.all([
      fetchFirstMoneyProgress(),
      fetchFirstMoneyNextAction(),
      fetchFreelanceChannels().catch(() => ({ channels: {}, note: '' })),
      fetchMilestoneTracker().catch(() => null),
      fetchAggressivePlan(aggressiveTarget.value).catch(() => null),
    ])
    progress.value = p
    nextAction.value = n
    channels.value = c.channels ?? {}
    milestoneTracker.value = m
    aggressivePlan.value = a
    try {
      const evo = await fetchEvolutionLearning([], 0)
      calibration.value = evo.calibration ?? null
      repeatable.value = evo.repeatable ?? []
    } catch {
      calibration.value = null
      repeatable.value = []
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function doStart(stage: string): Promise<void> {
  busyStage.value = stage
  try {
    await startFirstMoneyStage(stage, currentStage.value?.platform ?? undefined)
    await load()
  } catch (e) {
    console.error('start stage failed', e)
  } finally {
    busyStage.value = null
  }
}

async function doComplete(stage: string): Promise<void> {
  busyStage.value = stage
  try {
    await completeFirstMoneyStage(stage)
    await load()
  } catch (e) {
    console.error('complete stage failed', e)
  } finally {
    busyStage.value = null
  }
}

async function doRecordRevenue(): Promise<void> {
  const amount = Number(revenueAmount.value)
  if (!Number.isFinite(amount) || amount <= 0 || !revenuePlatform.value) return
  revenueBusy.value = true
  revenueDone.value = null
  try {
    await recordFirstRevenue(amount, revenuePlatform.value, revenueNotes.value || undefined)
    revenueDone.value = `Registrados $${amount} en ${revenuePlatform.value}. El ledger solo cuenta PAID real.`
    revenueAmount.value = ''
    revenueNotes.value = ''
    await load()
  } catch (e) {
    console.error('record revenue failed', e)
  } finally {
    revenueBusy.value = false
  }
}

async function doSetChannel(channel: string, status: 'active' | 'paused'): Promise<void> {
  busyChannel.value = channel
  try {
    await setFreelanceChannel(channel, status)
    await load()
  } catch (e) {
    console.error('set channel failed', e)
  } finally {
    busyChannel.value = null
  }
}

function goToPlatforms(): void {
  void router.push('/operations/platforms')
}

async function setAggressiveTarget(target: 5000 | 10000): Promise<void> {
  aggressiveTarget.value = target
  busyAggressive.value = true
  try {
    const plan = await fetchAggressivePlan(target)
    aggressivePlan.value = plan
  } catch (e) {
    console.error('fetch aggressive plan failed', e)
  } finally {
    busyAggressive.value = false
  }
}

function goToWorkQueue(): void {
  void router.push('/operations/work-queue')
}

function goToUrl(url: string): void {
  if (url.startsWith('/')) {
    void router.push(url)
  } else {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="First Money">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">First Money</h1>
        <p class="text-sm opacity-70">$0 → primer ingreso real. Sin dinero simulado: solo PAID cuenta.</p>
      </div>
      <div class="ml-auto flex gap-2">
        <OwnexButton variant="secondary" size="sm" @click="goToPlatforms">Guías de plataforma</OwnexButton>
        <OwnexButton variant="secondary" size="sm" @click="goToWorkQueue">Cola de trabajo</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando progreso..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="progress">
      <!-- Progreso global -->
      <OwnexCard class="mb-4">
        <div class="flex flex-wrap items-center gap-4">
          <div class="min-w-48 flex-1">
            <div class="mb-1 flex items-center justify-between text-sm">
              <span>
                Etapa actual: <strong>{{ progress.current_stage_label }}</strong>
              </span>
              <span>{{ progress.completed_count }}/{{ progress.total_count }}</span>
            </div>
            <ProgressBar :value="progress.completion_percentage" color="primary" size="md" show-label />
          </div>
          <OwnexBadge v-if="progress.is_complete" variant="success">Ciclo completo</OwnexBadge>
          <OwnexBadge v-else variant="default">En curso</OwnexBadge>
          <div v-if="progress.first_revenue_amount > 0" class="text-sm">
            Primer ingreso: <strong>${{ progress.first_revenue_amount }}</strong>
            <span class="opacity-70">({{ progress.first_revenue_platform }})</span>
          </div>
        </div>
      </OwnexCard>

      <!-- Milestone Tracker Dashboard -->
      <OwnexCard v-if="milestoneTracker" class="mb-4" variant="highlight">
        <div class="mb-3 flex flex-wrap items-center gap-3">
          <div class="flex-1">
            <div class="text-xs uppercase opacity-60">Próximo hito</div>
            <div class="flex items-baseline gap-2">
              <div class="text-2xl font-bold">{{ milestoneTracker.next_milestone.label }}</div>
              <OwnexBadge :variant="milestoneTracker.next_milestone.pct_complete > 0 ? 'success' : 'default'">
                {{ milestoneTracker.next_milestone.pct_complete.toFixed(1) }}%
              </OwnexBadge>
            </div>
            <div class="text-sm opacity-70">Faltan ${{ milestoneTracker.next_milestone.usd_needed.toLocaleString() }}</div>
          </div>
          <ProgressBar :value="milestoneTracker.next_milestone.pct_complete" color="primary" size="md" show-label class="w-48" />
        </div>

        <!-- Hititos -->
        <div class="mb-3 overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border opacity-50">
                <th class="text-left pb-1">Hito</th>
                <th class="text-left pb-1">Progreso</th>
                <th class="text-left pb-1">Falta</th>
                <th class="text-left pb-1">Motores</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in milestoneTracker.milestones" :key="m.milestone" :class="{ 'bg-primary/5': m.is_next }">
                <td class="py-1 font-medium">{{ m.label }}</td>
                <td class="py-1">
                  <ProgressBar :value="m.pct_complete" color="primary" size="sm" show-label class="w-32" />
                </td>
                <td class="py-1 opacity-70">${{ m.usd_needed.toLocaleString() }}</td>
                <td class="py-1">
                  <div class="flex flex-wrap gap-1">
                    <OwnexBadge
                      v-for="e in m.engines_contributing"
                      :key="e"
                      size="xs"
                      variant="default"
                    >
                      {{ e.replace('_', ' ') }}
                    </OwnexBadge>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Motores más cercanos -->
        <div class="mb-3">
          <div class="text-xs uppercase opacity-60 mb-2">Motores hacia el hito</div>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="e in milestoneTracker.engine_proximities"
              :key="e.engine"
              class="flex flex-col gap-1 rounded border border-border/60 px-3 py-2 text-sm"
              :class="{ 'border-primary bg-primary/5': e.is_closest, 'opacity-50': e.status === 'blocked' }"
            >
              <div class="flex items-center gap-1">
                <strong>{{ e.label }}</strong>
                <OwnexBadge :variant="e.status === 'ready' ? 'success' : e.status === 'needs_action' ? 'warning' : e.status === 'needs_setup' ? 'default' : 'error'" size="xs">
                  {{ e.status }}
                </OwnexBadge>
                <OwnexBadge v-if="e.is_closest" variant="success" size="xs">Más cerca</OwnexBadge>
              </div>
              <div class="flex items-center gap-2 text-xs opacity-70">
                <span>${{ e.current_usd }} → ${{ e.projected_usd }}</span>
                <span class="font-mono">${{ e.usd_to_milestone.toLocaleString() }} al hito</span>
                <OwnexBadge :variant="e.confidence > 0.6 ? 'success' : e.confidence > 0.4 ? 'warning' : 'default'" size="xs">
                  {{ (e.confidence * 100).toFixed(0) }}%
                </OwnexBadge>
              </div>
              <div class="text-xs opacity-60">{{ e.next_action }}</div>
            </div>
          </div>
        </div>

        <!-- Acción diaria -->
        <div v-if="milestoneTracker.daily_action" class="p-3 rounded bg-primary/10 border border-primary/20">
          <div class="flex items-center gap-2 mb-1">
            <div class="text-xs uppercase opacity-60">Acción de hoy</div>
            <OwnexBadge :variant="milestoneTracker.daily_action.priority === 1 ? 'success' : milestoneTracker.daily_action.priority === 2 ? 'warning' : 'default'" size="xs">
              Prioridad {{ milestoneTracker.daily_action.priority }}
            </OwnexBadge>
          </div>
          <div class="font-semibold">{{ milestoneTracker.daily_action.title }}</div>
          <div class="text-sm opacity-70">{{ milestoneTracker.daily_action.description }}</div>
          <div class="flex flex-wrap items-center gap-2 mt-2 text-xs opacity-60">
            <span>⏱ ~{{ milestoneTracker.daily_action.estimated_minutes }} min</span>
            <span>💰 EV ~${{ milestoneTracker.daily_action.impact_usd }}</span>
            <OwnexButton v-if="milestoneTracker.daily_action.url" variant="primary" size="xs" @click="goToUrl(milestoneTracker.daily_action.url!)">
              Ir
            </OwnexButton>
          </div>
        </div>
      </OwnexCard>

      <!-- Aggressive Plan (EOY Targets: $5k / $10k) -->
      <OwnexCard v-if="aggressivePlan" class="mb-4" variant="highlight">
        <div class="mb-3 flex flex-wrap items-center gap-3">
          <div class="flex-1">
            <div class="text-xs uppercase opacity-60">Plan agresivo fin de año</div>
            <div class="flex items-baseline gap-2">
              <div class="text-xl font-bold">${{ aggressivePlan.target_usd.toLocaleString() }}</div>
              <OwnexBadge :variant="aggressivePlan.probability_note.includes('ALTA') ? 'success' : aggressivePlan.probability_note.includes('MEDIA') ? 'warning' : 'error'">
                {{ aggressivePlan.probability_note.split(':')[0] }}
              </OwnexBadge>
            </div>
            <div class="text-sm opacity-70">
              Gap: ${{ aggressivePlan.gap_usd.toLocaleString() }} en {{ aggressivePlan.weeks_left }} semanas
              → ${{ aggressivePlan.weekly_required_total.toFixed(0) }}/sem (${{ aggressivePlan.monthly_required_total.toFixed(0) }}/mes)
            </div>
          </div>
          <div class="flex gap-2">
            <OwnexButton
              :variant="aggressiveTarget === 5000 ? 'primary' : 'secondary'"
              size="sm"
              :loading="busyAggressive"
              @click="setAggressiveTarget(5000)"
            >
              $5k
            </OwnexButton>
            <OwnexButton
              :variant="aggressiveTarget === 10000 ? 'primary' : 'secondary'"
              size="sm"
              :loading="busyAggressive"
              @click="setAggressiveTarget(10000)"
            >
              $10k
            </OwnexButton>
          </div>
        </div>

        <!-- Plan semanal por motor -->
        <div class="mb-3">
          <div class="text-xs uppercase opacity-60 mb-2">Plan semanal por motor</div>
          <div class="space-y-2">
            <div
              v-for="e in aggressivePlan.engine_plan"
              :key="e.engine"
              class="flex flex-col gap-1 rounded border border-border/60 px-3 py-2 text-sm"
              :class="{ 'border-primary bg-primary/5': e.is_primary, 'opacity-50': e.setup_phase }"
            >
              <div class="flex items-center gap-1">
                <strong>{{ e.label }}</strong>
                <OwnexBadge :variant="e.status === 'ready' ? 'success' : e.status === 'needs_action' ? 'warning' : 'default'" size="xs">
                  {{ e.status }}
                </OwnexBadge>
                <OwnexBadge v-if="e.is_primary" variant="success" size="xs">Principal</OwnexBadge>
                <OwnexBadge v-if="e.setup_phase" variant="default" size="xs">Setup</OwnexBadge>
              </div>
              <div class="flex items-center gap-2 text-xs opacity-70">
                <span class="font-mono">${{ e.weekly_usd_target.toFixed(0) }}/sem</span>
                <span class="font-mono">${{ e.monthly_usd_target.toFixed(0) }}/mes</span>
                <span>{{ e.est_hours_per_week.toFixed(1) }}h/sem</span>
                <OwnexBadge :variant="e.confidence > 0.6 ? 'success' : e.confidence > 0.4 ? 'warning' : 'default'" size="xs">
                  {{ (e.confidence * 100).toFixed(0) }}%
                </OwnexBadge>
              </div>
              <div class="text-xs opacity-60" v-if="e.setup_phase">{{ e.setup_actions }}</div>
            </div>
          </div>
        </div>

        <!-- Checklist semanal -->
        <div class="mb-3">
          <div class="text-xs uppercase opacity-60 mb-2">Checklist semanal</div>
          <ul class="space-y-1">
            <li v-for="c in aggressivePlan.weekly_checklist" :key="c" class="text-sm flex items-start gap-2">
              <span class="text-primary mt-0.5">→</span>
              <span>{{ c }}</span>
            </li>
          </ul>
        </div>

        <!-- Probabilidad -->
        <div class="p-3 rounded border border-warning/30 bg-warning/10">
          <div class="text-xs uppercase opacity-60 mb-1">Probabilidad honesta</div>
          <div class="text-sm">{{ aggressivePlan.probability_note }}</div>
        </div>
      </OwnexCard>

      <!-- Próxima acción -->
      <OwnexCard v-if="nextAction" class="mb-4" variant="highlight">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex-1">
            <div class="text-xs uppercase opacity-60">Próxima acción</div>
            <div class="text-lg font-semibold">{{ nextAction.title }}</div>
            <div class="text-sm opacity-80">{{ nextAction.description }}</div>
          </div>
          <OwnexButton
            v-if="currentStage && currentStage.status !== 'completed'"
            variant="primary"
            size="sm"
            :loading="busyStage === currentStage.stage"
            @click="doStart(currentStage.stage)"
          >
            Empezar etapa
          </OwnexButton>
        </div>
      </OwnexCard>

      <!-- Registrar ingreso real -->
      <OwnexCard class="mb-4">
        <h2 class="mb-2 text-base font-semibold">Registrar ingreso real</h2>
        <p class="mb-3 text-sm opacity-70">
          Solo dinero efectivamente cobrado (PAID). Nunca registres potencial como ingreso.
        </p>
        <div class="flex flex-wrap items-end gap-2">
          <label class="flex flex-col gap-1 text-sm">
            Monto (USD)
            <input
              v-model="revenueAmount"
              type="number"
              min="0"
              step="0.01"
              placeholder="150.00"
              class="rounded border border-border bg-background px-2 py-1"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            Plataforma
            <input
              v-model="revenuePlatform"
              type="text"
              placeholder="hackerone"
              class="rounded border border-border bg-background px-2 py-1"
            />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            Notas
            <input
              v-model="revenueNotes"
              type="text"
              placeholder="Bounty XSS — programa Acme"
              class="rounded border border-border bg-background px-2 py-1"
            />
          </label>
          <OwnexButton variant="primary" size="sm" :loading="revenueBusy" @click="doRecordRevenue">
            Registrar
          </OwnexButton>
        </div>
        <p v-if="revenueDone" class="mt-2 text-sm text-green-500">{{ revenueDone }}</p>
      </OwnexCard>

      <!-- Canales freelance (opcionales) -->
      <OwnexCard class="mb-4">
        <h2 class="mb-1 text-base font-semibold">Canales freelance (opcionales)</h2>
        <p class="mb-3 text-sm opacity-70">
          El freelance no es obligatorio: solo los canales ACTIVE participan en las recomendaciones.
        </p>
        <EmptyState
          v-if="Object.keys(channels).length === 0"
          title="Sin canales freelance"
          description="No hay canales configurados."
        />
        <div v-else class="flex flex-wrap gap-3">
          <div
            v-for="(info, channel) in channels"
            :key="channel"
            class="flex items-center gap-2 rounded border border-border px-3 py-2"
          >
            <strong class="text-sm capitalize">{{ channel }}</strong>
            <OwnexBadge :variant="info.recommending ? 'success' : 'default'">
              {{ info.status }}
            </OwnexBadge>
            <OwnexButton
              v-if="info.recommending"
              variant="secondary"
              size="sm"
              :loading="busyChannel === channel"
              @click="doSetChannel(channel, 'paused')"
            >
              Pausar
            </OwnexButton>
            <OwnexButton
              v-else
              variant="secondary"
              size="sm"
              :loading="busyChannel === channel"
              @click="doSetChannel(channel, 'active')"
            >
              Activar
            </OwnexButton>
          </div>
        </div>
      </OwnexCard>

      <!-- Aprendizaje: calibración + patrones repetibles -->
      <OwnexCard class="mb-4">
        <h2 class="mb-1 text-base font-semibold">Aprendizaje del sistema</h2>
        <p class="mb-3 text-sm opacity-70">
          Predicho vs real. Sin predicciones registradas, el sistema dice UNKNOWN en vez de inventar.
        </p>
        <div v-if="calibration" class="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <OwnexBadge
            :variant="
              calibration.verdict === 'CALIBRATED'
                ? 'success'
                : calibration.verdict === 'THIN_EVIDENCE'
                  ? 'warning'
                  : 'default'
            "
          >
            {{ calibration.verdict }}
          </OwnexBadge>
          <span v-if="calibration.mae_amount_usd !== null" class="font-mono">
            MAE ${{ calibration.mae_amount_usd }}
          </span>
          <span v-if="calibration.mae_hours !== null" class="font-mono">
            MAE {{ calibration.mae_hours }}h
          </span>
          <span class="opacity-70">{{ calibration.note }}</span>
        </div>
        <EmptyState
          v-if="repeatable.length === 0"
          title="Sin patrones todavía"
          description="Con 3+ resultados verificados, OWNEX identifica qué se repite."
        />
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="row in repeatable"
            :key="`${row.platform}:${row.category}`"
            class="flex flex-wrap items-center gap-3 rounded border border-border/60 px-3 py-2 text-sm"
          >
            <OwnexBadge
              :variant="row.verdict === 'REPEATABLE' ? 'success' : row.verdict === 'NON_REPEATABLE' ? 'error' : 'default'"
            >
              {{ row.verdict }}
            </OwnexBadge>
            <strong>{{ row.platform }}</strong>
            <span class="opacity-70">{{ row.category || 'general' }}</span>
            <span class="ml-auto font-mono">${{ row.revenue_usd }} · {{ row.accepted }}/{{ row.total }}</span>
          </div>
        </div>
      </OwnexCard>

      <!-- Etapas -->
      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Etapas del funnel</h2>
        <ol class="flex flex-col gap-2">
          <li
            v-for="stage in progress.stages"
            :key="stage.stage"
            class="flex flex-wrap items-center gap-3 rounded border border-border/60 px-3 py-2"
            :class="{ 'border-primary': stage.is_current }"
          >
            <OwnexBadge :variant="statusVariant(stage.status)">
              {{ statusLabel(stage.status) }}
            </OwnexBadge>
            <div class="min-w-52 flex-1">
              <div class="text-sm font-semibold">{{ stage.label }}</div>
              <div class="text-xs opacity-70">{{ stage.description }}</div>
              <div v-if="stage.platform" class="text-xs opacity-60">Plataforma: {{ stage.platform }}</div>
              <div v-if="stage.blocking_reason" class="text-xs text-red-500">
                Bloqueo: {{ stage.blocking_reason }}
              </div>
            </div>
            <div v-if="stage.status !== 'completed'" class="flex gap-2">
              <OwnexButton
                v-if="stage.status === 'not_started'"
                variant="secondary"
                size="sm"
                :loading="busyStage === stage.stage"
                @click="doStart(stage.stage)"
              >
                Empezar
              </OwnexButton>
              <OwnexButton
                v-if="stage.status === 'in_progress' || stage.is_current"
                variant="primary"
                size="sm"
                :loading="busyStage === stage.stage"
                @click="doComplete(stage.stage)"
              >
                Completar
              </OwnexButton>
            </div>
          </li>
        </ol>
      </OwnexCard>
    </template>
  </div>
</template>
