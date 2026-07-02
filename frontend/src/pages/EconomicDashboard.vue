<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  DollarSign, TrendingUp, TrendingDown, Clock, Target, ArrowRight, Wallet,
  Sparkles, Brain, Radar, FileText, Globe, Gauge,
  Unlink, ListChecks, BarChart3, Zap, ShieldCheck, Activity,
  ChevronRight, LayoutDashboard, Bug, PieChart,
} from '@lucide/vue'
import { BarChart, DoughnutChart, LineChart } from '@/components/charts'

interface RadarItem {
  id: number; name: string; platform: string; orion_score: number
  max_reward: number | null; evh: number; competition: number
  total_earned: number; total_reports: number; confirmed_reports: number
  technologies_summary: string | null
}
interface RoiData {
  total_earned: number; total_pending: number; usd_per_hour: number
  usd_per_hour_rating: string; weekly_earnings: number; monthly_earnings: number
  best_program: string | null; acceptance_rate: number; report_count: number
}
interface FinData {
  total_collected: number; total_pending: number; total_estimated: number
  usd_per_hour: number; best_program: string | null; next_action: string | null
}
interface QueueItem {
  id: number; report_id: number; report_title: string; report_status: string
  program: string; vulnerability: string; estimated_reward: number
  priority_score: number; expected_value: number; time_to_submit: string | null
}
interface PlatformEarnings {
  name: string; earned: number; pending: number; connected: boolean
}

const router = useRouter()
const loading = ref(true)
const radarItems = ref<RadarItem[]>([])
const roi = ref<RoiData | null>(null)
const fin = ref<FinData | null>(null)
const queue = ref<QueueItem[]>([])
const platformEarnings = ref<PlatformEarnings[]>([])
const showAllPrograms = ref(false)

