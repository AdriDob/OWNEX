<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { getOrionContext } from '@/lib/api'
import type { OrionContext } from '@/types'
import { useHuntStore } from '@/stores/hunt'
import { useSettingsStore } from '@/stores/settings'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { Activity, AlertTriangle, ArrowRight, Sparkles, Clock, DollarSign, Target, Zap, Play, Square, Pause, Eye, Crosshair, Bug, ShieldCheck, Scan, Cpu, RefreshCw, Globe } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import OnboardingWizard from '@/components/onboarding/OnboardingWizard.vue'

const hunt = useHuntStore()
const settings = useSettingsStore()
const ctx = ref<OrionContext | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const showOnboarding = ref(false)
const onboardingAutoShown = ref(false)
const uptime = ref(0)
let uptimeInterval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    ctx.value = await getOrionContext()
    await settings.loadFromBackend()
  }
  catch (e: any) { error.value = e?.message || 'Error al cargar' }
  finally { loading.value = false }
  if (!onboardingAutoShown.value && settings.onboardingNeeded && (!ctx.value || ctx.value.counts.targets === 0)) {
    showOnboarding.value = true
    onboardingAutoShown.value = true
  }
  await hunt.fetchStatus()
  if (hunt.isActive) {
    uptimeInterval = setInterval(() => { uptime.value++ }, 1000)
  }
})

