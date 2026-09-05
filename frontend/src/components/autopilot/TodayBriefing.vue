<script setup lang="ts">
/**
 * TodayBriefing — the heart of OWNEX LITE mode.
 *
 * Shows exactly what the user needs to know:
 * 1. Capital & Income at a glance
 * 2. Next Best Action (prominent)
 * 3. System status (compact)
 * 4. Quick actions
 *
 * Philosophy: "Open → Read → Act → Leave"
 */

import {
  Activity,
  Bot,
  CalendarClock,
  CheckCircle,
  ChevronRight,
  CircleDollarSign,
  Clock,
  Cog,
  RefreshCw,
  Target,
  TrendingUp,
  Zap,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Skeleton from '@/components/ui/Skeleton.vue'
import { fetchOneAction, fetchPatrimony, fetchQuickWins, type OneAction } from '@/services/ownexData'

const router = useRouter()

const loading = ref(true)
const action = ref<OneAction | null>(null)
const patrimony = ref<any>(null)
const quickWins = ref<any[]>([])
const error = ref<string | null>(null)

// ── Data Loading ──────────────────────────────────────────────────────────

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [actionRes, patrimonyRes, quickWinsRes] = await Promise.allSettled([
      fetchOneAction(),
      fetchPatrimony(),
      fetchQuickWins(),
    ])

    if (actionRes.status === 'fulfilled') {
      action.value = actionRes.value.action || actionRes.value
    }
    if (patrimonyRes.status === 'fulfilled') {
      patrimony.value = patrimonyRes.value
    }
    if (quickWinsRes.status === 'fulfilled') {
      quickWins.value = (quickWinsRes.value as any).quick_wins || quickWinsRes.value || []
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ── Formatting ────────────────────────────────────────────────────────────

const usd = (n: number | null | undefined): string =>
  n != null ? `$${Math.round(n).toLocaleString('es-AR')}` : '—'

const pct = (n: number | null | undefined): string =>
  n != null ? `${Math.round(n * 100)}%` : '—'

const capital = computed(() => patrimony.value?.net_worth ?? patrimony.value?.total ?? null)
const monthlyIncome = computed(() => patrimony.value?.monthly_income ?? patrimony.value?.income?.monthly ?? null)
const goalProgress = computed(() => patrimony.value?.progress_to_1m ?? (capital.value ? capital.value / 1_000_000 : null))

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'GOOD MORNING'
  if (h < 18) return 'GOOD AFTERNOON'
  return 'GOOD EVENING'
})

const timeNow = computed(() => {
  return new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
})

// ── Actions ───────────────────────────────────────────────────────────────

function goToAction() {
  if (action.value?.url) {
    window.open(action.value.url, '_blank')
  }
}

function goToCapital() {
  router.push('/capital')
}

function goToOpportunities() {
  router.push('/opportunities')
}
</script>

