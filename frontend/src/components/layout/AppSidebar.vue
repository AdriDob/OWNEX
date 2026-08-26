<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHuntStore } from '@/stores/hunt'
import { api } from '@/lib/api'
import type { PlatformStatus, BankAccount } from '@/lib/api'
import {
  Bug, Cable, ChevronLeft, ChevronRight, ChevronDown, Cpu, Dices,
  DollarSign, ExternalLink, Eye, FileText, Globe,
  LayoutDashboard, Link2, MessageCircle, Search, Settings,
  Shield, Target, TrendingUp, Unlink,
  Activity, Database, RefreshCw, X, HeartPulse, Zap, Send,
  Copy, Wallet, Sparkles, Bot, BarChart3, Brain, Coins,
  BookOpen, Lightbulb, UserRound,
  Calendar, ListTodo, Landmark, ShieldAlert,
} from '@lucide/vue'

const hunt = useHuntStore()
const emit = defineEmits<{
  'toggleCopilot': []
}>()

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const platforms = ref<PlatformStatus[]>([])
const bank = ref<BankAccount | null>(null)
const totalEarned = ref(0)
const totalPending = ref(0)
const loading = ref(true)

// Dynamic badge counts from backend
const badgeCounts = ref<Record<string, number>>({})
const setupIncomplete = ref(false)

async function fetchBadges() {
  try {
    const [targets, workbank, findings] = await Promise.allSettled([
      api.get<{ target_count: number }>('/overview'),
      api.get<{ ready_to_deliver: number; needs_access: number }>('/direct-work/workbank'),
      api.get<{ finding_count: number }>('/overview'),
    ])
    if (targets.status === 'fulfilled') {
      badgeCounts.value.targets = targets.value.target_count || 0
    }
    if (workbank.status === 'fulfilled') {
      badgeCounts.value.workQueue = (workbank.value.ready_to_deliver || 0) + (workbank.value.needs_access || 0)
    }
    if (findings.status === 'fulfilled') {
      badgeCounts.value.findings = findings.value.finding_count || 0
    }

    // Check setup state
    const setupRes = await api.get<{ next_task: unknown; complete: boolean }>('/setup/checklist/status').catch(() => null)
    if (setupRes) setupIncomplete.value = !setupRes.complete
  } catch { /* silent */ }
}

function getBadge(path: string): number | null {
  if (path === '/targets') return badgeCounts.value.targets || null
  if (path === '/operations/work-queue') return badgeCounts.value.workQueue || null
  if (path === '/intelligence/findings') return badgeCounts.value.findings || null
  return null
}

function isSetupPending(path: string): boolean {
  if (!setupIncomplete.value) return false
  const setupPaths = ['/profile-kit', '/operations/applications', '/integrations/platforms']
  return setupPaths.includes(path)
}

