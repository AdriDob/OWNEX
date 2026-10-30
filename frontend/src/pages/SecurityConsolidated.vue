<script setup lang="ts">
/**
 * Security — Consolidated page with tabs.
 * Combines: SecurityCycle + ExecutiveDashboard
 */
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import { Shield, BarChart3, Activity, RefreshCw, CheckCircle, AlertTriangle, Clock } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const activeTab = ref('pipeline')
const loading = ref(true)
const pipeline = ref<any>(null)
const executive = ref<any>(null)

async function fetchData() {
  loading.value = true
  try {
    // `/api/cycles/security/executive` no existe (404 siempre, verificado
    // contra `app.openapi()['paths']`). Los 4 números que la tab prometía sí
    // existen, repartidos en endpoints que el front ya usa:
    //   · Findings  y Confirmed → GET /api/overview
    //   · Reports               → GET /api/reports?limit=1  (`total`)
    //   · Revenue               → GET /api/revenue/summary (`total_earned`)
    // Compone de datos reales en vez de un endpoint inexistente.
    // Ver KNOWN_DEBT #76.
    const [pRes, oRes, rRes, vRes] = await Promise.allSettled([
      api.get<any>('/api/cycles/security/dashboard'),
      api.get<any>('/api/overview'),
      api.get<any>('/api/reports?limit=1'),
      api.get<any>('/api/revenue/summary'),
    ])
    if (pRes.status === 'fulfilled') pipeline.value = pRes.value
    if (oRes.status === 'fulfilled') {
      executive.value = {
        findings: {
          total: oRes.value?.findings ?? null,
          confirmed: oRes.value?.confirmed ?? null,
        },
        reports: { total: rRes.status === 'fulfilled' ? (rRes.value?.total ?? null) : null },
        revenue: {
          total: vRes.status === 'fulfilled' ? (vRes.value?.total_earned ?? null) : null,
        },
      }
    }
  } catch { /* silent */ }
  loading.value = false
}

const tabs = computed(() => [
  { id: 'pipeline', label: 'Pipeline', icon: Activity },
  { id: 'executive', label: 'Executive', icon: BarChart3 },
])

const stages = computed(() => {
  if (!pipeline.value?.stages) return []
  return pipeline.value.stages.map((s: any) => ({
    name: s.name,
    status: s.status,
    count: s.count || 0,
    icon: s.status === 'completed' ? CheckCircle : s.status === 'running' ? Clock : AlertTriangle,
  }))
})

const stageProgress = computed(() => {
  if (!stages.value.length) return 0
  const completed = stages.value.filter((s: any) => s.status === 'completed').length
  return Math.round((completed / stages.value.length) * 100)
})

/**
 * `null` = UNKNOWN y se muestra como "—".
 *
 * Antes los tiles usaban `|| 0`, que convierte "no lo sé" en "cero": con
 * el endpoint en 404 la tab entera enseñaba 0/0/0/$0, indistinguible de un
 * pipeline realmente vacío. Es la misma clase de mentira que
 * `acceptance_rate: 0.0` sobre 960 registros sin clasificar.
 */
function num(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : String(v)
}

function money(v: number | null | undefined): string {
  return v === null || v === undefined ? '—' : `$${v.toLocaleString('en-US')}`
}

const executiveSummary = computed(() => {
  const e = executive.value
  if (!e) return 'No data available'
  const parts: string[] = []
  const f = e.findings?.total
  const c = e.findings?.confirmed
  if (f !== null && f !== undefined) {
    parts.push(c === null || c === undefined
      ? `${f} findings`
      : `${c} de ${f} findings confirmados (${f ? Math.round((c / f) * 100) : 0}%)`)
  }
  const r = e.reports?.total
  if (r !== null && r !== undefined) parts.push(`${r} reports`)
  const v = e.revenue?.total
  if (v !== null && v !== undefined) parts.push(`$${v.toLocaleString('en-US')} cobrados`)
  return parts.length ? parts.join(' · ') : 'No data available'
})

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Security Cycle</h1>
        <p class="text-sm text-muted-foreground">Pipeline de seguridad y executive dashboard</p>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Fetchdata" @click="fetchData"
      >
        <RefreshCw class="h-3 w-3" /> Refresh
      </button>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Pipeline -->
      <template #pipeline>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <!-- Progress -->
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-foreground">Pipeline Progress</h3>
              <span class="font-mono text-xs text-muted-foreground">{{ stageProgress }}%</span>
            </div>
            <ProgressBar :value="stageProgress" color="primary" />
          </div>

          <!-- Stages -->
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div
              v-for="stage in stages"
              :key="stage.name"
              class="rounded-xl border border-border/30 bg-surface/50 p-4"
            >
              <div class="flex items-center gap-2">
                <component :is="stage.icon" class="h-4 w-4" :class="stage.status === 'completed' ? 'text-emerald-400' : stage.status === 'running' ? 'text-yellow-400' : 'text-muted-foreground'" />
                <span class="text-sm font-medium text-foreground capitalize">{{ stage.name }}</span>
              </div>
              <p class="mt-2 font-mono text-xs text-muted-foreground">{{ stage.count }} items</p>
            </div>
          </div>
        </div>
      </template>

      <!-- Executive -->
      <template #executive>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Findings</p>
              <p class="mt-1 font-mono text-2xl font-bold">{{ num(executive?.findings?.total) }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Confirmed</p>
              <p class="mt-1 font-mono text-2xl font-bold text-emerald-400">{{ num(executive?.findings?.confirmed) }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Reports</p>
              <p class="mt-1 font-mono text-2xl font-bold">{{ num(executive?.reports?.total) }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Revenue</p>
              <p class="mt-1 font-mono text-2xl font-bold text-primary">
                {{ money(executive?.revenue?.total) }}
              </p>
            </div>
          </div>

          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Pipeline Summary</h3>
            <p class="text-xs text-muted-foreground">{{ executiveSummary }}</p>
          </div>
        </div>
      </template>
    </Tabs>
  </div>
</template>
