<script setup lang="ts">
import {
  Activity,
  AlertTriangle,
  BarChart3,
  ClipboardCheck,
  Clock,
  DollarSign,
  FileText,
  HeartPulse,
  RefreshCw,
  Shield,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ReportPipeline from '@/components/dashboard/ReportPipeline.vue'
import ThroughputCore from '@/components/dashboard/ThroughputCore.vue'
import WorkCyclesGrid from '@/components/dashboard/WorkCyclesGrid.vue'
import GuidedDashboard from '@/components/guided-mode/GuidedDashboard.vue'
import AgentFleet from '@/components/mission-control/AgentFleet.vue'
import AutoDispute from '@/components/mission-control/AutoDispute.vue'
import AutonomyDashboard from '@/components/mission-control/AutonomyDashboard.vue'
import CapitalBar from '@/components/mission-control/CapitalBar.vue'
import ConfigProgressBar from '@/components/mission-control/ConfigProgressBar.vue'
import ControlPanel from '@/components/mission-control/ControlPanel.vue'
import DailyCompanion from '@/components/mission-control/DailyCompanion.vue'
import DailyIncomePlan from '@/components/mission-control/DailyIncomePlan.vue'
import DailyTasks from '@/components/mission-control/DailyTasks.vue'
import DevBountyAutopilot from '@/components/mission-control/DevBountyAutopilot.vue'
import DirectWorkRadar from '@/components/mission-control/DirectWorkRadar.vue'
import EvolveMatrix from '@/components/mission-control/EvolveMatrix.vue'
import FinanceGuru from '@/components/mission-control/FinanceGuru.vue'
import GoalEvaluator from '@/components/mission-control/GoalEvaluator.vue'
import GoodMorning from '@/components/mission-control/GoodMorning.vue'
import InvoicerAR from '@/components/mission-control/InvoicerAR.vue'
import KnowledgeFeed from '@/components/mission-control/KnowledgeFeed.vue'
import MasterGuide from '@/components/mission-control/MasterGuide.vue'
import MoneyPlan from '@/components/mission-control/MoneyPlan.vue'
import NextBestAction from '@/components/mission-control/NextBestAction.vue'
import NotificationCenter from '@/components/mission-control/NotificationCenter.vue'
import ObsidianSync from '@/components/mission-control/ObsidianSync.vue'
import OfframpExecutor from '@/components/mission-control/OfframpExecutor.vue'
import OpportunityRadar from '@/components/mission-control/OpportunityRadar.vue'
import PaymentCompatPanel from '@/components/mission-control/PaymentCompatPanel.vue'
import PayoutNet from '@/components/mission-control/PayoutNet.vue'
import PlatformConnectors from '@/components/mission-control/PlatformConnectors.vue'
import ProfileBuilder from '@/components/mission-control/ProfileBuilder.vue'
import SandboxMode from '@/components/mission-control/SandboxMode.vue'
import SkillMethod from '@/components/mission-control/SkillMethod.vue'
import TaskAssistant from '@/components/mission-control/TaskAssistant.vue'
import TaxAR from '@/components/mission-control/TaxAR.vue'
import VPNEmbed from '@/components/mission-control/VPNEmbed.vue'
import WelcomeGuide from '@/components/mission-control/WelcomeGuide.vue'
import CommandCenter from '@/components/mission-control/CommandCenter.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { useAudio } from '@/composables/useAudio'
import type { OwnexDashboardData } from '@/services/ownexData'
import { fetchIncomePlan, fetchOwnexDashboard, type IncomePlanAction } from '@/services/ownexData'

const router = useRouter()
const dashboard = ref<OwnexDashboardData | null>(null)
const incomeNext = ref<IncomePlanAction | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const degraded = ref(false)
let refreshInterval: ReturnType<typeof setInterval> | null = null
const audio = useAudio()

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const systemOk = computed(() => (dashboard.value?.systemHealth ?? 0) >= 70)

const quickActions = [
  { id: 'hunt', label: 'HUNT', icon: Zap, path: '/baby-mode' },
  { id: 'targets', label: 'Security', icon: Shield, path: '/security' },
  { id: 'bounties', label: 'Forge', icon: Activity, path: '/integrations/platforms' },
  { id: 'capital', label: 'Wealth', icon: DollarSign, path: '/capital' },
  { id: 'reports', label: 'Reportes', icon: FileText, path: '/reports/center' },
  { id: 'pipeline', label: 'Pipeline', icon: BarChart3, path: '/operations/pipelines' },
  { id: 'health', label: 'Health', icon: HeartPulse, path: '/operations/health' },
  { id: 'claims', label: 'Mis pruebas', icon: ClipboardCheck, path: null },
]

const showClaimsModal = ref(false)
const claimsList = ref<EvidenceClaim[]>([])
const claimsLoading = ref(false)

async function loadClaims() {
  claimsLoading.value = true
  try {
    const res = await fetch('/api/evidence/claims').then((r) => r.json())
    claimsList.value = res.items || res || []
  } catch {
    claimsList.value = []
  } finally {
    claimsLoading.value = false
  }
}

function openClaimsModal() {
  showClaimsModal.value = true
  loadClaims()
}

function closeClaimsModal() {
  showClaimsModal.value = false
}

async function downloadClaim(claim: EvidenceClaim) {
  const blob = new Blob([JSON.stringify(claim, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${claim.finding_id}.claim.json`
  a.click()
  URL.revokeObjectURL(url)
}

interface EvidenceClaim {
  finding_id: string
  bounty_id?: string
  outcome: string
  detail: string
  timestamp_utc: string
  sha256: string
  path: string
  version: string
}

async function load() {
  // Next Action real (Income Plan): fetch propio con degradación silenciosa —
  // si falla, cae al nextAction de /mission/status (nunca rompe el dashboard).
  fetchIncomePlan()
    .then((p) => {
      incomeNext.value = p.next_action
      if (p.next_action) audio.play('success')
    })
    .catch(() => {
      incomeNext.value = null
    })
  try {
    const data = await fetchOwnexDashboard()
    dashboard.value = data
    degraded.value = false
    error.value = null
    audio.play('success')
  } catch (e: any) {
    if (!dashboard.value) {
      error.value = e?.message || 'Error al cargar'
      audio.play('error')
    } else {
      degraded.value = true
      audio.play('warning')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  audio.play('startup')
  load()
  refreshInterval = setInterval(() => load(), 30000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

// ── Adapters: service shapes → component prop shapes ──

const fleetAgents = computed(() =>
  (dashboard.value?.agents || []).map((a, i) => ({
    id: String(i),
    name: a.name,
    role: a.description || 'Agente',
    status: a.status,
    model: undefined as string | undefined,
    progress: undefined as number | undefined,
    currentTask: a.description,
  })),
)

const radarOpportunities = computed(() =>
  (dashboard.value?.opportunities || []).map((o) => ({
    id: o.id,
    title: o.title,
    platform: 'custom' as const,
    type: (o.type === 'bug-bounty' ||
    o.type === 'vdp' ||
    o.type === 'ctf' ||
    o.type === 'freelance' ||
    o.type === 'research'
      ? o.type
      : 'research') as 'bug-bounty' | 'vdp' | 'ctf' | 'freelance' | 'research',
    severity: 'info' as const,
    reward: o.reward ? `$${o.reward.toLocaleString()}` : undefined,
    confidence: o.confidence,
    tags: [o.source],
    postedAt: new Date().toISOString(),
  })),
)

const feedItems = computed(() =>
  (dashboard.value?.knowledgeFeed || []).map((k) => ({
    id: k.id,
    type: (k.type === 'alert' || k.type === 'pattern' || k.type === 'learning' || k.type === 'decision'
      ? k.type === 'alert'
        ? 'alert'
        : k.type === 'pattern'
          ? 'pattern'
          : k.type === 'learning'
            ? 'learning'
            : 'insight'
      : 'system') as 'insight' | 'learning' | 'pattern' | 'alert' | 'achievement' | 'system',
    title: k.message,
    description: k.typeLabel,
    timestamp: k.timestamp,
    tags: [],
  })),
)
</script>

<template>
  <div class="space-y-6 animate-in">
    <LoadingState v-if="loading" />

    <ErrorState
      v-else-if="error && !dashboard"
      title="Error al cargar Mission Control"
      :error="error"
      :on-retry="load"
    />

    <template v-else>
      <!-- Degraded banner -->
      <div
        v-if="degraded"
        class="flex items-center gap-2 rounded-lg bg-warning/10 border border-warning/30 px-4 py-2 text-xs text-warning"
      >
        <AlertTriangle class="h-3.5 w-3.5 shrink-0" />
        <span>Datos parciales — algunos servicios no responden</span>
      </div>

      <!-- Header -->
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div class="space-y-1 min-w-0">
          <div class="flex items-center gap-2">
            <Activity class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX MISSION CONTROL</span>
            <span class="status-dot" :class="systemOk ? 'status-dot-green' : 'status-dot-red'" />
          </div>
          <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
          <p class="text-[9px] font-mono text-muted-foreground tracking-[0.2em] uppercase">OWNEX ● Personal Autonomous Work OS</p>
          <p class="text-xs text-muted-foreground flex items-center gap-2">
            <Clock class="h-3 w-3" />
            {{ dashboard?.timestamp ? new Date(dashboard.timestamp).toLocaleString() : '—' }}
            <button @click="load" class="text-primary hover:underline flex items-center gap-1">
              <RefreshCw class="h-3 w-3" /> Actualizar
            </button>
          </p>
        </div>
        <div class="panel shrink-0 flex flex-col items-center gap-1 rounded-xl px-6 py-3">
          <span class="font-mono text-[10px] text-muted-foreground tracking-wider uppercase">Salud del sistema</span>
          <span
            :class="['text-4xl font-bold font-mono', dashboard && dashboard.systemHealth >= 90 ? 'text-success' : dashboard && dashboard.systemHealth >= 70 ? 'text-warning' : 'text-destructive']"
          >
            {{ dashboard?.systemHealth ?? '—' }}
          </span>
          <span class="font-mono text-[9px] text-muted-foreground uppercase">{{ dashboard?.systemStatus || '—' }}</span>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="flex flex-wrap items-center gap-2 rounded-xl bg-surface/20 border border-border/30 px-4 py-3">
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider text-muted-foreground mr-1">Acciones rápidas</span>
        <button
          v-for="qa in quickActions" :key="qa.id"
          @click="qa.path ? router.push(qa.path) : openClaimsModal()"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-foreground/80 hover:text-foreground hover:bg-primary/10 border border-border/30 transition-colors"
        >
          <component :is="qa.icon" class="h-3.5 w-3.5" />
          {{ qa.label }}
        </button>
      </div>

      <!-- TODO DIARIO: lista de tareas del día propuestas por OWNEX -->
      <DailyTasks />

      <!-- CONFIG PROGRESS BAR: barra de progresión de todos los ajustes -->
      <ConfigProgressBar />

      <!-- CONTROL PANEL: modos, ciclo, automación, acciones -->
      <ControlPanel />

      <!-- GUÍA MAESTRA: checklist guiada de todas las categorías -->
      <MasterGuide />

      <!-- PLAN DE PLATA: proyección con tus horas -->
      <MoneyPlan />

      <!-- ASISTENTE DE TAREAS: pega el enunciado, te da material de trabajo -->
      <TaskAssistant />

      <!-- DEV BOUNTY AUTOPILOT: descubre y propone, vos validás -->
        <DevBountyAutopilot />

      <!-- GITHUB PROFILE BUILDER: vincula GitHub, construye perfil -->
        <ProfileBuilder />

      <!-- SKILL METHOD: ruta de estudio del 0,1% con sesiones de evidencia -->
      <SkillMethod />

      <!-- CAPITAL BAR: acumulación hacia $100K con umbrales pasivos -->
      <CapitalBar />

      <!-- GOAL EVALUATOR: decile tu meta, OWNEX la evalúa con datos reales -->
      <GoalEvaluator />

      <!-- MATRIX DE CRECIMIENTO: work, postmortem, accounts, cobro, brand, vault, emergencia -->
      <EvolveMatrix />

      <!-- PAYOUT NET: red de cobro solo KYC con fallbacks y resolución -->
      <PayoutNet />

      <!-- PAYMENT COMPAT: ¿puedo cobrar este requerimiento? veredicto determinista -->
      <PaymentCompatPanel />

      <!-- FINANCE GURU: preguntá cualquier cosa de cobro/cuentas USA/INTL desde AR -->
      <FinanceGuru />

      <!-- AUTONOMY DASHBOARD: closed-loop, trust engine, payment tracking -->
      <AutonomyDashboard />

      <!-- Row 1: Throughput + Agent Fleet -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ThroughputCore
          v-if="dashboard"
          :stages="dashboard.throughputStages"
          :efficiency="dashboard.throughputEfficiency"
          class="lg:col-span-2"
        />
        <ThroughputCore v-else class="lg:col-span-2" />
        <AgentFleet v-if="dashboard" :agents="fleetAgents" />
        <AgentFleet v-else :agents="[]" />
      </div>

      <!-- Row 2: Opportunity Radar + Next Best Action -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <OpportunityRadar
          v-if="dashboard && radarOpportunities.length > 0"
          :opportunities="radarOpportunities"
          class="lg:col-span-2"
        />
        <OpportunityRadar v-else :opportunities="[]" class="lg:col-span-2" />
        <!-- Next Action REAL (Income Plan): navega a la plataforma o al plan -->
        <NextBestAction
          v-if="incomeNext"
          :title="incomeNext.title"
          :description="incomeNext.detail || 'Sigue la guía paso a paso en Postulaciones'"
          :href="incomeNext.url || '/operations/applications'"
          :primary-action="{ label: incomeNext.url ? 'Abrir y ejecutar' : 'Ver plan completo', variant: 'primary' }"
          :secondary-action="{ label: 'Posponer', variant: 'ghost' }"
          :reasoning="incomeNext.why || 'Elegida por mayor dinero esperado por hora de intervención humana'"
          :ev-per-hour="incomeNext.ev_per_human_hour_usd ?? null"
          :payoff-range="incomeNext.payoff_range ?? null"
          :cash-speed-days="incomeNext.cash_speed_days ?? null"
          :assessment-required="incomeNext.assessment_required ?? null"
          :zero-experience="incomeNext.zero_experience ?? null"
        />
        <NextBestAction
          v-else-if="dashboard && dashboard.nextAction"
          :title="dashboard.nextAction.title"
          :description="dashboard.nextAction.reason || 'Revisar prioridades en Mission Control'"
          :primary-action="{ label: 'Ejecutar', variant: 'primary' }"
          :secondary-action="{ label: 'Posponer', variant: 'ghost' }"
          :reasoning="dashboard.nextAction.reason || ''"
          :meta="{
            esfuerzo: dashboard.nextAction.effort || '—',
            recompensa: dashboard.nextAction.estimatedReward
              ? `$${dashboard.nextAction.estimatedReward}`
              : '—',
          }"
        />
        <NextBestAction v-else title="Sin acción pendiente" description="Revisar oportunidades o iniciar un ciclo de trabajo" :primary-action="{ label: 'Ejecutar', variant: 'primary' }" />
      </div>

      <!-- Row 2.4: Command Center — ONE BEST ACTION -->
      <CommandCenter v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 0: Welcome Guide (Day 1 hand-holding) -->
      <WelcomeGuide v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 0.5: Sandbox Mode (Learning playground) -->
      <SandboxMode v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 0.6: VPN Embed (Auto-install + health check) -->
      <VPNEmbed v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 0.7: Auto Dispute (Payment claims) -->
      <AutoDispute v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 0.8: Obsidian Sync (Real bidirectional) -->
      <ObsidianSync v-if="!degraded && loading === false && dashboard" class="lg:col-span-3" />

      <!-- Row 2.5: Daily Operation Mode -->
      <GoodMorning />

      <!-- Row 2.5b: Daily Companion -->
      <DailyCompanion />

      <!-- Row 2.6: Daily Income Plan -->
      <DailyIncomePlan />

      <!-- Row 2.7: Notifications -->
      <NotificationCenter />

      <!-- Row 2.8: Direct Work recommendations -->
      <DirectWorkRadar />

      <!-- Row 2.8: Guided Dashboard (Mode Selector + First Day + Income Guidance + Work Bank) -->
      <GuidedDashboard />

      <!-- Row 3: Report Pipeline (Daily/Weekly Top -->
      <ReportPipeline />

      <!-- Row 4: Work Cycles -->
      <WorkCyclesGrid />

      <!-- Row 5: Knowledge Feed -->
      <KnowledgeFeed
        v-if="dashboard && feedItems.length > 0"
        :items="feedItems"
      />
      <KnowledgeFeed v-else :items="[]" />

      <!-- TAX AR + FACTURACIÓN -->
      <TaxAR />
      <InvoicerAR />

<!-- OFFRAMP + CONNECTORS -->
      <OfframpExecutor />
      <PlatformConnectors />

      </template>

      <!-- CLAIMS MODAL -->
      <div v-if="showClaimsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div class="bg-surface border border-border rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <div class="flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 class="font-semibold text-foreground flex items-center gap-2">
              <ClipboardCheck class="h-5 w-5 text-primary" />
              Mis pruebas guardadas
            </h3>
            <button @click="closeClaimsModal" class="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-accent transition-colors">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="p-4 overflow-y-auto">
            <template v-if="claimsLoading">
              <div class="flex items-center justify-center py-8 text-muted-foreground">Cargando pruebas...</div>
            </template>
            <template v-else-if="!claimsList.length">
              <div class="text-center py-8 text-muted-foreground">
                <ClipboardCheck class="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No hay pruebas guardadas aún.</p>
                <p class="text-sm mt-1">Valida una bounty en DevBountyAutopilot para generar una prueba.</p>
              </div>
            </template>
            <template v-else>
              <div class="space-y-3">
                <div v-for="c in claimsList" :key="c.finding_id" class="bg-background/50 border border-border/30 rounded-lg p-4">
                  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 mb-1">
                        <code class="font-mono text-sm bg-accent px-2 py-0.5 rounded">{{ c.finding_id }}</code>
                        <span class="text-xs font-medium px-2 py-0.5 rounded"
                          :class="c.outcome === 'approved' ? 'bg-green-500/20 text-green-400' : 'bg-zinc-500/20 text-zinc-300'">
                          {{ c.outcome }}
                        </span>
                      </div>
                      <p class="text-sm text-muted-foreground truncate">{{ c.detail }}</p>
                      <div class="flex flex-wrap gap-3 mt-2 text-xs text-muted-foreground">
                        <span>{{ new Date(c.timestamp_utc).toLocaleString() }}</span>
                        <span v-if="c.bounty_id">Bounty: {{ c.bounty_id }}</span>
                        <span>sha256: {{ c.sha256 }}</span>
                      </div>
                    </div>
                    <button
                      @click="downloadClaim(c)"
                      class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 border border-primary/30 rounded-lg transition-colors flex-shrink-0"
                    >
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                      Exportar JSON
                    </button>
                  </div>
                </div>
              </div>
            </template>
</div>
        </div>
      </div>
    </div>
</template>
