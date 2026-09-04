<script setup lang="ts">
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Globe,
  ListChecks,
  Play,
  RefreshCw,
  Route,
  Search,
  SkipBack,
  SkipForward,
  StepBack,
  StepForward,
  Target,
  TrendingUp,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import LineChart from '@/components/charts/LineChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface ReplayTarget {
  id: number
  name: string
  domain: string
  steps_completed: number
  total_steps: number
  last_replayed?: string
}

/** ScanRun real (GET /scans/runs) — fuente de replay disponible. */
interface ScanRunEntry {
  id: number
  target_id: number
  mode: string
  status: string
  endpoint_count: number
  started_at: string | null
  finished_at: string | null
}

interface ReplayStep {
  stage: string
  label: string
  description: string
  status: 'pending' | 'active' | 'completed' | 'skipped'
  completed_at?: string
  data?: Record<string, unknown>
}

/** Detalle real de GET /scans/runs/{id} */
interface ScanRunDetail {
  id: number
  target_id: number
  mode: string
  status: string
  endpoint_count: number
  outputs: string | null
  started_at: string | null
  finished_at: string | null
}

interface ReplayTimeline {
  target_id: number
  target_name: string
  current_step: number
  total_steps: number
  steps: ReplayStep[]
}

type IconComponent = typeof Search
const stageIcons: Record<string, IconComponent> = {
  recon: Search,
  endpoints: Globe,
  hot_paths: Route,
  evidence: Camera,
  verdicts: CheckCircle2,
  findings: FileText,
  reports: FileText,
}

const stageColors: Record<string, string> = {
  recon: 'text-primary',
  endpoints: 'text-success',
  hot_paths: 'text-warning',
  evidence: 'text-intigriti',
  verdicts: 'text-warning',
  findings: 'text-destructive',
  reports: 'text-muted-foreground',
}

const stageOrder = ['recon', 'endpoints', 'hot_paths', 'evidence', 'verdicts', 'findings', 'reports']

const loading = ref(true)
const error = ref('')
const targets = ref<ReplayTarget[]>([])
const selectedTargetId = ref<number | null>(null)
const timeline = ref<ReplayTimeline | null>(null)
const timelineLoading = ref(false)
const timelineError = ref('')
const currentStepIndex = ref(0)

const currentStep = computed(() => {
  if (!timeline.value) return null
  return timeline.value.steps[currentStepIndex.value] || null
})

const timelineLabels = computed(() => {
  if (!timeline.value) return []
  return timeline.value.steps.map((s) => s.label)
})

const timelineData = computed(() => {
  if (!timeline.value) return []
  return timeline.value.steps.map((_s, idx) => (idx <= currentStepIndex.value ? 1 : 0))
})

const progressPercent = computed(() => {
  if (!timeline.value || timeline.value.total_steps === 0) return 0
  return ((currentStepIndex.value + 1) / timeline.value.total_steps) * 100
})

function stageIcon(stage: string) {
  return stageIcons[stage] || Search
}

function stageColor(stage: string) {
  return stageColors[stage] || 'text-muted-foreground'
}

async function loadTargets() {
  loading.value = true
  error.value = ''
  try {
    // Fuente real: GET /scans/runs (ScanRun). Cada run es un replay disponible.
    const runs = await api.get<ScanRunEntry[]>('/scans/runs', { limit: 50 })
    targets.value = (Array.isArray(runs) ? runs : []).map((r) => ({
      id: r.id,
      name: `Scan #${r.id} · target ${r.target_id} (${r.mode})`,
      domain: r.status,
      steps_completed: r.status === 'completed' ? 1 : r.status === 'failed' || r.status === 'timeout' ? 0 : 0,
      total_steps: 1,
      last_replayed: r.started_at ?? undefined,
    }))
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load replay targets'
  } finally {
    loading.value = false
  }
}

async function selectTarget(targetId: number) {
  selectedTargetId.value = targetId
  currentStepIndex.value = 0
  timelineLoading.value = true
  timelineError.value = ''
  timeline.value = null
  try {
    // Detalle real del run: GET /scans/runs/{id} → outputs + timestamps.
    const res = await api.get<ScanRunDetail>(`/scans/runs/${targetId}`)
    const outputs = (res?.outputs as string) || ''
    timeline.value = {
      target_id: targetId,
      target_name: `Scan #${targetId} (${res?.mode ?? 'n/a'})`,
      current_step: 0,
      total_steps: 1,
      steps: [
        {
          stage: 'scan',
          label: 'Ejecución del scan',
          description: outputs ? outputs.slice(0, 400) : 'Sin salida registrada para este run.',
          status: res?.status === 'completed' ? 'completed' : res?.status === 'failed' ? 'skipped' : 'pending',
          completed_at: res?.finished_at ?? undefined,
          data: res as Record<string, unknown>,
        },
      ],
    }
    currentStepIndex.value = 0
  } catch (e: unknown) {
    timelineError.value = e instanceof Error ? e.message : 'Failed to load replay timeline'
  } finally {
    timelineLoading.value = false
  }
}