const topPrograms = computed(() => {
  const items = [...radarItems.value].sort((a, b) => b.evh - a.evh)
  return showAllPrograms.value ? items : items.slice(0, 5)
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const totalBalance = computed(() => fin.value?.total_collected || roi.value?.total_earned || 0)
const totalPendingAmt = computed(() => fin.value?.total_pending || roi.value?.total_pending || 0)
const effectiveRate = computed(() => fin.value?.usd_per_hour || roi.value?.usd_per_hour || 0)
const bestProgramName = computed(() => fin.value?.best_program || roi.value?.best_program || '—')

const platformColors: Record<string, string> = {
  hackerone: 'bg-emerald-500', bugcrowd: 'bg-orange-500', intigriti: 'bg-purple-500',
  synack: 'bg-blue-500', yeswehack: 'bg-rose-400',
}
const platformTextColors: Record<string, string> = {
  hackerone: 'text-emerald-400', bugcrowd: 'text-orange-400', intigriti: 'text-purple-400',
  synack: 'text-blue-400', yeswehack: 'text-rose-300',
}

onMounted(async () => {
  try {
    const [radarRes, roiRes, finRes, queueRes, platRes] = await Promise.all([
      api.get<{ items: RadarItem[] }>('/economic/money-radar', { limit: 50 }).catch(() => ({ items: [] })),
      api.get<RoiData>('/economic/roi-summary').catch(() => null),
      api.get<FinData>('/economic/financial-summary').catch(() => null),
      api.get<{ items: QueueItem[] }>('/economic/report-queue', { limit: 10 }).catch(() => ({ items: [] })),
      api.get<{ platforms: PlatformEarnings[] }>('/platforms/status').catch(() => ({ platforms: [] })),
    ])
    radarItems.value = radarRes.items || []
    roi.value = roiRes
    fin.value = finRes
    queue.value = queueRes.items || []
    if (platRes.platforms?.length) {
      platformEarnings.value = platRes.platforms.map((p: any) => ({
        name: p.name, earned: p.earnings || 0, pending: p.pending || 0, connected: p.connected,
      }))
    }
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function formatMoney(n: number | null | undefined) {
  if (n === null || n === undefined) return '—'
  return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function formatCompact(n: number | null | undefined) {
  if (n === null || n === undefined) return '—'
  if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '$' + (n / 1_000).toFixed(1) + 'k'
  return '$' + n.toLocaleString()
}

function scoreColor(s: number) {
  if (s >= 0.8) return 'success' as const
  if (s >= 0.6) return 'info' as const
  if (s >= 0.4) return 'warning' as const
  return 'default' as const
}

function competitionLabel(c: number) {
  if (c >= 0.7) return { text: 'Alta', color: 'text-destructive' }
  if (c >= 0.4) return { text: 'Media', color: 'text-warning' }
  return { text: 'Baja', color: 'text-success' }
}

function openProgram(id: number) { router.push({ name: 'program-intel', params: { id } }) }
function openPlan(id: number) { router.push({ name: 'opportunity-planner', params: { id } }) }
function openQueue() { router.push({ name: 'report-queue' }) }

const kpiData = computed(() => [
  { label: 'Ganado', value: formatCompact(totalBalance.value), sub: 'USD cobrados', color: 'text-success', border: 'border-l-success', icon: Wallet },
  { label: 'Pendiente', value: formatCompact(totalPendingAmt.value), sub: 'USD por cobrar', color: 'text-warning', border: 'border-l-warning', icon: Clock },
  { label: 'USD/hora', value: formatCompact(effectiveRate.value), sub: roi.value?.usd_per_hour_rating || '—', color: 'text-primary', border: 'border-l-primary', icon: Gauge },
  { label: 'Mejor programa', value: bestProgramName.value, sub: roi.value?.acceptance_rate ? (roi.value.acceptance_rate * 100).toFixed(0) + '% aceptación' : '—', color: 'text-gold', border: 'border-l-gold', icon: Target },
])
</script>

<template>
  <div class="space-y-5">
    <!-- Loading state -->
    <template v-if="loading">
      <div class="space-y-4">
        <div class="flex items-center gap-3 pb-2">
          <Skeleton class="h-10 w-10 rounded-xl" />
          <div class="space-y-2"><Skeleton class="h-4 w-48" /><Skeleton class="h-3 w-32" /></div>
        </div>
        <div class="grid grid-cols-4 gap-3"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div>
        <Skeleton class="h-32 rounded-xl" />
        <Skeleton class="h-72 rounded-xl" />
      </div>
    </template>

    <template v-else>
      <!-- Quick Navigation Strip -->
      <div class="animate-in flex items-center gap-1.5 rounded-xl border border-border/40 bg-[#11131f]/60 p-1.5 text-xs">
        <button @click="router.push({name:'money-radar'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <DollarSign class="h-3.5 w-3.5" /> Money Radar
        </button>
        <button @click="router.push({name:'findings'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <Bug class="h-3.5 w-3.5" /> Hallazgos
        </button>
        <button @click="router.push({name:'reports'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <FileText class="h-3.5 w-3.5" /> Reportes
        </button>
        <button @click="router.push({name:'hot-paths'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <Zap class="h-3.5 w-3.5" /> Rutas Críticas
        </button>
        <button @click="router.push({name:'radar'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <Radar class="h-3.5 w-3.5" /> Radar
        </button>
        <button @click="router.push({name:'connections'})" class="flex items-center gap-1.5 rounded-lg px-3 py-2 text-muted-foreground hover:bg-primary/10 hover:text-primary transition-all">
          <Globe class="h-3.5 w-3.5" /> Conexiones
        </button>
        <div class="ml-auto flex items-center gap-1.5">
          <span class="flex h-2 w-2 rounded-full bg-success animate-pulse" />
          <span class="text-[10px] text-muted-foreground">Sistema operativo</span>
        </div>
      </div>

      <!-- Hero: Greeting + Balance -->
      <div class="animate-in flex items-end justify-between rounded-xl border border-border/30 bg-gradient-to-r from-primary/[0.03] to-transparent p-5">
        <div class="space-y-1">
          <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">{{ greeting }}, OPERADOR</p>
          <h1 class="font-display text-2xl font-bold tracking-tight text-foreground">Panel Económico</h1>
          <p class="text-xs text-muted-foreground">Inteligencia financiera de bug bounty en tiempo real</p>
        </div>
        <div class="text-right">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">Balance total</p>
          <p class="animate-count text-2xl font-bold tabular-nums text-foreground">{{ formatCompact(totalBalance + totalPendingAmt) }}</p>
          <p class="text-[10px] text-muted-foreground">
            <span class="text-success">{{ formatCompact(totalBalance) }}</span> cobrado
            · <span class="text-warning">{{ formatCompact(totalPendingAmt) }}</span> pendiente
          </p>
        </div>
      </div>

      <!-- Platform Connection Cards -->
      <div v-if="platformEarnings.length" class="animate-in grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div
          v-for="p in platformEarnings" :key="p.name"
          class="glass-fintech rounded-xl px-3 py-2.5"
        >
          <div class="flex items-center gap-2">
            <span
              :class="['h-1.5 w-1.5 rounded-full', p.connected ? platformColors[p.name.toLowerCase()] || 'bg-primary' : 'bg-muted']"
            />
            <span class="text-[10px] font-semibold text-foreground">{{ p.name }}</span>
            <span v-if="p.connected" class="ml-auto text-[9px] text-muted-foreground">conectado</span>
            <span v-else class="ml-auto flex items-center gap-1 text-[9px] text-warning">
              <Unlink class="h-2.5 w-2.5" /> conectar
            </span>
          </div>
          <div v-if="p.connected" class="mt-1.5 flex gap-3">
            <div>
              <p class="text-[8px] text-muted-foreground">cobrado</p>
              <p class="text-xs font-semibold tabular-nums text-success">{{ formatCompact(p.earned) }}</p>
            </div>
            <div>
              <p class="text-[8px] text-muted-foreground">pendiente</p>
              <p class="text-xs font-semibold tabular-nums text-warning">{{ formatCompact(p.pending) }}</p>
            </div>
          </div>
          <p v-else class="mt-1 text-[9px] text-muted-foreground">Sin conexión</p>
        </div>
      </div>

      <!-- KPI Grid -->
      <div class="animate-in grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div
          v-for="(kpi, i) in kpiData" :key="i"
          :class="['glass-fintech rounded-xl p-4 border-l-2', kpi.border]"
        >
          <div class="flex items-center justify-between">
            <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{{ kpi.label }}</p>
            <component :is="kpi.icon" class="h-3.5 w-3.5 text-muted-foreground/50" />
          </div>
          <p :class="['mt-1.5 text-xl font-bold tabular-nums', kpi.color]">{{ kpi.value }}</p>
          <p class="mt-0.5 text-[10px] text-muted-foreground">{{ kpi.sub }}</p>
        </div>
      </div>

      <!-- Weekly / Monthly earnings + key stats -->
      <div class="animate-in grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div class="glass-fintech rounded-xl p-3 flex items-center gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success">
            <TrendingUp class="h-4 w-4" />
          </div>
          <div>
            <p class="text-[9px] font-medium text-muted-foreground">Esta semana</p>
            <p class="text-sm font-bold tabular-nums text-foreground">{{ formatCompact(roi?.weekly_earnings) }}</p>
          </div>
        </div>
        <div class="glass-fintech rounded-xl p-3 flex items-center gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <TrendingUp class="h-4 w-4" />
          </div>
          <div>
            <p class="text-[9px] font-medium text-muted-foreground">Este mes</p>
            <p class="text-sm font-bold tabular-nums text-foreground">{{ formatCompact(roi?.monthly_earnings) }}</p>
          </div>
        </div>
        <div class="glass-fintech rounded-xl p-3 flex items-center gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
            <Globe class="h-4 w-4" />
          </div>
          <div>
            <p class="text-[9px] font-medium text-muted-foreground">Reportes enviados</p>
            <p class="text-sm font-bold tabular-nums text-foreground">{{ roi?.report_count || 0 }}</p>
          </div>
        </div>
        <div class="glass-fintech rounded-xl p-3 flex items-center gap-3">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gold/10 text-gold">
            <Wallet class="h-4 w-4" />
          </div>
          <div>
            <p class="text-[9px] font-medium text-muted-foreground">Potencial total</p>
            <p class="text-sm font-bold tabular-nums text-foreground">{{ formatCompact(fin?.total_estimated) }}</p>
          </div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="animate-in grid grid-cols-1 gap-4 lg:grid-cols-2">
        <!-- Platform earnings doughnut -->
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <PieChart class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Distribución por plataforma</p>
          </div>
          <DoughnutChart
            v-if="platformEarnings.filter(p => p.connected).length > 0"
            :labels="platformEarnings.filter(p => p.connected).map(p => p.name)"
            :data="platformEarnings.filter(p => p.connected).map(p => p.earned)"
            :height="220"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">
            Conectá plataformas para ver la distribución
          </div>
        </Card>

        <!-- Program EVH comparison bar -->
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">EVH por programa</p>
          </div>
          <BarChart
            v-if="topPrograms.length"
            :labels="topPrograms.slice(0, 8).map(p => p.name.length > 16 ? p.name.slice(0, 14) + '…' : p.name)"
            :datasets="[{ label: 'EVH ($/h)', data: topPrograms.slice(0, 8).map(p => p.evh), backgroundColor: '#7c3aed' }]"
            :horizontal="true"
            :height="220"
            yLabel="Programa"
            xLabel="EVH (USD/h)"
            :showLegend="false"
          />
          <div v-else class="py-8 text-center text-xs text-muted-foreground">
            Sin datos de programas
          </div>
        </Card>
      </div>

      <!-- Earnings trend area chart -->
      <Card v-if="roi?.weekly_earnings || roi?.monthly_earnings" class="animate-in p-4">
        <div class="flex items-center gap-2 mb-3">
          <TrendingUp class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Tendencia de ingresos</p>
        </div>
        <LineChart
          :labels="['Semanal', 'Mensual']"
          :datasets="[
            { label: 'Ganado', data: [roi?.weekly_earnings || 0, roi?.monthly_earnings || 0], borderColor: '#7c3aed', fill: true },
          ]"
          :area="true"
          :height="180"
          yLabel="USD"
        />
      </Card>

      <!-- Next Action -->
      <div v-if="fin?.next_action" class="animate-in">
        <div class="glass-fintech rounded-xl border-l-2 border-l-primary p-4">
          <div class="flex items-start gap-3">
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles class="h-4 w-4" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-[9px] font-bold uppercase tracking-widest text-primary">Próxima acción</p>
              <p class="mt-0.5 text-sm font-medium text-foreground">{{ fin.next_action }}</p>
            </div>
            <ArrowRight class="mt-1.5 h-4 w-4 shrink-0 text-muted-foreground" />
          </div>
        </div>
      </div>

      <!-- Top Programs -->
      <div class="animate-in space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <Target class="h-3.5 w-3.5 text-primary" />
            Mejores programas para hoy
          </h2>
          <div class="flex items-center gap-2">
            <button
              v-if="radarItems.length > 5"
              @click="showAllPrograms = !showAllPrograms"
              class="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {{ showAllPrograms ? 'Mostrar menos' : 'Ver todos (' + radarItems.length + ')' }}
            </button>
            <Button variant="ghost" size="sm" @click="router.push({ name: 'money-radar' })">
              <ArrowRight class="h-3 w-3" />
            </Button>
          </div>
        </div>

        <div v-if="topPrograms.length" class="space-y-1.5">
          <div
            v-for="(item, i) in topPrograms" :key="item.id"
            class="glass-fintech rounded-xl px-4 py-3 flex items-center gap-4 cursor-pointer transition-all hover:border-primary/20"
            @click="openProgram(item.id)"
          >
            <div
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold"
              :class="i === 0 ? 'bg-gold/20 text-gold ring-1 ring-gold/20' : i === 1 ? 'bg-surface/50 text-muted-foreground' : i === 2 ? 'bg-warning/10 text-warning' : 'bg-surface/20 text-muted-foreground'"
            >
              {{ i + 1 }}
            </div>
            <div class="flex-1 min-w-0 grid grid-cols-12 gap-2 items-center">
              <div class="col-span-4 min-w-0">
                <p class="text-sm font-semibold text-foreground truncate">{{ item.name }}</p>
                <p class="text-[10px] text-muted-foreground flex items-center gap-1">
                  <span class="capitalize">{{ item.platform }}</span>
                  <span class="text-muted">·</span>
                  <span class="truncate">{{ item.technologies_summary || 'Sin datos' }}</span>
                </p>
              </div>
              <div class="col-span-2 text-right">
                <p class="text-sm font-bold tabular-nums text-success">{{ formatCompact(item.evh) }}/h</p>
                <p class="text-[9px] text-muted-foreground">EVH estimado</p>
              </div>
              <div class="col-span-2 text-right">
                <p class="text-sm font-semibold tabular-nums text-foreground">{{ formatMoney(item.max_reward) }}</p>
                <p class="text-[9px] text-muted-foreground">máx recompensa</p>
              </div>
              <div class="col-span-2 text-right">
                <Badge :variant="scoreColor(item.orion_score)" class="text-[9px]">
                  {{ (item.orion_score * 100).toFixed(0) }}
                </Badge>
                <p class="text-[9px] text-muted-foreground mt-0.5">orion score</p>
              </div>
              <div class="col-span-2 text-right">
                <span
                  class="text-[11px] font-medium"
                  :class="competitionLabel(item.competition).color"
                >
                  {{ competitionLabel(item.competition).text }}
                </span>
                <p class="text-[9px] text-muted-foreground">competencia</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="glass-fintech rounded-xl p-8 text-center">
          <Radar class="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p class="mt-2 text-sm text-muted-foreground">No hay programas con datos todavía</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Agregá programas desde Settings o esperá el primer escaneo</p>
        </div>
      </div>

      <!-- Report Queue Preview -->
      <div class="animate-in space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <ListChecks class="h-3.5 w-3.5 text-primary" />
            Cola priorizada de reportes
          </h2>
          <Button v-if="queue.length" variant="ghost" size="sm" @click="openQueue">
            <ArrowRight class="h-3 w-3" />
          </Button>
        </div>

        <div v-if="queue.length" class="space-y-1">
          <div
            v-for="(item, i) in queue.slice(0, 5)" :key="item.id"
            class="glass-fintech rounded-lg px-3.5 py-2.5 flex items-center gap-3 cursor-pointer transition-all hover:border-primary/20"
            @click="router.push({ name: 'reports' })"
          >
            <div
              class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-bold"
              :class="item.time_to_submit === 'immediate' ? 'bg-destructive/15 text-destructive' : item.time_to_submit === 'today' ? 'bg-warning/15 text-warning' : 'bg-accent/15 text-accent'"
            >
              {{ i + 1 }}
            </div>
            <div class="flex-1 min-w-0 grid grid-cols-10 gap-2 items-center">
              <div class="col-span-4 min-w-0">
                <p class="text-xs font-medium text-foreground truncate">{{ item.report_title || item.vulnerability }}</p>
                <p class="text-[10px] text-muted-foreground truncate">{{ item.program }} · {{ item.vulnerability }}</p>
              </div>
              <div class="col-span-3 text-right">
                <p class="text-xs font-semibold tabular-nums text-gold">{{ formatCompact(item.expected_value) }}</p>
                <p class="text-[9px] text-muted-foreground">valor esperado</p>
              </div>
              <div class="col-span-3 text-right">
                <Badge
                  :variant="item.time_to_submit === 'immediate' ? 'destructive' : item.time_to_submit === 'today' ? 'warning' : 'default'"
                  class="text-[9px]"
                >
                  {{ item.time_to_submit === 'immediate' ? 'URGENTE' : item.time_to_submit === 'today' ? 'HOY' : item.time_to_submit === 'this_week' ? 'SEMANA' : item.time_to_submit === 'this_month' ? 'MES' : '—' }}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="glass-fintech rounded-xl p-8 text-center">
          <FileText class="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p class="mt-2 text-sm text-muted-foreground">No hay reportes pendientes de priorizar</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Los reportes aparecerán aquí cuando ORION los analice</p>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="animate-in flex flex-wrap gap-2 pb-4">
        <Button variant="default" size="sm" @click="router.push({ name: 'money-radar' })">
          <DollarSign class="h-3.5 w-3.5" /> Explorar Money Radar
        </Button>
        <Button variant="secondary" size="sm" @click="router.push({ name: 'memory-patterns' })">
          <Brain class="h-3.5 w-3.5" /> Patrones aprendidos
        </Button>
        <Button variant="outline" size="sm" @click="router.push({ name: 'report-queue' })">
          <ListChecks class="h-3.5 w-3.5" /> Cola de reportes
        </Button>
        <Button variant="outline" size="sm" @click="router.push({ name: 'radar' })">
          <Radar class="h-3.5 w-3.5" /> Radar de oportunidades
        </Button>
      </div>
    </template>
  </div>
</template>