const navSections = [
  {
    section: 'OPERATE',
    cycle: 'mission',
    items: [
      { name: 'Command Center', path: '/', icon: LayoutDashboard, exact: true },
      { name: 'HUNT', path: '/baby-mode', icon: Zap },
      { name: 'Oportunidades', path: '/targets/prioritization', icon: Globe },
      { name: 'Bounties', path: '/integrations/platforms', icon: DollarSign },
      { name: 'Postulaciones', path: '/operations/applications', icon: Send },
      { name: 'Profile Kit', path: '/profile-kit', icon: UserRound },
      { name: 'Capital Dashboard', path: '/capital', icon: DollarSign },
      { name: 'Centro de Ingresos', path: '/revenue/center', icon: Landmark },
      { name: 'Cola de Trabajo', path: '/operations/work-queue', icon: ListTodo },
      { name: 'Agenda', path: '/operations/agenda', icon: Calendar },
      { name: 'Investment Hub', path: '/investments', icon: TrendingUp },
      { name: 'ATLAS Inversiones', path: '/atlas/', icon: Coins },
      { name: 'Trading', path: '/trading', icon: Activity },
      { name: 'Copy Trading', path: '/trading/intelligence', icon: Copy },
      { name: 'Polymarket', path: '/polymarket', icon: Dices },
      // Reconnect Pass (2026-08-26): superficies construidas que estaban sin navegación.
      { name: 'Money Radar', path: '/money-radar', icon: Globe },
      { name: 'Verdad Financiera', path: '/financial-truth', icon: Landmark },
      { name: 'Revenue Multiplier', path: '/revenue-multiplier', icon: TrendingUp },
      { name: 'Finance Intel', path: '/finance-intel', icon: BarChart3 },
      { name: 'Hot Paths', path: '/hot-paths', icon: Zap },
      { name: 'Truth Inspector', path: '/truth-inspector', icon: Search },
      { name: 'Agentes', path: '/agents', icon: Bot },
      { name: 'Insights', path: '/insights', icon: Sparkles },
    ],
  },
  {
    section: 'INTELLIGENCE',
    cycle: 'atlas',
    items: [
      { name: 'Targets', path: '/targets', icon: Target },
      { name: 'Findings', path: '/intelligence/findings', icon: Bug },
      { name: 'Hipótesis', path: '/intelligence/hypotheses', icon: Brain },
      { name: 'Evidencia', path: '/intelligence/evidence', icon: Shield },
      { name: 'Investigaciones', path: '/intelligence/investigations', icon: Search },
      { name: 'Confianza', path: '/intelligence/confidence', icon: BarChart3 },
      { name: 'Cola Priorizada', path: '/reports/queue', icon: Database },
      { name: 'Centro de Reportes', path: '/reports/center', icon: FileText },
      { name: 'Historial', path: '/reports/history', icon: BookOpen },
      { name: 'Validación', path: '/reports/verification', icon: Shield },
      { name: 'Knowledge Vault', path: '/knowledge', icon: Database },
      { name: 'Knowledge Graph', path: '/copilot/memory', icon: Database },
      { name: 'Aprendizaje', path: '/copilot/learning', icon: Brain },
      { name: 'Recomendaciones', path: '/copilot/recommendations', icon: Sparkles },
    ],
  },
  {
    section: 'AUTOMATION',
    cycle: 'forge',
    items: [
      { name: 'MERLIN', path: '/merlin', icon: Bot },
      { name: 'Copilot', path: '/copilot/assistant', icon: MessageCircle },
      { name: 'Workflows', path: '/operations/workflows', icon: RefreshCw },
      { name: 'Scheduler', path: '/operations/scheduler', icon: Zap },
      { name: 'Pipelines', path: '/operations/pipelines', icon: Activity },
    ],
  },
  {
    section: 'SYSTEM',
    cycle: 'system',
    items: [
      { name: 'Operaciones', path: '/operations/dashboard', icon: Cpu },
      { name: 'Centro de IA', path: '/ai', icon: Bot },
      { name: 'Centro de Riesgo', path: '/risk', icon: ShieldAlert },
      { name: 'Health Center', path: '/operations/health', icon: HeartPulse },
      { name: 'Configuración', path: '/operations/settings', icon: Settings },
      { name: 'Conexiones', path: '/integrations/connections', icon: Cable },
      { name: 'Billeteras', path: '/integrations/wallets', icon: Wallet },
      { name: 'Próximamente', path: '/faqs', icon: Sparkles },
    ],
  },
]

const platformColors: Record<string, string> = {
  hackerone: 'text-hackerone',
  bugcrowd: 'text-bugcrowd',
  intigriti: 'text-intigriti',
  synack: 'text-synack',
  yeswehack: 'text-yeswehack',
}

const connectedCount = computed(() => platforms.value.filter(p => p.connected).length)

// Collapsible sections: show first 4 items, rest behind toggle
const expandedSections = ref<Set<number>>(new Set())
const VISIBLE_PER_SECTION = 4

function toggleSection(gi: number) {
  const s = new Set(expandedSections.value)
  if (s.has(gi)) s.delete(gi)
  else s.add(gi)
  expandedSections.value = s
}

function visibleItems(gi: number) {
  const items = navSections[gi]?.items ?? []
  if (expandedSections.value.has(gi)) return items
  // Always show all if any item is active
  if (items.some(item => isActive(item.path))) return items
  return items.slice(0, VISIBLE_PER_SECTION)
}

function hiddenCount(gi: number): number {
  const items = navSections[gi]?.items ?? []
  if (expandedSections.value.has(gi)) return 0
  if (items.some(item => isActive(item.path))) return 0
  return Math.max(0, items.length - VISIBLE_PER_SECTION)
}

// Keyboard shortcuts: g+h → home, g+w → work queue, g+c → capital
let lastKey = ''
function handleKeydown(e: KeyboardEvent) {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
  const key = e.key.toLowerCase()
  if (lastKey === 'g') {
    if (key === 'h') router.push('/')
    else if (key === 'w') router.push('/operations/work-queue')
    else if (key === 'c') router.push('/capital')
    lastKey = ''
    return
  }
  if (key === 'g' && !e.ctrlKey && !e.metaKey) { lastKey = 'g'; setTimeout(() => { lastKey = '' }, 1000); return }
}
onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

function navigate(path: string) {
  router.push(path)
}

