<script setup lang="ts">
/**
 * Platform Onboarding — guías Zero-to-Earning por plataforma (Steps 0-11).
 * Backend: /platform-guides/* (guías, pasos, first-opportunity, mapping).
 * Conecta con First Money: seleccionar plataforma inicia la etapa correspondiente.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EmptyState from '@/components/ui/EmptyState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import Tabs from '@/components/ui/Tabs.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import {
  fetchPlatformFirstOpportunity,
  fetchPlatformGuideSteps,
  fetchPlatformGuides,
  startFirstMoneyStage,
  type PlatformFirstOpportunity,
  type PlatformGuideStep,
} from '@/services/ownexData'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const platforms = ref<string[]>([])
const selected = ref<string>('')
const guideType = ref<'account' | 'work'>('account')
const steps = ref<PlatformGuideStep[]>([])
const platformName = ref('')
const platformUrl = ref('')
const tips = ref<string[]>([])
const commonErrors = ref<Array<{ error: string; solution: string }>>([])
const firstOpp = ref<PlatformFirstOpportunity['recommendation'] | null>(null)
const stepsLoading = ref(false)
const starting = ref(false)
const startedMsg = ref<string | null>(null)

const tabOptions = [
  { id: 'account', label: 'Crear cuenta' },
  { id: 'work', label: 'Primer trabajo' },
]

const currentTab = computed({
  get: () => guideType.value,
  set: (v: string) => {
    guideType.value = v === 'work' ? 'work' : 'account'
    void loadSteps()
  },
})

async function loadPlatforms(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const data = await fetchPlatformGuides()
    platforms.value = data.platforms
    const fromRoute = typeof route.params.platform === 'string' ? route.params.platform : ''
    selected.value = fromRoute && data.platforms.includes(fromRoute) ? fromRoute : (data.platforms[0] ?? '')
    if (selected.value) await loadSteps()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function loadSteps(): Promise<void> {
  if (!selected.value) return
  stepsLoading.value = true
  startedMsg.value = null
  try {
    const [detail, opp] = await Promise.all([
      fetchPlatformGuideSteps(selected.value, guideType.value),
      fetchPlatformFirstOpportunity(selected.value).catch(() => null),
    ])
    steps.value = detail.steps
    platformName.value = detail.name
    platformUrl.value = detail.url
    tips.value = detail.tips
    commonErrors.value = detail.common_errors
    firstOpp.value = opp?.recommendation ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    stepsLoading.value = false
  }
}

async function useInFirstMoney(): Promise<void> {
  if (!selected.value) return
  starting.value = true
  try {
    await startFirstMoneyStage('platform_selected', selected.value)
    startedMsg.value = `Plataforma ${selected.value} registrada en First Money.`
  } catch (e) {
    console.error('start first-money stage failed', e)
  } finally {
    starting.value = false
  }
}

function goToFirstMoney(): void {
  void router.push('/operations/first-money')
}

function openPlatform(): void {
  if (platformUrl.value) window.open(platformUrl.value, '_blank', 'noopener')
}

watch(selected, () => {
  void loadSteps()
})

onMounted(() => {
  void loadPlatforms()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Platform Onboarding">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">Guías de plataforma</h1>
        <p class="text-sm opacity-70">De "nunca usé esta plataforma" a primera operación real, paso a paso.</p>
      </div>
      <div class="ml-auto flex gap-2">
        <OwnexButton variant="secondary" size="sm" @click="goToFirstMoney">First Money</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando plataformas..." />
    <ErrorState v-else-if="error" :message="error" @retry="loadPlatforms" />
    <template v-else>
      <OwnexCard class="mb-4">
        <div class="flex flex-wrap items-center gap-2">
          <label class="text-sm opacity-70" for="platform-select">Plataforma</label>
          <select
            id="platform-select"
            v-model="selected"
            class="rounded border border-border bg-background px-2 py-1 text-sm capitalize"
          >
            <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
          </select>
          <OwnexButton v-if="platformUrl" variant="secondary" size="sm" @click="openPlatform">
            Abrir {{ platformName || selected }}
          </OwnexButton>
          <OwnexButton variant="primary" size="sm" :loading="starting" @click="useInFirstMoney">
            Usar en First Money
          </OwnexButton>
        </div>
        <p v-if="startedMsg" class="mt-2 text-sm text-green-500">{{ startedMsg }}</p>
      </OwnexCard>

      <Tabs v-model="currentTab" :tabs="tabOptions" class="mb-4" />

      <LoadingState v-if="stepsLoading" message="Cargando guía..." />
      <template v-else>
        <EmptyState
          v-if="steps.length === 0"
          title="Sin pasos"
          description="No hay guía disponible para esta plataforma."
        />
        <ol v-else class="mb-4 flex flex-col gap-2">
          <li
            v-for="step in steps"
            :key="step.index"
            class="flex gap-3 rounded border border-border/60 px-3 py-2"
          >
            <OwnexBadge variant="default">{{ step.index }}</OwnexBadge>
            <div class="flex-1">
              <div class="text-sm font-semibold">{{ step.title }}</div>
              <div class="text-sm opacity-80">{{ step.description }}</div>
              <div class="mt-1 flex flex-wrap gap-2 text-xs opacity-70">
                <span>Acción: <code>{{ step.action }}</code></span>
                <span v-if="step.value">Valor: <code>{{ step.value }}</code></span>
                <span v-if="step.screenshot_hint">Hint: {{ step.screenshot_hint }}</span>
              </div>
            </div>
          </li>
        </ol>

        <div class="grid gap-4 md:grid-cols-2">
          <OwnexCard v-if="firstOpp">
            <h2 class="mb-1 text-base font-semibold">Primera oportunidad recomendada</h2>
            <div class="text-sm font-semibold">{{ firstOpp.title }}</div>
            <p class="text-sm opacity-80">{{ firstOpp.description }}</p>
            <p class="mt-1 text-sm"><strong>Por qué:</strong> {{ firstOpp.why }}</p>
            <p class="text-sm opacity-70">Tiempo estimado: {{ firstOpp.estimated_time }}</p>
            <p class="text-sm"><strong>Siguiente acción:</strong> {{ firstOpp.next_action }}</p>
          </OwnexCard>

          <OwnexCard>
            <h2 class="mb-1 text-base font-semibold">Consejos</h2>
            <ul class="list-disc pl-5 text-sm opacity-80">
              <li v-for="(tip, i) in tips" :key="i">{{ tip }}</li>
            </ul>
            <h3 class="mb-1 mt-3 text-sm font-semibold">Errores comunes</h3>
            <ul class="flex flex-col gap-1 text-sm">
              <li v-for="(ce, i) in commonErrors" :key="i">
                <strong>{{ ce.error }}:</strong> <span class="opacity-80">{{ ce.solution }}</span>
              </li>
            </ul>
          </OwnexCard>
        </div>
      </template>
    </template>
  </div>
</template>
