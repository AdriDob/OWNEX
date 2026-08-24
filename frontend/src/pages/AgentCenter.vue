<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Activity, Cpu, Play, AlertTriangle } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'

interface AgentHealth {
  agent_id: string;
  name: string;
  capabilities: string[];
  status: string;
  tasks_completed: number;
  tasks_failed: number;
  avg_time_ms: number;
  total_time_ms: number;
  last_event: string | null;
  last_error: string | null;
  running: boolean;
}

interface BusEvent {
  event_id: string;
  event_type: string;
  source: string;
  target: string | null;
  correlation_id: string;
  priority: number;
  timestamp: string;
  payload: Record<string, unknown>;
}

const agents = ref<AgentHealth[]>([])
const events = ref<BusEvent[]>([])
const pipelines = ref<Record<string, any>>({})
const loading = ref(true)
const error = ref<string | null>(null)

let healthInterval: ReturnType<typeof setInterval> | null = null
let pipelineInterval: ReturnType<typeof setInterval> | null = null

const statusColors: Record<string, string> = {
  idle: '#16A34A', working: '#ffffff', waiting: '#A16207', error: '#00d5ff', offline: '#6b7280',
}

const agentIcons: Record<string, string> = {
  coordinator: '🎯', research: '🔍', validator: '✅', exploit: '⚡',
  documentation: '📝', strategy: '🧠', memory: '💾', financial: '💰',
}

async function fetchHealth() {
  try {
    const res = await api.get<{ agents: Record<string, AgentHealth> }>('/agents/health')
    agents.value = Object.values(res.agents || {})
  } catch (e: any) { error.value = e?.message || 'Error al cargar agentes' }
  finally { loading.value = false }
}

async function fetchPipelines() {
  try {
    const res = await api.get<{ pipelines: Record<string, any> }>('/agents/coordinator/pipelines')
    pipelines.value = res.pipelines || {}
  } catch { /* ignore */ }
}

function setupEventStream() {
  let es: EventSource | null = null
  try {
    es = new EventSource('/api/agents/events/stream')
    es.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data) as BusEvent
        events.value = [ev, ...events.value].slice(0, 100)
      } catch { /* ignore */ }
    }
  } catch { /* ignore */ }
  return () => es?.close()
}

const onlineCount = () => agents.value.filter(a => a.running).length

onMounted(() => {
  fetchHealth()
  fetchPipelines()
  healthInterval = setInterval(fetchHealth, 3000)
  pipelineInterval = setInterval(fetchPipelines, 5000)
})

