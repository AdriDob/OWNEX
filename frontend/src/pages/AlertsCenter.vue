<script setup lang="ts">
/**
 * AlertsCenter — "¿Qué necesita atención hoy?"
 * Live warnings + active alerts with one-click resolve.
 * POST /alerts/sweep scans the system for actionable warnings.
 */
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangle,
  BellRing,
  CheckCheck,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Info,
  OctagonAlert,
  RefreshCw,
} from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'
import { useNotificationsStore } from '@/stores/notifications'

interface SweepFinding {
  type: string
  category: string
  title: string
  message: string
  severity: string
  priority: string
  requires_action: boolean
  action_steps: string[]
  ui_path: string
}

interface ActiveAlert {
  id: string
  type: string
  category: string
  title: string
  message: string
  timestamp: string
  severity: string
  priority: string
  requires_action: boolean
  action_steps: string[]
  ui_path: string
  resolved: boolean
}

const notifications = useNotificationsStore()
const loading = ref(true)
const sweeping = ref(false)
const findings = ref<SweepFinding[]>([])
const alerts = ref<ActiveAlert[]>([])

const criticalCount = computed(
  () => findings.value.filter((f) => f.priority === 'critical' || f.severity === 'error').length,
)

const kindIcon = computed(() => ({
  error: OctagonAlert,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle2,
}))

const kindVariant = computed(() => ({
  error: 'error' as const,
  warning: 'warning' as const,
  info: 'info' as const,
  success: 'success' as const,
}))

async function sweep(create = false): Promise<void> {
  sweeping.value = true
  try {
    const res = await api.post<{ findings: SweepFinding[] }>('/alerts/sweep', { create })
    findings.value = (res.findings ?? []).filter((f) => f.type !== 'success')
  } catch {
    findings.value = []
  } finally {
    sweeping.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const res = await api.get<{ alerts: ActiveAlert[] }>('/alerts/active')
    alerts.value = (res.alerts ?? []).filter((a) => !a.resolved)
  } catch {
    alerts.value = []
  }
  await sweep(false)
  loading.value = false
}

async function resolve(id: string): Promise<void> {
  try {
    await api.post('/alerts/resolve', { alert_id: id })
    alerts.value = alerts.value.filter((a) => a.id !== id)
  } catch {
    /* silent */
  }
}

function go(path: string): void {
  if (path) window.location.hash = path
}

function openExternal(path: string): void {
  if (path) window.open(path, '_blank', 'noopener')
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

onMounted(() => {
  notifications.connectWs()
  load()
})
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <!-- Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between animate-in">
      <div>
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Alertas</p>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Centro de Alertas</h1>
        <p class="mt-0.5 text-sm text-muted-foreground">
          <span v-if="criticalCount > 0" class="font-semibold text-destructive">{{ criticalCount }} críticas</span>
          <span v-else-if="findings.length > 0">{{ findings.length }} avisos activos</span>
          <span v-else>Todo bajo control</span>
          · {{ alerts.length }} notificaciones persistentes
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" :disabled="sweeping" @click="sweep(false)">
          <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': sweeping }" />
          Escanear sistema
        </Button>
        <Button variant="outline" size="sm" :disabled="sweeping" @click="sweep(true)">
          <BellRing class="h-3.5 w-3.5" />
          Convertir en alertas
        </Button>
      </div>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- System warnings (live sweep) -->
      <Card v-if="findings.length" class="p-0">
        <div class="flex items-center gap-2 border-b border-border/30 px-4 py-3">
          <AlertTriangle class="h-4 w-4 text-warning" />
          <span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Advertencias del sistema</span>
          <Badge variant="warning" class="ml-auto">{{ findings.length }}</Badge>
        </div>
        <div class="divide-y divide-border/20">
          <div v-for="(f, i) in findings" :key="`${f.title}-${i}`" class="flex items-start gap-3 px-4 py-3">
            <component :is="kindIcon[f.type] ?? Info" class="mt-0.5 h-4 w-4 shrink-0"
              :class="f.type === 'error' ? 'text-destructive' : f.type === 'warning' ? 'text-warning' : 'text-accent'" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold">{{ f.title }}</p>
                <Badge :variant="kindVariant[f.type] ?? 'default'" class="text-[9px] px-1.5 py-0">{{ f.priority }}</Badge>
              </div>
              <p class="mt-0.5 text-xs text-muted-foreground">{{ f.message }}</p>
              <ol v-if="f.action_steps?.length" class="mt-1.5 space-y-0.5">
                <li v-for="(s, j) in f.action_steps" :key="j" class="text-[11px] text-muted-foreground/80">· {{ s }}</li>
              </ol>
            </div>
            <button
              v-if="f.ui_path"
              class="mt-0.5 flex shrink-0 items-center gap-1 text-xs font-medium text-primary hover:underline"
              @click="go(f.ui_path)"
            >
              Ir <ChevronRight class="h-3 w-3" />
            </button>
          </div>
        </div>
      </Card>

      <!-- Persistent alerts -->
      <Card v-if="alerts.length" class="p-0">
        <div class="flex items-center gap-2 border-b border-border/30 px-4 py-3">
          <BellRing class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Alertas activas</span>
          <Badge variant="default" class="ml-auto">{{ alerts.length }}</Badge>
        </div>
        <div class="divide-y divide-border/20">
          <div v-for="a in alerts" :key="a.id" class="flex items-start gap-3 px-4 py-3">
            <component :is="kindIcon[a.type] ?? Info" class="mt-0.5 h-4 w-4 shrink-0"
              :class="a.type === 'error' ? 'text-destructive' : a.type === 'warning' ? 'text-warning' : 'text-accent'" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold">{{ a.title }}</p>
                <span class="text-[10px] text-muted-foreground">{{ formatTime(a.timestamp) }}</span>
              </div>
              <p class="mt-0.5 whitespace-pre-wrap text-xs text-muted-foreground">{{ a.message }}</p>
              <div v-if="a.requires_action && a.action_steps?.length" class="mt-1.5 rounded-md bg-surface/40 px-2 py-1.5">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-warning">Pasos</p>
                <ol class="mt-0.5 list-decimal pl-4">
                  <li v-for="(s, j) in a.action_steps" :key="j" class="text-[11px] text-muted-foreground">{{ s }}</li>
                </ol>
              </div>
              <a v-if="a.ui_path" :href="a.ui_path" class="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline" @click.prevent="go(a.ui_path)">
                Resolver ahora <ExternalLink class="h-3 w-3" />
              </a>
            </div>
            <button class="mt-0.5 shrink-0 rounded p-1 text-muted-foreground hover:text-success" title="Marcar resuelta" @click="resolve(a.id)">
              <CheckCheck class="h-4 w-4" />
            </button>
          </div>
        </div>
      </Card>

      <!-- Empty state -->
      <div v-if="!findings.length && !alerts.length" class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10">
          <CheckCircle2 class="h-8 w-8 text-success" />
        </div>
        <p class="mt-4 text-sm font-semibold">Sin alertas pendientes</p>
        <p class="mt-1 text-xs text-muted-foreground">El sistema escanea periódicamente y te avisará si algo requiere atención.</p>
      </div>
    </template>
  </div>
</template>
