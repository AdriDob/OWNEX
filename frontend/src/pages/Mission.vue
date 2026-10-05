<script setup lang="ts">
/**
 * Mission — tarjeta de misión mensual + niveles + workspaces (L7+L9).
 * Backend: /mission-hub/* (overview, target, workspaces activate/deactivate).
 * Una sola llamada para la tarjeta; el resto es lectura + toggles humanos.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import {
  fetchEconomicTrajectory,
  fetchHunterOverview,
  setHunterTarget,
  setWorkspaceActive,
  type EconomicTrajectory,
  type HubWorkspace,
  type HunterOverview,
} from '@/services/ownexData'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const overview = ref<HunterOverview | null>(null)
const targetInput = ref('5000')
const busyTarget = ref(false)
const busyWorkspace = ref<string | null>(null)
const traj = ref<EconomicTrajectory | null>(null)
const trajError = ref('')

const usd2 = (n: number | null | undefined): string =>
  n == null ? '—' : `$${n.toLocaleString('es-AR', { maximumFractionDigits: 0 })}`
const perHour = (n: number | null | undefined): string =>
  n == null ? 'UNKNOWN' : `$${n.toLocaleString('es-AR', { maximumFractionDigits: 0 })}/h`

const usd = (n: number | null | undefined): string => (n != null ? `$${Math.round(n).toLocaleString('es-AR')}` : '—')

const roleVariant = (role: string): 'success' | 'warning' | 'error' | 'default' => {
  if (role === 'primary') return 'success'
  if (role === 'upside') return 'warning'
  if (role === 'capital_only' || role === 'last_resort') return 'error'
  return 'default'
}

const roleLabel = (role: string): string => {
  const labels: Record<string, string> = {
    primary: 'Renta base',
    upside: 'Opcional',
    core: 'Núcleo',
    capital_only: 'Solo capital',
    last_resort: 'Último recurso',
  }
  return labels[role] ?? role
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    overview.value = await fetchHunterOverview()
    targetInput.value = String(Math.round(overview.value.target_usd))
    await loadTrajectory()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando Mission Hub'
  } finally {
    loading.value = false
  }
}

async function loadTrajectory(): Promise<void> {
  trajError.value = ''
  try {
    traj.value = await fetchEconomicTrajectory()
  } catch (e: unknown) {
    trajError.value = e instanceof Error ? e.message : 'Error cargando trayectoria'
  }
}

async function doSetTarget(): Promise<void> {
  const amount = Number(targetInput.value)
  if (!Number.isFinite(amount) || amount <= 0) return
  busyTarget.value = true
  try {
    await setHunterTarget(amount)
    await load()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo guardar el objetivo'
  } finally {
    busyTarget.value = false
  }
}

async function doToggleWorkspace(ws: HubWorkspace): Promise<void> {
  busyWorkspace.value = ws.id
  try {
    await setWorkspaceActive(ws.id, !ws.active)
    await load()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo cambiar el workspace'
  } finally {
    busyWorkspace.value = null
  }
}

function goToWorkQueue(): void {
  void router.push('/operations/work-queue')
}

function goToNextAction(): void {
  const url = overview.value?.next_action?.url
  if (url && url.startsWith('/')) {
    void router.push(url)
  } else {
    void router.push('/operations/work-queue')
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Mission Hub">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">Mission</h1>
        <p class="text-sm opacity-70">$X este mes: objetivo, niveles y workspaces en una vista.</p>
      </div>
      <div class="ml-auto flex gap-2">
        <OwnexButton variant="secondary" size="sm" @click="goToWorkQueue">Cola de trabajo</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando misión..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="overview">
      <!-- Mission card -->
      <OwnexCard class="mb-4" variant="highlight">
        <div class="mb-3 flex flex-wrap items-center gap-3">
          <div class="flex-1">
            <div class="text-xs uppercase opacity-60">Misión {{ overview.mission.month }}</div>
            <div class="flex items-baseline gap-2">
              <div class="text-2xl font-bold">{{ usd(overview.mission.target_usd) }}</div>
              <OwnexBadge :variant="overview.mission.is_met ? 'success' : 'default'">
                {{ overview.mission.is_met ? 'Cumplida' : `${overview.mission.progress_pct}%` }}
              </OwnexBadge>
            </div>
            <div class="text-sm opacity-70">
              Ganado {{ usd(overview.mission.earned_usd) }} · Faltan {{ usd(overview.mission.gap_usd) }}
            </div>
          </div>
          <ProgressBar :value="overview.mission.progress_pct" color="primary" size="md" show-label class="w-48" />
        </div>
        <div class="mb-3 flex flex-wrap items-end gap-2">
          <label class="flex flex-col gap-1 text-sm">
            Objetivo mensual (USD)
            <input
              v-model="targetInput"
              type="number"
              min="1"
              step="100"
              class="rounded border border-border bg-background px-2 py-1"
            />
          </label>
          <OwnexButton variant="primary" size="sm" :loading="busyTarget" @click="doSetTarget">
            Guardar
          </OwnexButton>
        </div>
        <p class="text-xs opacity-50">{{ overview.mission.disclaimer }}</p>
      </OwnexCard>

      <!-- Levels + next action -->
      <div class="mb-4 grid gap-4 md:grid-cols-2">
        <OwnexCard>
          <div class="text-xs uppercase opacity-60">Nivel hunter</div>
          <div class="flex items-baseline gap-2">
            <div class="text-xl font-bold">Nv. {{ overview.levels.level }} · {{ overview.levels.title }}</div>
          </div>
          <div class="text-sm opacity-70">{{ overview.levels.total_xp }} XP totales</div>
          <ProgressBar :value="overview.levels.pct_to_next" color="primary" size="sm" show-label class="mt-2" />
          <div v-if="Object.keys(overview.levels.events).length > 0" class="mt-2 flex flex-wrap gap-1">
            <OwnexBadge v-for="(count, event) in overview.levels.events" :key="event" size="xs" variant="default">
              {{ event }} ×{{ count }}
            </OwnexBadge>
          </div>
          <EmptyState
            v-else
            title="Sin XP todavía"
            description="El XP llega solo de resultados verificados, nunca de vistas."
          />
        </OwnexCard>
        <OwnexCard variant="highlight">
          <div class="text-xs uppercase opacity-60">Próxima acción</div>
          <div class="text-lg font-semibold">{{ overview.next_action.title }}</div>
          <div v-if="overview.next_action.why" class="mt-1 text-sm opacity-70">
            {{ overview.next_action.why }}
          </div>
          <div class="mt-2 flex flex-wrap gap-1">
            <OwnexBadge v-if="overview.next_action.est_minutes != null" size="xs" variant="default">
              ~{{ overview.next_action.est_minutes }} min
            </OwnexBadge>
            <OwnexBadge v-if="overview.next_action.life_goal" size="xs" variant="success">
              {{ overview.next_action.life_goal }}
            </OwnexBadge>
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <OwnexButton variant="primary" size="sm" @click="goToNextAction">
              Hacer ahora
            </OwnexButton>
            <OwnexButton variant="secondary" size="sm" @click="goToWorkQueue">
              Ir a la cola
            </OwnexButton>
          </div>
          <div v-if="overview.next_action.endpoint" class="mt-1 text-xs opacity-50">
            {{ overview.next_action.endpoint }}
          </div>
        </OwnexCard>
      </div>

      <!-- Economics: neto/hora-humana (métrica reina, UNKNOWN honesto) -->
      <OwnexCard v-if="overview.money_loop" class="mb-4" data-test="money-loop">
        <div class="text-xs uppercase opacity-60 mb-2">Embudo de ingreso</div>
        <div class="flex flex-wrap items-baseline gap-4">
          <div>
            <div class="text-xs uppercase opacity-60">PAID</div>
            <div class="text-xl font-bold" data-test="money-loop-paid">
              {{ overview.money_loop.funnel.paid }}
            </div>
          </div>
          <div>
            <div class="text-xs uppercase opacity-60">Neto / hora</div>
            <div class="text-xl font-bold" data-test="money-loop-perhour">
              {{
                overview.money_loop.funnel.net_per_hour != null
                  ? `$${overview.money_loop.funnel.net_per_hour}/h`
                  : 'UNKNOWN'
              }}
            </div>
          </div>
          <div>
            <div class="text-xs uppercase opacity-60">Estado</div>
            <div class="text-sm font-mono" data-test="money-loop-state">
              {{ overview.money_loop.funnel.state }}
            </div>
          </div>
          <div v-if="overview.money_loop.pending_validations.total">
            <div class="text-xs uppercase opacity-60">Pendientes de revisión</div>
            <div class="text-xl font-bold">{{ overview.money_loop.pending_validations.total }}</div>
          </div>
        </div>
      </OwnexCard>

      <OwnexCard v-if="overview.economics" class="mb-4">
        <div class="flex flex-wrap items-baseline gap-4">
          <div>
            <div class="text-xs uppercase opacity-60">Neto / hora humana</div>
            <div class="text-xl font-bold">
              {{
                overview.economics.money_per_human_hour != null
                  ? `$${overview.economics.money_per_human_hour}/h`
                  : 'Sin datos todavía'
              }}
            </div>
          </div>
          <div>
            <div class="text-xs uppercase opacity-60">Cobrado</div>
            <div class="text-lg font-semibold">{{ usd(overview.economics.paid_usd) }}</div>
          </div>
          <div>
            <div class="text-xs uppercase opacity-60">En pipeline</div>
            <div class="text-lg font-semibold">{{ usd(overview.economics.pipeline_usd) }}</div>
          </div>
          <div v-if="overview.economics.automation_ratio != null">
            <div class="text-xs uppercase opacity-60">Automatización</div>
            <div class="text-lg font-semibold">{{ Math.round(overview.economics.automation_ratio * 100) }}%</div>
          </div>
        </div>
      </OwnexCard>

      <!-- Workspaces -->
      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Workspaces</h2>        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border opacity-50">
                <th class="pb-1 text-left">Workspace</th>
                <th class="pb-1 text-left">Rol</th>
                <th class="pb-1 text-left">Política</th>
                <th class="pb-1 text-left">Estado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ws in overview.workspaces" :key="ws.id" class="border-b border-border/40">
                <td class="py-2">
                  <div class="font-medium">{{ ws.name }}</div>
                  <div class="text-xs opacity-60">{{ ws.goals[0] ?? '' }}</div>
                </td>
                <td class="py-2">
                  <OwnexBadge :variant="roleVariant(ws.role)" size="xs">{{ roleLabel(ws.role) }}</OwnexBadge>
                </td>
                <td class="max-w-64 py-2 text-xs opacity-70">{{ ws.policy }}</td>
                <td class="py-2">
                  <OwnexButton
                    variant="secondary"
                    size="xs"
                    :loading="busyWorkspace === ws.id"
                    @click="doToggleWorkspace(ws)"
                  >
                    {{ ws.active ? 'Pausar' : 'Activar' }}
                  </OwnexButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </OwnexCard>

      <!-- APP FACTORY: NEXA vs FOCUS (solo si el backend lo trae) -->
      <OwnexCard v-if="overview.factory && Object.keys(overview.factory).length" class="mt-4">
        <h2 class="mb-3 text-base font-semibold">App Factory — validación</h2>
        <div class="grid gap-3 md:grid-cols-2">
          <div
            v-for="(f, id) in overview.factory"
            :key="id"
            class="rounded border border-border p-3"
          >
            <div class="mb-1 flex items-center gap-2">
              <span class="font-semibold uppercase">{{ id }}</span>
              <OwnexBadge size="xs" :variant="f.verdict === 'SIGNAL' ? 'success' : 'default'">
                {{ f.verdict }}
              </OwnexBadge>
              <span class="ml-auto text-sm font-bold">
                {{ f.demand_score != null ? `${f.demand_score}` : '—' }}
              </span>
            </div>
            <div class="text-xs opacity-70">
              {{ f.views }} visitas · {{ f.plans }} planes · {{ f.saves }} saves · {{ f.emails }} emails
            </div>
          </div>
        </div>
        <p class="mt-2 text-xs opacity-50">
          Demand Score = hipótesis experimental (25% demo + 20% creación + 20% save + 15% retorno + 20% pago).
          Nada acá es previsión.
        </p>
      </OwnexCard>
    </template>

    <!-- ECONOMIC TRAJECTORY — REAL / PIPELINE / SCENARIO (nunca mezclados) -->
    <OwnexCard class="mt-4">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <h2 class="text-base font-semibold">Economic Trajectory</h2>
        <OwnexBadge v-if="traj" size="xs" variant="default">
         NIVEL {{ traj.calibration.level }} · {{ traj.calibration.label }}
        </OwnexBadge>
        <OwnexBadge v-if="traj" size="xs" variant="default">
          {{ traj.available_hours_per_week }} h/sem disponibles
        </OwnexBadge>
      </div>

      <ErrorState v-if="trajError" :message="trajError" @retry="loadTrajectory" />
      <LoadingState v-else-if="!traj" message="Cargando trayectoria..." />

      <template v-else>
        <!-- REAL: solo paid/net -->
        <div class="mb-3 rounded border border-border p-3">
          <div class="mb-2 text-xs uppercase opacity-60">Real (caja cobrada)</div>
          <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div>
              <div class="text-xs opacity-60">Cobrado 12m</div>
              <div class="text-lg font-bold">{{ usd2(traj.real.d365.realized_cash) }}</div>
            </div>
            <div>
              <div class="text-xs opacity-60">$/hora real</div>
              <div class="text-lg font-bold">{{ perHour(traj.real.net_cash_per_hour) }}</div>
            </div>
            <div>
              <div class="text-xs opacity-60">90d</div>
              <div class="text-sm">{{ usd2(traj.real.d90.realized_cash) }} · {{ traj.real.d90.paid_outcomes }} PAID</div>
            </div>
            <div>
              <div class="text-xs opacity-60">180d</div>
              <div class="text-sm">{{ usd2(traj.real.d180.realized_cash) }} · {{ traj.real.d180.paid_outcomes }} PAID</div>
            </div>
          </div>
          <p class="mt-2 text-xs opacity-50">{{ traj.calibration.note }}</p>
        </div>

        <!-- PIPELINE: submitted/accepted/awarded, NO cash -->
        <div class="mb-3 rounded border border-border p-3">
          <div class="mb-2 text-xs uppercase opacity-60">Pipeline (verificable, no es caja)</div>
          <div class="text-sm">
            {{ usd2(traj.pipeline.pipeline_value) }} en submitted/accepted/awarded ·
            {{ traj.pipeline.accepted_outcomes }} aceptados
          </div>
        </div>

        <!-- SPECULATIVE: potencial/expected, excluido explícitamente -->
        <div class="mb-3 rounded border border-border p-3">
          <div class="mb-2 text-xs uppercase opacity-60">Especulativo (no cuenta como caja)</div>
          <div class="text-sm">
            {{ usd2(traj.speculative.value) }} en potential/expected
            <OwnexBadge size="xs" variant="warning">EXCLUIDO</OwnexBadge>
          </div>
        </div>

        <!-- SCENARIO: planificación, no forecast -->
        <div class="mb-3 rounded border border-border p-3">
          <div class="mb-2 flex items-center gap-2 text-xs uppercase opacity-60">
            Escenarios
            <OwnexBadge size="xs" variant="warning">{{ traj.scenarios.label }}</OwnexBadge>
          </div>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <div v-for="(bands, tier) in traj.scenarios.horizons" :key="tier">
              <div class="font-semibold uppercase">{{ tier }}</div>
              <div class="opacity-70">m1-3: {{ usd2(bands.m1_3?.[0]) }}–{{ usd2(bands.m1_3?.[1]) }}</div>
              <div class="opacity-70">m1-6: {{ usd2(bands.m1_6?.[0]) }}–{{ usd2(bands.m1_6?.[1]) }}</div>
              <div class="opacity-70">m7-12: {{ usd2(bands.m7_12?.[0]) }}–{{ usd2(bands.m7_12?.[1]) }}</div>
            </div>
          </div>
        </div>

        <!-- CANALES: qué funciona y qué no -->
        <div v-if="traj.channels.some((c) => c.attempts > 0)">
          <div class="mb-2 text-xs uppercase opacity-60">Canales (cash solo de paid)</div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-border opacity-50">
                  <th class="pb-1 text-left">Canal</th>
                  <th class="pb-1 text-right">Intentos</th>
                  <th class="pb-1 text-right">Aceptados</th>
                  <th class="pb-1 text-right">PAID</th>
                  <th class="pb-1 text-right">Cash</th>
                  <th class="pb-1 text-left">Validación</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in traj.channels.filter((x) => x.attempts > 0)"
                  :key="c.channel"
                  class="border-b border-border/40"
                >
                  <td class="py-1">{{ c.channel }}</td>
                  <td class="py-1 text-right">{{ c.attempts }}</td>
                  <td class="py-1 text-right">{{ c.accepted }}</td>
                  <td class="py-1 text-right">{{ c.paid }}</td>
                  <td class="py-1 text-right">{{ usd2(c.cash) }}</td>
                  <td class="py-1 text-xs opacity-70">{{ c.validation }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </OwnexCard>
  </div>
</template>
