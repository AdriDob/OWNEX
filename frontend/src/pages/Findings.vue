<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useFindingsStore } from '@/stores/findings'
import type { Finding } from '@/types'
import FindingDetailDrawer from '@/components/findings/FindingDetailDrawer.vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Button from '@/components/ui/Button.vue'
import { Bug, AlertTriangle, CheckCircle2, Clock, FileText, ListFilter, Search, X, PieChart, BarChart3 } from '@lucide/vue'
import { DoughnutChart, BarChart } from '@/components/charts'

const store = useFindingsStore()
const activeTab = ref<'pipeline' | 'all'>('pipeline')
const drawerOpen = ref(false)
const searchQuery = ref('')
const selectedFinding = ref<Finding | null>(null)

onMounted(async () => {
  await store.fetchAll()
})

const pipelineStages = computed(() => {
  if (!store.pipeline) return []
  return [
    { key: 'detected', items: store.pipeline.detected, icon: Bug, color: 'text-muted-foreground' },
    { key: 'validated', items: store.pipeline.validated, icon: Clock, color: 'text-accent' },
    { key: 'confirmed', items: store.pipeline.confirmed, icon: CheckCircle2, color: 'text-success' },
    { key: 'reported', items: store.pipeline.reported, icon: FileText, color: 'text-gold' },
  ]
})

const severityDistribution = computed(() => {
  const all = store.findings.length ? store.findings : (store.pipeline ? [...store.pipeline.detected, ...store.pipeline.validated, ...store.pipeline.confirmed, ...store.pipeline.reported] : [])
  const map: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  all.forEach(f => { const s = f.severity?.toLowerCase() || 'info'; map[s] = (map[s] || 0) + 1 })
  return map
})

const pipelineStageCounts = computed(() => {
  if (!store.pipeline) return [0, 0, 0, 0]
  return [store.pipeline.detected.length, store.pipeline.validated.length, store.pipeline.confirmed.length, store.pipeline.reported.length]
})

const filteredFindings = computed(() => {
  const q = searchQuery.value.toLowerCase()
  if (!q) return store.findings
  return store.findings.filter(f =>
    f.title?.toLowerCase().includes(q) ||
    f.target_name?.toLowerCase().includes(q) ||
    f.endpoint_path?.toLowerCase().includes(q)
  )
})

function openDrawer(finding: Finding) {
  selectedFinding.value = finding
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
  selectedFinding.value = null
}

function onStatusUpdated() {
  store.fetchAll()
}

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