function goToStep(index: number) {
  if (!timeline.value) return
  currentStepIndex.value = Math.max(0, Math.min(index, timeline.value.steps.length - 1))
}

function previousStep() {
  goToStep(currentStepIndex.value - 1)
}

function nextStep() {
  goToStep(currentStepIndex.value + 1)
}

function targetProgress(target: ReplayTarget) {
  if (target.total_steps === 0) return 0
  return (target.steps_completed / target.total_steps) * 100
}

onMounted(loadTargets)
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3"><Skeleton v-for="i in 3" :key="i" class="h-20 rounded-xl" /></div>
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error loading replay data</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadTargets">
          <RefreshCw class="h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="animate-in space-y-1">
        <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Investigation</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Replay Center</h1>
        <p class="text-xs text-muted-foreground">Step through investigation timelines chronologically</p>
      </div>

      <div v-if="targets.length === 0 && !selectedTargetId" class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Play class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No replay targets available</p>
        <p class="mt-1 text-xs text-muted-foreground">Complete investigations to see replay timelines</p>
      </div>

      <template v-else>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-in">
          <div
            v-for="target in targets" :key="target.id"
            @click="selectTarget(target.id)"
            :class="[
              'cursor-pointer rounded-xl border p-4 transition-all',
              selectedTargetId === target.id
                ? 'border-primary bg-primary/5 ring-1 ring-primary/30'
                : 'border-border/40 bg-surface/30 hover:border-primary/30'
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Target class="h-4 w-4 text-primary" />
                <p class="text-sm font-semibold text-foreground">{{ target.name }}</p>
              </div>
              <Badge variant="outline" class="text-[8px]">
                {{ target.steps_completed }}/{{ target.total_steps }}
              </Badge>
            </div>
            <p class="mt-1 text-[10px] text-muted-foreground">{{ target.domain }}</p>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-surface">
              <div
                class="h-full rounded-full bg-gradient-to-r from-primary to-primary/70 transition-all"
                :style="{ width: `${targetProgress(target)}%` }"
              />
            </div>
            <p v-if="target.last_replayed" class="mt-1 text-[8px] text-muted-foreground">
              Last replayed: {{ target.last_replayed.slice(0, 10) }}
            </p>
          </div>
        </div>

        <template v-if="selectedTargetId">
          <div v-if="timelineLoading" class="space-y-4 animate-in">
            <Skeleton class="h-8 w-48" />
            <Skeleton class="h-48 rounded-xl" />
            <Skeleton class="h-24 rounded-xl" />
          </div>

          <div v-else-if="timelineError" class="flex flex-col items-center py-10 text-center animate-in">
            <AlertTriangle class="h-6 w-6 text-destructive" />
            <p class="mt-2 text-xs text-muted-foreground">{{ timelineError }}</p>
            <Button variant="outline" size="sm" class="mt-3" @click="selectTarget(selectedTargetId)">
              <RefreshCw class="h-3 w-3" /> Retry
            </Button>
          </div>

          <template v-else-if="timeline">
            <Card class="p-4 animate-in space-y-4">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
                  <TrendingUp class="h-3.5 w-3.5 text-primary" />
                  Timeline Progression · {{ timeline.target_name }}
                </h3>
                <span class="text-[10px] text-muted-foreground">
                  Step {{ currentStepIndex + 1 }} / {{ timeline.total_steps }}
                </span>
              </div>

              <LineChart
                :labels="timelineLabels"
                :datasets="[{
                  label: 'Progress',
                  data: timelineData,
                  borderColor: 'var(--ownex-accent)',
                  backgroundColor: 'var(--ownex-accent)30',
                  fill: true,
                  pointRadius: 4,
                  tension: 0.2,
                }]"
                :height="150"
                :show-legend="false"
                y-label="Stage"
              />

              <div class="h-1.5 overflow-hidden rounded-full bg-surface">
                <div
                  class="h-full rounded-full bg-gradient-to-r from-primary to-primary/70 transition-all duration-500"
                  :style="{ width: `${progressPercent}%` }"
                />
              </div>

              <div class="flex items-center justify-center gap-3">
                <Button variant="outline" size="sm" :disabled="currentStepIndex === 0" @click="goToStep(0)">
                  <SkipBack class="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="sm" :disabled="currentStepIndex === 0" @click="previousStep">
                  <ChevronLeft class="h-3.5 w-3.5" />
                </Button>
                <span class="text-[10px] text-muted-foreground min-w-[60px] text-center">
                  {{ currentStep?.label || '—' }}
                </span>
                <Button variant="outline" size="sm" :disabled="currentStepIndex >= timeline.steps.length - 1" @click="nextStep">
                  <ChevronRight class="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="sm" :disabled="currentStepIndex >= timeline.steps.length - 1" @click="goToStep(timeline.steps.length - 1)">
                  <SkipForward class="h-3.5 w-3.5" />
                </Button>
              </div>
            </Card>

            <div class="grid gap-6 lg:grid-cols-3 animate-in">
              <div class="lg:col-span-2 space-y-3">
                <Card class="p-4" v-if="currentStep">
                  <div class="flex items-start gap-3">
                    <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface/50">
                      <component :is="stageIcon(currentStep.stage)" :class="['h-5 w-5', stageColor(currentStep.stage)]" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <p class="text-sm font-semibold text-foreground">{{ currentStep.label }}</p>
                        <Badge :variant="currentStep.status === 'completed' ? 'success' : currentStep.status === 'active' ? 'info' : 'default'" class="text-[8px]">
                          {{ currentStep.status }}
                        </Badge>
                      </div>
                      <p class="mt-1 text-xs text-muted-foreground">{{ currentStep.description }}</p>
                      <p v-if="currentStep.completed_at" class="mt-1 text-[9px] text-muted-foreground">
                        Completed: {{ currentStep.completed_at.slice(0, 16).replace('T', ' ') }}
                      </p>
                      <div v-if="currentStep.data && Object.keys(currentStep.data).length" class="mt-3 rounded-lg bg-surface/20 p-3 space-y-1">
                        <p class="text-[9px] font-semibold text-foreground uppercase tracking-wider">Step Data</p>
                        <pre class="text-[9px] text-muted-foreground whitespace-pre-wrap font-mono">{{ JSON.stringify(currentStep.data, null, 2) }}</pre>
                      </div>
                    </div>
                  </div>
                </Card>

                <Card class="p-4">
                  <div class="flex items-center justify-between mb-3">
                    <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
                      <ListChecks class="h-3.5 w-3.5 text-primary" />
                      All Stages
                    </h3>
                  </div>
                  <div class="space-y-1">
                    <div
                      v-for="(step, i) in timeline.steps" :key="i"
                      @click="goToStep(i)"
                      :class="[
                        'flex items-center gap-3 rounded-lg px-3 py-2.5 cursor-pointer transition-all',
                        i === currentStepIndex
                          ? 'bg-primary/10 ring-1 ring-primary/30'
                          : 'hover:bg-surface/10'
                      ]"
                    >
                      <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface/40">
                        <component :is="stageIcon(step.stage)" :class="['h-3.5 w-3.5', stageColor(step.stage)]" />
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="text-xs font-medium text-foreground">{{ step.label }}</p>
                        <p class="text-[9px] text-muted-foreground truncate">{{ step.description }}</p>
                      </div>
                      <Badge
                        :variant="step.status === 'completed' ? 'success' : step.status === 'active' ? 'info' : 'default'"
                        class="text-[8px]"
                      >
                        {{ step.status }}
                      </Badge>
                    </div>
                  </div>
                </Card>
              </div>

              <div class="space-y-3">
                <Card class="p-4 space-y-3">
                  <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
                    <Target class="h-3.5 w-3.5 text-primary" />
                    Investigation Info
                  </h3>
                  <div>
                    <p class="text-[9px] text-muted-foreground">Target</p>
                    <p class="text-sm font-semibold text-foreground">{{ timeline.target_name }}</p>
                  </div>
                  <div>
                    <p class="text-[9px] text-muted-foreground">Progress</p>
                    <p class="text-sm font-semibold text-foreground">{{ currentStepIndex + 1 }} / {{ timeline.total_steps }} steps</p>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-surface">
                    <div
                      class="h-full rounded-full bg-gradient-to-r from-primary to-primary/70 transition-all"
                      :style="{ width: `${progressPercent}%` }"
                    />
                  </div>
                </Card>

                <Card class="p-4">
                  <div class="flex items-center justify-between mb-3">
                    <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
                      <Globe class="h-3.5 w-3.5 text-primary" />
                      Switch Target
                    </h3>
                  </div>
                  <div class="space-y-1 max-h-60 overflow-y-auto">
                    <button
                      v-for="target in targets" :key="target.id"
                      @click="selectTarget(target.id)"
                      :class="[
                        'w-full text-left rounded-lg px-3 py-2 transition-colors',
                        selectedTargetId === target.id ? 'bg-primary/10' : 'hover:bg-surface/10'
                      ]"
                    >
                      <p class="text-xs font-medium text-foreground">{{ target.name }}</p>
                      <p class="text-[9px] text-muted-foreground">{{ target.steps_completed }}/{{ target.total_steps }} steps</p>
                    </button>
                  </div>
                </Card>
              </div>
            </div>
          </template>
        </template>
      </template>
    </template>
  </div>
</template>
