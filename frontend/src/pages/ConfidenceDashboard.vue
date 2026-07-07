<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart3, AlertTriangle } from '@lucide/vue'
import LineChart from '@/components/charts/LineChart.vue'
import Button from '@/components/ui/Button.vue'

interface ConfidenceFactor {
  name: string; value: number; weight: number; description: string
}

interface ConfidenceAudit {
  item_id: string; item_label: string; item_type: string; overall_score: number;
  historical_influence: number; evidence_influence: number; roi_influence: number;
  factors: ConfidenceFactor[]; reasoning_summary: string | null;
}

const audits = ref<ConfidenceAudit[]>([])
const totalAudited = ref(0)
const averageConfidence = ref(0)
const itemType = ref<'verdict' | 'finding'>('verdict')
const loading = ref(true)
const error = ref<string | null>(null)
const expanded = ref<Record<string, boolean>>({})

function getTier(score: number): { label: string; color: string; variant: 'success' | 'warning' | 'destructive' } {
  if (score >= 0.7) return { label: 'HIGH', color: '#22c55e', variant: 'success' }
  if (score >= 0.4) return { label: 'MEDIUM', color: '#eab308', variant: 'warning' }
  return { label: 'LOW', color: '#ef4444', variant: 'destructive' }
}

const highConf = computed(() => audits.value.filter(a => a.overall_score >= 0.7))
const medConf = computed(() => audits.value.filter(a => a.overall_score >= 0.4 && a.overall_score < 0.7))
const lowConf = computed(() => audits.value.filter(a => a.overall_score < 0.4))

async function fetchAudits() {
  loading.value = true
  try {
    const res = await api.get<{ audits: ConfidenceAudit[]; total_audited: number; average_confidence: number }>(
      '/confidence/audit', { item_type: itemType.value, limit: 50 }
    )
    audits.value = res.audits || []
    totalAudited.value = res.total_audited || 0
    averageConfidence.value = res.average_confidence || 0
  } catch (e: any) { error.value = e?.message || 'Error al cargar datos de confianza' }
  finally { loading.value = false }
}

function toggleExpand(id: string) { expanded.value[id] = !expanded.value[id] }

