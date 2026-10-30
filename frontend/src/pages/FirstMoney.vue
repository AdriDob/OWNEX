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
  fetchEvolutionLearning,
  fetchFirstMoneyNextAction,
  fetchFirstMoneyProgress,
  fetchFreelanceChannels,
  recordFirstRevenue,
  setFreelanceChannel,
  startFirstMoneyStage,
  type EvolutionCalibration,
  type FirstMoneyNextAction,
  type FirstMoneyProgress,
  type FirstMoneyStageStatus,
  type FreelanceChannelInfo,
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
    const [p, n, c] = await Promise.all([
      fetchFirstMoneyProgress(),
      fetchFirstMoneyNextAction(),
      fetchFreelanceChannels().catch(() => ({ channels: {}, note: '' })),
    ])
    progress.value = p
    nextAction.value = n
    channels.value = c.channels ?? {}
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

function goToWorkQueue(): void {
  void router.push('/operations/work-queue')
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
