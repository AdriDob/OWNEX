<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import { GitCompare, AlertTriangle, RotateCw, TrendingUp, Crosshair, Layers, Activity, Shield } from '@lucide/vue'

interface AnalysisFinding {
  id: string
  title: string
  risk_level: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  description: string
  confidence: number
  novelty: number
  roi: number
  endpoint: string
  target: string
}

interface AnalysisSection {
  id: string
  title: string
  icon: string
  findings: AnalysisFinding[]
}

interface DifferentialData {
  sections: AnalysisSection[]
  summary: {
    total_findings: number
    critical_count: number
    high_count: number
    medium_count: number
    categories: Record<string, number>
  }
}

const data = ref<DifferentialData | null>(null)
const loading = ref(true)
const error = ref('')

const sectionIcons: Record<string, any> = {
  'New & Changed Endpoints': Activity,
  'Target Diffs': GitCompare,
  'Historical Changes': TrendingUp,
  'Cross-Target Patterns': Crosshair,
  'Interesting Anomalies': Shield,
}

function sectionIcon(title: string) {
  return sectionIcons[title] || Activity
}

const riskDistributionLabels = computed(() => ['Critical', 'High', 'Medium', 'Low', 'Info'])
const riskDistributionData = computed(() => {
  if (!data.value) return [0, 0, 0, 0, 0]
  const s = data.value.summary
  return [s.critical_count, s.high_count, s.medium_count, 0, 0]
})

const categoryLabels = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value.summary.categories)
})
const categoryData = computed(() => {
  if (!data.value) return []
  return Object.values(data.value.summary.categories)
})

function riskVariant(level: string): 'destructive' | 'warning' | 'info' | 'success' | 'default' {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive',
    high: 'warning',
    medium: 'info',
    low: 'success',
    info: 'default',
  }
  return map[level] || 'default'
}

function scoreColor(score: number) {
  if (score >= 0.7) return 'bg-success'
  if (score >= 0.4) return 'bg-warning'
  return 'bg-destructive'
}

async function fetchAnalysis() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<DifferentialData>('/differential-intelligence/analysis')
    data.value = res
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el análisis diferencial'
  } finally {
    loading.value = false
  }
}

onMounted(fetchAnalysis)
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Análisis</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Differential Engine</h1>
      <p class="text-sm text-muted-foreground">
        {{ data ? `${data.summary.total_findings} hallazgos diferenciales` : 'Análisis de cambios y patrones' }}
      </p>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 3" :key="i" class="h-32 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <!-- Error -->
    <template v-else-if="error && !data">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchAnalysis">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Empty -->
    <template v-else-if="!data || !data.sections?.length">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <GitCompare class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin análisis disponible</p>
        <p class="mt-1 text-xs text-muted-foreground">No hay datos diferenciales para mostrar. Ejecutá escaneos para generar comparativas.</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchAnalysis">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Distribución por Riesgo</p>
          </div>
          <BarChart
            :labels="riskDistributionLabels"
            :datasets="[{
              label: 'Hallazgos',
              data: riskDistributionData,
              backgroundColor: ['#ef4444', '#f97316', '#eab308', '#22c55e', '#6b7280'],
            }]"
            :height="200"
            yLabel="Count"
            :showLegend="false"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Layers class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Categorías</p>
          </div>
          <DoughnutChart
            :labels="categoryLabels"
            :data="categoryData"
            :height="220"
          />
        </Card>
      </div>

      <!-- Sections -->
      <div v-for="section in data.sections" :key="section.id" class="space-y-3 animate-in">
        <div class="flex items-center gap-2 pt-2">
          <component :is="sectionIcon(section.title)" class="h-4 w-4 text-primary" />
          <h2 class="text-sm font-semibold text-foreground">{{ section.title }}</h2>
          <span class="text-xs text-muted-foreground">({{ section.findings.length }})</span>
        </div>

        <div v-if="!section.findings.length" class="py-4 text-center text-xs text-muted-foreground rounded-xl bg-surface/30">
          Sin hallazgos en esta sección
        </div>

        <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Card v-for="finding in section.findings" :key="finding.id" class="p-4">
            <div class="flex items-start justify-between mb-2">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-foreground truncate">{{ finding.title }}</p>
                <p class="text-xs text-muted-foreground mt-0.5 truncate">{{ finding.target }} • {{ finding.endpoint }}</p>
              </div>
              <Badge :variant="riskVariant(finding.risk_level)" class="ml-2 shrink-0 text-[10px] capitalize">
                {{ finding.risk_level }}
              </Badge>
            </div>

            <p class="text-xs text-muted-foreground mb-3 line-clamp-2">{{ finding.description }}</p>

            <div class="flex items-center gap-1 mb-2 flex-wrap">
              <Badge variant="outline" class="text-[9px]">{{ finding.category }}</Badge>
            </div>

            <!-- Score bars -->
            <div class="space-y-1.5">
              <div>
                <div class="flex justify-between text-[10px] mb-0.5">
                  <span class="text-muted-foreground">Confidence</span>
                  <span class="font-semibold text-foreground">{{ (finding.confidence * 100).toFixed(0) }}%</span>
                </div>
                <div class="h-1 overflow-hidden rounded-full bg-[#1a1d29]">
                  <div class="h-full rounded-full transition-all" :class="scoreColor(finding.confidence)" :style="{ width: `${finding.confidence * 100}%` }" />
                </div>
              </div>
              <div>
                <div class="flex justify-between text-[10px] mb-0.5">
                  <span class="text-muted-foreground">Novelty</span>
                  <span class="font-semibold text-foreground">{{ (finding.novelty * 100).toFixed(0) }}%</span>
                </div>
                <div class="h-1 overflow-hidden rounded-full bg-[#1a1d29]">
                  <div class="h-full rounded-full transition-all" :class="scoreColor(finding.novelty)" :style="{ width: `${finding.novelty * 100}%` }" />
                </div>
              </div>
              <div>
                <div class="flex justify-between text-[10px] mb-0.5">
                  <span class="text-muted-foreground">ROI</span>
                  <span class="font-semibold text-foreground">{{ (finding.roi * 100).toFixed(0) }}%</span>
                </div>
                <div class="h-1 overflow-hidden rounded-full bg-[#1a1d29]">
                  <div class="h-full rounded-full transition-all" :class="scoreColor(finding.roi)" :style="{ width: `${finding.roi * 100}%` }" />
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
