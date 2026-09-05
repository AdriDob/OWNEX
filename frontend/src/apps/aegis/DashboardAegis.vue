<script setup lang="ts">
import { Activity, Bug, Crosshair, Plus, Shield, Target, Zap } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

interface TargetSummary {
  id: number
  name: string
  domain: string | null
  status: string
  priority: string
}

interface FindingSummary {
  id: number
  title: string
  severity: string
  status: string
}

interface Stats {
  targets_active: number
  findings_open: number
  scans_today: number
}

const router = useRouter()
const { toast } = useToast()
const targets = ref<TargetSummary[]>([])
const findings = ref<FindingSummary[]>([])
const stats = ref<Stats>({ targets_active: 0, findings_open: 0, scans_today: 0 })
const loading = ref(true)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [targetsRes, findingsRes, activeRes, openRes, scansRes] = await Promise.allSettled([
      fetch('/api/aegis/targets?limit=10'),
      fetch('/api/aegis/findings?limit=10'),
      fetch('/api/aegis/targets/active'),
      fetch('/api/aegis/findings/open'),
      fetch('/api/aegis/scans/today'),
    ])
    if (targetsRes.status === 'fulfilled' && targetsRes.value.ok) {
      const data = await targetsRes.value.json()
      targets.value = data.targets || []
    }
    if (findingsRes.status === 'fulfilled' && findingsRes.value.ok) {
      const data = await findingsRes.value.json()
      findings.value = data.findings || []
    }
    if (activeRes.status === 'fulfilled' && activeRes.value.ok) {
      const data = await activeRes.value.json()
      stats.value.targets_active = data.count
    }
    if (openRes.status === 'fulfilled' && openRes.value.ok) {
      const data = await openRes.value.json()
      stats.value.findings_open = data.count
    }
    if (scansRes.status === 'fulfilled' && scansRes.value.ok) {
      const data = await scansRes.value.json()
      stats.value.scans_today = data.count
    }
  } catch (e) {
    error.value = 'Error de conexión con AEGIS'
    toast.error('Error', 'No se pudo cargar el dashboard')
  } finally {
    loading.value = false
  }
}

const severityColor = (s: string) => {
  const map: Record<string, string> = {
    critical: 'text-destructive',
    high: 'text-warning',
    medium: 'text-accent',
    low: 'text-muted-foreground',
    info: 'text-muted',
  }
  return map[s] || 'text-muted-foreground'
}

onMounted(fetchData)
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
          <Shield class="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-foreground">AEGIS</h1>
          <p class="text-xs text-muted-foreground">Offensive Security Platform</p>
        </div>
      </div>
      <button @click="fetchData" class="flex items-center gap-1.5 rounded-lg border border-border/40 px-3 py-1.5 text-xs text-muted-foreground hover:bg-surface transition-colors">
        <Activity class="h-3.5 w-3.5" />
        Actualizar
      </button>
    </div>

    <!-- Stats -->
    <div v-if="loading" class="grid grid-cols-3 gap-4">
      <Skeleton v-for="i in 3" :key="i" class="h-24 rounded-xl" />
    </div>
    <div v-else-if="error" class="flex items-center justify-center h-24 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-sm">
      {{ error }}
    </div>
    <div v-else class="grid grid-cols-3 gap-4">
      <div class="rounded-xl border border-border/40 bg-surface/40 p-4">
        <div class="flex items-center gap-2 text-muted-foreground text-xs mb-2">
          <Crosshair class="h-3.5 w-3.5" />
          Targets activos
        </div>
        <p class="text-3xl font-bold font-mono text-foreground">{{ stats.targets_active }}</p>
      </div>
      <div class="rounded-xl border border-border/40 bg-surface/40 p-4">
        <div class="flex items-center gap-2 text-muted-foreground text-xs mb-2">
          <Bug class="h-3.5 w-3.5" />
          Findings abiertos
        </div>
        <p class="text-3xl font-bold font-mono text-warning">{{ stats.findings_open }}</p>
      </div>
      <div class="rounded-xl border border-border/40 bg-surface/40 p-4">
        <div class="flex items-center gap-2 text-muted-foreground text-xs mb-2">
          <Zap class="h-3.5 w-3.5" />
          Scans hoy
        </div>
        <p class="text-3xl font-bold font-mono text-accent">{{ stats.scans_today }}</p>
      </div>
    </div>

    <!-- Targets -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-foreground">Targets</h2>
        <button @click="router.push('/aegis/settings')" class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <Plus class="h-3 w-3" />
          Nuevo target
        </button>
      </div>
      <div v-if="loading" class="space-y-2">
        <Skeleton v-for="i in 3" :key="i" class="h-14 rounded-lg" />
      </div>
      <EmptyState v-else-if="targets.length === 0" title="Sin targets" description="Agregá un target para empezar a escanear" icon="Crosshair" />
      <div v-else class="space-y-2">
        <div v-for="t in targets" :key="t.id" class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/30 px-4 py-3 hover:bg-surface/50 transition-colors">
          <div>
            <p class="text-sm font-medium text-foreground">{{ t.name }}</p>
            <p class="text-xs text-muted-foreground">{{ t.domain || '—' }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface text-muted-foreground border border-border/30">{{ t.status }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Findings -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-foreground">Findings recientes</h2>
      </div>
      <div v-if="loading" class="space-y-2">
        <Skeleton v-for="i in 3" :key="i" class="h-14 rounded-lg" />
      </div>
      <EmptyState v-else-if="findings.length === 0" title="Sin findings" description="Ejecutá un scan para descubrir vulnerabilidades" icon="Bug" />
      <div v-else class="space-y-2">
        <div v-for="f in findings" :key="f.id" class="flex items-center justify-between rounded-lg border border-border/30 bg-surface/30 px-4 py-3 hover:bg-surface/50 transition-colors">
          <div class="flex-1 min-w-0">
            <p class="text-sm text-foreground truncate">{{ f.title }}</p>
          </div>
          <div class="flex items-center gap-2 ml-3">
            <span :class="['text-xs font-mono font-semibold', severityColor(f.severity)]">{{ f.severity }}</span>
            <span class="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface text-muted-foreground border border-border/30">{{ f.status }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
