<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart, DoughnutChart } from '@/components/charts'
import { Activity, AlertTriangle, ArrowRight, BarChart3, Calendar, Clock, FileText, LayoutDashboard, ListChecks, RefreshCw, Target, Users, Wrench } from '@lucide/vue'

interface ProjectSummary {
  progress: number
  total_contributors: number
  total_stories: number
  completed_stories: number
  active_sprints: number
  estimated_completion: string
}

interface FeatureItem {
  id: number
  name: string
  status: string
  completion: number
  stories_count: number
  priority: string
}

interface TechDebtItem {
  id: number
  title: string
  severity: string
  effort: string
  impact: string
  area: string
  created_at: string
}

interface TimelineEntry {
  date: string
  title: string
  description: string
  type: string
}

type TabName = 'overview' | 'features' | 'tech-debt' | 'timeline'

const activeTab = ref<TabName>('overview')
const summary = ref<ProjectSummary | null>(null)
const features = ref<FeatureItem[]>([])
const techDebt = ref<TechDebtItem[]>([])
const timeline = ref<TimelineEntry[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const tabs: { key: TabName; label: string; icon: any }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'features', label: 'Features', icon: ListChecks },
  { key: 'tech-debt', label: 'Tech Debt', icon: Wrench },
  { key: 'timeline', label: 'Timeline', icon: Calendar },
]

async function fetchProjectDashboard() {
  loading.value = true
  error.value = null
  try {
    const [s, f, t, tl] = await Promise.all([
      api.get<ProjectSummary>('/project-dashboard/summary'),
      api.get<{ items: FeatureItem[] }>('/project-dashboard/feature-matrix'),
      api.get<{ items: TechDebtItem[] }>('/project-dashboard/tech-debt'),
      api.get<{ entries: TimelineEntry[] }>('/project-dashboard/timeline'),
    ])
    summary.value = s
    features.value = f.items || []
    techDebt.value = t.items || []
    timeline.value = tl.entries || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el dashboard del proyecto'
  } finally {
    loading.value = false
  }
}

onMounted(fetchProjectDashboard)

function severityBadge(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'default',
  }
  return map[sev?.toLowerCase()] || 'default'
}

function effortBadge(effort: string) {
  const map: Record<string, 'destructive' | 'warning' | 'success' | 'default'> = {
    high: 'destructive', medium: 'warning', low: 'success',
  }
  return map[effort?.toLowerCase()] || 'default'
}

const featureChartData = computed(() => {
  if (!features.value.length) return { labels: [], datasets: [] }
  return {
    labels: features.value.slice(0, 12).map(f => f.name.length > 18 ? f.name.slice(0, 16) + '…' : f.name),
    datasets: [{
      label: 'Completion %',
      data: features.value.slice(0, 12).map(f => f.completion),
      backgroundColor: '#3b82f6',
    }],
  }
})