onMounted(fetchAudits)
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Quality</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Confidence Dashboard</h1>
      <p class="text-sm text-muted-foreground">{{ totalAudited }} items audited · Average: {{ (averageConfidence * 100).toFixed(1) }}%</p>
    </div>

    <!-- Type toggle -->
    <div class="flex gap-2 animate-in">
      <button @click="itemType = 'verdict'; fetchAudits()"
        class="rounded-lg px-5 py-2 text-xs font-semibold transition-all"
        :class="itemType === 'verdict' ? 'bg-primary text-white' : 'bg-surface/50 text-muted-foreground hover:text-foreground'"
      >Verdicts</button>
      <button @click="itemType = 'finding'; fetchAudits()"
        class="rounded-lg px-5 py-2 text-xs font-semibold transition-all"
        :class="itemType === 'finding' ? 'bg-primary text-white' : 'bg-surface/50 text-muted-foreground hover:text-foreground'"
      >Findings</button>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Skeleton v-for="i in 3" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl mt-4" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="fetchAudits">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="audits.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <BarChart3 class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No Confidence Data</p>
        <p class="mt-1 text-xs text-muted-foreground">Run validations to generate confidence audits</p>
      </div>
    </template>

    <template v-else>
      <!-- Confidence Trend -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Tendencia de Confianza</h3>
        <LineChart
          :labels="audits.slice(0, 20).map(a => a.item_label.slice(0, 12))"
          :datasets="[{ label: 'Confidence Score', data: audits.slice(0, 20).map(a => a.overall_score), borderColor: '#7c3aed', tension: 0.3 }]"
          :height="200"
          :area="true"
        />
      </Card>

      <!-- Summary cards -->
      <div class="grid grid-cols-1 gap-3 animate-in sm:grid-cols-3">
        <Card class="p-4 border-success/30 bg-success/5">
          <p class="text-[10px] font-bold text-success uppercase tracking-wider">HIGH</p>
          <p class="text-2xl font-bold text-success">{{ highConf.length }}</p>
        </Card>
        <Card class="p-4 border-warning/30 bg-warning/5">
          <p class="text-[10px] font-bold text-warning uppercase tracking-wider">MEDIUM</p>
          <p class="text-2xl font-bold text-warning">{{ medConf.length }}</p>
        </Card>
        <Card class="p-4 border-destructive/30 bg-destructive/5">
          <p class="text-[10px] font-bold text-destructive uppercase tracking-wider">LOW</p>
          <p class="text-2xl font-bold text-destructive">{{ lowConf.length }}</p>
          <p v-if="lowConf.length > 0" class="text-[10px] text-destructive mt-1">Needs manual review</p>
        </Card>
      </div>

      <!-- Low confidence -->
      <Card v-if="lowConf.length > 0" class="animate-in p-4 border-destructive/30">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs">⚠️</span>
          <p class="text-xs font-semibold text-foreground">Needs Manual Review ({{ lowConf.length }})</p>
        </div>
        <div v-for="a in lowConf" :key="a.item_id" class="mb-2 last:mb-0">
          <button @click="toggleExpand(a.item_id)"
            class="w-full rounded-lg border border-destructive/20 bg-[#1e2230] px-4 py-3 text-left transition-all hover:border-destructive/40"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-foreground">{{ a.item_label }}</span>
                <Badge variant="destructive" class="text-[10px]">{{ getTier(a.overall_score).label }}</Badge>
              </div>
              <span class="text-[10px] text-muted-foreground">{{ a.item_type }}</span>
            </div>
            <!-- Score bar -->
            <div class="mb-1">
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Confidence</span>
                <span class="font-semibold" :style="{ color: getTier(a.overall_score).color }">{{ (a.overall_score * 100).toFixed(0) }}%</span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-[#1a1d29]">
                <div class="h-full rounded-full transition-all" :style="{ width: `${a.overall_score * 100}%`, background: getTier(a.overall_score).color }" />
              </div>
            </div>
            <div class="flex gap-4 text-[10px] text-muted-foreground">
              <span>Historical: <strong class="text-foreground">{{ (a.historical_influence * 100).toFixed(0) }}%</strong></span>
              <span>Evidence: <strong class="text-foreground">{{ (a.evidence_influence * 100).toFixed(0) }}%</strong></span>
              <span>ROI: <strong class="text-foreground">{{ (a.roi_influence * 100).toFixed(0) }}%</strong></span>
            </div>
          </button>
          <Transition name="fade">
            <div v-if="expanded[a.item_id]" class="mt-1 rounded-lg bg-[#0d0f14] p-3">
              <p class="mb-2 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Factors</p>
              <div v-for="(f, fi) in a.factors" :key="fi" class="mb-2">
                <div class="flex justify-between text-[10px] mb-0.5">
                  <span class="text-muted-foreground">{{ f.name }}</span>
                  <span class="font-semibold text-foreground">{{ (f.value * f.weight).toFixed(3) }}</span>
                </div>
                <div class="h-1 overflow-hidden rounded-full bg-[#1a1d29]">
                  <div class="h-full rounded-full bg-primary/60" :style="{ width: `${f.value * 100}%` }" />
                </div>
                <p class="text-[9px] text-muted-foreground mt-0.5">{{ f.description }}</p>
              </div>
              <p v-if="a.reasoning_summary" class="mt-2 text-[10px] italic text-muted-foreground">{{ a.reasoning_summary }}</p>
            </div>
          </Transition>
        </div>
      </Card>

      <!-- High confidence -->
      <Card v-if="highConf.length > 0" class="animate-in p-4">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs">✅</span>
          <p class="text-xs font-semibold text-foreground">High Confidence ({{ highConf.length }})</p>
        </div>
        <div v-for="a in highConf" :key="a.item_id" class="mb-2 last:mb-0">
          <button @click="toggleExpand(a.item_id)"
            class="w-full rounded-lg border border-success/20 bg-[#1e2230] px-4 py-3 text-left transition-all hover:border-success/40"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-foreground">{{ a.item_label }}</span>
                <Badge variant="success" class="text-[10px]">{{ getTier(a.overall_score).label }}</Badge>
              </div>
              <span class="text-[10px] text-muted-foreground">{{ a.item_type }}</span>
            </div>
            <div class="mb-1">
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Confidence</span>
                <span class="font-semibold text-success">{{ (a.overall_score * 100).toFixed(0) }}%</span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-[#1a1d29]">
                <div class="h-full rounded-full bg-success" :style="{ width: `${a.overall_score * 100}%` }" />
              </div>
            </div>
          </button>
        </div>
      </Card>

      <!-- Medium confidence -->
      <Card v-if="medConf.length > 0" class="animate-in p-4">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs">🔶</span>
          <p class="text-xs font-semibold text-foreground">Medium Confidence ({{ medConf.length }})</p>
        </div>
        <div v-for="a in medConf" :key="a.item_id" class="mb-2 last:mb-0">
          <button @click="toggleExpand(a.item_id)"
            class="w-full rounded-lg border border-warning/20 bg-[#1e2230] px-4 py-3 text-left transition-all hover:border-warning/40"
          >
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-foreground">{{ a.item_label }}</span>
                <Badge variant="warning" class="text-[10px]">{{ getTier(a.overall_score).label }}</Badge>
              </div>
              <span class="text-[10px] text-muted-foreground">{{ a.item_type }}</span>
            </div>
            <div class="mb-1">
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Confidence</span>
                <span class="font-semibold text-warning">{{ (a.overall_score * 100).toFixed(0) }}%</span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-[#1a1d29]">
                <div class="h-full rounded-full bg-warning" :style="{ width: `${a.overall_score * 100}%` }" />
              </div>
            </div>
          </button>
        </div>
      </Card>
    </template>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
