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
  fetchHunterOverview,
  setHunterTarget,
  setWorkspaceActive,
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
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando Mission Hub'
  } finally {
    loading.value = false
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
          <div class="text-lg font-semibold">{{ overview.next_action }}</div>
          <OwnexButton variant="primary" size="sm" class="mt-2" @click="goToWorkQueue">
            Ir a la cola
          </OwnexButton>
        </OwnexCard>
      </div>

      <!-- Workspaces -->
      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Workspaces</h2>
        <div class="overflow-x-auto">
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
    </template>
  </div>
</template>
