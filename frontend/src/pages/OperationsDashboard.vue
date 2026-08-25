<script setup lang="ts">
import {
  Activity,
  AlertTriangle,
  BarChart3,
  ChevronRight,
  Clock,
  HeartPulse,
  LayoutDashboard,
  ListOrdered,
  RefreshCw,
  Shield,
  Star,
  Target,
  TrendingUp,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import type { TimelineResponse } from '@/lib/api'
import { api, getTimeline } from '@/lib/api'

/** Compuesto client-side desde endpoints reales (stats/overview/verdicts/timeline).
 *  El /operations/metrics original nunca existió en el backend. */
interface SystemMetrics {
  /** findings confirmados / total findings */
  quick_win_rate: number | null
  avg_confidence: number | null
  total_active: number
  total_completed: number
  confidence_distribution: { range: string; count: number }[]
  daily_activity: { date: string; events: number }[]
}

interface HealthStatus {
  status: string
  health_score: number
  uptime_hours: number
  details: string[]
}

interface TimelineEvent {
  event_type: string
  timestamp: string
  description: string
  source: string
  target_name?: string
  confidence?: number
}

const loading = ref(true)
const error = ref('')
const activeTab = ref<'overview' | 'timeline' | 'metrics'>('overview')

const timeline = ref<TimelineEvent[]>([])
const metrics = ref<SystemMetrics | null>(null)
const health = ref<HealthStatus | null>(null)
interface FavoriteItem {
  id: string | number
  label: string
  route?: string
}
const favorites = ref<FavoriteItem[]>([])

const timelineLabels = computed(() => {
  const counts: Record<string, number> = {}
  timeline.value.forEach((e) => {
    const hour = e.timestamp?.slice(11, 13) || '00'
    counts[`${hour}:00`] = (counts[`${hour}:00`] || 0) + 1
  })
  return Object.keys(counts).sort()
})

const timelineData = computed(() => {
  const counts: Record<string, number> = {}
  timeline.value.forEach((e) => {
    const hour = e.timestamp?.slice(11, 13) || '00'
    counts[`${hour}:00`] = (counts[`${hour}:00`] || 0) + 1
  })
  return timelineLabels.value.map((h) => counts[h] || 0)
})

const healthColor = computed(() => {
  if (!health.value) return 'text-muted-foreground'
  if (health.value.health_score >= 80) return 'text-success'
  if (health.value.health_score >= 50) return 'text-warning'
  return 'text-destructive'
})

const eventTypeIcon: Record<string, string> = {
  scan: 'text-primary',
  finding: 'text-intigriti',
  report: 'text-warning',
  system: 'text-success',
  error: 'text-destructive',
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [tlRes, statsRes, ovRes, vdRes, hlRes] = await Promise.allSettled([
      getTimeline({ limit: 48 }),
      api.get<{ targets: number; findings: number; verdicts: number; scan_runs: number }>('/stats'),
      api.get<{ active_scans: number; confirmed: number; avg_risk_score: number }>('/overview'),
      api.get<Array<{ confidence: number }>>('/verdicts?limit=500'),
      api.get<HealthStatus>('/system/health'),
    ])
    if (tlRes.status === 'fulfilled') timeline.value = tlRes.value.events || []
    if (hlRes.status === 'fulfilled') health.value = hlRes.value

    // Composición honesta desde datos reales:
    const stats = statsRes.status === 'fulfilled' ? statsRes.value : null
    const ov = ovRes.status === 'fulfilled' ? ovRes.value : null
    const verdicts = vdRes.status === 'fulfilled' ? vdRes.value : []

    const totalFindings = stats?.findings ?? 0
    const confirmed = ov?.confirmed ?? 0
    const avgConf =
      verdicts.length > 0 ? verdicts.reduce((acc, v) => acc + (v.confidence || 0), 0) / verdicts.length : null

    // daily_activity: agregación por día del timeline ya cargado
    const byDay = new Map<string, number>()
    for (const ev of timeline.value) {
      const day = (ev.timestamp || '').slice(0, 10)
      if (day) byDay.set(day, (byDay.get(day) ?? 0) + 1)
    }
    const daily_activity = [...byDay.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, events]) => ({ date, events }))

    // confidence_distribution: buckets 0.2
    const buckets = [0, 0, 0, 0, 0]
    for (const v of verdicts) {
      const idx = Math.min(4, Math.max(0, Math.floor((v.confidence || 0) * 5)))
      buckets[idx]++
    }
    const confidence_distribution = buckets.map((count, i) => ({
      range: `${i * 20}-${(i + 1) * 20}%`,
      count,
    }))

    metrics.value = {
      quick_win_rate: totalFindings > 0 ? confirmed / totalFindings : null,
      avg_confidence: avgConf,
      total_active: ov?.active_scans ?? 0,
      total_completed: stats?.scan_runs ?? 0,
      confidence_distribution,
      daily_activity,
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load operations data'
  } finally {
    loading.value = false
  }
}

