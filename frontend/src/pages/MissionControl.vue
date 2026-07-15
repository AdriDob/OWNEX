<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import {
  Activity, AlertTriangle, ArrowRight, Bug, Clock, Database,
  DollarSign, Eye, RefreshCw, Shield, ShieldCheck, Sparkles,
  TrendingUp, Zap, Bell, Dices, Bot, Plus, FileText,
  HeartPulse, BarChart3, Cpu, Globe,
} from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'

interface MissionData {
  system: { health_score: number; status: string; timestamp: string }
  apps: Array<{ id: string; name: string; icon: string; version: string; description: string; has_db: boolean; providers: number }>
  next_action: { title: string; why_now: string; effort: string; estimated_reward: number } | null
  priorities: Array<{ type: string; severity: string; title: string; detail: string }>
  ingress: { confirmed: number; pending: number; total_earned: number }
}

interface ActivityItem {
  id: string; type: string; message: string; timestamp: string; severity?: string
}

interface SystemStatus {
  scheduler: string; agents: number; pipelines: number; events_24h: number
}

const router = useRouter()
const data = ref<MissionData | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const autoRefresh = ref(true)
const activity = ref<ActivityItem[]>([])
const sysStatus = ref<SystemStatus | null>(null)
const bottlenecks = ref<any[]>([])
let refreshInterval: ReturnType<typeof setInterval> | null = null

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const appIcons: Record<string, any> = {
  cateye: Eye, atlas: TrendingUp, odyssey: Dices, hermes: Bot, aegis: Shield,
}

const severityColor = (s: string) => {
  const map: Record<string, string> = { high: 'text-destructive', warning: 'text-warning', medium: 'text-accent', info: 'text-muted-foreground' }
  return map[s] || 'text-muted-foreground'
}

const healthColor = (score: number) => {
  if (score >= 90) return 'text-success'
  if (score >= 70) return 'text-warning'
  return 'text-destructive'
}

const effortColor = (e: string) => {
  const map: Record<string, string> = { low: 'text-success', medium: 'text-warning', high: 'text-destructive' }
  return map[e] || 'text-muted-foreground'
}

const quickActions = [
  { id: 'new-target', label: 'Nuevo Target', icon: Plus, path: '/discovery' },
  { id: 'findings', label: 'Hallazgos', icon: Bug, path: '/findings' },
  { id: 'reports', label: 'Reportes', icon: FileText, path: '/reports' },
  { id: 'pipeline', label: 'Pipeline', icon: BarChart3, path: '/pipelines' },
  { id: 'health', label: 'Health Center', icon: HeartPulse, path: '/health-center' },
  { id: 'agents', label: 'Agentes', icon: Cpu, path: '/agents' },
]

interface ActivityEvent {
  id: string; type: string; message: string; timestamp: string; severity?: string
}

