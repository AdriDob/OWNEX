<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { DoughnutChart } from '@/components/charts'
import { ArrowLeft, AlertTriangle, BarChart3, Bug, DollarSign, Target, FileText, RefreshCw, Shield } from '@lucide/vue'

interface FindingDetail {
  id: number
  target_id: number
  endpoint_id: number | null
  title: string
  severity: string
  cvss_score: number
  description: string | null
  payout: number
  target_name: string
  endpoint_path: string
  poc_path: string | null
  suggested_responses: string[] | null
  created_at: string | null
}

const route = useRoute()
const router = useRouter()
const findingId = computed(() => Number(route.params.id))

const finding = ref<FindingDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    finding.value = await api.get<FindingDetail>(`/findings/${findingId.value}`)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el hallazgo'
  } finally {
    loading.value = false
  }
}

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

const cvssPercent = computed(() => {
  if (!finding.value) return 0
  return Math.min((finding.value.cvss_score / 10) * 100, 100)
})

const cvssColor = computed(() => {
  if (!finding.value) return 'bg-muted-foreground'
  const s = finding.value.cvss_score
  if (s >= 7) return 'bg-destructive'
  if (s >= 4) return 'bg-warning'
  return 'bg-accent'
})

const severityChartData = computed(() => {
  if (!finding.value) return { labels: [], data: [] }
  const sev = finding.value.severity.toLowerCase()
  const map: Record<string, { value: number; color: string }> = {
    critical: { value: 10, color: '#ef4444' },
    high: { value: 7.5, color: '#f97316' },
    medium: { value: 5, color: '#eab308' },
    low: { value: 2.5, color: '#22c55e' },
    info: { value: 1, color: '#6b7280' },
  }
  const entry = map[sev] || { value: 1, color: '#6b7280' }
  return {
    labels: [finding.value.title, 'Severidad base'],
    data: [entry.value, 10 - entry.value],
  }
})

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 animate-in">
      <Button variant="ghost" size="icon" @click="router.push('/findings')">
        <ArrowLeft class="h-4 w-4" />
      </Button>
      <div>
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Finding</p>
        <h1 class="font-display text-2xl font-bold text-foreground truncate max-w-lg">
          {{ finding?.title || 'Detalle de Hallazgo' }}
        </h1>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-32 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar el hallazgo</p>
        <p class="mt-1 text-xs text-muted-foreground max-w-md">{{ error }}</p>
        <Button variant="outline" class="mt-4" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!finding">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Bug class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Hallazgo no encontrado</p>
        <p class="mt-1 text-xs text-muted-foreground">El hallazgo solicitado no existe o fue eliminado</p>
        <Button variant="outline" class="mt-4" @click="router.push('/findings')">
          Volver al Pipeline
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Bug class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Severidad</span>
          </div>
          <Badge :variant="severityVariant(finding.severity)" class="mt-1 text-xs px-2 py-0.5">
            {{ finding.severity.toUpperCase() }}
          </Badge>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Shield class="h-4 w-4 text-accent" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">CVSS</span>
          </div>
          <p class="text-2xl font-bold text-foreground">{{ finding.cvss_score.toFixed(1) }}</p>
          <div class="mt-2 h-1.5 w-full rounded-full bg-surface">
            <div class="h-full rounded-full transition-all duration-500" :class="cvssColor" :style="{ width: `${cvssPercent}%` }" />
          </div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <DollarSign class="h-4 w-4 text-gold" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Pago Est.</span>
          </div>
          <p class="text-2xl font-bold text-gold">${{ finding.payout.toLocaleString() }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Target class="h-4 w-4 text-gold" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Target</span>
          </div>
          <p class="text-sm font-semibold text-foreground truncate">{{ finding.target_name }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 animate-in">
        <Card class="p-4 lg:col-span-2">
          <div class="flex items-center gap-2 mb-3">
            <FileText class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Descripción</span>
          </div>
          <p class="text-sm text-foreground whitespace-pre-wrap">{{ finding.description || 'Sin descripción disponible' }}</p>
          <div v-if="finding.endpoint_path" class="mt-4">
            <p class="text-xs text-muted-foreground mb-1">Endpoint</p>
            <code class="text-xs font-mono text-accent bg-surface/50 px-2 py-1 rounded">{{ finding.endpoint_path }}</code>
          </div>
          <div v-if="finding.poc_path" class="mt-3">
            <p class="text-xs text-muted-foreground mb-1">PoC</p>
            <code class="text-xs font-mono text-accent bg-surface/50 px-2 py-1 rounded break-all">{{ finding.poc_path }}</code>
          </div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-accent" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Severidad Relativa</span>
          </div>
          <DoughnutChart
            :labels="severityChartData.labels"
            :data="severityChartData.data"
            :height="200"
            :show-legend="true"
          />
        </Card>
      </div>

      <Card v-if="finding.suggested_responses && finding.suggested_responses.length > 0" class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <FileText class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Respuestas Sugeridas</span>
        </div>
        <ul class="space-y-2">
          <li v-for="(r, i) in finding.suggested_responses" :key="i"
            class="text-sm text-foreground bg-surface/30 rounded-lg px-3 py-2"
          >{{ r }}</li>
        </ul>
      </Card>
    </template>
  </div>
</template>
