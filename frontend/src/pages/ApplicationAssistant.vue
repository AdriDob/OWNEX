<script setup lang="ts">
/**
 * Application Assistant — plan asistido de postulación a plataformas de ingreso.
 * Backend: core/application_assistant.py vía /api/applications/* (control.py).
 */

import { CheckCircle2, Circle, ExternalLink, Target } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'

interface PlanField {
  key: string
  label: string
  value: string
  hint?: string
}
interface PlanStep {
  step_id: string
  order?: number
  title: string
  description?: string
  fields?: PlanField[]
  done?: boolean
}
interface PlanPlatform {
  platform: string
  name: string
  url?: string
  status?: string
  priority?: number
  pay_range?: string
  notes?: string
  steps: PlanStep[]
}
interface PlanResponse {
  generated_at?: string
  platforms: PlanPlatform[] | Record<string, PlanPlatform>
}
interface OverviewNextAction {
  platform: string
  platform_name: string
  url?: string
  step: string
}
interface OverviewResponse {
  generated_at?: string
  by_status: Record<string, number>
  progress_pct: number
  next_action: OverviewNextAction | null
}

const loading = ref(true)
const error = ref<string | null>(null)
const plan = ref<PlanPlatform[]>([])
const overview = ref<OverviewResponse | null>(null)
const activePlatform = ref<string>('')
const completing = ref<string>('')

const doneSteps = computed(() => {
  const set = new Set<string>()
  for (const p of plan.value) {
    for (const s of p.steps ?? []) if (s.done) set.add(`${p.platform}:${s.step_id}`)
  }
  return set
})

const active = computed(() => plan.value.find((p) => p.platform === activePlatform.value) ?? null)

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
    const [planRes, ovRes] = await Promise.all([
      api.get<PlanResponse>('/applications/plan'),
      api.get<OverviewResponse>('/applications/overview'),
    ])
    const raw = planRes.platforms
    plan.value = Array.isArray(raw) ? raw : Object.values(raw ?? {})
    overview.value = ovRes
    if (!activePlatform.value && plan.value.length > 0) {
      activePlatform.value = overview.value?.next_action?.platform ?? plan.value[0]?.platform ?? ''
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function completeStep(platform: string, stepId: string): Promise<void> {
  completing.value = `${platform}:${stepId}`
  try {
    await api.post(`/applications/${platform}/steps/${stepId}/complete`)
    const step = plan.value.find((p) => p.platform === platform)?.steps.find((s) => s.step_id === stepId)
    if (step) step.done = true
    overview.value = await api.get<OverviewResponse>('/applications/overview')
  } catch {
    // keep silent-ish: the row stays unchecked; user can retry
  } finally {
    completing.value = ''
  }
}

async function setStatus(platform: string, status: string): Promise<void> {
  await api.post(`/applications/${platform}/status`, { status })
  const p = plan.value.find((x) => x.platform === platform)
  if (p) p.status = status
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
      <!-- Next action -->
      <Card v-if="overview?.next_action" class="border-accent/30 bg-accent/5 p-5">
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
            :key="p.platform"
            class="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface/40"
            :class="{ 'bg-primary/5': activePlatform === p.platform }"
            @click="activePlatform = p.platform"
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
              @change="setStatus(active.platform, ($event.target as HTMLSelectElement).value)"
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
              :key="s.step_id"
              class="rounded-lg border border-border/20 bg-surface/20 p-3"
              :class="{ 'opacity-60': doneSteps.has(`${active.platform}:${s.step_id}`) }"
            >
              <div class="flex items-start gap-2.5">
                <CheckCircle2 v-if="doneSteps.has(`${active.platform}:${s.step_id}`)" class="mt-0.5 h-4 w-4 shrink-0 text-success" />
                <Circle v-else class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div class="min-w-0 flex-1 space-y-1.5">
                  <p class="font-mono text-xs font-medium">{{ i + 1 }}. {{ s.title }}</p>
                  <p v-if="s.description" class="text-xs leading-relaxed text-muted-foreground">{{ s.description }}</p>
                  <dl v-if="s.fields?.length" class="grid grid-cols-1 gap-1 sm:grid-cols-2">
                    <div v-for="f in s.fields" :key="f.key" class="rounded border border-border/20 bg-background/40 px-2 py-1">
                      <dt class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{{ f.label }}</dt>
                      <dd class="truncate font-mono text-[11px]" :title="f.hint || f.value">{{ f.value }}</dd>
                    </div>
                  </dl>
                  <Button
                    v-if="!doneSteps.has(`${active.platform}:${s.step_id}`)"
                    size="sm"
                    variant="outline"
                    class="h-7 px-2 text-[11px]"
                    :disabled="completing === `${active.platform}:${s.step_id}`"
                    @click="completeStep(active.platform, s.step_id)"
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