async function fetchAll() {
  try {
    const [missionRes, actRes, sysRes, btlRes] = await Promise.allSettled([
      api.get<MissionData>('/mission/status'),
      api.get<{ items: ActivityEvent[] }>('/activity'),
      api.get<SystemStatus>('/system/status'),
      api.get<{ bottlenecks: any[] }>('/evolution/bottlenecks?min_hours=0.1'),
    ])
    if (missionRes.status === 'fulfilled') {
      data.value = missionRes.value
    }
    if (actRes.status === 'fulfilled') {
      const items = actRes.value.items || []
      activity.value = items.slice(0, 10).map((e, i) => ({
        id: e.id || `act-${i}`,
        type: e.type || 'event',
        message: e.message || 'Evento registrado',
        timestamp: e.timestamp || new Date().toISOString(),
        severity: e.severity || 'info',
      }))
    }
    if (sysRes.status === 'fulfilled') {
      sysStatus.value = sysRes.value
    }
    if (btlRes.status === 'fulfilled') {
      bottlenecks.value = btlRes.value.bottlenecks || []
    }
    error.value = null
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAll()
  refreshInterval = setInterval(() => {
    if (autoRefresh.value) fetchAll()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

const systemIsOk = computed(() => data.value && data.value.system.health_score >= 70)
</script>

<template>
  <div class="space-y-6 animate-in">
    <LoadingState v-if="loading" />

    <ErrorState
      v-else-if="error && !data"
      title="Error al cargar Mission Control"
      :message="error"
      :retry="fetchAll"
    />

    <template v-else-if="data">
      <!-- Header -->
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1 min-w-0">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] font-bold tracking-widest text-primary">ORION MISSION CONTROL</span>
            <span :class="['h-1.5 w-1.5 rounded-full', systemIsOk ? 'bg-success animate-pulse' : 'bg-destructive']" />
          </div>
          <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
          <p class="text-xs text-muted-foreground flex items-center gap-2">
            <Clock class="h-3 w-3" />
            {{ data.system.timestamp ? new Date(data.system.timestamp).toLocaleString() : '—' }}
            <button @click="fetchAll" class="text-primary hover:underline flex items-center gap-1">
              <RefreshCw class="h-3 w-3" /> Actualizar
            </button>
          </p>
        </div>

        <!-- Health Score -->
        <div class="shrink-0 flex flex-col items-center gap-1 rounded-xl card-base px-6 py-3">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider uppercase">Salud del sistema</span>
          <span :class="['text-4xl font-bold font-mono', healthColor(data.system.health_score)]">{{ data.system.health_score }}</span>
          <span class="font-mono text-[9px] text-muted-foreground uppercase">{{ data.system.status }}</span>
        </div>
      </div>

      <!-- Quick Actions Strip -->
      <div class="flex flex-wrap items-center gap-2 rounded-xl card-base px-4 py-3">
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider text-muted-foreground mr-1">Acciones rápidas</span>
        <button
          v-for="qa in quickActions" :key="qa.id"
          @click="router.push(qa.path)"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-foreground/80 hover:text-foreground hover:bg-primary/10 border border-border/30 transition-colors"
        >
          <component :is="qa.icon" class="h-3.5 w-3.5" />
          {{ qa.label }}
        </button>
      </div>

      <!-- Priorities -->
      <div v-if="data.priorities.length > 0" class="rounded-xl card-base card-highlight border-l-warning p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Bell class="h-4 w-4 text-warning" />
          <span class="font-mono text-xs font-semibold text-foreground">Cosas que requieren atención</span>
        </div>
        <div class="space-y-2">
          <div v-for="(p, i) in data.priorities" :key="i" class="flex items-center gap-3 rounded-lg bg-surface/30 px-3 py-2.5">
            <div :class="['h-2 w-2 rounded-full shrink-0', p.severity === 'high' ? 'bg-destructive' : p.severity === 'warning' ? 'bg-warning' : p.severity === 'medium' ? 'bg-accent' : 'bg-muted']" />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-foreground truncate">{{ p.title }}</p>
              <p class="text-xs text-muted-foreground truncate">{{ p.detail }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Ingress & Quick Stats -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div class="rounded-xl card-base p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">Salud</span>
            <ShieldCheck class="h-4 w-4 text-success" />
          </div>
          <p class="font-mono text-xl font-bold text-foreground">{{ data.system.health_score }}<span class="text-xs text-muted-foreground">/100</span></p>
        </div>
        <div class="rounded-xl card-base p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">Confirmado</span>
            <DollarSign class="h-4 w-4 text-gold" />
          </div>
          <p class="font-mono text-xl font-bold text-foreground">${{ data.ingress.confirmed.toLocaleString() }}</p>
        </div>
        <div class="rounded-xl card-base p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">Pendiente</span>
            <Clock class="h-4 w-4 text-warning" />
          </div>
          <p class="font-mono text-xl font-bold text-warning">${{ data.ingress.pending.toLocaleString() }}</p>
        </div>
        <div class="rounded-xl card-base p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">Total</span>
            <Database class="h-4 w-4 text-accent" />
          </div>
          <p class="font-mono text-xl font-bold text-accent">${{ data.ingress.total_earned.toLocaleString() }}</p>
        </div>
      </div>

      <!-- Two-column: Next Action + System Status -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <!-- Next Action (spans 2 cols) -->
        <div v-if="data.next_action" class="lg:col-span-2 rounded-xl card-base card-highlight border-l-primary p-5 animate-in">
          <div class="flex items-start gap-4">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Zap class="h-5 w-5" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-primary mb-1">
                <Sparkles class="h-3 w-3" />
                <span>Próxima acción recomendada</span>
              </div>
              <h3 class="text-base font-semibold text-foreground">{{ data.next_action.title }}</h3>
              <p class="mt-1 text-xs text-muted-foreground">{{ data.next_action.why_now }}</p>
              <div class="mt-3 flex flex-wrap gap-4">
                <span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                  Esfuerzo: <span :class="['font-semibold', effortColor(data.next_action.effort)]">{{ data.next_action.effort }}</span>
                </span>
                <span v-if="data.next_action.estimated_reward" class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                  Recompensa estimada: <span class="font-semibold text-gold">${{ data.next_action.estimated_reward }}</span>
                </span>
              </div>
            </div>
            <ArrowRight class="mt-2 h-5 w-5 shrink-0 text-muted-foreground" />
          </div>
        </div>

        <!-- System Status Mini Panel -->
        <div class="rounded-xl card-base p-4 space-y-3">
          <div class="flex items-center gap-2 mb-1">
            <Activity class="h-4 w-4 text-accent" />
            <span class="font-mono text-xs font-semibold text-foreground">Estado del sistema</span>
          </div>
          <div v-if="!sysStatus" class="space-y-2">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-3/4" />
            <Skeleton class="h-4 w-1/2" />
          </div>
          <div v-else class="space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Scheduler</span>
              <span :class="['font-mono font-medium', sysStatus.scheduler === 'running' ? 'text-success' : 'text-destructive']">
                {{ sysStatus.scheduler === 'running' ? 'Activo' : 'Detenido' }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Agentes</span>
              <span class="font-mono font-medium text-foreground">{{ sysStatus.agents }} activos</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Pipelines</span>
              <span class="font-mono font-medium text-foreground">{{ sysStatus.pipelines }} en curso</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-muted-foreground">Eventos 24h</span>
              <span class="font-mono font-medium text-foreground">{{ sysStatus.events_24h }}</span>
            </div>
          </div>
          <button @click="router.push('/health-center')" class="w-full mt-1 text-[10px] text-primary hover:underline font-mono text-center">
            Ver health center →
          </button>
        </div>
      </div>

      <!-- Bottlenecks section -->
      <Card v-if="bottlenecks.length > 0" class="card-base">
        <CardHeader>
          <div class="flex items-center gap-2">
            <BarChart3 class="h-4 w-4 text-warning" />
            <CardTitle class="text-xs">Cuellos de botella detectados</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <div v-for="b in bottlenecks" :key="b.name"
              class="flex items-center justify-between rounded-lg card-base px-3 py-2.5"
            >
              <div class="min-w-0 flex-1">
                <p class="text-xs font-medium text-foreground truncate">{{ b.name }}</p>
                <p class="font-mono text-[10px] text-muted-foreground">
                  {{ b.runs }} ejecuciones · {{ b.total_hours.toFixed(1) }}h
                </p>
              </div>
              <span :class="['font-mono text-[10px] px-1.5 py-0.5 rounded', b.status === 'warning' ? 'bg-warning/20 text-warning' : 'bg-muted/20 text-muted-foreground']">
                {{ b.avg_duration_ms ? (b.avg_duration_ms / 1000).toFixed(1) + 's' : '—' }}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Activity Feed -->
      <Card class="card-base">
        <CardHeader>
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" />
            <CardTitle class="text-xs">Actividad reciente</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div v-if="activity.length === 0" class="py-6 text-center">
            <p class="font-mono text-xs text-muted-foreground">Sin actividad reciente</p>
          </div>
          <div v-else class="space-y-1.5">
            <div v-for="a in activity" :key="a.id"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-xs hover:bg-surface/20 transition-colors"
            >
              <span class="h-1.5 w-1.5 shrink-0 rounded-full"
                :class="a.severity === 'high' ? 'bg-destructive' : a.severity === 'warning' ? 'bg-warning' : 'bg-primary'"
              />
              <span class="flex-1 text-foreground truncate">{{ a.message }}</span>
              <span class="shrink-0 font-mono text-[10px] text-muted-foreground">
                {{ new Date(a.timestamp).toLocaleTimeString() }}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Apps Grid -->
      <div>
        <h2 class="font-mono text-xs font-semibold text-foreground mb-3">Módulos del sistema</h2>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <div v-for="app in data.apps" :key="app.id"
            @click="router.push(`/${app.id === 'cateye' ? '' : app.id}/`)"
            class="rounded-xl border border-border/30 bg-surface/30 p-4 hover:bg-surface/50 hover:border-primary/20 transition-all cursor-pointer"
          >
            <div class="flex items-center gap-2 mb-2">
              <component :is="appIcons[app.id] || Activity" class="h-4 w-4 text-primary" />
              <span class="text-sm font-semibold text-foreground">{{ app.name }}</span>
            </div>
            <p class="text-[10px] text-muted-foreground line-clamp-2">{{ app.description }}</p>
            <div class="mt-2 flex items-center gap-2">
              <Badge variant="outline" class="text-[8px] px-1.5 py-0">{{ app.version }}</Badge>
              <span v-if="app.has_db" class="text-[8px] text-accent font-mono">● DB</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
