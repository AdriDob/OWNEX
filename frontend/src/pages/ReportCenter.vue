<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, getReports, getReportStats, getRewardLearning, getFindings } from '@/lib/api'
import type { ReportItem, FindingItem } from '@/lib/api'
import { useReportStore } from '@/stores/report'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { FileText, Download, Eye, AlertTriangle, Plus, DollarSign, TrendingUp, Clock, Wallet, Search, X, Sparkles, Loader2, CheckCircle2, FileDown } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'

const reportStore = useReportStore()
const reports = ref<ReportItem[]>([])
const stats = ref<{ total: number; estimated_rewards: number; paid_count: number; status_counts: Record<string, number>; total_rewards: number } | null>(null)
const rewardLearning = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const sessionStart = ref(Date.now())

// Finding selector for draft generation
const findings = ref<FindingItem[]>([])
const findingSearch = ref('')
const findingLoading = ref(false)
const showFindingPicker = ref(false)
const selectedFinding = ref<FindingItem | null>(null)
const showDraftPreview = ref(false)

onMounted(async () => {
  try {
    const [r, s, rl] = await Promise.all([
      getReports({ limit: 50, sort_by: 'created_at', sort_order: 'desc' }),
      getReportStats().catch(() => null),
      getRewardLearning().catch(() => null),
      fetchMonthlyRevenue().catch(() => {}),
    ])
    reports.value = r.items || []
    stats.value = s
    rewardLearning.value = rl
    loading.value = false
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar reportes'
    loading.value = false
  }
})

async function searchFindings() {
  if (!findingSearch.value.trim() || findingSearch.value.length < 2) return
  findingLoading.value = true
  try {
    const res = await getFindings({ search: findingSearch.value, limit: 10 })
    findings.value = res.items || []
  } catch {
    findings.value = []
  } finally {
    findingLoading.value = false
  }
}

function selectFinding(f: FindingItem) {
  selectedFinding.value = f
  showFindingPicker.value = false
  findingSearch.value = ''
  findings.value = []
}

async function generateDraft() {
  if (!selectedFinding.value) return
  showDraftPreview.value = true
  await reportStore.generateDraft(selectedFinding.value.id)
}

function clearSelection() {
  selectedFinding.value = null
  reportStore.clearDraft()
  showDraftPreview.value = false
}

