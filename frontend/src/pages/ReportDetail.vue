<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, getToken } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { DoughnutChart } from '@/components/charts'
import {
  ArrowLeft, AlertTriangle, FileText, DollarSign, CalendarDays,
  RefreshCw, Download, CheckCircle2, Send, Clock, Target,
  Wallet, TrendingUp,
} from '@lucide/vue'

interface ReportDetail {
  id: number
  investigation_id: number | null
  format: string
  program: string
  target: string
  vulnerability: string
  severity: string
  status: 'draft' | 'ready' | 'submitted' | 'paid' | 'rejected'
  estimated_reward: number
  confirmed_reward: number
  currency: string
  evidence_count: number
  summary: string
  content: Record<string, any> | null
  created_at: string | null
  updated_at: string | null
}

const route = useRoute()
const router = useRouter()
const reportId = computed(() => Number(route.params.id))

const report = ref<ReportDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const saving = ref(false)
const exporting = ref<'json' | 'markdown' | null>(null)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    report.value = await api.get<ReportDetail>(`/reports/${reportId.value}`)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el reporte'
  } finally {
    loading.value = false
  }
}

async function updateStatus(status: string) {
  if (!report.value) return
  saving.value = true
  try {
    report.value = await api.put<ReportDetail>(`/reports/${reportId.value}`, { ...report.value, status })
  } catch { /* ignore */ }
  finally { saving.value = false }
}

async function handleExport(format: 'markdown' | 'json') {
  exporting.value = format
  try {
    const token = getToken()
    const res = await fetch(`/api/reports/${reportId.value}/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error()
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${reportId.value}.${format === 'markdown' ? 'md' : 'json'}`
    a.click()
    URL.revokeObjectURL(url)
  } catch { /* ignore */ }
  finally { exporting.value = null }
}

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

function statusVariant(st: string) {
  const map: Record<string, 'success' | 'warning' | 'destructive' | 'info' | 'default'> = {
    paid: 'success', submitted: 'info', ready: 'info', draft: 'default', rejected: 'destructive',
  }
  return map[st.toLowerCase()] || 'default'
}

const nextStatus = computed(() => {
  if (!report.value) return null
  const flow: Record<string, string> = { draft: 'ready', ready: 'submitted' }
  return flow[report.value.status] || null
})

const payoutBreakdownData = computed(() => {
  if (!report.value) return { labels: [], data: [] }
  return {
    labels: ['Estimado', 'Confirmado', 'Pendiente'],
    data: [
      report.value.estimated_reward,
      report.value.confirmed_reward,
      Math.max(0, report.value.estimated_reward - report.value.confirmed_reward),
    ],
  }
})

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 animate-in">
      <Button variant="ghost" size="icon" @click="router.push('/reports')">
        <ArrowLeft class="h-4 w-4" />
      </Button>
      <div class="flex-1 min-w-0">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Reporte</p>
        <h1 class="font-display text-2xl font-bold text-foreground truncate max-w-lg">
          {{ report?.vulnerability || report?.target || `Reporte #${reportId}` }}
        </h1>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
        <p class="text-sm font-semibold text-foreground">Error al cargar el reporte</p>
        <p class="mt-1 text-xs text-muted-foreground max-w-md">{{ error }}</p>
        <Button variant="outline" class="mt-4" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!report">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <FileText class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Reporte no encontrado</p>
        <p class="mt-1 text-xs text-muted-foreground">El reporte solicitado no existe o fue eliminado</p>
        <Button variant="outline" class="mt-4" @click="router.push('/reports')">
          Volver al Centro de Reportes
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <FileText class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Estado</span>
          </div>
          <Badge :variant="statusVariant(report.status)" class="mt-1 text-xs px-2 py-0.5">{{ report.status }}</Badge>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Target class="h-4 w-4 text-accent" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Target</span>
          </div>
          <p class="text-sm font-semibold text-foreground truncate">{{ report.target }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Badge :variant="severityVariant(report.severity)" class="text-[10px] px-1.5 py-0">{{ report.severity }}</Badge>
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Severidad</span>
          </div>
          <p class="text-sm text-foreground mt-1">{{ report.vulnerability }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <DollarSign class="h-4 w-4 text-gold" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recompensa</span>
          </div>
          <p class="text-2xl font-bold text-gold">${{ report.estimated_reward.toLocaleString() }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 animate-in">
        <Card class="p-4 lg:col-span-2">
          <div class="flex items-center gap-2 mb-3">
            <FileText class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Resumen</span>
          </div>
          <p class="text-sm text-foreground whitespace-pre-wrap">{{ report.summary || 'Sin resumen disponible' }}</p>
          <div class="mt-4 grid grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div>
              <CalendarDays class="h-3.5 w-3.5 inline mr-1" />
              Creado: {{ report.created_at ? new Date(report.created_at).toLocaleDateString('es-AR') : '—' }}
            </div>
            <div>
              <CalendarDays class="h-3.5 w-3.5 inline mr-1" />
              Actualizado: {{ report.updated_at ? new Date(report.updated_at).toLocaleDateString('es-AR') : '—' }}
            </div>
          </div>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <TrendingUp class="h-4 w-4 text-gold" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Payout</span>
          </div>
          <DoughnutChart
            :labels="payoutBreakdownData.labels"
            :data="payoutBreakdownData.data"
            :height="200"
            :colors="['#16A34A', '#ffffff', '#A16207']"
          />
        </Card>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <Send class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Acciones</span>
          </div>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <template v-if="nextStatus">
            <Button @click="updateStatus(nextStatus)" :disabled="saving" :loading="saving">
              <CheckCircle2 class="h-4 w-4" />
              {{ saving ? 'Guardando...' : `Marcar como ${nextStatus}` }}
            </Button>
          </template>
          <Button variant="secondary" @click="handleExport('markdown')" :disabled="exporting === 'markdown'" :loading="exporting === 'markdown'">
            <Download class="h-4 w-4" /> Exportar MD
          </Button>
          <Button variant="secondary" @click="handleExport('json')" :disabled="exporting === 'json'" :loading="exporting === 'json'">
            <Download class="h-4 w-4" /> Exportar JSON
          </Button>
        </div>
      </Card>

      <Card v-if="report.content" class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <FileText class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Contenido del Reporte</span>
        </div>
        <pre class="text-xs text-foreground whitespace-pre-wrap font-sans bg-surface/30 rounded-lg p-4 max-h-96 overflow-y-auto">{{ JSON.stringify(report.content, null, 2) }}</pre>
      </Card>
    </template>
  </div>
</template>
