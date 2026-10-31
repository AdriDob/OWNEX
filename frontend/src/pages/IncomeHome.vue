<script setup lang="ts">
/**
 * OWNEX CEO HOME — Income Command Center ('/', 2026-08-25).
 * Responde en <60s sin documentación: ¿cuánto gano? ¿qué hago? ¿por qué?
 * ¿qué hace OWNEX? ¿qué hago yo? ¿cuándo cobro?
 * Datos reales únicamente: /applications/income-plan + /mission/status.
 */

import {
  AlertTriangle,
  Bot,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  CircleUser,
  Clock,
  ExternalLink,
  Target,
  TrendingUp,
  Wallet,
  Zap,
  DollarSign,
  Shield,
  Activity,
  BarChart3,
  Users,
  RotateCcw,
  Moon,
  Sun,
  Archive,
  AlertCircle,
  Calendar,
  Flag,
  Download,
  Mail,
  Link,
  Phone,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import OneActionCard from '@/components/autopilot/OneActionCard.vue'
import DailyDigest from '@/components/daily/DailyDigest.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import ComputerUseWidget from '@/components/computer-use/ComputerUseWidget.vue'
import { useHuntStore } from '@/stores/hunt'
import { api } from '@/lib/api'
import {
  type CapitalSnapshot,
  fetchAiCenter,
  fetchCapitalSnapshot,
  fetchCareerStatus,
  fetchIncomePlan,
  fetchMissionStatus,
  fetchPlatformRanking,
  fetchRevenueTimeline,
  fetchZeroBarrierStats,
  type IncomePlanAction,
  type IncomePlanState,
  type PlatformRankingItem,
  fetchDirectWorkWorkBank,
} from '@/services/ownexData'

/** FEATURE PARITY: snapshot de capital (SSOT patrimonio) + estado IA. */
const capital = ref<CapitalSnapshot | null>(null)
const aiOk = ref<boolean | null>(null)
const career = ref<any>(null)
const zbStats = ref<any>(null)
const timeline = ref<any>(null)
const platformRanking = ref<PlatformRankingItem[]>([])

/** Daily return digest — what changed since last visit. */
interface SessionDigest {
  newOpportunities: number
  pendingUsd: number
  aiHealthy: boolean
  hoursSince: number
}

const digest = ref<SessionDigest | null>(null)

function computeDigest(): void {
  const LAST_VISIT_KEY = 'ownex_last_visit'
  const lastVisit = Number(localStorage.getItem(LAST_VISIT_KEY) || '0')
  const now = Date.now()
  const hoursSince = (now - lastVisit) / (1000 * 60 * 60)
  localStorage.setItem(LAST_VISIT_KEY, String(now))

  // Only show digest if >4h since last visit
  if (!lastVisit || hoursSince < 4) {
    digest.value = null
    return
  }

  try {
    Promise.allSettled([
      api.get<{ finding_count?: number; target_count?: number }>('/overview'),
      api.get<{ pending_amount?: number }>('/revenue/summary'),
    ]).then(([findRes, revRes]) => {
      const findings = findRes.status === 'fulfilled' ? findRes.value.finding_count || 0 : 0
      const pending = revRes.status === 'fulfilled' ? revRes.value.pending_amount || 0 : 0
      if (!findings && !pending) {
        digest.value = null
        return
      }
      digest.value = {
        newOpportunities: findings,
        pendingUsd: pending,
        aiHealthy: aiOk.value !== false,
        hoursSince: Math.round(hoursSince),
      }
    })
  } catch {
    digest.value = null
  }
}

/** Dinero REALIZADO (cobrado/pagado) — separado por contrato del esperado.
 *  Fuentes: /payment-tracker (webhooks/polling) + /revenue/summary (payouts). */
interface RealizedRevenue {
  total_earned: number
  pending_amount: number
  earnings_30d: number
  has_any: boolean
}

const loading = ref(true)
const error = ref<string | null>(null)
const income = ref<IncomePlanState | null>(null)
const system = ref<{ health: number; status: string } | null>(null)
const realized = ref<RealizedRevenue | null>(null)

const hunt = useHuntStore()
const workBankReady = ref(0)

interface IncomeGoalPlan {
  status: string
  target: { amount_usd: number; period: string }
  required_opportunities: number
  required_hours_per_week: number
  required_hours_per_day: number
  recommended_sources: string[]
  probability_of_success: number
  risk_factors: string[]
  fallback_plan: string | null
  progress: {
    earned_this_period: number
    pending_amount: number
    progress_pct: number
    days_remaining: number
    on_track: boolean
    required_daily_rate: number
    actual_daily_rate: number
  }
}
const goalText = ref('quiero ganar 10k este mes')
const goalPlan = ref<IncomeGoalPlan | null>(null)
const goalLoading = ref(false)
const goalError = ref<string | null>(null)

// 🧠 MINDRIFT TRACKING — co-pilot de gestión (NO ejecuta tasks, solo monitoriza)
// Contrato real de la fuente de Mindrift: tareas abiertas (no métricas de pago).
// Los campos que la UI muestra sin datos reales se dejan explícitos,
// sin rellenar con valores inventados.
const mindrift = ref({
  // Métricas que la UI consultaba (fallaban: backend sin endpoint)
  // - tasks_available, tasks_this_week, hours_this_week, earnings_this_week,
  //   earnings_per_hour, next_payout_date, next_payout_cycle, assessment_deadline,
  //   assessment_status, last_payout, weekly_history, new_tasks
  // Estado real de la integración (GET /applications/{platform}/status)
  // (TODO: /applications/{platform}/status solo existe para income/plan.
  //  Por ahora el estado se infiere de la app y de la fuente, y se deja
  //  'no conectada' hasta que el backend la sirva como real.)
  connection: 'unknown' as const, // unknown | connected | disconnected | needs_manual_setup
  status: 'desconocido', // Estado visible de la fuente actual
  connectionState: 'unknown', // polling | connected | disconnected | error
  lastPoll: 0,
})

// Polling interval: check every 15 minutes (900000ms) when visible
const MINDRIFT_POLL_INTERVAL = 900000
// Mindrift polling: NO se consulta /mindrift/status porque ese
// endpoint no existe en backend (la integración real es:
// MindriftAdapter -> /api/mindrift/tasks/available, sin métricas de pago).
// El estado real de la aplicación de la fuente se lee vía
// GET /applications/mindrift/status (GET de la aplicación existente).
function startMindriftPolling(): void {
  // No polling periódico: la fuente real (MindriftAdapter) se sincroniza
  // vía el punto de integración (cron / operación) y el estado de la
  // aplicación se lee soporte (cada vez que el backend lo responde).
}

// Sources status tracking (polling every 30 min)
const sourcesStatus = ref<Record<string, string>>({
  // 🟢 Grupo 1: Tareas recurrentes (4 fuentes, sin entrevista obligatoria)
  // Prioridad #1: Outlier - Scale AI, assessment por proyecto escrito
  outlier: 'desconocido',              // ✅ $25-50/hr coding, AirTM → MP/Santander · semanal
  // Prioridad #2: Mindrift - Toloka, all-access + specialized
  mindrift: 'polling activO',          // ✅ $15-100/hr, quincenal (1 y 15), Payoneer/PayPal
  // Prioridad #3: RemoExperts (REX) - Entry Exam escrito + onboarding pagado
  remoexperts: 'desconocido',        // ✅ $25-150/hr, mensual, Payoneer/Wise, Entry Exam escrito
  // Prioridad #4: OneForma (Centific) - qualification tests escritos
  oneforma: 'desconocido',            // ✅ $15-32/hr, mensual, Payoneer/PayPal, 100+ países
  // 🟢 Grupo 2: Bounties y recompensas (3 fuentes, KYC permitido)
  // Prioridad #5: HackerOne - bug bounties, pago PayPal/Bank/BTC/USDC
  hackerone: 'desconocido',          // ✅ KYC permitido (obligatorio u opcional segun fuente)
  // Prioridad #6: Bugcrowd - bug bounties, PayPal compatible AR
  bugcrowd: 'desconocido',           // ✅ PayPal compatible, formulario fiscal requerido (permitido)
  // Prioridad #7: Intigriti - bug bounties, PayPal/Payoneer/Bank
  intigriti: 'desconocido',          // ✅ PayPal admite recepción y retiro desde Argentina
  // Notification when new high-score opportunities detected
  notification: ref<{ type: 'success' | 'warning' | 'info'; message: string; timeout?: number } | null>(null),
  // ⚪ Grupo 3: Herramientas de descubrimiento (2 fuentes)
  // bountyRadar: 'desconocido',      // ✅ 47 issues verificados (29 oct), 12 con pago conocido
  // issuefinder: 'desconocido',        // ✅ GitHub issues con recompensas monetarias
})

async function fetchSourcesStatus(): Promise<void> {
  try {
    // 🟢 Grupo 1: Tareas recurrentes (4 fuentes)

    // Prioridad #1: Outlier - Scale AI
    try {
      const olRes = await api.get('/sources/outlier')
      // Status: 'activo' = roles disponibles, 'desconocido' = sin conexión
      // Badge: 'AirTM' = pago a MP/Santander/BBVA (minutos)
      // Ciclo: Semanal (martes procesa, viernes llega)
      // Tasa: $25-50/hr coding (Argentina-based posting)
      sourcesStatus.value.outlier = olRes.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.outlier = 'sin conexión'
    }

    // Prioridad #2: Mindrift - Toloka
    // La fuente real expone /mindrift/status o /sources/mindrift; el backend
    // NO los implementa actualmente, así que el estado de la aplicación se
    // infiere de la app y se deja como 'no conectada' hasta que el backend
    // los exponga con los datos reales.
    try {
      // El backend NO expone /sources/mindrift. Si lo hiciera, se usaría:
      //   const mRes = await api.get('/sources/mindrift')
      //   sourcesStatus.value.mindrift = mRes.data?.status || 'no disponible'
      sourcesStatus.value.mindrift = 'no conectada'
    } catch {
      sourcesStatus.value.mindrift = 'sin conexión'
    }

    // Prioridad #3: RemoExperts (REX)
    try {
      const reRes = await api.get('/sources/remoexperts')
      // Status: 'activo' = proyectos disponibles
      // Tasa: $25-150/hr, mensual
      // Pago: Payoneer/Wise
      // Proceso: Registro + Entry Exam (15-20 min, escrito, 1 intento) + ID
      // Onboarding: pagado
      sourcesStatus.value.remoexperts = reRes.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.remoexperts = 'sin conexión'
    }

    // Prioridad #4: OneForma (Centific)
    try {
      const oFRes = await api.get('/sources/oneforma')
      // Status: 'activo' = proyectos disponibles
      // Tasa: $15-32/hr, mensual
      // Pago: Payoneer/PayPal
      // Proceso: Registro + qualification tests (escritos). Sin entrevista.
      sourcesStatus.value.oneforma = oFRes.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.oneforma = 'sin conexión'
    }

    // 🟢 Grupo 2: Bounties y recompensas (3 fuentes, KYC permitido)

    // Prioridad #5: HackerOne - bug bounties
    try {
      const h1Res = await api.get('/sources/hackerone')
      // Status: 'activo' = bounties disponibles
      // Pago: PayPal/Bank transfer/BTC/USDC
      // KYC: permitido (obligatorio u opcional segun fuente)
      // Argentina: route via Binance USDC/BTC → AR
      sourcesStatus.value.hackerone = h1Res.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.hackerone = 'sin conexión'
    }

    // Prioridad #6: Bugcrowd - bug bounties
    try {
      const bcRes = await api.get('/sources/bugcrowd')
      // Status: 'activo' = bounties disponibles
      // Pago: PayPal/Bank transfer
      // PayPal: compatible Argentina (recepción y retiro)
      // KYC: formulario fiscal requerido (permitido)
      sourcesStatus.value.bugcrowd = bcRes.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.bugcrowd = 'sin conexión'
    }

    // Prioridad #7: Intigriti - bug bounties
    try {
      const igRes = await api.get('/sources/intigriti')
      // Status: 'activo' = bounties disponibles
      // Pago: PayPal/Payoneer/Bank transfer
      // PayPal: admite recepción y retiro desde Argentina
      // KYC: según programa, permitido
      sourcesStatus.value.intigriti = igRes.data?.status || 'desconocido'
    } catch {
      sourcesStatus.value.intigriti = 'sin conexión'
    }

  } catch {
    // Silencioso: fallo de polling no rompe el dashboard
  }
}

// Start polling when component mounts
onMounted(() => {
  startMindriftPolling()
  fetchSourcesStatus()
})

// Cleanup on unmount
onBeforeUnmount(() => {
  stopMindriftPolling()
})

/** Timer manual para Mindrift: trackear horas por task */
interface MindriftTimer {
  taskId: string | null
  startedAt: number | null
  elapsedMs: number // acumulado mientras está running
  isRunning: boolean
}

const mindriftTimer = ref<MindriftTimer>({
  taskId: null,
  startedAt: null,
  elapsedMs: 0,
  isRunning: false,
})

function startMindriftTimer(taskId: string): void {
  if (mindriftTimer.value.isRunning) return // already running
  mindriftTimer.value = {
    taskId,
    startedAt: Date.now(),
    elapsedMs: mindriftTimer.value.elapsedMs, // preserve accumulated time
    isRunning: true,
  }
  // Store start time in localStorage for persistence across refresh
  localStorage.setItem('mindrift_timer_start', String(mindriftTimer.value.startedAt))
  localStorage.setItem('mindrift_timer_task', String(taskId))
}

function stopMindriftTimer(): void {
  if (!mindriftTimer.value.isRunning) return
  const now = Date.now()
  const durationMs = now - (mindriftTimer.value.startedAt || now)
  mindriftTimer.value = {
    taskId: mindriftTimer.value.taskId,
    startedAt: null,
    elapsedMs: mindriftTimer.value.elapsedMs + durationMs,
    isRunning: false,
  }
  localStorage.removeItem('mindrift_timer_start')
  localStorage.removeItem('mindrift_timer_task')
  // TODO: submit horas al backend / registrar en ledger USD
  // Por ahora solo registramos en el frontend
}

function resetMindriftTimer(): void {
  mindriftTimer.value = {
    taskId: null,
    startedAt: null,
    elapsedMs: 0,
    isRunning: false,
  }
  localStorage.removeItem('mindrift_timer_start')
  localStorage.removeItem('mindrift_timer_task')
}

// Restore timer state from localStorage if refreshed
onMounted(() => {
  const storedStart = localStorage.getItem('mindrift_timer_start')
  const storedTask = localStorage.getItem('mindrift_timer_task')
  if (storedStart && storedTask) {
    mindriftTimer.value = {
      taskId: storedTask,
      startedAt: Number(storedStart),
      elapsedMs: mindriftTimer.value.elapsedMs,
      isRunning: true,
    }
  }
})

onBeforeUnmount(() => {
  stopMindriftPolling()
})

async function askGoal(): Promise<void> {
  if (!goalText.value.trim() || goalLoading.value) return
  goalLoading.value = true
  goalError.value = null
  try {
    goalPlan.value = await api.post<IncomeGoalPlan>('/copilot/income-goal', { message: goalText.value })
  } catch {
    goalError.value = 'No se pudo generar el plan. Probá: "quiero ganar 10k este mes".'
    goalPlan.value = null
  } finally {
    goalLoading.value = false
  }
}

const usd = (n: number): string => `$${Math.round(n).toLocaleString('es-AR')}`
const rangeLabel = (r: { low: number; high: number }): string =>
  r.low === r.high ? usd(r.low) : `${usd(r.low)}–${usd(r.high)}`

// Formatea elapsed ms a formato hh:mm o mm:ss
const formatElapsed = (ms: number): string => {
  const totalSec = Math.floor(ms / 1000)
  const hrs = Math.floor(totalSec / 3600)
  const mins = Math.floor((totalSec % 3600) / 60)
  if (hrs > 0) return `${hrs}h ${mins}m`
  return `${mins}min`
}

const horizons = {
  today: 'HOY',
  week: 'ESTA SEMANA',
  fortnight: 'QUINCENA',
  month: 'MES',
} as const

const statusVariant = computed<'success' | 'warning' | 'error'>(() => {
  const s = system.value?.status.toLowerCase()
  if (!s || s === 'unknown') return 'warning'
  if (['healthy', 'operational', 'ready'].includes(s)) return 'success'
  if (['degraded', 'starting', 'scanning', 'processing', 'waiting'].includes(s)) return 'warning'
  return 'error'
})

/** 🤖 Lo que OWNEX hace solo (estado real del plan, no métricas decorativas). */
const automation = computed(() => {
  const t = income.value?.tracks
  return [
    {
      done: true,
      text: `Descubriendo y rankeando por $/hora humana (${(t?.active.first_day_progress_pct ?? 0) > 0 ? 'guía first-day activa' : 'radar de fuentes curadas'})`,
    },
    {
      done: true,
      text: `Work Bank: ${t?.active.workbank_ready_to_deliver ?? 0} entrega(s) lista(s)`,
    },
    {
      done: (t?.passive.accepted_streams?.length ?? 0) > 0,
      text:
        (t?.passive.accepted_streams?.length ?? 0) > 0
          ? `Streams aprobados: ${t?.passive.accepted_streams?.join(', ')}`
          : 'Postulaciones AI-training en curso (sin stream aprobado aún)',
    },
    {
      done: false,
      text: `Esperando plataforma: ${income.value?.phases.waiting.map((w) => w.name).join(', ') || 'ninguna'}`,
    },
  ]
})

/** 👤 Tus acciones humanas concretas (cola this_week del plan). */
const humanActions = computed<Array<IncomePlanAction>>(() => income.value?.phases.this_week.slice(0, 5) ?? [])

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  // Promise.allSettled: un backend caído no borra lo que sí respondió.
  const [planRes, sysRes] = await Promise.allSettled([fetchIncomePlan(), fetchMissionStatus()])
  if (planRes.status === 'fulfilled') income.value = planRes.value
  else error.value = planRes.reason instanceof Error ? planRes.reason.message : String(planRes.reason)
  if (sysRes.status === 'fulfilled') system.value = { health: sysRes.value.health, status: sysRes.value.status }

  // REALIZADO: fallo silencioso → la banda se oculta (no bloquea el plan).
  try {
    const [pt, rev] = await Promise.all([
      api.get<{ total_earnings_30d_usd?: number; confirmed?: number }>('/payment-tracker'),
      api.get<{ total_earned?: number; pending_amount?: number }>('/revenue/summary'),
    ])
    const earned = rev.total_earned ?? 0
    realized.value = {
      total_earned: earned,
      pending_amount: rev.pending_amount ?? 0,
      earnings_30d: pt.total_earnings_30d_usd ?? 0,
      has_any: earned > 0 || (rev.pending_amount ?? 0) > 0,
    }
  } catch {
    realized.value = null
  }

  // FEATURE PARITY: capital snapshot + estado de IA (fallo silencioso, no bloquea)
  try {
    const [cap, ai] = await Promise.allSettled([fetchCapitalSnapshot(), fetchAiCenter()])
    if (cap.status === 'fulfilled') capital.value = cap.status === 'fulfilled' ? cap.value : null
    if (ai.status === 'fulfilled') aiOk.value = !!ai.value.config?.available
    try {
      const [c, z, t] = await Promise.allSettled([
        fetchCareerStatus(),
        fetchZeroBarrierStats(),
        fetchRevenueTimeline(3000),
      ])
      if (c.status === 'fulfilled') career.value = c.value
      if (z.status === 'fulfilled') zbStats.value = z.value
      if (t.status === 'fulfilled') timeline.value = t.value
    } catch {}
  } catch {
    /* degradación silenciosa */
  }

  // PLATFORM RANKING: ¿dónde trabajo hoy? (fallo silencioso)
  try {
    const rankRes = await fetchPlatformRanking()
    platformRanking.value = rankRes.ranking ?? []
  } catch {
    /* degradación silenciosa */
  }

  // WORK BANK READY COUNT
  try {
    const wb = await fetchDirectWorkWorkBank()
    workBankReady.value = wb.ready_to_deliver || 0
  } catch {
    /* silencioso */
  }

  loading.value = false
  computeDigest()
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <!-- CEO CONSOLE HEADER -->
    <header class="space-y-4">
      <!-- Row 1: System Status + Money + OWNEX Status -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <!-- System Health -->
        <Card class="p-4 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Activity class="h-4 w-4 text-primary" />
              </div>
              <div>
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">SISTEMA</p>
                <p class="font-mono text-sm font-semibold">{{ system?.status.toUpperCase() || 'UNKNOWN' }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="font-mono text-2xl font-bold tabular-nums" :class="system?.health !== undefined ? (system.health >= 90 ? 'text-success' : system.health >= 70 ? 'text-warning' : 'text-destructive') : 'text-muted-foreground'">
                {{ system?.health !== undefined ? Math.round(system.health) : '—' }}%
              </p>
              <p class="font-mono text-[10px] text-muted-foreground">salud</p>
            </div>
          </div>
          <div class="flex items-center gap-4 text-xs text-muted-foreground">
            <span>{{ system?.workers || '—' }} workers</span>
            <span>{{ system?.queue || '—' }} queue</span>
            <span v-if="system?.errors > 0">{{ system.errors }} errors</span>
            <span v-else class="text-[10px] text-success">Sistema estable</span>
            <span>{{ system?.uptime || '—' }} uptime</span>
          </div>
          <!-- Indicadores de procesos críticos -->
          <div v-if="system?.errors > 0 || system?.queue > 5" class="mt-2 flex items-center gap-2 text-xs text-destructive">
            <AlertTriangle class="h-3 w-3" /> {{ system.errors > 0 ? `⚠️ ${system.errors} err` : '' }} {{ system.queue > 5 ? `• ${system.queue} en cola` : '' }}
          </div>
        </Card>

        <!-- Money Snapshot -->
        <Card class="p-4 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center">
                <DollarSign class="h-4 w-4 text-success" />
              </div>
              <div>
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">REALIZADO</p>
                <p class="font-mono text-sm font-semibold">{{ usd(realized?.total_earned || 0) }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="font-mono text-2xl font-bold tabular-nums text-success">{{ usd(realized?.pending_amount || 0) }}</p>
              <p class="font-mono text-[10px] text-muted-foreground">pendiente</p>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 text-xs">
            <div class="text-center">
              <p class="font-mono text-lg font-bold tabular-nums text-success">{{ usd(realized?.earnings_30d || 0) }}</p>
              <p class="text-muted-foreground">30 días</p>
            </div>
            <div class="text-center border-x border-border/30">
              <p class="font-mono text-lg font-bold tabular-nums">{{ income?.income_command_center?.today || '$0' }}</p>
              <p class="text-muted-foreground">HOY (potencial)</p>
            </div>
            <div class="text-center">
              <p class="font-mono text-lg font-bold tabular-nums text-warning">{{ income?.income_command_center?.month || '$0' }}</p>
              <p class="text-muted-foreground">MES (potencial)</p>
            </div>
          </div>
        </Card>

        <!-- OWNEX Status -->
        <Card class="p-4 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg" :class="hunt.status === 'running' ? 'bg-primary/10' : hunt.status === 'paused' ? 'bg-warning/10' : 'bg-muted/10'">
                <Bot class="h-4 w-4" :class="hunt.status === 'running' ? 'text-primary' : hunt.status === 'paused' ? 'text-warning' : 'text-muted-foreground'" />
              </div>
              <div>
                <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">OWNEX</p>
                <p class="font-mono text-sm font-semibold capitalize">{{ hunt.status || 'inactivo' }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="h-2 w-2 rounded-full" :class="hunt.status === 'running' ? 'bg-success animate-pulse' : hunt.status === 'paused' ? 'bg-warning' : 'bg-muted'" />
            </div>
          </div>
          <div class="flex items-center gap-4 text-xs text-muted-foreground">
            <button @click="router.push('/operations/work-queue')" class="hover:text-foreground transition-colors flex items-center gap-1">
              <Zap class="h-3 w-3" /> {{ income?.phases?.this_week?.length || 0 }} acciones
            </button>
            <button @click="router.push('/operations/work-queue')" class="hover:text-foreground transition-colors flex items-center gap-1">
              <Users class="h-3 w-3" /> {{ workBankReady || 0 }} listos
            </button>
          </div>
          <div class="flex items-center gap-2 pt-2 border-t border-border/30">
            <button @click="router.push('/')" class="btn-primary px-3 py-1.5 text-sm flex-1">
              <Target class="h-3.5 w-3.5 mr-1" /> ¿Qué hago ahora?
            </button>
            <button @click="router.push('/operations/work-queue')" class="btn-secondary px-3 py-1.5 text-sm">
              <ExternalLink class="h-3.5 w-3.5 mr-1" /> Cola trabajo
            </button>
          </div>
        </Card>
      </div>

      <!-- Row 2: Quick Actions -->
      <div class="flex flex-wrap gap-2">
        <button @click="router.push('/')" class="btn-primary px-4 py-2 flex items-center gap-2">
          <Target class="h-4 w-4" /> Acción principal
        </button>
        <button @click="router.push('/operations/work-queue')" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <ExternalLink class="h-4 w-4" /> Cola de trabajo
        </button>
        <button @click="router.push('/targets/prioritization')" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <Zap class="h-4 w-4" /> Oportunidades
        </button>
        <button @click="router.push('/capital')" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <DollarSign class="h-4 w-4" /> Ingresos
        </button>
        <button @click="router.push('/intelligence/findings')" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <Shield class="h-4 w-4" /> Hallazgos
        </button>
        <button @click="window.dispatchEvent(new CustomEvent('toggle-copilot'))" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <Bot class="h-4 w-4" /> MERLIN
        </button>
        <button @click="router.push('/operations/scheduler')" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <RotateCcw class="h-4 w-4" /> Scheduler
        </button>
        <!-- NUEVO: Indicador de aprobaciones pendientes -->
        <button v-if="humanActions.length > 0 || income?.phases?.this_week?.length > 0" @click="window.dispatchEvent(new CustomEvent('toggle-approvals'))" class="btn-secondary px-4 py-2 flex items-center gap-2">
          <AlertTriangle class="h-4 w-4" /> {{ humanActions.length > 0 ? humanActions.length : income.phases.this_week.length }} pending
        </button>
      </div>

      <!-- NUEVO: Panel de aprobaciones rápidas (progressive disclosure) -->
      <details v-if="humanActions.length > 0 || income?.phases?.this_week?.length > 0" @click.stop class="mt-3 rounded-lg border border-border/20 bg-surface/20 p-3 text-xs text-muted-foreground">
        <summary class="cursor-pointer font-mono uppercase tracking-wider">
          ⚠️ Aprobaciones pendientes {{ humanActions.length > 0 ? `(${humanActions.length})` : `(${income.phases.this_week.length} phases)` }}
          <span class="float-right text-[10px] opacity-50">▾</span>
        </summary>
        <ul class="mt-2 space-y-1 max-h-40 overflow-y-auto">
          <li v-if="humanActions.length > 0" v-for="a in humanActions" :key="a.title" class="font-mono text-[9px] rounded-md border border-border/20 bg-surface/20 p-1.5">
            <span class="truncate font-mono text-[9px]">{{ a.title }}</span>
            <template v-if="a.ev_per_human_hour_usd != null">
              <span class="text-[10px] text-muted-foreground/50">· ${{ a.ev_per_human_hour_usd }}/h</span>
            </template>
            <template v-if="a.human_hours != null">
              <span class="text-[10px] text-muted-foreground/50"> · {{ a.human_hours }}h</span>
            </template>
          </li>
          <li v-else class="text-[10px] text-muted-foreground/50">Ninguna pendiente</li>
        </ul>
      </details>
    </header>

    <ErrorState v-if="error && !income" title="No se pudo cargar el plan de ingresos" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading && !income" />

    <template v-else-if="income">
      <!-- N0: DAILY DIGEST — qué importa hoy (agrega de todos los sistemas) -->
      <DailyDigest />

      <!-- N1: THE ONE ACTION — la única acción que importa ahora -->
      <OneActionCard :auto-refresh="true" :refresh-interval="300000" />

      <!-- N1: potencial económico -->
      <Card class="space-y-3 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">💰 Ingreso potencial</p>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div v-for="(label, key) in horizons" :key="key" class="rounded-lg border border-border/20 bg-surface/20 p-4">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{{ label }}</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums">
              {{ rangeLabel(income.income_command_center[key]) }}
            </p>
          </div>
        </div>
        <p class="font-mono text-[10px] leading-relaxed text-muted-foreground/70">
          {{ income.income_command_center.basis.note }} · {{ income.income_command_center.basis.sources }}
        </p>
      </Card>

      <!-- Daily return digest: what changed since last visit -->
      <div v-if="digest" class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-accent/20 bg-accent/5 px-4 py-2.5">
        <span class="font-mono text-[10px] font-semibold uppercase tracking-wider text-accent">Desde tu última visita (hace {{ digest.hoursSince }}h)</span>
        <span v-if="digest.newOpportunities" class="font-mono text-xs text-success">+{{ digest.newOpportunities }} oportunidades</span>
        <span v-if="digest.pendingUsd > 0" class="font-mono text-xs text-warning">${{ Math.round(digest.pendingUsd).toLocaleString() }} pendiente</span>
        <span class="font-mono text-xs" :class="digest.aiHealthy ? 'text-success' : 'text-muted-foreground'">
          {{ digest.aiHealthy ? 'IA operativa' : 'IA en fallback' }}
        </span>
      </div>

      <!-- N3: Platform ranking (progressive disclosure) -->
      <details class="group">
        <summary class="cursor-pointer font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors select-none">
            🎯 ¿Dónde trabajo hoy? <span class="text-muted-foreground/50 group-open:hidden">▸</span><span class="hidden group-open:inline text-muted-foreground/50">▾</span>
        </summary>
        <div class="mt-3">
      <!-- PLATFORM RANKING: ¿dónde trabajo hoy? -->
      <Card v-if="platformRanking.length" class="space-y-3 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">🎯 ¿Dónde trabajo hoy?</p>
        <div class="space-y-2">
          <div v-for="p in platformRanking.slice(0, 5)" :key="p.platform"
            class="flex items-center justify-between rounded-lg border border-border/20 bg-surface/20 p-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="truncate font-mono text-xs font-medium">{{ p.name }}</span>
                <Badge :variant="p.recommendation === 'WORK_HERE' ? 'success' : p.recommendation === 'FINISH_SETUP' ? 'info' : p.recommendation === 'ACTIVE_STREAM' ? 'success' : 'default'" class="shrink-0">
                  {{ p.recommendation === 'WORK_HERE' ? '→ Trabajar acá' : p.recommendation === 'FINISH_SETUP' ? 'Completar setup' : p.recommendation === 'ACTIVE_STREAM' ? 'Stream activo' : 'Empezar onboarding' }}
                </Badge>
              </div>
              <p v-if="p.next_action" class="mt-1 truncate font-mono text-[10px] text-muted-foreground">
                → {{ p.next_action.title }} (~{{ p.next_action.est_minutes }} min)
              </p>
            </div>
            <div class="ml-3 shrink-0 text-right">
              <p v-if="p.effective_rate_usd_h != null" class="font-mono text-sm font-semibold tabular-nums text-success">
                ${{ p.effective_rate_usd_h }}/h
              </p>
              <p v-if="p.documented_rate_usd_h != null && p.readiness_pct < 100" class="font-mono text-[9px] text-muted-foreground">
                (doc: ${{ p.documented_rate_usd_h }}/h)
              </p>
              <p class="font-mono text-[9px] text-muted-foreground">{{ p.readiness_pct }}% listo</p>
            </div>
          </div>
        </div>
        <p class="font-mono text-[10px] leading-relaxed text-muted-foreground/70">
          Rankeado por $/h efectivo (tarifa documentada × readiness). Completá el onboarding para subir el rate efectivo.
        </p>
      </Card>
        </div>
      </details>

        <!-- ESPERADO ≠ REALIZED: el cobrado vive en /payment-tracker+/revenue -->
        <div v-if="realized" class="grid grid-cols-3 gap-3 rounded-lg border border-gold/25 bg-gold/5 p-3">
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Cobrado (realizado)</p>
            <p class="font-mono text-base font-semibold tabular-nums" :class="realized.has_any ? 'text-success' : 'text-muted-foreground'">
              {{ usd(realized.total_earned) }}
            </p>
          </div>
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Pendiente de pago</p>
            <p class="font-mono text-base font-semibold tabular-nums">{{ usd(realized.pending_amount) }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Últimos 30 días</p>
            <p class="font-mono text-base font-semibold tabular-nums">{{ usd(realized.earnings_30d) }}</p>
          </div>
          <p v-if="!realized.has_any" class="col-span-3 font-mono text-[10px] leading-relaxed text-muted-foreground/70">
            Sin cobros registrados todavía — el potencial de arriba se convierte en realizado cuando confirmás cada pago.
          </p>
        </div>

        <!-- INCOME GOAL: "quiero ganar 10k este mes" → plan concreto -->
        <Card class="border-primary/25 bg-primary/5 p-4">
          <div class="flex items-center gap-2">
            <Bot class="h-3.5 w-3.5 text-primary" />
            <h2 class="text-xs font-semibold uppercase tracking-wider">¿Cuánto querés ganar?</h2>
          </div>
          <form class="mt-3 flex gap-2" @submit.prevent="askGoal">
            <input
              v-model="goalText"
              type="text"
              placeholder="quiero ganar 10k este mes"
              class="flex-1 rounded-md border border-border/40 bg-background/60 px-3 py-1.5 font-mono text-xs outline-none focus:border-primary/60"
            />
            <button
              type="submit"
              :disabled="goalLoading || !goalText.trim()"
              class="rounded-md bg-primary px-3 py-1.5 font-mono text-xs font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {{ goalLoading ? '…' : 'Plan' }}
            </button>
          </form>
          <p v-if="goalError" class="mt-2 font-mono text-[10px] text-destructive">{{ goalError }}</p>
          <template v-if="goalPlan">
            <div class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div class="rounded-md border border-border/20 p-2">
                <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Objetivo</p>
                <p class="font-mono text-sm font-semibold tabular-nums">{{ usd(goalPlan.target.amount_usd) }}<span class="text-[9px] font-normal text-muted-foreground">/{{ goalPlan.target.period === 'weekly' ? 'sem' : 'mes' }}</span></p>
              </div>
              <div class="rounded-md border border-border/20 p-2">
                <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Oportunidades</p>
                <p class="font-mono text-sm font-semibold tabular-nums">{{ goalPlan.required_opportunities }}</p>
              </div>
              <div class="rounded-md border border-border/20 p-2">
                <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Horas/semana</p>
                <p class="font-mono text-sm font-semibold tabular-nums">{{ goalPlan.required_hours_per_week }}h</p>
              </div>
              <div class="rounded-md border border-border/20 p-2">
                <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Probabilidad</p>
                <p class="font-mono text-sm font-semibold tabular-nums" :class="goalPlan.probability_of_success >= 0.5 ? 'text-success' : 'text-warning'">
                  {{ Math.round(goalPlan.probability_of_success * 100) }}%
                </p>
              </div>
            </div>
            <div v-if="goalPlan.recommended_sources.length" class="mt-2 flex flex-wrap gap-1">
              <Badge v-for="s in goalPlan.recommended_sources.slice(0, 6)" :key="s" variant="outline" class="font-mono text-[9px]">{{ s }}</Badge>
            </div>
            <ul v-if="goalPlan.risk_factors.length" class="mt-2 space-y-0.5">
              <li v-for="(r, i) in goalPlan.risk_factors" :key="i" class="font-mono text-[10px] text-muted-foreground">· {{ r }}</li>
            </ul>
            <div class="mt-2 flex items-center justify-between border-t border-border/20 pt-2">
              <p class="font-mono text-[10px] text-muted-foreground">
                Progreso: {{ usd(goalPlan.progress.earned_this_period) }} de {{ usd(goalPlan.target.amount_usd) }} ({{ goalPlan.progress.progress_pct }}%)
                · {{ goalPlan.progress.days_remaining }}d restantes
              </p>
              <span :class="['font-mono text-[9px] font-medium', goalPlan.progress.on_track ? 'text-success' : 'text-warning']">
                {{ goalPlan.progress.on_track ? 'EN CAMINO' : 'AJUSTAR RITMO' }}
              </span>
            </div>
          </template>
        </Card>

        <!-- FEATURE PARITY §7: snapshot de capital (SSOT patrimonio) -->
        <div v-if="capital" class="grid grid-cols-2 gap-3 rounded-lg border border-border/20 bg-surface/10 p-3 sm:grid-cols-4">
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Capital total</p>
            <p class="font-mono text-base font-semibold tabular-nums">{{ usd(capital.total_usd ?? 0) }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Inversiones</p>
            <p class="font-mono text-base font-semibold tabular-nums">{{ usd(capital.investment?.total_usd ?? 0) }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Crypto</p>
            <p class="font-mono text-base font-semibold tabular-nums">{{ usd(capital.crypto?.total_usd ?? 0) }}</p>
          </div>
          <div class="flex items-center justify-between gap-2">
            <div>
              <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">IA</p>
              <Badge :variant="aiOk === null ? 'default' : aiOk ? 'success' : 'info'" dot>
                {{ aiOk === null ? '—' : aiOk ? 'OK' : 'Fallback' }}
              </Badge>
            </div>
          </div>
        </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- N1b: qué hace OWNEX vs qué hacés vos -->
        <Card class="space-y-3 p-5">
          <div class="flex items-center gap-2">
            <Bot class="h-4 w-4 text-accent" aria-hidden="true" />
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">🤖 OWNEX está haciendo</p>
          </div>
          <ul class="space-y-2">
            <li v-for="(a, i) in automation" :key="i" class="flex items-start gap-2 text-sm">
              <span :class="a.done ? 'text-success' : 'text-warning'" class="mt-0.5 font-mono">{{ a.done ? '✓' : '…' }}</span>
              <span class="text-foreground/90">{{ a.text }}</span>
            </li>
          </ul>
        </Card>

        <Card class="space-y-3 p-5">
          <div class="flex items-center gap-2">
            <Eye class="h-4 w-4 text-gold" aria-hidden="true" />
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">🧠 Mindrift tracking</p>
          </div>
          <div class="space-y-3">
            <!-- Estado general -->
            <div v-if="mindrift.tasksAvailable > 0 || mindrift.tasksThisWeek > 0" class="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Tasks disponibles: {{ mindrift.tasksAvailable }}</span>
              <span v-if="mindrift.tasksThisWeek > 0"> · {{ mindrift.tasksThisWeek }} esta semana</span>
            </div>

            <!-- Hours & earnings -->
            <div v-if="mindrift.earningsThisWeek > 0 || mindrift.hoursThisWeek > 0" class="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
              <div>
                <p class="font-mono text-[9px] uppercase tracking-wider">Horas esta semana</p>
                <p class="font-mono text-base font-semibold tabular-nums">{{ mindrift.hoursThisWeek }}h</p>
              </div>
              <div>
                <p class="font-mono text-[9px] uppercase tracking-wider">Ingresos esta semana</p>
                <p class="font-mono text-base font-semibold tabular-nums">{{ usd(mindrift.earningsThisWeek) }}</p>
              </div>
            </div>

            <!-- $/hr real -->
            <div v-if="mindrift.earningsPerHour > 0" class="text-right">
              <p class="font-mono text-[10px] font-semibold text-success">{{ usd(mindrift.earningsPerHour) }}/h</p>
              <p class="font-mono text-[9px] text-muted-foreground">$/h real estimado</p>
            </div>

            <!-- Assessment deadline -->
            <p v-if="mindrift.assessmentDeadline" class="flex items-center gap-2 text-xs text-muted-foreground">
              <Calendar class="h-3.5 w-3.5" /> Assessment: {{ mindrift.assessmentStatus }} (deadline {{ mindrift.assessmentDeadline }})
            </p>

            <!-- Next payout -->
            <p v-if="mindrift.nextPayoutDate" class="flex items-center gap-2 text-xs text-muted-foreground">
              <Archive class="h-3.5 w-3.5" /> Payout: {{ mindrift.nextPayoutDate }} (ciclo {{ mindrift.nextPayoutCycle || '?' }})
            </p>

            <!-- Last payout -->
            <p v-if="mindrift.lastPayout" class="flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle class="h-3.5 w-3.5 text-success" /> {{ mindrift.lastPayout.date }}: {{ usd(mindrift.lastPayout.amount) }} ({{ mindrift.lastPayout.tasks }} tasks, {{ mindrift.lastPayout.hours }}h)
            </p>

            <!-- Weekly history summary -->
            <p v-if="mindrift.weeklyHistory.length > 0" class="text-[9px] text-muted-foreground/70">
              Últimos {{ mindrift.weeklyHistory.length }} ciclos: {{ mindrift.weeklyHistory.map((h)=>`${usd(h.amount)}·${h.hours}h`).join(', ') }}
            </p>

            <!-- New task alert -->
            <p v-if="mindrift.newTaskAlert" class="flex items-center gap-2 text-xs text-destructive">
              <AlertCircle class="h-3.5 w-3.5 text-destructive" /> ¡Nueva task disponible!
            </p>

            <!-- Manual start timer button -->
            <div v-if="!mindriftTimer.value.isRunning" class="mt-2 pt-2 border-t border-border/20">
              <OwnexButton @click="startMindriftTimer('manual-' + Date.now())" class="btn-secondary flex items-center gap-2 text-[10px] uppercase tracking-wider">
                <Clock class="h-3.5 w-3.5" /> Iniciar timer
              </OwnexButton>
            </div>

            <!-- Timer running display -->
            <div v-else class="mt-2 flex items-center gap-2 text-sm text-success">
              <span class="font-mono">Timer running: </span>
              <span class="font-mono text-[10px]">{{ formatElapsed(mindriftTimer.value.elapsedMs) }}</span>
              <OwnexButton @click="stopMindriftTimer()" class="btn-secondary px-2 py-1.5 text-[8px] uppercase tracking-wider">
                Detener
              </OwnexButton>
            </div>

            <!-- Reset timer -->
            <OwnexButton v-if="mindriftTimer.value.elapsedMs > 0" @click="resetMindriftTimer()" class="btn-secondary px-2 py-1.5 text-[8px] uppercase tracking-wider ml-2">
              <RefreshCw class="h-3 w-3" /> Restar
            </OwnexButton>

            <!-- Manual start timer button -->
            <div class="mt-3 pt-3 border-t border-border/20">
              <OwnexButton @click="startMindriftTimer" class="btn-secondary flex items-center gap-2 text-[10px] uppercase tracking-wider">
                <Clock class="h-3.5 w-3.5" /> Iniciar timer manual
              </OwnexButton>
            </div>
          </div>
        </Card>

        <!-- Computer Use widget -->
        <ComputerUseWidget />
      </div>

      <!-- N3: Stack activo + career (progressive disclosure) -->
      <details class="group">
        <summary class="cursor-pointer font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors select-none">
            📈 Stack activo · skills · proyección <span class="text-muted-foreground/50 group-open:hidden">▸</span><span class="hidden group-open:inline text-muted-foreground/50">▾</span>
        </summary>
        <div class="mt-3">
      <Card class="space-y-2 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">📈 Stack activo (tarifas documentadas)</p>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <div v-for="s in income.income_command_center.active_stack" :key="s.key"
            class="rounded-lg border border-border/20 bg-surface/20 p-3">
            <p class="truncate font-mono text-xs font-medium">{{ s.name }}</p>
            <p class="font-mono text-[11px]" :class="s.rate_documented ? 'text-success' : 'text-muted-foreground'">
              {{ s.rate_documented ? `$${s.rate_documented}/h` : 'tarifa n/d' }}
            </p>
            <Badge :variant="s.status === 'accepted' ? 'success' : s.status === 'in_review' ? 'info' : 'default'" class="mt-1">
              {{ s.status }}
            </Badge>
          </div>
        </div>

        <!-- FEATURE PARITY: career + zero-barrier + revenue timeline -->
        <div v-if="career || zbStats || timeline" class="grid grid-cols-3 gap-2 rounded-lg border border-border/20 p-3">
          <div v-if="career?.skill_gaps?.length">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Skill gaps</p>
            <p class="font-mono text-sm font-semibold">{{ career.skill_gaps.length }} pendientes</p>
            <p class="font-mono text-[9px] text-muted-foreground truncate">{{ career.skill_gaps.slice(0,2).map((s:any)=>s.skill).join(', ') }}</p>
          </div>
          <div v-if="zbStats?.total_opportunities">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Zero-barrier</p>
            <p class="font-mono text-sm font-semibold">{{ zbStats.total_opportunities }} sin barrera</p>
          </div>
          <div v-if="timeline?.milestones?.length">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Próximo hito</p>
            <p class="font-mono text-sm font-semibold">{{ timeline.milestones[0]?.label || '—' }}</p>
            <p v-if="timeline.milestones[0]?.months" class="font-mono text-[9px] text-muted-foreground">{{ timeline.milestones[0].months }} meses</p>
          </div>
        </div>
      </Card>
        </div>
      </details>

      <!-- N4: SOURCES OVERVIEW — 7 fuentes (3 grupos) -->
      <Card class="space-y-3 p-5">
        <div class="flex items-center gap-2">
          <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">📋 Fuentes OwnEX (7)</p>
        </div>
        <div class="space-y-2 text-xs text-muted-foreground">
          <!-- Grupo 1: Tareas recurrentes -->
          <details>
            <summary class="font-mono text-xs uppercase text-warning">🟢 Tareas recurrentes (4)</summary>
            <div class="space-y-1 text-xs text-muted-foreground">
              <div class="flex items-center gap-3">
                <span class="w-2 h-2 rounded-full bg-gold" /> <span class="truncate">Outlier: {{ sourcesStatus.outlier }}</span>
                <span class="w-2 h-2 rounded-full bg-primary" /> <span class="truncate">Mindrift: {{ sourcesStatus.mindrift }}</span>
                <span class="w-2 h-2 rounded-full bg-lime-500" /> <span class="truncate">RemoExperts: {{ sourcesStatus.remoexperts }}</span>
                <span class="w-2 h-2 rounded-full bg-warning" /> <span class="truncate">OneForma: {{ sourcesStatus.oneforma }}</span>
              </div>
            </div>
          </details>
          <!-- Grupo 2: Bounties y recompensas -->
          <details>
            <summary class="font-mono text-xs uppercase text-orange-500">🟠 Bounties y recompensas (3)</summary>
            <div class="space-y-1 text-xs text-muted-foreground">
              <div class="flex items-center gap-3">
                <span class="w-2 h-2 rounded-full bg-orange-500" /> <span class="truncate">HackerOne: {{ sourcesStatus.hackerone }}</span>
                <span class="w-2 h-2 rounded-full bg-orange-500" /> <span class="truncate">Bugcrowd: {{ sourcesStatus.bugcrowd }}</span>
                <span class="w-2 h-2 rounded-full bg-orange-500" /> <span class="truncate">Intigriti: {{ sourcesStatus.intigriti }}</span>
              </div>
            </div>
          </details>
          <!-- Grupo 3: Herramientas descubrimiento -->
          <details>
            <summary class="font-mono text-xs uppercase text-green-500">🔍 Descubrimiento (2)</summary>
            <div class="space-y-1 text-xs text-muted-foreground">
              <div class="flex items-center gap-3">
                <span class="w-2 h-2 rounded-full bg-green-500" /> <span class="truncate">Bounty Radar: {{ sourcesStatus.bountyRadar }}</span>
                <span class="w-2 h-2 rounded-full bg-green-500" /> <span class="truncate">IssueFinder: {{ sourcesStatus.issuefinder }}</span>
              </div>
            </div>
          </details>
          <p class="text-[9px] text-muted-foreground/70">
            🟢 = tarea recurrente | 🟠 = bounty/recompensa | 🔍 = herramienta descubrimiento
            🔶 = assessment escrito | 📋 = KYC permitido (según fuente)
          </p>
        </div>
        <div v-if="sourcesStatus" class="mt-3 grid grid-cols-2 gap-2">
          <div v-for="(status, key) in sourcesStatus" :key="key" class="rounded-lg border border-border/20 bg-surface/20 p-3 text-[9px]">
            <p class="font-mono uppercase tracking-wider text-success">{{ key }}</p>
            <p class="font-mono text-[9px]">{{ status }}</p>
          </div>
        </div>
      </Card>
    </template>

    <!-- FLIGHT RECORDER - System Activity Log -->
    <div class="h-96 bg-surface"></div>

  </div>
</template>