const debtSeverityData = computed(() => {
  const counts: Record<string, number> = {}
  for (const d of techDebt.value) {
    const sev = d.severity?.toLowerCase() || 'unknown'
    counts[sev] = (counts[sev] || 0) + 1
  }
  return {
    labels: Object.keys(counts).map(s => s.charAt(0).toUpperCase() + s.slice(1)),
    data: Object.values(counts),
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Project</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Project Dashboard</h1>
      <p class="text-sm text-muted-foreground">Development progress, features, tech debt, and timeline</p>
    </div>

    <template v-if="loading">
      <div class="flex gap-2">
        <Skeleton v-for="i in 4" :key="i" class="h-9 w-28 rounded-lg" />
      </div>
      <Skeleton class="h-32 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">No se pudo cargar el dashboard</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" size="sm" @click="fetchProjectDashboard()">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </Card>
    </template>

    <template v-else>
      <div class="flex gap-1 animate-in overflow-x-auto pb-1">
        <button v-for="tab in tabs" :key="tab.key"
          @click="activeTab = tab.key"
          class="flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold transition-all"
          :class="activeTab === tab.key ? 'bg-primary/15 text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground hover:bg-surface/50'"
        >
          <component :is="tab.icon" class="h-3.5 w-3.5" />
          {{ tab.label }}
        </button>
      </div>

      <div v-if="activeTab === 'overview' && summary" class="space-y-6 animate-in">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs text-muted-foreground"><Activity class="h-3.5 w-3.5 text-primary" /> Progress</div>
            <div class="mt-2">
              <p class="text-2xl font-bold text-foreground">{{ summary.progress }}%</p>
              <div class="mt-1 h-1.5 w-full rounded-full bg-surface">
                <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${summary.progress}%` }" />
              </div>
            </div>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs text-muted-foreground"><Users class="h-3.5 w-3.5 text-accent" /> Contributors</div>
            <p class="mt-2 text-2xl font-bold text-foreground">{{ summary.total_contributors }}</p>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs text-muted-foreground"><FileText class="h-3.5 w-3.5 text-success" /> Stories</div>
            <p class="mt-2 text-2xl font-bold text-foreground">{{ summary.completed_stories }}/{{ summary.total_stories }}</p>
          </Card>
          <Card class="p-4">
            <div class="flex items-center gap-2 text-xs text-muted-foreground"><Target class="h-3.5 w-3.5 text-warning" /> Active Sprints</div>
            <p class="mt-2 text-2xl font-bold text-foreground">{{ summary.active_sprints }}</p>
          </Card>
          <Card class="p-4 lg:col-span-2">
            <div class="flex items-center gap-2 text-xs text-muted-foreground"><Clock class="h-3.5 w-3.5 text-muted-foreground" /> Est. Completion</div>
            <p class="mt-2 text-lg font-bold text-foreground">{{ summary.estimated_completion ? new Date(summary.estimated_completion).toLocaleDateString() : '—' }}</p>
          </Card>
        </div>
      </div>

      <div v-if="activeTab === 'overview' && !summary" class="animate-in">
        <div class="flex flex-col items-center py-16 text-center">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface/50 mb-3">
            <LayoutDashboard class="h-6 w-6 text-muted-foreground/50" />
          </div>
          <p class="text-sm text-muted-foreground">No hay datos de resumen disponibles</p>
        </div>
      </div>

      <div v-if="activeTab === 'features'" class="space-y-4 animate-in">
        <div v-if="features.length === 0" class="flex flex-col items-center py-16 text-center">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface/50 mb-3">
            <ListChecks class="h-6 w-6 text-muted-foreground/50" />
          </div>
          <p class="text-sm text-muted-foreground">No hay features registradas</p>
        </div>

        <Card v-if="featureChartData.labels.length" class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Feature Completion</p>
          </div>
          <BarChart
            :labels="featureChartData.labels"
            :datasets="featureChartData.datasets"
            :height="220"
            :horizontal="true"
            :showLegend="false"
            xLabel="Completion %"
            yLabel="Feature"
          />
        </Card>

        <div v-if="features.length" class="space-y-2">
          <div v-for="f in features" :key="f.id" class="rounded-xl border border-border/40 bg-[#11131f]/40 px-4 py-3 transition-all hover:border-primary/30">
            <div class="flex items-center justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-foreground">{{ f.name }}</span>
                  <Badge :variant="f.status === 'completed' ? 'success' : f.status === 'in_progress' ? 'info' : 'default'" class="text-[10px] px-1.5 py-0 capitalize">{{ f.status?.replace(/_/g, ' ') }}</Badge>
                  <Badge :variant="f.priority === 'critical' ? 'destructive' : f.priority === 'high' ? 'warning' : 'default'" class="text-[10px] px-1.5 py-0">{{ f.priority }}</Badge>
                </div>
                <p class="mt-1 text-xs text-muted-foreground">{{ f.stories_count }} stories</p>
              </div>
              <div class="flex items-center gap-3">
                <div class="w-24">
                  <div class="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                    <span>{{ f.completion }}%</span>
                  </div>
                  <div class="h-1.5 w-full rounded-full bg-surface">
                    <div class="h-full rounded-full bg-primary transition-all" :style="{ width: `${f.completion}%` }" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'tech-debt'" class="space-y-4 animate-in">
        <div v-if="techDebt.length === 0" class="flex flex-col items-center py-16 text-center">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface/50 mb-3">
            <Wrench class="h-6 w-6 text-muted-foreground/50" />
          </div>
          <p class="text-sm text-muted-foreground">No hay deuda técnica registrada</p>
        </div>

        <div v-if="debtSeverityData.labels.length" class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card class="p-4">
            <div class="flex items-center gap-2 mb-3">
              <Wrench class="h-4 w-4 text-warning" />
              <p class="text-xs font-semibold text-foreground">Tech Debt by Severity</p>
            </div>
            <DoughnutChart
              :labels="debtSeverityData.labels"
              :data="debtSeverityData.data"
              :height="220"
            />
          </Card>
          <div class="space-y-2">
            <div v-for="d in techDebt" :key="d.id" class="rounded-xl border border-border/40 bg-[#11131f]/40 px-4 py-3">
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold text-foreground">{{ d.title }}</span>
                    <Badge :variant="severityBadge(d.severity)" class="text-[10px] px-1.5 py-0">{{ d.severity }}</Badge>
                  </div>
                  <p class="text-[10px] text-muted-foreground mt-0.5">{{ d.area }}</p>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <Badge :variant="effortBadge(d.effort)" class="text-[10px] px-1.5 py-0">Effort: {{ d.effort }}</Badge>
                  <Badge :variant="d.impact === 'high' ? 'destructive' : d.impact === 'medium' ? 'warning' : 'default'" class="text-[10px] px-1.5 py-0">Impact: {{ d.impact }}</Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'timeline'" class="space-y-4 animate-in">
        <div v-if="timeline.length === 0" class="flex flex-col items-center py-16 text-center">
          <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface/50 mb-3">
            <Calendar class="h-6 w-6 text-muted-foreground/50" />
          </div>
          <p class="text-sm text-muted-foreground">No hay entradas en la línea de tiempo</p>
        </div>

        <div v-else class="space-y-3">
          <div v-for="(entry, i) in timeline" :key="i" class="relative pl-6 pb-3 border-l border-border/40 last:pb-0 last:border-l-0">
            <div class="absolute left-0 top-1 -translate-x-1/2 flex h-4 w-4 items-center justify-center">
              <div class="h-2 w-2 rounded-full"
                :class="entry.type === 'milestone' ? 'bg-primary' : entry.type === 'release' ? 'bg-success' : entry.type === 'task' ? 'bg-accent' : 'bg-muted-foreground/40'"
              />
            </div>
            <div class="rounded-lg bg-surface/20 p-3">
              <div class="flex items-center gap-2 text-xs">
                <span class="font-semibold text-foreground">{{ entry.title }}</span>
                <span class="text-muted-foreground">{{ new Date(entry.date).toLocaleDateString() }}</span>
                <Badge variant="outline" class="text-[9px] px-1.5 py-0 capitalize">{{ entry.type }}</Badge>
              </div>
              <p v-if="entry.description" class="mt-1 text-xs text-muted-foreground">{{ entry.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
