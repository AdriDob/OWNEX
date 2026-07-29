<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Activity, Clock, AlertTriangle, RefreshCw, Filter,
  Bug, FileText, Scan, Brain, Bell, Target, Cpu,
} from '@lucide/vue'

interface TimelineEvent {
  type: string; id: number; label: string
  severity?: string; status?: string; mode?: string
  category?: string; target_id?: number
  timestamp: string
}

const events = ref<TimelineEvent[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const filterType = ref('')
const since = ref('')

const typeIcons: Record<string, any> = {
  finding: Bug, verdict: FileText, scan: Scan, evidence: Activity,
  intelligence: Brain, notification: Bell, target: Target, agent: Cpu,
}

const typeColors: Record<string, string> = {
  finding: 'text-destructive', verdict: 'text-accent', scan: 'text-primary',
  evidence: 'text-success', intelligence: 'text-[#8B5CF6]',
  notification: 'text-warning', target: 'text-[#00A98F]', agent: 'text-[#0D90F4]',
}

const severityColor = (s?: string) => {
  if (!s) return 'bg-primary'
  if (s === 'high' || s === 'critical') return 'bg-destructive'
  if (s === 'medium' || s === 'warning') return 'bg-warning'
  return 'bg-primary'
}

async function fetchData() {
  loading.value = true; error.value = ''
  try {
    const params: Record<string, any> = { limit: 100 }
    if (filterType.value) params.event_type = filterType.value
    if (since.value) params.hours = parseInt(since.value)
    const res = await api.get<{ events: TimelineEvent[]; total: number }>('/operations/timeline', params)
    events.value = res.events || []
    total.value = res.total || 0
  } catch (e: any) {
    error.value = e?.message || 'Error loading timeline'
  } finally { loading.value = false }
}

onMounted(fetchData)

const eventTypes = computed(() => {
  const set = new Set(events.value.map(e => e.type))
  return Array.from(set).sort()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between animate-in">
      <div class="space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">System Intelligence</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Activity Log</h1>
        <p class="text-sm text-muted-foreground">Everything OWNEX is doing — events, tasks, learning, and errors</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3 animate-in">
      <select v-model="filterType" @change="fetchData"
        class="rounded-lg border border-border/60 bg-[#11131f]/60 px-3 py-2 text-xs text-foreground">
        <option value="">All events</option>
        <option v-for="t in eventTypes" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="since" @change="fetchData"
        class="rounded-lg border border-border/60 bg-[#11131f]/60 px-3 py-2 text-xs text-foreground">
        <option value="">Last 72h</option>
        <option value="24">Last 24h</option>
        <option value="168">Last week</option>
        <option value="720">Last 30d</option>
      </select>
      <Button variant="outline" size="sm" @click="fetchData" class="gap-2">
        <RefreshCw class="h-3.5 w-3.5" /> Refresh
      </Button>
    </div>

    <template v-if="loading">
      <div class="space-y-2"><Skeleton v-for="i in 10" :key="i" class="h-12 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" @click="fetchData">Retry</Button>
      </div>
    </template>

    <template v-else-if="events.length === 0">
      <div class="flex flex-col items-center py-20 text-center">
        <Activity class="mb-4 h-10 w-10 text-muted-foreground/50" />
        <p class="text-sm font-semibold text-foreground">No activity recorded</p>
        <p class="mt-1 text-xs text-muted-foreground">Events will appear here as OWNEX works</p>
      </div>
    </template>

    <!-- Timeline -->
    <template v-else>
      <div class="space-y-1 animate-in">
        <div v-for="ev in events" :key="`${ev.type}-${ev.id}-${ev.timestamp}`"
          class="flex items-center gap-4 rounded-lg px-4 py-3 transition-all hover:bg-surface/20">
          <!-- Timeline dot -->
          <div class="relative flex flex-col items-center">
            <div :class="['h-2.5 w-2.5 rounded-full shrink-0', severityColor(ev.severity)]" />
          </div>
          <!-- Icon -->
          <component :is="typeIcons[ev.type] || Activity" class="h-4 w-4 shrink-0" :class="typeColors[ev.type] || 'text-muted-foreground'" />
          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-xs font-medium text-foreground truncate">{{ ev.label }}</span>
              <Badge variant="outline" class="text-[8px]">{{ ev.type }}</Badge>
            </div>
            <div v-if="ev.severity || ev.status" class="flex items-center gap-2 mt-0.5">
              <span v-if="ev.severity" class="text-[10px] font-mono" :class="ev.severity === 'high' || ev.severity === 'critical' ? 'text-destructive' : 'text-muted-foreground'">{{ ev.severity }}</span>
              <span v-if="ev.status && ev.status !== ev.severity" class="text-[10px] text-muted-foreground font-mono">{{ ev.status }}</span>
            </div>
          </div>
          <!-- Time -->
          <span class="shrink-0 font-mono text-[10px] text-muted-foreground">
            {{ new Date(ev.timestamp).toLocaleString() }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>
