<script setup lang="ts">
import { Activity, AlertTriangle, CheckCircle2, Clock, HeartPulse, RefreshCw, ShieldCheck, XCircle } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

interface HealthSnapshot {
  status: string
  timestamp: string
  checks: Record<string, boolean>
  details: Record<string, any>
}

interface HealthCheckDef {
  name: string
  category: string
  last_ok: boolean
  last_error: string
}

const { toast } = useToast()
const currentStatus = ref<string>('unknown')
const currentScore = ref(0)
const checks = ref<HealthCheckDef[]>([])
const history = ref<HealthSnapshot[]>([])
const loading = ref(true)
const running = ref(false)

const statusColor = (s: string) => {
  const map: Record<string, string> = { green: 'text-success', yellow: 'text-warning', red: 'text-destructive' }
  return map[s] || 'text-muted-foreground'
}

const statusBg = (s: string) => {
  const map: Record<string, string> = {
    green: 'bg-success/10 border-success/30',
    yellow: 'bg-warning/10 border-warning/30',
    red: 'bg-destructive/10 border-destructive/30',
  }
  return map[s] || 'bg-surface/40 border-border/40'
}

const healthScore = computed(() => {
  const all = checks.value
  if (!all.length) return 0
  const ok = all.filter((c) => c.last_ok).length
  return Math.round((ok / all.length) * 100)
})

const byCategory = computed(() => {
  const groups: Record<string, HealthCheckDef[]> = {}
  for (const c of checks.value) {
    const cat = c.category || 'system'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(c)
  }
  return groups
})

const categories = computed(() => Object.keys(byCategory.value))

async function fetchAll() {
  loading.value = true
  try {
    const [healthRes, checksRes, historyRes] = await Promise.allSettled([
      fetch('/api/core/health'),
      fetch('/api/core/health/checks'),
      fetch('/api/core/health/history?limit=20'),
    ])
    if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
      const data = await healthRes.value.json()
      currentStatus.value = data.status || 'unknown'
      currentScore.value = data.score || 0
    }
    if (checksRes.status === 'fulfilled' && checksRes.value.ok) {
      const data = await checksRes.value.json()
      checks.value = (data.checks || []).map((c: any) => ({
        name: c.name || c[0],
        category: c.category || 'system',
        last_ok: c.last_ok ?? true,
        last_error: c.last_error || '',
      }))
    }
    if (historyRes.status === 'fulfilled' && historyRes.value.ok) {
      const data = await historyRes.value.json()
      history.value = (data.history || []).slice(0, 20)
    }
  } catch (e) {
    toast.error('Error', 'No se pudo cargar el health center')
  } finally {
    loading.value = false
  }
}

async function runChecks() {
  running.value = true
  try {
    const res = await fetch('/api/core/health/run', { method: 'POST' })
    if (res.ok) {
      toast.success('Health Check', 'Checks ejecutados correctamente')
      await fetchAll()
    }
  } catch {
    toast.error('Error', 'Falló la ejecución de checks')
  } finally {
    running.value = false
  }
}

function statusIcon(ok: boolean) {
  return ok ? CheckCircle2 : XCircle
}

function statusIconColor(ok: boolean) {
  return ok ? 'text-success' : 'text-destructive'
}

onMounted(fetchAll)
</script>

<template>
  <div class="p-6 space-y-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
          <HeartPulse class="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-foreground">Health Center</h1>
          <p class="text-xs text-muted-foreground">Monitor de salud del sistema</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button size="sm" variant="outline" @click="fetchAll">
          <RefreshCw class="h-3.5 w-3.5" /> Actualizar
        </Button>
        <Button size="sm" @click="runChecks" :loading="running">
          <Activity class="h-3.5 w-3.5" /> Ejecutar checks
        </Button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-32 rounded-xl" />
      <Skeleton v-for="i in 3" :key="i" class="h-24 rounded-xl" />
    </div>

    <template v-else>
      <!-- Big Status Card -->
      <div :class="['rounded-xl border-2 p-6 text-center', statusBg(currentStatus)]">
        <div class="flex justify-center mb-2">
          <ShieldCheck class="h-12 w-12" :class="statusColor(currentStatus)" />
        </div>
        <p class="text-5xl font-bold font-mono" :class="statusColor(currentStatus)">{{ healthScore }}<span class="text-xl text-muted-foreground">/100</span></p>
        <p class="mt-2 font-mono text-sm uppercase tracking-wider" :class="statusColor(currentStatus)">{{ currentStatus }}</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ checks.filter(c => c.last_ok).length }}/{{ checks.length }} checks pasando</p>
      </div>

      <!-- Category Grid -->
      <div v-for="cat in categories" :key="cat" class="space-y-2">
        <h2 class="font-mono text-xs font-semibold text-foreground uppercase tracking-wider">{{ cat }}</h2>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="c in byCategory[cat]" :key="c.name"
            class="flex items-center gap-3 rounded-xl border border-border/30 bg-surface/30 px-4 py-3"
          >
            <component :is="statusIcon(c.last_ok)" :class="['h-5 w-5 shrink-0', statusIconColor(c.last_ok)]" />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-foreground truncate">{{ c.name }}</p>
              <p v-if="c.last_error" class="text-[10px] text-destructive truncate">{{ c.last_error }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- History -->
      <div v-if="history.length > 0" class="space-y-2">
        <h2 class="font-mono text-xs font-semibold text-foreground uppercase tracking-wider">Historial</h2>
        <div class="rounded-xl border border-border/30 bg-surface/30 overflow-hidden">
          <div v-for="(h, i) in history" :key="i" class="flex items-center gap-3 px-4 py-2.5 border-b border-border/20 last:border-0">
            <div :class="['h-2.5 w-2.5 rounded-full shrink-0', h.status === 'green' ? 'bg-success' : h.status === 'yellow' ? 'bg-warning' : 'bg-destructive']" />
            <span class="font-mono text-xs text-muted-foreground">{{ new Date(h.timestamp).toLocaleString() }}</span>
            <Badge :variant="h.status === 'green' ? 'success' : h.status === 'yellow' ? 'warning' : 'destructive'" class="text-[9px] px-1.5 py-0">{{ h.status }}</Badge>
            <span class="font-mono text-[10px] text-muted-foreground ml-auto">{{ Object.values(h.checks).filter(Boolean).length }}/{{ Object.keys(h.checks).length }} ok</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