function severityColor(sev: string) {
  if (sev === 'critical' || sev === 'high') return 'text-destructive'
  if (sev === 'medium') return 'text-warning'
  return 'text-accent'
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Pipeline</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Findings Pipeline</h1>
      <p class="text-sm text-muted-foreground">Hallazgos en todas las etapas del pipeline</p>
    </div>

    <template v-if="store.loading">
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-20 rounded-xl" />
      </div>
      <Skeleton class="h-40 rounded-xl" />
    </template>

    <template v-else-if="store.error">
      <div class="flex flex-col items-center py-16 text-center">
        <AlertTriangle class="h-10 w-10 text-muted-foreground mb-4" />
        <p class="text-sm text-muted-foreground">{{ store.error }}</p>
      </div>
    </template>

    <template v-else>
      <!-- Pipeline summary counts -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card v-for="(stage, i) in pipelineStages" :key="stage.key" class="p-4 text-center cursor-pointer hover:bg-surface/50 transition-colors stagger-item" :style="{ '--i': i }" @click="activeTab = 'pipeline'">
          <p class="text-2xl font-bold tabular-nums text-foreground">{{ stage.items.length }}</p>
          <p class="mt-1 text-xs text-muted-foreground capitalize">{{ stage.key }}</p>
        </Card>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Severidad</p>
          </div>
          <BarChart
            :labels="['Critical', 'High', 'Medium', 'Low', 'Info']"
            :datasets="[{ label: 'Hallazgos', data: [severityDistribution.critical, severityDistribution.high, severityDistribution.medium, severityDistribution.low, severityDistribution.info], backgroundColor: ['#E82127', '#D97706', '#A16207', '#16A34A', '#6b7280'] }]"
            :height="180"
            yLabel="Count"
            :showLegend="false"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <PieChart class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Pipeline stage</p>
          </div>
          <DoughnutChart
            :labels="['Detected', 'Validated', 'Confirmed', 'Reported']"
            :data="pipelineStageCounts"
            :height="200"
          />
        </Card>
      </div>

      <!-- Tabs -->
      <div class="flex items-center gap-2 border-b border-border/40">
        <button @click="activeTab = 'pipeline'"
          :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === 'pipeline' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
        >Pipeline</button>
        <button @click="activeTab = 'all'"
          :class="['px-4 py-2 text-xs font-semibold transition-colors border-b-2 -mb-px', activeTab === 'all' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground']"
        >Todos ({{ store.findings.length }})</button>
      </div>

      <!-- Pipeline View -->
      <div v-if="activeTab === 'pipeline' && store.pipeline" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="stage in pipelineStages" :key="stage.key" class="space-y-2">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">{{ stage.key }} ({{ stage.items.length }})</h3>
          <Card v-for="f in stage.items" :key="f.id"
            class="p-3 animate-in cursor-pointer hover:border-primary/30 transition-colors"
            @click="openDrawer(f)"
          >
            <div class="flex items-start gap-2">
              <component :is="stage.icon" :class="['mt-0.5 h-4 w-4 shrink-0', stage.color]" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-foreground truncate">{{ f.title }}</span>
                  <Badge :variant="severityVariant(f.severity)" class="text-[10px] px-1.5 py-0 shrink-0">{{ f.severity }}</Badge>
                </div>
                <p class="text-[11px] text-muted-foreground mt-0.5 truncate">{{ f.target_name || `Target #${f.target_id}` }}</p>
                <p v-if="f.endpoint_path" class="text-[10px] font-mono text-muted-foreground/70 truncate">{{ f.endpoint_path }}</p>
              </div>
            </div>
          </Card>
          <div v-if="stage.items.length === 0" class="py-4 text-center text-xs text-muted-foreground">Sin hallazgos</div>
        </div>
      </div>

      <!-- All Findings View -->
      <div v-else-if="activeTab === 'all'">
        <!-- Search -->
        <div class="relative mb-3">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            v-model="searchQuery"
            placeholder="Buscar hallazgos..."
            class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-8 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
          />
          <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
            <X class="h-3.5 w-3.5" />
          </button>
        </div>

        <div class="space-y-2">
          <Card v-for="f in filteredFindings" :key="f.id"
            class="p-3 animate-in cursor-pointer hover:border-primary/30 transition-colors"
            @click="openDrawer(f)"
          >
            <div class="flex items-start gap-2">
              <div :class="['mt-0.5', severityColor(f.severity)]">
                <AlertTriangle v-if="f.severity === 'critical' || f.severity === 'high'" class="h-4 w-4" />
                <Bug v-else class="h-4 w-4" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-semibold text-foreground">{{ f.title }}</span>
                  <Badge :variant="severityVariant(f.severity)" class="text-[10px] px-1.5 py-0">{{ f.severity }}</Badge>
                </div>
                <div class="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{{ f.target_name || `Target #${f.target_id}` }}</span>
                  <span v-if="f.endpoint_path" class="font-mono text-[10px]">{{ f.endpoint_path }}</span>
                  <span v-if="f.payout" class="text-gold font-semibold">${{ f.payout.toLocaleString() }}</span>
                </div>
              </div>
            </div>
          </Card>
          <div v-if="filteredFindings.length === 0" class="py-12 text-center text-sm text-muted-foreground">
            {{ searchQuery ? 'Sin resultados para la búsqueda' : 'No hay hallazgos aún' }}
          </div>
        </div>
      </div>
    </template>

    <!-- Detail Drawer -->
    <FindingDetailDrawer
      :finding="selectedFinding"
      @close="closeDrawer"
      @status-updated="onStatusUpdated"
    />
  </div>
</template>
