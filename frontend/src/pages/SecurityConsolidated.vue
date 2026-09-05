<script setup lang="ts">
/**
 * Security — Consolidated page with tabs.
 * Combines: SecurityCycle + ExecutiveDashboard
 */
import { ref, computed, onMounted } from 'vue'
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
    const [pRes, eRes] = await Promise.allSettled([
      fetch('/api/cycles/security/dashboard').then(r => r.json()),
      fetch('/api/cycles/security/executive').then(r => r.json()),
    ])
    if (pRes.status === 'fulfilled') pipeline.value = pRes.value
    if (eRes.status === 'fulfilled') executive.value = eRes.value
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
        @click="fetchData"
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
              <p class="mt-1 font-mono text-2xl font-bold">{{ executive?.findings?.total || 0 }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Confirmed</p>
              <p class="mt-1 font-mono text-2xl font-bold text-emerald-400">{{ executive?.findings?.confirmed || 0 }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Reports</p>
              <p class="mt-1 font-mono text-2xl font-bold">{{ executive?.reports?.total || 0 }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Revenue</p>
              <p class="mt-1 font-mono text-2xl font-bold text-primary">${{ executive?.revenue?.total || 0 }}</p>
            </div>
          </div>

          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Pipeline Summary</h3>
            <p class="text-xs text-muted-foreground">{{ executive?.summary || 'No data available' }}</p>
          </div>
        </div>
      </template>
    </Tabs>
  </div>
</template>