onMounted(async () => {
  hunt.fetchStatus()
  fetchBadges()
  try {
    const [pRes, bRes, fRes, ctxRes] = await Promise.allSettled([
      api.get<{ platforms: PlatformStatus[] }>('/platforms/status'),
      api.get<BankAccount>('/economic/bank-account'),
      api.get<{ verified: number; pending: number; effective: number }>('/financial/state/summary'),
      api.get<{ total_earned: number; total_pending: number }>('/economic/financial-summary'),
    ])
    if (pRes.status === 'fulfilled') platforms.value = pRes.value.platforms || []
    if (bRes.status === 'fulfilled') bank.value = bRes.value
    if (fRes.status === 'fulfilled') {
      totalEarned.value = (fRes.value as any).verified || 0
      totalPending.value = (fRes.value as any).pending || 0
    } else if (ctxRes.status === 'fulfilled') {
      totalEarned.value = (ctxRes.value as any).total_collected || 0
      totalPending.value = (ctxRes.value as any).total_pending || 0
    }
  } catch (e) {
    console.warn('[Sidebar] Failed to load platforms/bank:', e)
  }
  loading.value = false
})

function formatCompact(n: number) {
  if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '$' + (n / 1_000).toFixed(1) + 'k'
  return '$' + n.toLocaleString()
}
</script>

