<script setup lang="ts">
/**
 * Operations — Consolidated page with tabs.
 * Combines: OperationsDashboard + HealthCenter + Settings
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Activity, HeartPulse, Settings, Zap, RefreshCw, Database } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const router = useRouter()
const activeTab = ref('overview')

// System data
const systemStatus = ref<any>(null)
const loading = ref(true)

async function fetchStatus() {
  loading.value = true
  try {
    const res = await fetch('/api/system/status')
    systemStatus.value = await res.json()
  } catch { /* silent */ }
  loading.value = false
}

const tabs = computed(() => [
  { id: 'overview', label: 'Panel', icon: Activity },
  { id: 'health', label: 'Health', icon: HeartPulse },
  { id: 'settings', label: 'Settings', icon: Settings },
])

const healthScore = computed(() => {
  if (!systemStatus.value) return 0
  const mem = systemStatus.value.system?.memory_percent || 0
  const cpu = systemStatus.value.system?.cpu_percent || 0
  return Math.round(100 - (mem + cpu) / 2)
})

onMounted(fetchStatus)
</script>

<template>
  <div class="min-h-screen bg-background p-6">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-foreground">Operaciones</h1>
      <p class="text-sm text-muted-foreground">Estado del sistema, health y configuración</p>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Overview -->
      <template #overview>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-24 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <!-- System status -->
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-foreground">System Status</h3>
              <span
                class="rounded-full px-2 py-0.5 text-[10px] font-mono"
                :class="systemStatus?.status === 'ok' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-yellow-500/10 text-yellow-400'"
              >
                {{ systemStatus?.status || 'unknown' }}
              </span>
            </div>
            <div class="mt-4 grid grid-cols-3 gap-4">
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">CPU</p>
                <ProgressBar :value="systemStatus?.system?.cpu_percent || 0" color="primary" size="sm" />
              </div>
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Memory</p>
                <ProgressBar :value="systemStatus?.system?.memory_percent || 0" color="warning" size="sm" />
              </div>
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Health</p>
                <p class="font-mono text-lg font-bold" :class="healthScore > 70 ? 'text-emerald-400' : 'text-yellow-400'">
                  {{ healthScore }}%
                </p>
              </div>
            </div>
          </div>

          <!-- Quick actions -->
          <div class="flex flex-wrap gap-2">
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              @click="activeTab = 'health'"
            >
              <HeartPulse class="h-3.5 w-3.5" /> Ver Health
            </button>
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              @click="activeTab = 'settings'"
            >
              <Settings class="h-3.5 w-3.5" /> Configuración
            </button>
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              @click="router.push('/operations/scheduler')"
            >
              <Zap class="h-3.5 w-3.5" /> Scheduler
            </button>
            <button
              class="flex items-center gap-2 rounded-lg border border-border/30 px-3 py-2 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
              @click="router.push('/operations/pipelines')"
            >
              <RefreshCw class="h-3.5 w-3.5" /> Pipelines
            </button>
          </div>
        </div>
      </template>

      <!-- Health -->
      <template #health>
        <div class="space-y-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Health Center</h3>
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div class="text-center">
                <p class="text-[10px] font-mono text-muted-foreground">Uptime</p>
                <p class="font-mono text-sm font-bold">{{ Math.round((systemStatus?.uptime_seconds || 0) / 3600) }}h</p>
              </div>
              <div class="text-center">
                <p class="text-[10px] font-mono text-muted-foreground">PID</p>
                <p class="font-mono text-sm font-bold">{{ systemStatus?.pid || '-' }}</p>
              </div>
              <div class="text-center">
                <p class="text-[10px] font-mono text-muted-foreground">Threads</p>
                <p class="font-mono text-sm font-bold">{{ systemStatus?.system?.num_threads || '-' }}</p>
              </div>
              <div class="text-center">
                <p class="text-[10px] font-mono text-muted-foreground">DB Size</p>
                <p class="font-mono text-sm font-bold">{{ (systemStatus?.database?.file_size_mb || 0).toFixed(1) }}MB</p>
              </div>
            </div>
          </div>

          <button
            class="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"
            @click="fetchStatus"
          >
            <RefreshCw class="h-3 w-3" /> Refresh
          </button>
        </div>
      </template>

      <!-- Settings -->
      <template #settings>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-foreground">Configuración</h3>
          <p class="text-xs text-muted-foreground">
            Configuración completa disponible en{' '}
            <button class="text-primary hover:underline" @click="router.push('/operations/settings')">
              Settings avanzado
            </button>
          </p>
        </div>
      </template>
    </Tabs>
  </div>
</template>