<template>
  <div class="w-full max-w-2xl mx-auto space-y-6">
    <!-- Loading State -->
    <template v-if="loading">
      <div class="space-y-4 p-6">
        <Skeleton height="1rem" width="120px" />
        <Skeleton height="2rem" width="200px" />
        <div class="grid grid-cols-3 gap-4">
          <Skeleton height="3rem" />
          <Skeleton height="3rem" />
          <Skeleton height="3rem" />
        </div>
        <Skeleton height="8rem" />
      </div>
    </template>

    <!-- Error State -->
    <template v-else-if="error">
      <div class="p-6 text-center">
        <p class="text-sm text-destructive mb-2">Unable to load briefing</p>
        <p class="text-xs text-muted-foreground mb-4">{{ error }}</p>
        <button
          class="px-3 py-1.5 text-xs font-medium text-foreground bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors"
          @click="loadAll"
        >
          <RefreshCw class="h-3 w-3 mr-1 inline" />
          Retry
        </button>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- ── Greeting & Time ─────────────────────────────────────── -->
      <div class="flex items-center justify-between px-1">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
            {{ greeting }}
          </p>
          <p class="text-[10px] text-muted/60 mt-0.5">{{ timeNow }}</p>
        </div>
        <button
          class="p-1.5 rounded-lg hover:bg-muted/20 text-muted-foreground hover:text-foreground transition-colors"
          @click="loadAll"
          aria-label="Refresh briefing"
        >
          <RefreshCw class="h-3.5 w-3.5" />
        </button>
      </div>

      <!-- ── KPI Row ─────────────────────────────────────────────── -->
      <div class="grid grid-cols-3 gap-3">
        <!-- Capital -->
        <button
          class="group p-4 rounded-xl border border-border bg-surface hover:bg-surface-hover transition-all text-left"
          @click="goToCapital"
        >
          <div class="flex items-center gap-2 mb-2">
            <CircleDollarSign class="h-3.5 w-3.5 text-muted-foreground" />
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Capital</span>
          </div>
          <p class="font-mono text-xl font-bold tabular-nums text-foreground">
            {{ usd(capital) }}
          </p>
          <div class="flex items-center gap-1 mt-1">
            <ChevronRight class="h-3 w-3 text-muted-foreground group-hover:text-foreground transition-colors" />
            <span class="text-[10px] text-muted-foreground">View</span>
          </div>
        </button>

        <!-- Monthly Income -->
        <div class="p-4 rounded-xl border border-border bg-surface">
          <div class="flex items-center gap-2 mb-2">
            <TrendingUp class="h-3.5 w-3.5 text-muted-foreground" />
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Income</span>
          </div>
          <p class="font-mono text-xl font-bold tabular-nums text-foreground">
            {{ usd(monthlyIncome) }}
          </p>
          <p class="text-[10px] text-muted-foreground mt-1">/month</p>
        </div>

        <!-- $1M Progress -->
        <div class="p-4 rounded-xl border border-border bg-surface">
          <div class="flex items-center gap-2 mb-2">
            <Target class="h-3.5 w-3.5 text-muted-foreground" />
            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">$1M</span>
          </div>
          <p class="font-mono text-xl font-bold tabular-nums text-foreground">
            {{ pct(goalProgress) }}
          </p>
          <!-- Progress bar -->
          <div class="mt-2 h-1 rounded-full bg-muted/20 overflow-hidden">
            <div
              class="h-full rounded-full bg-foreground/60 transition-all duration-500"
              :style="{ width: `${Math.min((goalProgress ?? 0) * 100, 100)}%` }"
            />
          </div>
        </div>
      </div>

      <!-- ── Next Best Action ────────────────────────────────────── -->
      <div v-if="action && action.action_type !== 'strategic_review'" class="rounded-xl border border-border bg-surface overflow-hidden">
        <!-- Action Header -->
        <div class="flex items-center gap-2 px-5 py-3 border-b border-border bg-muted/5">
          <Zap class="h-3.5 w-3.5 text-foreground" />
          <span class="text-[10px] font-bold uppercase tracking-widest text-foreground">Next Best Action</span>
        </div>

        <!-- Action Content -->
        <div class="p-5">
          <div class="flex items-start justify-between mb-3">
            <div>
              <h3 class="text-base font-semibold text-foreground">{{ action.title }}</h3>
              <p class="text-xs text-muted-foreground mt-0.5">{{ action.why }}</p>
            </div>
            <span
              class="px-2 py-0.5 text-[10px] font-semibold rounded-full"
              :class="{
                'bg-destructive/15 text-destructive': action.urgency === 'immediate',
                'bg-warning/15 text-warning': action.urgency === 'today',
                'bg-primary/15 text-primary': action.urgency === 'this_week',
              }"
            >
              {{ action.urgency === 'immediate' ? 'NOW' : action.urgency === 'today' ? 'TODAY' : 'THIS WEEK' }}
            </span>
          </div>

          <!-- Economics -->
          <div class="grid grid-cols-3 gap-3 mb-4">
            <div class="text-center p-2 rounded-lg bg-muted/10">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">EV</p>
              <p class="font-mono text-sm font-bold tabular-nums text-success">
                {{ usd(action.expected_value_usd) }}
              </p>
            </div>
            <div class="text-center p-2 rounded-lg bg-muted/10">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">EV/h</p>
              <p class="font-mono text-sm font-bold tabular-nums text-foreground">
                {{ usd(action.ev_per_human_hour_usd) }}
              </p>
            </div>
            <div class="text-center p-2 rounded-lg bg-muted/10">
              <p class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">Time</p>
              <p class="font-mono text-sm font-bold tabular-nums text-foreground">
                {{ action.estimated_human_hours ? `${action.estimated_human_hours}h` : '—' }}
              </p>
            </div>
          </div>

          <!-- Action Button -->
          <button
            v-if="action.url"
            class="w-full py-2.5 rounded-lg bg-foreground text-background text-sm font-semibold hover:bg-foreground/90 transition-colors flex items-center justify-center gap-2"
            @click="goToAction"
          >
            Start Now
            <ChevronRight class="h-4 w-4" />
          </button>
        </div>
      </div>

      <!-- ── No Action Required ──────────────────────────────────── -->
      <div
        v-else-if="action && action.action_type === 'strategic_review'"
        class="rounded-xl border border-success/30 bg-success/5 p-5 flex items-center gap-3"
      >
        <CheckCircle class="h-5 w-5 text-success shrink-0" />
        <div>
          <p class="text-sm font-semibold text-success">NO ACTION REQUIRED</p>
          <p class="text-xs text-muted-foreground">OWNEX will continue monitoring for opportunities.</p>
        </div>
      </div>

      <!-- ── System Status (compact) ─────────────────────────────── -->
      <div class="flex items-center justify-between px-1 py-2">
        <div class="flex items-center gap-4 text-[10px] text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 rounded-full bg-success" />
            OWNEX Working
          </span>
          <span class="flex items-center gap-1.5">
            <Bot class="h-3 w-3" />
            Agents active
          </span>
        </div>
        <button
          class="text-[10px] text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          @click="router.push('/settings')"
        >
          <Cog class="h-3 w-3" />
          Settings
        </button>
      </div>
    </template>
  </div>
</template>