onUnmounted(() => {
  if (uptimeInterval) clearInterval(uptimeInterval)
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const kpiItems = computed(() => {
  if (!ctx.value) return []
  const c = ctx.value.counts
  return [
    { label: 'Targets', value: String(c.targets), icon: Crosshair, color: '#00b8ff' },
    { label: 'Endpoints', value: String(c.endpoints), icon: Scan, color: '#00ff41' },
    { label: 'Confirmados', value: String(c.confirmed_findings), icon: ShieldCheck, color: '#00e676' },
    { label: 'ROI Est.', value: `$${(c.total_estimated_payout || 0).toLocaleString()}`, icon: DollarSign, color: '#ffd740' },
  ]
})

function severityBadge(sev?: string) {
  if (!sev) return 'default' as const
  const map: Record<string, 'destructive' | 'warning' | 'success' | 'info' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

const nextAction = computed(() => ctx.value?.next_action)
const opportunities = computed(() => ctx.value?.opportunities.top || [])
const activityEvents = computed(() => ctx.value?.activity_24h.events || [])

const pipelineStages = computed(() => {
  if (!ctx.value) return []
  const p = ctx.value.pipeline
  return [
    { label: 'Detectados', count: p.detected, color: 'bg-muted-foreground/30' },
    { label: 'Validados', count: p.validated, color: 'bg-accent/30' },
    { label: 'Confirmados', count: p.confirmed, color: 'bg-primary/30' },
    { label: 'Reportados', count: p.reported, color: 'bg-gold/30' },
  ]
})

const maxPipeline = computed(() => {
  if (!ctx.value) return 1
  const p = ctx.value.pipeline
  return Math.max(p.detected, p.validated, p.confirmed, p.reported, 1)
})

function handleHuntToggle() {
  if (hunt.status === 'idle') hunt.start()
  else if (hunt.status === 'running') hunt.pause()
  else if (hunt.status === 'paused') hunt.resume()
}

function formatUptime(s: number) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${sec}s`
  return `${sec}s`
}
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4 animate-in"><Skeleton class="h-6 w-64" /><Skeleton class="h-4 w-96" /><div class="grid grid-cols-4 gap-3"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div><Skeleton class="h-32 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 font-mono text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </div>
    </template>

    <!-- ═══════════════════ EMPTY STATE — ONBOARDING ═══════════════════ -->
    <template v-else-if="!ctx || (ctx.counts.targets === 0 && ctx.counts.findings === 0)">
      <div class="flex flex-col items-center py-16 text-center animate-in">
        <div class="flex h-20 w-20 items-center justify-center rounded-2xl cyber-card mb-6">
          <Eye class="h-10 w-10 text-primary" />
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Bienvenido a CATEYE</h1>
        <p class="mt-2 max-w-lg text-sm text-muted-foreground">Sistema de Inteligencia de Seguridad. Centralizá tus operaciones de bug bounty, automatizá recon y gestioná hallazgos desde un solo lugar.</p>

        <div class="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3 max-w-2xl">
          <div class="cyber-card rounded-xl p-4 text-left">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2"><Globe class="h-4 w-4" /></div>
            <p class="text-xs font-semibold text-foreground">1. Conectá plataformas</p>
            <p class="mt-1 text-[10px] text-muted-foreground">Vinculá tus cuentas de HackerOne, Bugcrowd, Intigriti. Las credenciales se cifran.</p>
          </div>
          <div class="cyber-card rounded-xl p-4 text-left">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2"><Crosshair class="h-4 w-4" /></div>
            <p class="text-xs font-semibold text-foreground">2. Agregá targets</p>
            <p class="mt-1 text-[10px] text-muted-foreground">Importá programas desde las plataformas o agregá dominios manualmente para monitorear.</p>
          </div>
          <div class="cyber-card rounded-xl p-4 text-left">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2"><Zap class="h-4 w-4" /></div>
            <p class="text-xs font-semibold text-foreground">3. Iniciá la caza</p>
            <p class="mt-1 text-[10px] text-muted-foreground">Activá la caza autónoma. CATEYE descubre, reconoce, hipotetiza, valida y reporta.</p>
          </div>
        </div>

        <div class="mt-8 flex gap-3">
          <Button variant="default" @click="showOnboarding = true">
            <Sparkles class="h-4 w-4" /> Configuración inicial
          </Button>
          <Button variant="outline" @click="$router.push('/connections')">
            <Globe class="h-4 w-4" /> Conectar plataformas
          </Button>
          <Button variant="outline" @click="$router.push('/program-catalog')">
            <Target class="h-4 w-4" /> Explorar programas
          </Button>
        </div>

        <div class="mt-8 rounded-lg border border-border/30 px-4 py-3 max-w-lg">
          <p class="font-mono text-[10px] text-muted-foreground">
            <span class="text-primary">$</span> Configurá tus API keys en <strong>Configuración → OSINT</strong> para habilitar inteligencia externa.
          </p>
        </div>
      </div>
    </template>

    <!-- ═══════════════════ MISSION CONTROL ═══════════════════ -->
    <template v-else-if="ctx">
      <div class="flex items-start justify-between gap-4">
        <div class="space-y-1 animate-in">
          <div class="flex items-center gap-2">
            <Eye class="h-4 w-4 text-primary" />
            <span class="font-mono text-[10px] font-bold tracking-widest text-primary">CATEYE MISSION CONTROL</span>
            <span :class="['h-1.5 w-1.5 rounded-full', ctx.system.status === 'healthy' ? 'bg-success animate-pulse' : 'bg-warning']" />
          </div>
          <h1 class="font-display text-2xl font-bold text-foreground">{{ greeting }}, Operador</h1>
          <p class="text-xs text-muted-foreground">
            Score salud: {{ ctx.system.health_score }}/100
            <span v-if="ctx.findings.new_24h"> · {{ ctx.findings.new_24h }} hallazgos nuevos hoy</span>
            <span v-if="ctx.counts.reports_ready > 0"> · {{ ctx.counts.reports_ready }} reportes pendientes</span>
          </p>
        </div>

        <!-- Hunt Control Panel -->
        <div class="shrink-0 animate-in flex gap-3">
          <div class="cyber-card rounded-xl p-4 min-w-[200px]">
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-[10px] font-bold tracking-wider text-muted-foreground">CAZA AUTÓNOMA</span>
              <Badge :variant="hunt.status === 'running' ? 'success' : hunt.status === 'paused' ? 'warning' : 'default'" class="font-mono text-[8px]">
                {{ hunt.status === 'running' ? 'ACTIVE' : hunt.status === 'paused' ? 'PAUSED' : 'IDLE' }}
              </Badge>
            </div>
            <div v-if="hunt.isActive" class="mb-2 flex gap-3 font-mono text-[10px] text-muted-foreground">
              <span><span class="text-foreground">{{ hunt.targetsScanned }}</span> targets</span>
              <span><span class="text-foreground">{{ hunt.findingsFound }}</span> findings</span>
              <span v-if="hunt.status === 'running'"><span class="text-foreground">{{ formatUptime(uptime) }}</span></span>
            </div>
            <div class="flex gap-1.5">
              <Tooltip v-if="hunt.status === 'idle'" text="Iniciar pipeline autónomo de 5 etapas: Discover → Recon → Hypothesis → Validate → Report">
                <Button size="sm" @click="hunt.start()" :loading="hunt.loading">
                  <Play class="h-3.5 w-3.5" /> Iniciar
                </Button>
              </Tooltip>
              <Tooltip v-if="hunt.status === 'running'" text="Pausar temporalmente la caza">
                <Button size="sm" variant="secondary" @click="hunt.pause()" :loading="hunt.loading">
                  <Pause class="h-3.5 w-3.5" /> Pausar
                </Button>
              </Tooltip>
              <Tooltip v-if="hunt.status === 'paused'" text="Reanudar la caza desde donde se pausó">
                <Button size="sm" variant="secondary" @click="hunt.resume()" :loading="hunt.loading">
                  <Play class="h-3.5 w-3.5" /> Reanudar
                </Button>
              </Tooltip>
              <Tooltip v-if="hunt.isActive" text="Detener la caza por completo">
                <Button size="sm" variant="destructive" @click="hunt.stop()" :loading="hunt.loading">
                  <Square class="h-3.5 w-3.5" />
                </Button>
              </Tooltip>
            </div>
          </div>
          <!-- MissionConfig -->
          <div v-if="settings.data.missionControl" class="cyber-card rounded-xl p-4 min-w-[180px] hidden sm:block">
            <span class="font-mono text-[10px] font-bold tracking-wider text-muted-foreground">CONFIGURACIÓN</span>
            <div class="mt-2 space-y-1 font-mono text-[10px] text-muted-foreground">
              <div class="flex justify-between"><span>Modo</span><span class="text-foreground">{{ settings.data.missionControl.autoMode ? 'Auto' : 'Manual' }}</span></div>
              <div class="flex justify-between"><span>Paralelismo</span><span class="text-foreground">{{ settings.data.missionControl.parallelism }}</span></div>
              <div class="flex justify-between"><span>Velocidad</span><span class="text-foreground">{{ settings.data.missionControl.speed }}</span></div>
              <div class="flex justify-between"><span>Profundidad</span><span class="text-foreground">{{ settings.data.missionControl.depth }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div v-for="(kpi, i) in kpiItems" :key="kpi.label" class="cyber-card rounded-xl p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">{{ kpi.label }}</span>
            <div class="flex h-6 w-6 items-center justify-center rounded-md bg-surface/50" :style="{ color: kpi.color }">
              <component :is="kpi.icon" class="h-3.5 w-3.5" />
            </div>
          </div>
          <p class="font-mono text-xl font-bold tabular-nums text-foreground" :style="{ color: kpi.color }">{{ kpi.value }}</p>
        </div>
      </div>

      <!-- Next Action -->
      <div v-if="nextAction" class="animate-in">
        <div class="cyber-card rounded-xl p-5 border-l-2 border-l-primary">
          <div class="flex items-start gap-4">
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><Zap class="h-5 w-5" /></div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-primary">
                <Sparkles class="h-3 w-3" /><span>Próxima acción</span>
              </div>
              <h3 class="mt-1 text-base font-semibold text-foreground">{{ nextAction.title }}</h3>
              <p class="mt-1 text-xs text-muted-foreground">{{ nextAction.why_now }}</p>
              <div class="mt-3 flex flex-wrap gap-4">
                <span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                  <Clock class="h-3 w-3" /> Esfuerzo: <span :class="nextAction.effort === 'low' ? 'text-success' : nextAction.effort === 'medium' ? 'text-warning' : 'text-destructive'" class="font-semibold">{{ nextAction.effort }}</span>
                </span>
                <span class="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                  <DollarSign class="h-3 w-3" /> Recompensa: <span class="font-semibold text-gold">{{ nextAction.estimated_reward }}</span>
                </span>
              </div>
            </div>
            <ArrowRight class="mt-2 h-5 w-5 shrink-0 text-muted-foreground" />
          </div>
        </div>
      </div>

      <!-- Pipeline & Charts -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <!-- Pipeline bar -->
        <div class="lg:col-span-2 cyber-card rounded-xl p-5">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-4">Pipeline</h3>
          <div class="flex items-end gap-2 h-24">
            <div v-for="stage in pipelineStages" :key="stage.label" class="flex-1 flex flex-col items-center gap-2">
              <div class="w-full rounded-t-md transition-all duration-500" :class="stage.color">
                <div class="w-full rounded-t-md" :style="{ height: `${(stage.count / maxPipeline) * 100}%`, minHeight: stage.count > 0 ? '8px' : '0' }" />
              </div>
              <span class="font-mono text-sm font-bold tabular-nums text-foreground">{{ stage.count }}</span>
              <span class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">{{ stage.label }}</span>
            </div>
          </div>
        </div>

        <!-- Doughnut -->
        <div class="cyber-card rounded-xl p-5">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-3">Distribución</h3>
          <DoughnutChart
            :labels="['Detectados', 'Validados', 'Confirmados', 'Reportados']"
            :data="[ctx.pipeline.detected, ctx.pipeline.validated, ctx.pipeline.confirmed, ctx.pipeline.reported]"
            :height="180"
          />
        </div>
      </div>

      <!-- Activity & Opportunities -->
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Top Opps -->
        <div class="lg:col-span-2 cyber-card rounded-xl p-5">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-3">Oportunidades prioritarias</h3>
          <div v-if="!opportunities.length" class="py-6 text-center font-mono text-xs text-muted-foreground">Sin oportunidades disponibles</div>
          <div v-else class="space-y-1.5">
            <div v-for="(opp, i) in opportunities" :key="opp.id"
              class="flex items-center justify-between rounded-lg bg-surface/20 px-3 py-2 transition-all hover:bg-surface/40"
            >
              <div class="flex-1 min-w-0">
                <p class="font-mono text-xs font-semibold text-foreground truncate">{{ opp.name }}</p>
                <p class="font-mono text-[10px] text-muted-foreground">{{ opp.domain }} · {{ opp.endpoints }} endpoints</p>
              </div>
              <div class="flex items-center gap-2 shrink-0 ml-3">
                <span class="font-mono text-[9px] text-muted-foreground">SCORE {{ opp.opportunity_score.toFixed(1) }}</span>
                <div class="flex h-6 w-6 items-center justify-center rounded-md text-[10px] font-bold font-mono"
                  :class="opp.opportunity_score >= 7 ? 'bg-success/20 text-success' : opp.opportunity_score >= 4 ? 'bg-warning/20 text-warning' : 'bg-muted/20 text-muted-foreground'"
                >{{ opp.opportunity_score.toFixed(0) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Activity -->
        <div class="cyber-card rounded-xl p-5">
          <h3 class="font-mono text-xs font-semibold text-foreground mb-3">Actividad 24h</h3>
          <div class="space-y-2">
            <div v-for="(ev, i) in activityEvents.slice(0, 10)" :key="i" class="animate-in flex items-start gap-3" :style="{ animationDelay: `${i * 30}ms` }">
              <div :class="['mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', ev.type === 'finding' ? 'bg-destructive/15 text-destructive' : 'bg-accent/15 text-accent']">
                <Bug v-if="ev.type === 'finding'" class="h-3 w-3" />
                <Activity v-else class="h-3 w-3" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-mono text-[10px] font-medium text-foreground capitalize">{{ ev.type }} #{{ ev.id }}</p>
                <p v-if="ev.severity" class="mt-0.5"><Badge :variant="severityBadge(ev.severity)" class="text-[8px] px-1.5 py-0">{{ ev.severity }}</Badge></p>
              </div>
            </div>
            <div v-if="activityEvents.length === 0" class="py-6 text-center font-mono text-xs text-muted-foreground">Sin actividad en 24h</div>
          </div>
        </div>
      </div>
    </template>
  </div>
  <OnboardingWizard :open="showOnboarding" @close="showOnboarding = false" />
</template>
