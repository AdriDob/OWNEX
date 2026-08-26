<script setup lang="ts">
/**
 * OWNEX CEO HOME — Income Command Center ('/', 2026-08-25).
 * Responde en <60s sin documentación: ¿cuánto gano? ¿qué hago? ¿por qué?
 * ¿qué hace OWNEX? ¿qué hago yo? ¿cuándo cobro?
 * Datos reales únicamente: /applications/income-plan + /mission/status.
 */

import { computed, onMounted, ref } from 'vue'
import { Bot, CircleUser, ExternalLink } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import DailyDigest from '@/components/daily/DailyDigest.vue'
import { fetchIncomePlan, fetchMissionStatus, fetchCapitalSnapshot, fetchAiCenter, fetchCareerStatus, fetchZeroBarrierStats, fetchRevenueTimeline, fetchPlatformRanking, type IncomePlanAction, type IncomePlanState, type CapitalSnapshot, type PlatformRankingItem } from '@/services/ownexData'
import { api } from '@/lib/api'

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
  if (!lastVisit || hoursSince < 4) { digest.value = null; return }

  try {
    Promise.allSettled([
      api.get<{ finding_count?: number; target_count?: number }>('/overview'),
      api.get<{ pending_amount?: number }>('/revenue/summary'),
    ]).then(([findRes, revRes]) => {
      const findings = findRes.status === 'fulfilled' ? (findRes.value.finding_count || 0) : 0
      const pending = revRes.status === 'fulfilled' ? (revRes.value.pending_amount || 0) : 0
      if (!findings && !pending) { digest.value = null; return }
      digest.value = {
        newOpportunities: findings,
        pendingUsd: pending,
        aiHealthy: aiOk.value !== false,
        hoursSince: Math.round(hoursSince),
      }
    })
  } catch { digest.value = null }
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

const usd = (n: number): string => `$${Math.round(n).toLocaleString('es-AR')}`
const rangeLabel = (r: { low: number; high: number }): string =>
  r.low === r.high ? usd(r.low) : `${usd(r.low)}–${usd(r.high)}`

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
const humanActions = computed<Array<IncomePlanAction>>(
  () => income.value?.phases.this_week.slice(0, 5) ?? [],
)

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
    const [cap, ai] = await Promise.allSettled([
      fetchCapitalSnapshot(),
      fetchAiCenter(),
    ])
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
  loading.value = false
  computeDigest()
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">OWNEX Command Center</h1>
        <p class="text-sm text-muted-foreground">Autonomous Work Operating System</p>
      </div>
      <Badge v-if="system" :variant="statusVariant" dot>
        {{ system.status.toUpperCase() }} · salud {{ Math.round(system.health) }}%
      </Badge>
    </div>

    <ErrorState v-if="error && !income" title="No se pudo cargar el plan de ingresos" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading && !income" />

    <template v-else-if="income">
      <!-- N0: DAILY DIGEST — qué importa hoy (agrega de todos los sistemas) -->
      <DailyDigest />

      <!-- N1: NEXT ACTION dominante -->
      <NextBestAction
        v-if="income.next_action"
        :title="income.next_action.title"
        :description="income.next_action.detail || ''"
        :href="income.next_action.url || '/operations/applications'"
        :primary-action="{ label: income.next_action.url ? 'Abrir y ejecutar' : 'Ver plan completo', variant: 'primary' }"
        :secondary-action="{ label: 'Posponer', variant: 'ghost' }"
        :reasoning="income.next_action.why || income.philosophy"
        :ev-per-hour="income.next_action.ev_per_human_hour_usd ?? null"
        :payoff-range="income.next_action.payoff_range ?? null"
        :cash-speed-days="income.next_action.cash_speed_days ?? null"
        :assessment-required="income.next_action.assessment_required ?? null"
        :zero-experience="income.next_action.zero_experience ?? null"
        :expected-cash="income.next_action.expected_cash ?? null"
        :htroi="income.next_action.htroi ?? null"
        :confidence-band="income.next_action.confidence_band ?? null"
      />

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

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
            <CircleUser class="h-4 w-4 text-gold" aria-hidden="true" />
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">👤 Tus próximas acciones</p>
          </div>
          <ol v-if="humanActions.length" class="space-y-2">
            <li v-for="(a, i) in humanActions" :key="a.title" class="flex items-start gap-2.5 rounded-lg border border-border/20 bg-surface/20 p-2.5">
              <span class="mt-0.5 font-mono text-[10px] text-muted-foreground">{{ i + 1 }}</span>
              <div class="min-w-0 flex-1">
                <a v-if="a.url" :href="a.url" target="_blank" rel="noopener noreferrer"
                  class="inline-flex items-center gap-1 truncate font-mono text-xs font-medium text-accent hover:underline">
                  {{ a.title }} <ExternalLink class="h-3 w-3 shrink-0" />
                </a>
                <p v-else class="truncate font-mono text-xs font-medium">{{ a.title }}</p>
                <p v-if="a.ev_per_human_hour_usd != null" class="font-mono text-[10px] text-muted-foreground">
                  ${{ a.ev_per_human_hour_usd }}/h documentado
                  <template v-if="a.human_hours != null"> · {{ a.human_hours }} h</template>
                </p>
              </div>
            </li>
          </ol>
          <p v-else class="text-sm text-muted-foreground">
            Sin cola pendiente. OWNEX sigue buscando; esta lista se llena sola.
          </p>
        </Card>
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
    </template>
  </div>
</template>