onUnmounted(() => {
  if (healthInterval) clearInterval(healthInterval)
  if (pipelineInterval) clearInterval(pipelineInterval)
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between animate-in">
      <div class="min-w-0">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">System</p>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Agent Center</h1>
        <p class="text-sm text-muted-foreground">{{ onlineCount() }}/{{ agents.length }} agentes en línea</p>
      </div>
      <button
        @click="api.post('/agents/pipeline/start', { target_id: 0, target_name: 'quick-scan' }).catch(() => {})"
        class="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-90"
      >
        <Play class="h-3.5 w-3.5" />
        Start Pipeline
      </button>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 4" :key="i" class="h-40 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <button @click="fetchHealth" class="mt-4 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white">Reintentar</button>
      </div>
    </template>

    <template v-else-if="agents.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Cpu class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay agentes disponibles</p>
        <p class="mt-1 text-xs text-muted-foreground">El sistema de agentes no está activo</p>
      </div>
    </template>

    <template v-else>
      <!-- Agent Status Distribution -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Distribución de Agentes</h3>
        <DoughnutChart
          :labels="Object.keys(statusColors)"
          :data="Object.keys(statusColors).map(s => agents.filter(a => a.status === s).length)"
          :height="200"
        />
      </Card>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div v-for="(agent, i) in agents" :key="agent.agent_id"
          class="stagger-item rounded-xl border border-border/40 bg-surface/50 p-4 transition-all hover:border-primary/30"
          :style="{ '--i': i }"
        >
          <div class="flex items-center gap-3 mb-3">
            <span class="text-2xl">{{ agentIcons[agent.agent_id] || '🤖' }}</span>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-foreground truncate">{{ agent.name }}</p>
              <p class="text-[10px] font-mono text-muted-foreground">{{ agent.agent_id }}</p>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full" :style="{ background: statusColors[agent.status] || '#6b7280', boxShadow: `0 0 6px ${statusColors[agent.status] || '#6b7280'}` }" />
              <span class="text-xs font-medium" :style="{ color: statusColors[agent.status] || '#6b7280' }">{{ agent.status }}</span>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2 mb-3">
            <div>
              <p class="text-[10px] text-muted-foreground">Completed</p>
              <p class="text-sm font-bold text-foreground">{{ agent.tasks_completed }}</p>
            </div>
            <div>
              <p class="text-[10px] text-muted-foreground">Failed</p>
              <p class="text-sm font-bold" :class="agent.tasks_failed > 0 ? 'text-destructive' : 'text-foreground'">{{ agent.tasks_failed }}</p>
            </div>
            <div>
              <p class="text-[10px] text-muted-foreground">Avg Time</p>
              <p class="text-sm font-bold text-foreground">{{ agent.avg_time_ms.toFixed(0) }}ms</p>
            </div>
            <div>
              <p class="text-[10px] text-muted-foreground">Total Time</p>
              <p class="text-sm font-bold text-foreground">{{ agent.total_time_ms.toFixed(0) }}ms</p>
            </div>
          </div>
          <div v-if="agent.last_error" class="mb-2 rounded-md bg-destructive/10 px-2 py-1 text-[11px] text-destructive">
            {{ agent.last_error }}
          </div>
          <div class="flex flex-wrap gap-1">
            <span v-for="cap in agent.capabilities" :key="cap"
              class="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary"
            >{{ cap }}</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <!-- Coordinator Panel -->
        <Card class="animate-in p-4">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Coordinator Activity</p>
          </div>
          <div v-if="Object.keys(pipelines).length === 0" class="py-4 text-center text-xs text-muted-foreground">
            No active pipelines
          </div>
          <div v-for="(info, pid) in pipelines" :key="pid as string"
            class="mb-2 rounded-lg bg-surface/10 px-3 py-2"
          >
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-foreground">{{ (info as any).target_name || '?' }}</span>
              <span class="rounded px-1.5 py-0.5 text-[10px] font-medium"
                :class="(info as any).state === 'completed' ? 'bg-success/15 text-success' : 'bg-primary/15 text-primary'"
              >{{ (info as any).state || '?' }}</span>
            </div>
            <p class="mt-0.5 text-[10px] font-mono text-muted-foreground">{{ (pid as string).slice(0, 12) }}... | retries: {{ (info as any).retries || 0 }}</p>
          </div>
        </Card>

        <!-- Event Stream -->
        <Card class="animate-in p-4 max-h-80 flex flex-col">
          <div class="flex items-center gap-2 mb-3">
            <Activity class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Event Stream</p>
          </div>
          <div class="flex-1 overflow-y-auto space-y-1 text-[11px] font-mono">
            <div v-if="events.length === 0" class="py-4 text-center text-xs text-muted-foreground">
              No events yet
            </div>
            <div v-for="ev in events" :key="ev.event_id"
              class="rounded bg-surface/10 px-2 py-1 border-l-2"
              :style="{ borderLeftColor: ev.priority <= 3 ? '#ffffff' : '#6b7280' }"
            >
              <div class="flex justify-between gap-2">
                <span class="text-primary">{{ ev.event_type }}</span>
                <span class="text-muted-foreground">{{ new Date(ev.timestamp).toLocaleTimeString() }}</span>
              </div>
              <div class="text-muted-foreground">
                {{ ev.source }} → {{ ev.target || '*' }}
                <span class="ml-2 text-[9px]">corr: {{ ev.correlation_id.slice(0, 8) }}</span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </template>
  </div>
</template>