function typeIconClass(type: string) {
  return eventTypeIcon[type] || eventTypeIcon.system
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3"><Skeleton v-for="i in 3" :key="i" class="h-24 rounded-xl" /></div>
        <Skeleton class="h-64 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error loading operations data</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadData">
          <RefreshCw class="h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="animate-in space-y-1">
        <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Operations</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Operations Dashboard</h1>
        <p class="text-xs text-muted-foreground">Command center for system activity, health, and operational metrics</p>
      </div>

      <div class="grid gap-4 sm:grid-cols-3 animate-in">
        <Card class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[10px] text-muted-foreground">System Health</p>
              <p class="text-2xl font-bold" :class="healthColor">{{ health?.health_score ?? '—' }}<span class="text-sm text-muted-foreground">/100</span></p>
            </div>
            <HeartPulse class="h-8 w-8 text-muted-foreground/30" />
          </div>
          <p class="mt-1 text-[10px] text-muted-foreground">{{ health?.status || 'Unknown' }} · {{ health?.uptime_hours ?? 0 }}h uptime</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[10px] text-muted-foreground">Quick-Win Rate</p>
              <p class="text-2xl font-bold text-success">{{ metrics?.quick_win_rate != null ? (metrics.quick_win_rate * 100).toFixed(0) : '—' }}<span class="text-sm text-muted-foreground">%</span></p>
            </div>
            <Zap class="h-8 w-8 text-muted-foreground/30" />
          </div>
          <p class="mt-1 text-[10px] text-muted-foreground">{{ metrics?.total_active ?? 0 }} active · {{ metrics?.total_completed ?? 0 }} completed</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[10px] text-muted-foreground">Avg Confidence</p>
              <p class="text-2xl font-bold text-primary">{{ metrics?.avg_confidence != null ? (metrics.avg_confidence * 100).toFixed(0) : '—' }}<span class="text-sm text-muted-foreground">%</span></p>
            </div>
            <TrendingUp class="h-8 w-8 text-muted-foreground/30" />
          </div>
          <p class="mt-1 text-[10px] text-muted-foreground">Across all active operations</p>
        </Card>
      </div>

      <div class="flex gap-1 border-b border-border/30 animate-in">
        <button
          v-for="tab in (['overview', 'timeline', 'metrics'] as const)" :key="tab"
          @click="activeTab = tab"
          :class="[
            'px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px',
            activeTab === tab ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
          ]"
        >
          {{ tab.charAt(0).toUpperCase() + tab.slice(1) }}
        </button>
      </div>

      <template v-if="activeTab === 'overview'">
        <div class="grid gap-6 lg:grid-cols-2 animate-in">
          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Activity class="h-3.5 w-3.5 text-primary" />
              24h Timeline Activity
            </h3>
            <LineChart
              v-if="timelineLabels.length > 0"
              :labels="timelineLabels"
              :datasets="[{ label: 'Events', data: timelineData, borderColor: '#00d5ff', fill: true }]"
              :height="200"
              :show-legend="false"
              :area="true"
              y-label="Events"
              x-label="Hour"
            />
            <div v-else class="py-8 text-center text-[10px] text-muted-foreground">
              No timeline data available
            </div>
          </Card>

          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <BarChart3 class="h-3.5 w-3.5 text-primary" />
              Confidence Distribution
            </h3>
            <BarChart
              v-if="metrics?.confidence_distribution?.length"
              :labels="metrics.confidence_distribution.map(d => d.range)"
              :datasets="[{ label: 'Count', data: metrics.confidence_distribution.map(d => d.count) }]"
              :height="200"
              :show-legend="false"
              y-label="Count"
              x-label="Confidence Range"
            />
            <div v-else class="py-8 text-center text-[10px] text-muted-foreground">
              No metrics data available
            </div>
          </Card>
        </div>

        <div class="grid gap-6 lg:grid-cols-3 animate-in">
          <Card class="p-4 lg:col-span-2 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <ListOrdered class="h-3.5 w-3.5 text-primary" />
              Recent Timeline Events
            </h3>
            <div v-if="timeline.length === 0" class="py-8 text-center text-[10px] text-muted-foreground">
              <Clock class="mx-auto h-6 w-6 text-muted-foreground/50" />
              <p class="mt-2">No events in the last 24 hours</p>
            </div>
            <div v-else class="space-y-1 max-h-80 overflow-y-auto">
              <div
                v-for="(ev, i) in timeline.slice(0, 20)" :key="i"
                class="flex items-start gap-3 rounded-lg px-3 py-2 hover:bg-surface/10 transition-colors"
              >
                <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface/50">
                  <Activity :class="['h-3 w-3', typeIconClass(ev.event_type)]" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-foreground truncate">{{ ev.description }}</p>
                  <p class="text-[9px] text-muted-foreground">
                    {{ ev.event_type }} · {{ ev.source }}
                    <span v-if="ev.target_name"> · {{ ev.target_name }}</span>
                  </p>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-[9px] text-muted-foreground">{{ ev.timestamp?.slice(11, 19) || '' }}</p>
                  <Badge v-if="ev.confidence != null" variant="default" class="text-[8px]">
                    {{ (ev.confidence * 100).toFixed(0) }}%
                  </Badge>
                </div>
              </div>
            </div>
          </Card>

          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Star class="h-3.5 w-3.5 text-primary" />
              Favorites
            </h3>
            <div v-if="favorites.length === 0" class="py-8 text-center text-[10px] text-muted-foreground">
              <Star class="mx-auto h-6 w-6 text-muted-foreground/50" />
              <p class="mt-2">No favorites yet</p>
              <p class="text-[9px]">Pin your frequently used items here</p>
            </div>
            <div v-else class="space-y-1">
              <div v-for="(fav, i) in favorites" :key="i" class="rounded-lg px-3 py-2 hover:bg-surface/10 transition-colors cursor-pointer">
                <p class="text-xs text-foreground">{{ fav.name }}</p>
                <p class="text-[9px] text-muted-foreground">{{ fav.type }}</p>
              </div>
            </div>
          </Card>
        </div>
      </template>

      <template v-else-if="activeTab === 'timeline'">
        <Card class="p-4 animate-in space-y-3">
          <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <Activity class="h-3.5 w-3.5 text-primary" />
            Unified Timeline (24h)
          </h3>
          <LineChart
            v-if="timelineLabels.length > 0"
            :labels="timelineLabels"
            :datasets="[{ label: 'Events', data: timelineData, borderColor: '#00d5ff', fill: true, tension: 0.4 }]"
            :height="200"
            :show-legend="false"
            :area="true"
            y-label="Event Count"
            x-label="Hour"
          />
          <div v-if="timeline.length === 0" class="py-8 text-center text-[10px] text-muted-foreground">
            <Clock class="mx-auto h-6 w-6 text-muted-foreground/50" />
            <p class="mt-2">No events in the last 24 hours</p>
          </div>
          <div v-else class="space-y-1 divide-y divide-border/20">
            <div
              v-for="(ev, i) in timeline" :key="i"
              class="flex items-start gap-3 px-3 py-2.5 hover:bg-surface/10 transition-colors"
            >
              <div class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface/50">
                <Activity :class="['h-3 w-3', typeIconClass(ev.event_type)]" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs text-foreground">{{ ev.description }}</p>
                <p class="text-[9px] text-muted-foreground flex items-center gap-2">
                  <Badge variant="outline" class="text-[8px]">{{ ev.event_type }}</Badge>
                  {{ ev.source }}
                  <span v-if="ev.target_name">· {{ ev.target_name }}</span>
                </p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-[9px] text-muted-foreground">{{ ev.timestamp?.slice(11, 19) || '' }}</p>
                <p class="text-[8px] text-muted-foreground">{{ ev.timestamp?.slice(0, 10) || '' }}</p>
              </div>
            </div>
          </div>
        </Card>
      </template>

      <template v-else-if="activeTab === 'metrics'">
        <div class="grid gap-6 lg:grid-cols-2 animate-in">
          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <BarChart3 class="h-3.5 w-3.5 text-primary" />
              Quick-Win Conversion
            </h3>
            <BarChart
              v-if="metrics"
              :labels="['Quick-Win Rate', 'Avg Confidence']"
              :datasets="[{
                label: 'Score',
                data: [
                  metrics.quick_win_rate != null ? metrics.quick_win_rate * 100 : 0,
                  metrics.avg_confidence != null ? metrics.avg_confidence * 100 : 0,
                ],
              }]"
              :height="200"
              y-label="Percentage"
            />
          </Card>

          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Target class="h-3.5 w-3.5 text-primary" />
              Active vs Completed
            </h3>
            <BarChart
              v-if="metrics"
              :labels="['Active', 'Completed']"
              :datasets="[{
                label: 'Operations',
                data: [metrics.total_active || 0, metrics.total_completed || 0],
              }]"
              :height="200"
              y-label="Count"
            />
          </Card>

          <Card class="p-4 space-y-3 lg:col-span-2">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Shield class="h-3.5 w-3.5 text-primary" />
              System Health Details
            </h3>
            <div v-if="health?.details?.length" class="space-y-1">
              <div v-for="(detail, i) in health.details" :key="i" class="flex items-center gap-2 text-xs text-muted-foreground">
                <div class="h-1.5 w-1.5 rounded-full" :class="detail.includes('error') || detail.includes('fail') ? 'bg-destructive' : 'bg-success'" />
                {{ detail }}
              </div>
            </div>
            <div v-else class="text-[10px] text-muted-foreground">No health details available</div>
          </Card>
        </div>
      </template>
    </template>
  </div>
</template>
