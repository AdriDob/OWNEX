<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import { ArrowLeft, AlertTriangle, RotateCw, Trash2, Activity, FileText, Target, Calendar } from '@lucide/vue'

interface StageProgress {
  name: string
  key: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
}

interface PipelineStageStats {
  stage: string
  count: number
}

interface Investigation {
  id: number
  name: string
  status: 'active' | 'paused' | 'completed'
  target: string
  target_id: number
  description?: string
  created_at: string
  stages: StageProgress[]
  pipeline_stats: PipelineStageStats[]
  summary?: string
}

const route = useRoute()
const router = useRouter()
const investigation = ref<Investigation | null>(null)
const loading = ref(true)
const error = ref('')
const updating = ref(false)

const stageLabels: Record<string, string> = {
  recon: 'Recon',
  hypotheses: 'Hypotheses',
  validation: 'Validation',
  evidence: 'Evidence',
  report: 'Report',
}

const stageColors: Record<string, string> = {
  pending: 'bg-muted/30',
  in_progress: 'bg-primary',
  completed: 'bg-success',
  failed: 'bg-destructive',
}

const pipelineChartLabels = computed(() => investigation.value?.pipeline_stats?.map(s => s.stage) || [])
const pipelineChartData = computed(() => investigation.value?.pipeline_stats?.map(s => s.count) || [])

const statusVariants: Record<string, 'default' | 'success' | 'warning' | 'destructive'> = {
  active: 'success',
  paused: 'warning',
  completed: 'default',
}

async function fetchInvestigation() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.id as string
    const res = await api.get<Investigation>(`/investigations/${id}`)
    investigation.value = res
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar la investigación'
    investigation.value = null
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!investigation.value || !confirm('¿Eliminar esta investigación?')) return
  updating.value = true
  try {
    await api.delete(`/investigations/${investigation.value.id}`)
    router.push('/investigations')
  } catch {
    updating.value = false
  }
}

async function changeStatus(status: 'active' | 'paused' | 'completed') {
  if (!investigation.value) return
  updating.value = true
  try {
    const res = await api.put<Investigation>(`/investigations/${investigation.value.id}`, { status })
    investigation.value = res
  } catch (e: any) {
    error.value = e?.message || 'Error al cambiar estado'
  } finally {
    updating.value = false
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('es-AR', { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(fetchInvestigation)
</script>

<template>
  <div class="space-y-6">
    <!-- Back -->
    <button @click="router.push('/investigations')" class="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
      <ArrowLeft class="h-3.5 w-3.5" />
      Volver a investigaciones
    </button>

    <!-- Loading -->
    <template v-if="loading">
      <Skeleton class="h-8 w-64 rounded-lg" />
      <Skeleton class="h-4 w-96 rounded-lg" />
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Skeleton v-for="i in 2" :key="i" class="h-40 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <!-- Error -->
    <template v-else-if="error && !investigation">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchInvestigation">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Empty / Not Found -->
    <template v-else-if="!investigation">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <FileText class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Investigación no encontrada</p>
        <p class="mt-1 text-xs text-muted-foreground">La investigación solicitada no existe o fue eliminada</p>
        <Button variant="outline" size="sm" class="mt-4" @click="router.push('/investigations')">
          Ver investigaciones
        </Button>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 animate-in">
        <div class="space-y-1">
          <p class="text-xs font-bold uppercase tracking-widest text-primary">Investigación</p>
          <h1 class="font-display text-2xl font-bold text-foreground">{{ investigation.name }}</h1>
          <div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
            <span class="flex items-center gap-1">
              <Target class="h-3 w-3" />
              {{ investigation.target }}
            </span>
            <span class="flex items-center gap-1">
              <Calendar class="h-3 w-3" />
              {{ formatDate(investigation.created_at) }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <Badge :variant="statusVariants[investigation.status] || 'default'" class="text-xs capitalize">
            {{ investigation.status }}
          </Badge>
          <div class="flex gap-1">
            <Button
              v-if="investigation.status !== 'active'"
              variant="outline" size="sm"
              :disabled="updating"
              @click="changeStatus('active')"
            >
              <Activity class="h-3 w-3" /> Activar
            </Button>
            <Button
              v-if="investigation.status === 'active'"
              variant="outline" size="sm"
              :disabled="updating"
              @click="changeStatus('paused')"
            >
              Pausar
            </Button>
            <Button
              v-if="investigation.status !== 'completed'"
              variant="outline" size="sm"
              :disabled="updating"
              @click="changeStatus('completed')"
            >
              Completar
            </Button>
            <Button variant="destructive" size="sm" :disabled="updating" @click="handleDelete">
              <Trash2 class="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      <!-- Summary -->
      <Card v-if="investigation.summary" class="p-4 animate-in">
        <p class="text-xs font-semibold text-foreground mb-1">Resumen</p>
        <p class="text-sm text-muted-foreground">{{ investigation.summary }}</p>
      </Card>

      <!-- Stage Progress -->
      <div class="animate-in">
        <p class="text-xs font-semibold text-foreground mb-3">Etapas</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <Card v-for="stage in investigation.stages" :key="stage.key" class="p-3">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-semibold text-foreground">{{ stageLabels[stage.key] || stage.name }}</span>
              <span :class="['h-2 w-2 rounded-full', stageColors[stage.status]]" />
            </div>
            <div class="h-1.5 overflow-hidden rounded-full bg-[#1a1d29]">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="stage.status === 'failed' ? 'bg-destructive' : 'bg-primary'"
                :style="{ width: `${stage.progress}%` }"
              />
            </div>
            <p class="mt-1 text-[10px] text-muted-foreground">{{ Math.round(stage.progress) }}%</p>
          </Card>
        </div>
      </div>

      <!-- Pipeline Stats & Chart -->
      <div v-if="investigation.pipeline_stats?.length" class="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-in">
        <Card class="p-4 lg:col-span-2">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Pipeline Stats</p>
          </div>
          <div class="space-y-2">
            <div v-for="stat in investigation.pipeline_stats" :key="stat.stage" class="flex items-center justify-between">
              <span class="text-xs text-muted-foreground capitalize">{{ stat.stage }}</span>
              <span class="text-xs font-semibold text-foreground">{{ stat.count }}</span>
            </div>
          </div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <FileText class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Distribución</p>
          </div>
          <DoughnutChart
            v-if="pipelineChartLabels.length"
            :labels="pipelineChartLabels"
            :data="pipelineChartData"
            :height="200"
          />
          <p v-else class="text-xs text-muted-foreground text-center py-8">Sin datos</p>
        </Card>
      </div>
    </template>
  </div>
</template>