async function downloadMarkdown() {
  if (!selectedFinding.value) return
  const md = await reportStore.exportMarkdown(selectedFinding.value.id)
  if (md) {
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${selectedFinding.value.id}.md`
    a.click()
    URL.revokeObjectURL(url)
  }
}

async function downloadPdf() {
  if (!selectedFinding.value) return
  const blob = await reportStore.exportPdf(selectedFinding.value.id)
  if (blob) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${selectedFinding.value.id}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }
}

function statusVariant(status: string) {
  const map: Record<string, 'success' | 'warning' | 'destructive' | 'info' | 'default'> = {
    paid: 'success', submitted: 'info', ready: 'info', pending: 'warning',
    draft: 'default', rejected: 'destructive',
  }
  return map[status.toLowerCase()] || 'default'
}

const financialStats = computed(() => {
  if (!stats.value) return null
  const totalPaid = stats.value.paid_count || 0
  const totalRewards = stats.value.total_rewards || 0
  const estimated = stats.value.estimated_rewards || 0
  const pending = Math.max(0, estimated - totalRewards)
  let hoursTracked = 0
  try {
    const sessions = JSON.parse(localStorage.getItem('CATEYE-sessions') || '{}')
    for (const day of Object.values(sessions) as any) {
      for (const s of day) {
        if (s.end) hoursTracked += (s.end - s.start) / 3600000
        else hoursTracked += (Date.now() - s.start) / 3600000
      }
    }
  } catch { /* ignore */ }
  const valuePerHour = hoursTracked > 0 ? totalRewards / hoursTracked : 0
  return {
    totalPaid, totalRewards, estimated, pending,
    hoursTracked: Math.round(hoursTracked * 10) / 10,
    valuePerHour: Math.round(valuePerHour * 100) / 100,
    paidRatio: estimated > 0 ? totalRewards / estimated : 0,
  }
})

const monthlyRevenue = ref<{ month: string; amount: number; paid: number; count: number }[]>([])
const monthlyLoading = ref(true)

async function fetchMonthlyRevenue() {
  monthlyLoading.value = true
  try {
    const res = await api.get<{ months: typeof monthlyRevenue.value; total: number }>('/economic/monthly-revenue')
    monthlyRevenue.value = res.months || []
  } catch {
    monthlyRevenue.value = []
  } finally {
    monthlyLoading.value = false
  }
}

const maxMonthlyAmount = computed(() => {
  if (monthlyRevenue.value.length === 0) return 1
  return Math.max(...monthlyRevenue.value.map(d => d.amount), 1)
})

</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Submissions</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Report Center</h1>
      <p class="text-sm text-muted-foreground">Generación y gestión de reportes de vulnerabilidad</p>
    </div>

    <!-- Draft Generator -->
    <div class="glass-card rounded-xl p-4 animate-in">
      <div class="flex items-center gap-2 mb-3">
        <Sparkles class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold text-foreground">Generar Borrador con IA</h2>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <div class="relative flex-1 min-w-[200px]">
          <Input
            v-model="findingSearch"
            :placeholder="selectedFinding ? selectedFinding.title : 'Buscar finding por título o target...'"
            @input="searchFindings"
            @focus="showFindingPicker = true"
            class="pl-9"
          />
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <button v-if="selectedFinding" @click="clearSelection" class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
            <X class="h-3.5 w-3.5" />
          </button>
        </div>
        <Button @click="generateDraft" :disabled="!selectedFinding || reportStore.generating" :loading="reportStore.generating">
          <FileText class="h-4 w-4" />
          {{ reportStore.generating ? 'Generando...' : 'Generar Borrador' }}
        </Button>
      </div>

      <!-- Finding Picker -->
      <Transition name="fade">
        <div v-if="showFindingPicker && findingSearch.length >= 2 && findings.length > 0" class="mt-2 glass-strong rounded-lg max-h-48 overflow-y-auto">
          <button v-for="f in findings" :key="f.id" @click="selectFinding(f)"
            class="w-full text-left px-3 py-2 text-sm hover:bg-surface/50 transition-colors border-b border-border/20 last:border-0">
            <span class="text-foreground font-medium">{{ f.title }}</span>
            <span class="text-muted-foreground ml-2 text-xs">{{ f.target_name }}</span>
            <Badge :variant="f.severity === 'critical' ? 'destructive' : f.severity === 'high' ? 'warning' : f.severity === 'medium' ? 'info' : 'default'" class="ml-2 text-[10px] px-1.5 py-0">{{ f.severity }}</Badge>
          </button>
        </div>
      </Transition>
    </div>

    <!-- Draft Preview Drawer -->
    <Transition name="panel">
      <div v-if="showDraftPreview && reportStore.draft" class="fixed inset-0 z-50 flex items-start justify-center pt-[5vh]" @click="showDraftPreview = false">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showDraftPreview = false" />
        <div class="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto glass-strong rounded-xl shadow-2xl shadow-black/40 p-6 animate-in" @click.stop>
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <CheckCircle2 class="h-5 w-5 text-success" />
              <h2 class="text-lg font-semibold text-foreground">Borrador Generado</h2>
            </div>
            <div class="flex items-center gap-2">
              <Button size="sm" variant="outline" @click="downloadMarkdown">
                <FileDown class="h-3.5 w-3.5" /> MD
              </Button>
              <Button size="sm" variant="outline" @click="downloadPdf">
                <Download class="h-3.5 w-3.5" /> PDF
              </Button>
              <button @click="showDraftPreview = false" class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-surface transition-colors">
                <X class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Título</p>
              <p class="text-sm font-semibold text-foreground">{{ reportStore.draft.title }}</p>
            </div>
            <div class="flex gap-4">
              <div>
                <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Severidad</p>
                <Badge :variant="reportStore.draft.severity === 'critical' ? 'destructive' : reportStore.draft.severity === 'high' ? 'warning' : reportStore.draft.severity === 'medium' ? 'info' : 'default'" class="mt-1">{{ reportStore.draft.severity }}</Badge>
              </div>
              <div>
                <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Vulnerabilidad</p>
                <p class="text-sm text-foreground mt-1">{{ reportStore.draft.vulnerability }}</p>
              </div>
            </div>
            <div>
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Descripción</p>
              <p class="text-sm text-foreground mt-1 whitespace-pre-wrap">{{ reportStore.draft.description }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Impacto</p>
              <p class="text-sm text-foreground mt-1 whitespace-pre-wrap">{{ reportStore.draft.impact }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Steps to Reproduce</p>
              <ol class="list-decimal list-inside mt-1 space-y-1">
                <li v-for="(step, i) in reportStore.draft.steps_to_reproduce" :key="i" class="text-sm text-foreground">{{ step }}</li>
              </ol>
            </div>
            <div>
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Recommended Fix</p>
              <p class="text-sm text-foreground mt-1 whitespace-pre-wrap">{{ reportStore.draft.recommended_fix }}</p>
            </div>
            <div v-if="reportStore.draft.poc">
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">PoC</p>
              <pre class="mt-1 text-sm text-foreground bg-surface/50 rounded-lg p-3 overflow-x-auto">{{ reportStore.draft.poc }}</pre>
            </div>
            <div v-if="reportStore.draft.references.length">
              <p class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Referencias</p>
              <ul class="list-disc list-inside mt-1">
                <li v-for="(ref, i) in reportStore.draft.references" :key="i" class="text-sm text-accent">{{ ref }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <template v-if="loading">
      <div class="flex gap-3"><Skeleton class="h-9 w-32 rounded-lg" /><Skeleton class="h-9 w-32 rounded-lg" /></div>
      <div class="space-y-3"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-16 text-center">
        <AlertTriangle class="h-10 w-10 text-muted-foreground mb-4" />
        <p class="text-sm text-muted-foreground">{{ error }}</p>
      </div>
    </template>

    <template v-else>
      <div v-if="stats" class="flex gap-6 text-sm animate-in flex-wrap">
        <div class="flex items-center gap-2">
          <FileText class="h-4 w-4 text-muted-foreground" />
          <span class="text-muted-foreground">Total:</span>
          <span class="font-semibold text-foreground tabular-nums">{{ stats.total }}</span>
        </div>
        <div class="flex items-center gap-2">
          <DollarSign class="h-4 w-4 text-gold" />
          <span class="text-muted-foreground">Est. rewards:</span>
          <span class="font-semibold text-gold tabular-nums">${{ (stats.estimated_rewards || 0).toLocaleString() }}</span>
        </div>
        <div class="flex items-center gap-2">
          <Badge variant="success" class="text-[10px] px-1.5 py-0">{{ stats.paid_count }} pagados</Badge>
        </div>
      </div>

      <!-- Status Distribution Chart -->
      <Card class="p-4 animate-in" v-if="stats?.status_counts">
        <h3 class="text-xs font-semibold text-foreground mb-3">Distribución de Estados</h3>
        <DoughnutChart
          :labels="Object.keys(stats.status_counts)"
          :data="Object.values(stats.status_counts)"
          :height="200"
        />
      </Card>

      <div v-if="financialStats" class="space-y-3 animate-in">
        <div class="flex items-center gap-2">
          <Wallet class="h-4 w-4 text-gold" />
          <h2 class="text-sm font-semibold text-foreground">La Bóveda</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Card class="p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider">Total Cobrado</p>
            <p class="mt-1 text-xl font-bold text-gold tabular-nums">${{ financialStats.totalRewards.toLocaleString() }}</p>
            <p class="mt-0.5 text-[11px] text-muted-foreground">{{ financialStats.totalPaid }} pagos confirmados</p>
          </Card>
          <Card class="p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider">Pendiente</p>
            <p class="mt-1 text-xl font-bold text-warning tabular-nums">${{ financialStats.pending.toLocaleString() }}</p>
            <div class="mt-2 h-1.5 w-full rounded-full bg-surface">
              <div class="h-full rounded-full bg-success transition-all duration-500" :style="{ width: `${financialStats.paidRatio * 100}%` }" />
            </div>
            <p class="mt-0.5 text-[11px] text-muted-foreground">{{ Math.round(financialStats.paidRatio * 100) }}% cobrado</p>
          </Card>
          <Card class="p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider">Value/Hour</p>
            <p class="mt-1 text-xl font-bold text-accent tabular-nums">${{ financialStats.valuePerHour.toFixed(2) }}</p>
            <p class="mt-0.5 text-[11px] text-muted-foreground">{{ financialStats.hoursTracked }}h rastreadas</p>
          </Card>
        </div>
        <Card class="p-4">
          <div class="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            <TrendingUp class="h-3 w-3" />
            <span>Ingresos Acumulados</span>
          </div>
          <div v-if="monthlyRevenue.length > 0" class="flex items-end gap-2 h-32">
            <div v-for="(d, i) in monthlyRevenue" :key="i" class="flex-1 flex flex-col items-center gap-1">
              <div class="w-full rounded-t-md relative" style="min-height: 4px;">
                <div class="w-full rounded-t-md bg-success/30 transition-all duration-500" :style="{ height: `${(d.amount / maxMonthlyAmount) * 100}%`, minHeight: '4px' }" />
                <div class="absolute bottom-0 w-full rounded-t-md bg-success/60 transition-all duration-500" :style="{ height: `${(d.paid / maxMonthlyAmount) * 100}%`, minHeight: '2px' }" />
              </div>
              <span class="text-[10px] text-muted-foreground">{{ d.month }}</span>
            </div>
          </div>
          <div v-else class="flex items-center justify-center h-32 text-center">
            <p class="font-mono text-[10px] text-muted-foreground">Sin datos mensuales disponibles</p>
          </div>
        </Card>
      </div>

      <Card v-if="rewardLearning" class="p-4 space-y-3">
        <div class="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          <TrendingUp class="h-3 w-3" />
          <span>Reward Learning</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p class="text-xs text-muted-foreground">Tasa de Aceptación</p>
            <p class="font-semibold text-foreground">{{ (rewardLearning.overall_acceptance_rate * 100).toFixed(1) }}%</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Reportes Totales</p>
            <p class="font-semibold text-foreground">{{ rewardLearning.total_reports }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Confirmados</p>
            <p class="font-semibold text-foreground">{{ rewardLearning.total_confirmed }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Valor Confirmado</p>
            <p class="font-semibold text-gold">${{ rewardLearning.total_confirmed_value?.toLocaleString() || 0 }}</p>
          </div>
        </div>
      </Card>

      <div class="flex gap-3">
        <Button><Plus class="h-4 w-4" /> Nuevo Reporte</Button>
        <Button variant="secondary"><Download class="h-4 w-4" /> Exportar Todo</Button>
      </div>

      <div class="space-y-3">
        <Card v-for="(r, i) in reports" :key="r.id" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-start gap-4">
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
              <FileText class="h-4 w-4" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="text-sm font-semibold text-foreground">{{ r.vulnerability || r.target || `Reporte #${r.id}` }}</h3>
                <Badge :variant="statusVariant(r.status)" class="text-[10px] px-1.5 py-0">{{ r.status }}</Badge>
                <Badge v-if="r.severity" :variant="r.severity === 'critical' ? 'destructive' : r.severity === 'high' ? 'warning' : r.severity === 'medium' ? 'info' : 'default'" class="text-[10px] px-1.5 py-0">{{ r.severity }}</Badge>
              </div>
              <div class="mt-1 flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                <span>{{ r.program || r.target || '—' }}</span>
                <span v-if="r.estimated_reward" class="font-semibold text-gold">${{ r.estimated_reward.toLocaleString() }}</span>
                <span v-if="r.evidence_count">{{ r.evidence_count }} evidencias</span>
              </div>
              <p v-if="r.summary" class="mt-1 text-xs text-muted-foreground/70 line-clamp-2">{{ r.summary }}</p>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <Button variant="ghost" size="icon"><Eye class="h-4 w-4" /></Button>
              <Button variant="ghost" size="icon"><Download class="h-4 w-4" /></Button>
            </div>
          </div>
        </Card>
        <div v-if="reports.length === 0" class="py-12 text-center text-sm text-muted-foreground">No hay reportes generados aún</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.panel-enter-active, .panel-leave-active { transition: opacity 0.2s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; }
</style>
