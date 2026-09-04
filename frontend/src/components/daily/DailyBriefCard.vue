<script setup lang="ts">
/**
 * DailyBriefCard — "¿Qué hago ahora?" ranked action list.
 * Consumes /api/daily-brief or /direct-work/daily-brief.
 * Shows top actions with EV, probability, time estimate, and next concrete step.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  Clock,
  DollarSign,
  ExternalLink,
  Loader2,
  Target,
  TrendingUp,
  Zap,
} from '@lucide/vue'
import { api } from '@/lib/api'

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)

interface BriefAction {
  id: string
  title: string
  platform: string
  category: string
  expected_value_usd: number
  expected_value_per_hour: number
  probability: number
  estimated_hours: number
  reward_usd: number
  score: number
  url: string
  next_action: string
  action_type: string
}

interface BriefResponse {
  actions: BriefAction[]
  blocked: Array<{ id: string; title: string; phase: string; description: string }>
  completed_today: Array<{ id: string; title: string; phase: string }>
  summary: {
    total_expected_usd: number
    action_count: number
    blocked_count: number
    completed_count: number
    revenue_today_usd: number
  }
  greeting: string
}

const brief = ref<BriefResponse | null>(null)

const topActions = computed(() => brief.value?.actions.slice(0, 5) ?? [])
const blockedItems = computed(() => brief.value?.blocked ?? [])

const usd = (n: number) => `$${Math.round(n).toLocaleString()}`

const platformColor = (p: string) => {
  const map: Record<string, string> = {
    hackerone: 'text-orange-400',
    bugcrowd: 'text-red-400',
    intigriti: 'text-blue-400',
    yeswehack: 'text-green-400',
    opire: 'text-purple-400',
    issuehunt: 'text-yellow-400',
    algora: 'text-cyan-400',
    outlier: 'text-pink-400',
    mindrift: 'text-indigo-400',
    fiverr: 'text-green-300',
  }
  return map[p.toLowerCase()] ?? 'text-muted-foreground'
}

const probBadge = (p: number) => {
  if (p >= 0.7) return 'bg-success/15 text-success'
  if (p >= 0.4) return 'bg-warning/15 text-warning'
  return 'bg-destructive/15 text-destructive'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    brief.value = await api.get<BriefResponse>('/daily-brief')
  } catch (e) {
    // Fallback: try the existing direct-work daily-brief
    try {
      const fallback = await api.post<{
        ranked: Array<{ opportunity?: { title?: string; platform?: string; category?: string; payment?: number; url?: string }; final_score?: number; score?: number }>
        summary?: string
      }>('/direct-work/daily-brief', { profile: {}, limit: 5 })
      brief.value = {
        actions: (fallback.ranked ?? []).map((r, i) => ({
          id: `opp-${i}`,
          title: r.opportunity?.title ?? 'Opportunity',
          platform: r.opportunity?.platform ?? 'unknown',
          category: r.opportunity?.category ?? 'unknown',
          expected_value_usd: r.opportunity?.payment ?? 0,
          expected_value_per_hour: 0,
          probability: 0.5,
          estimated_hours: 2,
          reward_usd: r.opportunity?.payment ?? 0,
          score: r.final_score ?? r.score ?? 0,
          url: r.opportunity?.url ?? '',
          next_action: 'Review opportunity',
          action_type: 'opportunity',
        })),
        blocked: [],
        completed_today: [],
        summary: {
          total_expected_usd: 0,
          action_count: fallback.ranked?.length ?? 0,
          blocked_count: 0,
          completed_count: 0,
          revenue_today_usd: 0,
        },
        greeting: 'Today\'s opportunities',
      }
    } catch {
      error.value = 'No se pudo cargar el briefing diario'
    }
  } finally {
    loading.value = false
  }
}

function openAction(action: BriefAction) {
  if (action.url) {
    window.open(action.url, '_blank', 'noopener')
  } else {
    router.push('/operations/work-queue')
  }
}

onMounted(load)
</script>

<template>
  <div class="rounded-xl border border-border/20 bg-surface/30 p-5 space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
          <Zap class="h-4 w-4 text-primary" />
        </div>
        <div>
          <h3 class="font-mono text-xs font-semibold uppercase tracking-wider">¿Qué hago ahora?</h3>
          <p class="font-mono text-[10px] text-muted-foreground">{{ brief?.greeting || 'Cargando...' }}</p>
        </div>
      </div>
      <button
        v-if="brief"
        @click="load"
        class="text-muted-foreground hover:text-foreground transition-colors"
        title="Actualizar"
      >
        <Loader2 v-if="loading" class="h-3.5 w-3.5 animate-spin" />
        <TrendingUp v-else class="h-3.5 w-3.5" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && !brief" class="flex items-center justify-center py-6">
      <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
    </div>

    <!-- Error -->
    <p v-else-if="error" class="text-xs text-destructive text-center py-4">{{ error }}</p>

    <!-- Content -->
    <template v-else-if="brief">
      <!-- Summary badges -->
      <div class="flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-wider">
        <span class="rounded-md bg-primary/10 px-2 py-1 text-primary">
          {{ brief.summary.action_count }} acciones
        </span>
        <span v-if="brief.summary.total_expected_usd > 0" class="rounded-md bg-success/10 px-2 py-1 text-success">
          {{ usd(brief.summary.total_expected_usd) }} EV total
        </span>
        <span v-if="brief.summary.blocked_count > 0" class="rounded-md bg-warning/10 px-2 py-1 text-warning">
          {{ brief.summary.blocked_count }} bloqueados
        </span>
        <span v-if="brief.summary.completed_count > 0" class="rounded-md bg-muted/50 px-2 py-1 text-muted-foreground">
          {{ brief.summary.completed_count }} completados
        </span>
      </div>

      <!-- Blocked items -->
      <div v-if="blockedItems.length > 0" class="space-y-1">
        <p class="font-mono text-[10px] uppercase tracking-wider text-warning">⚠️ Necesitan tu aprobación</p>
        <div
          v-for="b in blockedItems"
          :key="b.id"
          class="flex items-center justify-between rounded-lg border border-warning/20 bg-warning/5 px-3 py-2"
        >
          <div class="min-w-0">
            <p class="font-mono text-xs font-medium truncate">{{ b.title }}</p>
            <p class="font-mono text-[10px] text-muted-foreground">{{ b.description }}</p>
          </div>
          <button
            @click="router.push('/operations/work-queue')"
            class="ml-2 shrink-0 text-warning hover:text-foreground transition-colors"
          >
            <ArrowRight class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <!-- Top actions -->
      <div v-if="topActions.length > 0" class="space-y-1.5">
        <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Acciones rankeadas</p>
        <button
          v-for="action in topActions"
          :key="action.id"
          @click="openAction(action)"
          class="w-full text-left rounded-lg border border-border/20 bg-surface/20 px-3 py-2.5 hover:border-primary/30 hover:bg-primary/5 transition-all group"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="font-mono text-xs font-medium truncate group-hover:text-primary transition-colors">
                  {{ action.title }}
                </p>
                <ExternalLink class="h-3 w-3 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <div class="mt-1 flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
                <span :class="platformColor(action.platform)">{{ action.platform }}</span>
                <span>·</span>
                <span>{{ action.next_action }}</span>
              </div>
            </div>
            <div class="shrink-0 text-right space-y-0.5">
              <p class="font-mono text-xs font-bold text-success tabular-nums">{{ usd(action.expected_value_usd) }}</p>
              <div class="flex items-center justify-end gap-1">
                <span class="rounded px-1 py-0.5 text-[9px] font-mono" :class="probBadge(action.probability)">
                  {{ Math.round(action.probability * 100) }}%
                </span>
                <span class="flex items-center text-[10px] text-muted-foreground">
                  <Clock class="h-2.5 w-2.5 mr-0.5" />
                  {{ action.estimated_hours }}h
                </span>
              </div>
            </div>
          </div>
        </button>
      </div>

      <!-- Empty state -->
      <div v-else class="text-center py-4">
        <Target class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
        <p class="font-mono text-xs text-muted-foreground">Sin acciones pendientes</p>
        <p class="font-mono text-[10px] text-muted-foreground/60 mt-1">OWNEX está buscando oportunidades</p>
      </div>
    </template>
  </div>
</template>
