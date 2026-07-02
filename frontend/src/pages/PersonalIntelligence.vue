<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { LineChart } from '@/components/charts'
import { Brain, RefreshCw, Download, ToggleLeft, ToggleRight, AlertTriangle, FileJson, FileText, History, Activity, Target } from '@lucide/vue'

interface LearningProfile {
  exists: boolean
  adaptive_mode: boolean
  total_sessions: number
  total_findings: number
  total_reports: number
  avg_confidence: number
  learning_progress: { date: string; score: number }[]
  strengths: string[]
  weaknesses: string[]
  created_at: string
  updated_at: string
}

interface LearningEvent {
  id: number
  event_type: string
  description: string
  timestamp: string
  metadata?: Record<string, any>
}

const profile = ref<LearningProfile | null>(null)
const events = ref<LearningEvent[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const toggling = ref(false)
const resetting = ref(false)
const exporting = ref(false)
const exportingFormat = ref<'json' | 'markdown'>('json')

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [p, e] = await Promise.all([
      api.get<LearningProfile>('/system/learning/profile'),
      api.get<{ events: LearningEvent[] }>('/system/learning/events'),
    ])
    profile.value = p
    events.value = e.events || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar perfil de aprendizaje'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)

async function toggleAdaptiveMode() {
  if (!profile.value) return
  toggling.value = true
  try {
    const updated = await api.post<LearningProfile>('/system/learning/profile/reset')
    profile.value = updated
    await fetchData()
  } catch { /* ignore */ }
  finally { toggling.value = false }
}

async function resetProfile() {
  if (!confirm('¿Estás seguro de resetear tu perfil de aprendizaje? Se perderán todos los datos.')) return
  resetting.value = true
  try {
    await api.post('/system/learning/profile/reset')
    await fetchData()
  } catch { /* ignore */ }
  finally { resetting.value = false }
}

async function exportProfile(format: 'json' | 'markdown') {
  exporting.value = true
  exportingFormat.value = format
  try {
    const data = await api.post<any>('/system/learning/profile/export', { format })
    const blob = new Blob(
      [format === 'json' ? JSON.stringify(data, null, 2) : data],
      { type: format === 'json' ? 'application/json' : 'text/markdown' },
    )
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `learning-profile.${format}`
    a.click()
    URL.revokeObjectURL(url)
  } catch { /* ignore */ }
  finally { exporting.value = false }
}

const progressChartData = computed(() => {
  if (!profile.value?.learning_progress?.length) return { labels: [], datasets: [] }
  const sorted = [...profile.value.learning_progress].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  )
  return {
    labels: sorted.map(d => new Date(d.date).toLocaleDateString()),
    datasets: [{
      label: 'Learning Score',
      data: sorted.map(d => d.score),
      borderColor: '#7c3aed',
      backgroundColor: '#7c3aed',
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }],
  }
})