<template>
  <aside
    :class="[
      'flex flex-col border-r border-border/50 bg-background/80 backdrop-blur-xl transition-all duration-200 z-30 relative',
      collapsed ? 'w-16' : 'w-60',
    ]"
  >
    <!-- OWNEX Logo -->
    <div class="flex h-14 items-center gap-3 border-b border-border/40 px-4">
      <div class="flex h-7 w-7 shrink-0 items-center justify-center">
        <svg viewBox="0 0 512 512" width="28" height="28" fill="none">
          <polygon points="256,96 376,156 376,356 256,416 136,356 136,156" stroke="#ffffff" stroke-width="6" fill="rgba(255, 255, 255,0.08)" />
          <circle cx="256" cy="256" r="24" fill="#ffffff" opacity="0.8" />
          <circle cx="256" cy="256" r="200" stroke="#ffffff" stroke-width="8" opacity="0.1" />
        </svg>
      </div>
      <Transition name="fade">
        <span v-if="!collapsed" class="font-display text-sm font-bold tracking-[0.2em] text-foreground">OWNEX</span>
      </Transition>
      <div v-if="!collapsed" class="ml-auto flex items-center gap-1">
        <span
          :class="[
            'h-1.5 w-1.5 rounded-full',
            hunt.status === 'running' ? 'bg-success animate-pulse' : hunt.status === 'paused' ? 'bg-warning' : 'bg-muted',
          ]"
        />
        <span class="font-mono text-[9px] text-muted-foreground">{{ hunt.status === 'running' ? 'ACTIVO' : hunt.status === 'paused' ? 'PAUSADO' : 'INACTIVO' }}</span>
      </div>
    </div>

    <!-- Balance summary -->
    <Transition name="fade">
      <div v-if="!collapsed && !loading" class="border-b border-border/30 px-4 py-3">
        <div class="relative overflow-hidden rounded-lg border border-border/30 bg-gradient-to-br from-surface to-background px-3 py-2.5">
          <div class="pointer-events-none absolute -right-4 -top-4 h-12 w-12 rounded-full bg-primary/5 blur-xl" />
          <p class="font-mono text-[9px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">Verificado</p>
          <p class="mt-0.5 font-mono text-base font-bold tabular-nums text-success">{{ formatCompact(totalEarned) }}</p>
          <div class="mt-1 flex items-center justify-between font-mono text-[10px]">
            <span class="text-muted-foreground">Pendiente</span>
            <span class="font-medium text-warning">{{ formatCompact(totalPending) }}</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Platforms mini -->
    <Transition name="fade">
      <div v-if="!collapsed" class="border-b border-border/30 px-3 py-2.5">
        <div class="mb-1.5 flex items-center justify-between px-1">
          <span class="font-mono text-[8px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Plataformas</span>
          <span class="font-mono text-[8px] text-muted-foreground">{{ connectedCount }}/{{ platforms.length || 4 }}</span>
        </div>
        <div class="space-y-1">
          <div
            v-for="p in (platforms.length ? platforms : [
              { name: 'HackerOne', connected: false },
              { name: 'Bugcrowd', connected: false },
              { name: 'Intigriti', connected: false },
              { name: 'YesWeHack', connected: false },
            ])"
            :key="p.name"
            class="flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-surface/30"
          >
            <div class="relative flex h-2 w-2 shrink-0">
              <span
                v-if="p.connected"
                class="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-40"
                :class="platformColors[p.name.toLowerCase()] || 'text-primary'"
              />
              <span
                :class="[
                  'h-2 w-2 rounded-full',
                  p.connected ? (platformColors[p.name.toLowerCase()]?.replace('text-', 'bg-') || 'bg-primary') : 'bg-muted',
                ]"
              />
            </div>
            <span class="flex-1 font-mono text-[11px] font-medium text-foreground">{{ p.name }}</span>
            <span v-if="p.connected && p.earnings !== undefined" class="font-mono text-[9px] tabular-nums text-primary">{{ formatCompact(p.earnings) }}</span>
            <Unlink v-else class="h-2.5 w-2.5 text-muted-foreground" />
          </div>
        </div>
      </div>
    </Transition>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-2 py-3 scrollbar-thin">
      <div v-for="(group, gi) in navSections" :key="gi" class="mb-1">
        <button
          v-if="!collapsed"
          @click="toggleSection(gi)"
          class="mb-0.5 flex w-full items-center gap-2 px-2 py-1 text-left group/section"
        >
          <span class="font-mono text-[9px] font-bold uppercase tracking-[0.15em] text-muted-foreground">{{ group.section }}</span>
          <span class="flex-1 h-px bg-gradient-to-r from-border to-transparent" />
          <ChevronDown
            v-if="hiddenCount(gi) > 0"
            :class="['h-3 w-3 text-muted-foreground transition-transform', expandedSections.has(gi) ? 'rotate-180' : '']"
          />
        </button>
        <!-- Collapsed: just show section label -->
        <div v-if="collapsed" class="mb-1 h-px bg-border/40 mx-2" />
        <button
          v-for="item in visibleItems(gi)"
          :key="item.path"
          @click="navigate(item.path)"
          :title="collapsed ? item.name : undefined"
          :class="[
            'group relative flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200',
            isActive(item.path)
              ? 'text-primary font-semibold'
              : isSetupPending(item.path)
                ? 'text-warning/70 hover:bg-surface/30 hover:text-foreground'
                : 'text-muted-foreground hover:bg-surface/30 hover:text-foreground',
          ]"
        >
          <span
            v-if="isActive(item.path)"
            class="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_6px_rgba(255, 255, 255,0.5)]"
          />
          <component :is="item.icon" :class="['h-4 w-4 shrink-0', isActive(item.path) ? 'scale-110 text-primary' : '']" />
          <Transition name="fade">
            <span v-if="!collapsed" class="flex-1 truncate font-mono text-xs">{{ item.name }}</span>
          </Transition>
          <!-- Dynamic badge count -->
          <span
            v-if="!collapsed && getBadge(item.path)"
            class="shrink-0 rounded-full bg-primary/15 px-1.5 py-0.5 font-mono text-[9px] font-bold tabular-nums text-primary"
          >
            {{ getBadge(item.path)! > 99 ? '99+' : getBadge(item.path) }}
          </span>
          <!-- Setup pending dot -->
          <span
            v-if="!collapsed && isSetupPending(item.path) && !getBadge(item.path)"
            class="h-1.5 w-1.5 shrink-0 rounded-full bg-warning animate-pulse"
          />
        </button>
        <!-- Show more / less toggle -->
        <button
          v-if="!collapsed && hiddenCount(gi) > 0"
          @click="toggleSection(gi)"
          class="w-full px-3 py-1 text-left font-mono text-[9px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
        >
          +{{ hiddenCount(gi) }} más…
        </button>
      </div>
    </nav>

    <!-- Bottom -->
    <div class="border-t border-border/30 p-2 space-y-1">
      <button
        @click="emit('toggleCopilot')"
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-all duration-200 hover:bg-surface/30 hover:text-foreground"
        :title="collapsed ? 'Copilot' : undefined"
      >
        <MessageCircle class="h-4 w-4 shrink-0" />
        <Transition name="fade">
          <span v-if="!collapsed" class="font-mono text-xs">Copilot</span>
        </Transition>
      </button>
      <button
        @click="collapsed = !collapsed"
        :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        class="group flex w-full items-center justify-center rounded-lg px-3 py-2 text-muted-foreground transition-all duration-200 hover:bg-surface/30 hover:text-foreground"
      >
        <ChevronLeft v-if="!collapsed" class="h-4 w-4 transition-transform duration-200 group-hover:-translate-x-0.5" />
        <ChevronRight v-else class="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.backdrop-enter-active, .backdrop-leave-active { transition: opacity 0.2s ease; }
.backdrop-enter-from, .backdrop-leave-to { opacity: 0; }
.scrollbar-thin { scrollbar-width: thin; }
.scrollbar-thin::-webkit-scrollbar { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
