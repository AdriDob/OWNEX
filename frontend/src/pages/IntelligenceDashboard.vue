<script setup lang="ts">
import { Activity, BarChart3, Brain, Lightbulb, PieChart, Target, TrendingUp } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { BarChart, DoughnutChart, LineChart } from '@/components/charts'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

const history = ref<any>(null)
const trends = ref<any[]>([])
const recommendations = ref<any>(null)
const state = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const [hRes, tRes, rRes, sRes] = await Promise.allSettled([
      api.get('/intelligence/history'),
      api.get<{ trends: any[] }>('/intelligence/trends'),
      api.get('/intelligence/recommendations'),
      api.get('/intelligence/state'),
    ])
    if (hRes.status === 'fulfilled') history.value = hRes.value
    if (tRes.status === 'fulfilled') trends.value = tRes.value.trends || []
    if (rRes.status === 'fulfilled') recommendations.value = rRes.value
    if (sRes.status === 'fulfilled') state.value = sRes.value
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Intelligence</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Adaptive Intelligence</h1>
      <p class="text-sm text-muted-foreground">Historical trends · Emerging surfaces · Best performing targets</p>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-2 gap-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else>
      <!-- Summary charts row -->
      <div v-if="trends.length" class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <PieChart class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Trend Direction</p>
          </div>
          <DoughnutChart
            :labels="['Up', 'Down', 'Stable']"
            :data="[
              trends.filter(t => t.direction === 'up').length,
              trends.filter(t => t.direction === 'down').length,
              trends.filter(t => t.direction !== 'up' && t.direction !== 'down').length,
            ]"
            :height="200"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Trend Magnitudes</p>
          </div>
          <BarChart
            :labels="trends.slice(0, 8).map(t => t.name.length > 14 ? t.name.slice(0, 12) + '…' : t.name)"
            :datasets="[{ label: 'Magnitude', data: trends.slice(0, 8).map(t => t.magnitude || 0), backgroundColor: '#9CA3AF' }]"
            :horizontal="true"
            :height="220"
            xLabel="Magnitude"
            yLabel="Trend"
            :showLegend="false"
          />
        </Card>
      </div>

      <div v-if="state" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 animate-in">
        <Card class="p-4 border-accent/30">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Patterns Learned</p>
          <p class="text-2xl font-bold text-accent mt-1">{{ state.total_patterns_learned }}</p>
        </Card>
        <Card class="p-4 border-success/30">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Recommendations</p>
          <p class="text-2xl font-bold text-success mt-1">{{ state.total_recommendations_generated }}</p>
        </Card>
        <Card class="p-4 border-primary/30">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Snapshots</p>
          <p class="text-2xl font-bold text-primary mt-1">{{ state.total_snapshots_created }}</p>
        </Card>
        <Card class="p-4 border-warning/30">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Analysis Time</p>
          <p class="text-2xl font-bold text-warning mt-1">
            {{ state.total_analysis_time_ms > 1000 ? (state.total_analysis_time_ms / 1000).toFixed(1) + 's' : state.total_analysis_time_ms.toFixed(0) + 'ms' }}
          </p>
        </Card>
        <Card v-if="state.last_analysis" class="p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Last Analysis</p>
          <p class="text-sm font-semibold text-foreground mt-1">{{ new Date(state.last_analysis).toLocaleDateString() }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <TrendingUp class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Historical Trends</p>
          </div>
          <div v-if="trends.length === 0" class="py-6 text-center text-xs text-muted-foreground">No trend data available yet</div>
          <div v-else class="space-y-2">
            <div v-for="(t, i) in trends" :key="i" class="rounded-lg bg-surface/50 border border-border/40 p-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-semibold text-foreground">{{ t.name }}</span>
                <Badge :variant="t.direction === 'up' ? 'success' : t.direction === 'down' ? 'destructive' : 'warning'" class="text-[10px]">{{ t.direction }}</Badge>
              </div>
              <p class="text-[11px] text-muted-foreground">{{ t.description }}</p>
              <p v-if="t.magnitude !== undefined" class="text-[10px] text-muted-foreground mt-1">
                Magnitude: <strong class="text-foreground">{{ t.magnitude.toFixed(2) }}</strong>
              </p>
            </div>
          </div>
        </Card>

        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Target class="h-4 w-4 text-success" />
            <p class="text-xs font-semibold text-foreground">Top Recommendations</p>
          </div>
          <div v-if="!recommendations" class="py-6 text-center text-xs text-muted-foreground">No recommendations generated yet</div>
          <div v-else class="space-y-2">
            <div v-for="(r, i) in (recommendations.targets || []).slice(0, 3)" :key="'t-'+i" class="rounded-lg bg-surface/50 border border-border/40 p-3">
              <p class="text-xs font-semibold text-foreground">🎯 {{ r.name }}</p>
              <p class="text-[11px] text-muted-foreground mt-0.5">{{ r.reason }}</p>
            </div>
            <div v-for="(r, i) in (recommendations.surfaces || []).slice(0, 3)" :key="'s-'+i" class="rounded-lg bg-surface/50 border border-border/40 p-3">
              <p class="text-xs font-semibold text-foreground">🔍 {{ r.surface }}</p>
              <p class="text-[11px] text-muted-foreground mt-0.5">{{ r.reason }}</p>
            </div>
            <div v-for="(r, i) in (recommendations.quick_wins || []).slice(0, 3)" :key="'q-'+i" class="rounded-lg bg-surface/50 border border-border/40 p-3">
              <p class="text-xs font-semibold text-foreground">⚡ {{ r.endpoint }}</p>
              <p class="text-[11px] text-muted-foreground mt-0.5">{{ r.reason }}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Lightbulb class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Intelligence History</p>
        </div>
        <div v-if="history" class="text-xs text-muted-foreground space-y-2">
          <p v-if="history.summary" class="leading-relaxed">{{ history.summary }}</p>
          <div class="flex flex-wrap gap-2">
            <Badge v-if="history.total_targets !== undefined">{{ history.total_targets }} targets</Badge>
            <Badge v-if="history.total_endpoints !== undefined">{{ history.total_endpoints }} endpoints</Badge>
            <Badge v-if="history.total_findings !== undefined">{{ history.total_findings }} findings</Badge>
            <Badge v-if="history.total_patterns !== undefined">{{ history.total_patterns }} patterns</Badge>
          </div>
          <p v-if="history.generated_at" class="text-[10px] text-muted-foreground/60">
            Generated: {{ new Date(history.generated_at).toLocaleString() }}
          </p>
        </div>
      </Card>
    </template>
  </div>
</template>