function eventIcon(type: string) {
  if (type.includes('finding')) return 'finding'
  if (type.includes('report')) return 'report'
  if (type.includes('scan')) return 'scan'
  if (type.includes('analysis')) return 'analysis'
  return 'default'
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Learning</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Personal Intelligence</h1>
      <p class="text-sm text-muted-foreground">Adaptive learning profile and progress tracking</p>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-32 rounded-xl" />
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">No se pudo cargar el perfil</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" size="sm" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </Card>
    </template>

    <template v-else-if="!profile?.exists">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Brain class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay perfil de aprendizaje todavía</p>
        <p class="mt-1 text-xs text-muted-foreground">El sistema generará un perfil automáticamente con el uso</p>
      </div>
    </template>

    <template v-else>
      <div class="flex items-center justify-between animate-in">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Brain class="h-5 w-5" />
          </div>
          <div>
            <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Adaptive Mode</p>
            <div class="flex items-center gap-2 mt-0.5">
              <Badge :variant="profile.adaptive_mode ? 'success' : 'default'" class="text-[10px]">
                {{ profile.adaptive_mode ? 'Activado' : 'Desactivado' }}
              </Badge>
              <Button size="sm" variant="ghost" :disabled="toggling" @click="toggleAdaptiveMode">
                <component :is="profile.adaptive_mode ? ToggleRight : ToggleLeft" class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <Button size="sm" variant="outline" :disabled="exporting" @click="exportProfile('json')">
            <FileJson v-if="exportingFormat !== 'json' || !exporting" class="h-3.5 w-3.5" />
            <span v-else class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            JSON
          </Button>
          <Button size="sm" variant="outline" :disabled="exporting" @click="exportProfile('markdown')">
            <FileText v-if="exportingFormat !== 'markdown' || !exporting" class="h-3.5 w-3.5" />
            <span v-else class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            MD
          </Button>
          <Button size="sm" variant="destructive" :disabled="resetting" @click="resetProfile">
            <RefreshCw v-if="!resetting" class="h-3.5 w-3.5" />
            <span v-else class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Reset
          </Button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 animate-in">
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Sessions</p>
          <p class="text-2xl font-bold text-foreground mt-1">{{ profile.total_sessions }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Findings</p>
          <p class="text-2xl font-bold text-foreground mt-1">{{ profile.total_findings }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Reports</p>
          <p class="text-2xl font-bold text-foreground mt-1">{{ profile.total_reports }}</p>
        </Card>
        <Card class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Avg Confidence</p>
          <p class="text-2xl font-bold text-accent mt-1">{{ (profile.avg_confidence * 100).toFixed(1) }}%</p>
        </Card>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Activity class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Learning Progress Over Time</p>
        </div>
        <div v-if="progressChartData.labels.length" style="height: 220px">
          <LineChart
            :labels="progressChartData.labels"
            :datasets="progressChartData.datasets"
            :height="220"
            :showLegend="false"
            yLabel="Score"
            :area="true"
          />
        </div>
        <div v-else class="py-8 text-center text-xs text-muted-foreground">
          No hay datos de progreso todavía
        </div>
      </Card>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <p class="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Target class="h-3.5 w-3.5 text-success" /> Strengths
          </p>
          <div v-if="profile.strengths.length" class="flex flex-wrap gap-2">
            <Badge v-for="(s, i) in profile.strengths" :key="i" variant="success">{{ s }}</Badge>
          </div>
          <p v-else class="text-xs text-muted-foreground">Aún no se han identificado fortalezas</p>
        </Card>
        <Card class="p-4">
          <p class="text-xs font-semibold text-foreground mb-3 flex items-center gap-2">
            <Target class="h-3.5 w-3.5 text-warning" /> Areas to Improve
          </p>
          <div v-if="profile.weaknesses.length" class="flex flex-wrap gap-2">
            <Badge v-for="(w, i) in profile.weaknesses" :key="i" variant="warning">{{ w }}</Badge>
          </div>
          <p v-else class="text-xs text-muted-foreground">Aún no se han identificado áreas de mejora</p>
        </Card>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <History class="h-4 w-4 text-muted-foreground" />
          <p class="text-xs font-semibold text-foreground">Learning Events Timeline</p>
        </div>
        <div v-if="events.length" class="space-y-2">
          <div v-for="ev in events.slice(0, 20)" :key="ev.id" class="flex items-start gap-3 rounded-lg bg-surface/20 p-3">
            <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
              :class="eventIcon(ev.event_type) === 'finding' ? 'bg-destructive/15 text-destructive' : eventIcon(ev.event_type) === 'report' ? 'bg-success/15 text-success' : eventIcon(ev.event_type) === 'scan' ? 'bg-accent/15 text-accent' : 'bg-primary/15 text-primary'"
            >
              <Activity class="h-3.5 w-3.5" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-foreground capitalize">{{ ev.event_type.replace(/_/g, ' ') }}</span>
                <span class="text-[10px] text-muted-foreground">{{ new Date(ev.timestamp).toLocaleString() }}</span>
              </div>
              <p class="text-xs text-muted-foreground mt-0.5">{{ ev.description }}</p>
            </div>
          </div>
        </div>
        <div v-else class="py-6 text-center text-xs text-muted-foreground">
          No hay eventos de aprendizaje registrados
        </div>
      </Card>
    </template>
  </div>
</template>
