<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHuntStore } from '@/stores/hunt'
import { api } from '@/lib/api'
import type { PlatformStatus, BankAccount } from '@/lib/api'
import {
  Bug, Cable, ChevronLeft, ChevronRight, Cpu, Dices,
  DollarSign, ExternalLink, Eye, FileText, Globe,
  LayoutDashboard, Link2, MessageCircle, Search, Settings,
  Shield, Target, TrendingUp, Unlink,
  Activity, Database, RefreshCw, X, HeartPulse, Zap,
  Wallet, Sparkles, Bot, BarChart3, Brain, Coins,
  BookOpen, Lightbulb, UserRound,
} from '@lucide/vue'

const hunt = useHuntStore()
const emit = defineEmits<{
  'toggleCopilot': []
  'close': []
}>()

defineProps<{
  open: boolean
}>()

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const platforms = ref<PlatformStatus[]>([])
const bank = ref<BankAccount | null>(null)
const totalEarned = ref(0)
const totalPending = ref(0)
const loading = ref(true)

const navSections = [
  {
    section: 'MISIÓN',
    cycle: 'mission',
    items: [
      { name: 'Bienvenido', path: '/', icon: LayoutDashboard, exact: true },
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { name: 'HUNT', path: '/baby-mode', icon: Zap },
    ],
  },
  {
    section: 'SEGURIDAD ● Rastro',
    cycle: 'security',
    items: [
      { name: 'Targets', path: '/targets', icon: Target },
      { name: 'Findings', path: '/intelligence/findings', icon: Bug },
      { name: 'Hipótesis', path: '/intelligence/hypotheses', icon: Brain },
      { name: 'Evidencia', path: '/intelligence/evidence', icon: Shield },
      { name: 'Investigaciones', path: '/intelligence/investigations', icon: Search },
      { name: 'Confianza', path: '/intelligence/confidence', icon: BarChart3 },
    ],
  },
  {
    section: 'REPORTES',
    cycle: 'security',
    items: [
      { name: 'Cola Priorizada', path: '/reports/queue', icon: Database },
      { name: 'Centro de Reportes', path: '/reports/center', icon: FileText },
      { name: 'Historial', path: '/reports/history', icon: BookOpen },
      { name: 'Validación', path: '/reports/verification', icon: Shield },
    ],
  },
  {
    section: 'FORJA ● Dev Bounty',
    cycle: 'forge',
    items: [
      { name: 'Oportunidades', path: '/targets/prioritization', icon: Globe },
      { name: 'Bounties', path: '/integrations/platforms', icon: DollarSign },
    ],
  },
  {
    section: 'PULSO ● AI Work',
    cycle: 'pulse',
    items: [
      { name: 'MERLIN', path: '/merlin', icon: Bot },
      { name: 'Próximamente', path: '/faqs', icon: Sparkles },
    ],
  },
  {
    section: 'PERFIL',
    cycle: 'profile',
    items: [
      { name: 'Profile Kit', path: '/profile-kit', icon: UserRound },
    ],
  },
  {
    section: 'VAULT ● Wealth',
    cycle: 'vault',
    items: [
      { name: 'Capital Dashboard', path: '/capital', icon: DollarSign },
      { name: 'Investment Hub', path: '/investments', icon: TrendingUp },
      { name: 'ATLAS Inversiones', path: '/atlas/', icon: Coins },
      { name: 'Trading', path: '/trading', icon: Activity },
      { name: 'Polymarket', path: '/polymarket', icon: Dices },
      { name: 'Billeteras', path: '/integrations/wallets', icon: Wallet },
    ],
  },
  {
    section: 'ATLAS ● Intelligence',
    cycle: 'atlas',
    items: [
      { name: 'Knowledge Vault', path: '/knowledge', icon: Database },
      { name: 'Knowledge Graph', path: '/copilot/memory', icon: Database },
      { name: 'Aprendizaje', path: '/copilot/learning', icon: Brain },
      { name: 'Recomendaciones', path: '/copilot/recommendations', icon: Sparkles },
    ],
  },
  {
    section: 'SISTEMA',
    cycle: 'system',
    items: [
      { name: 'Operaciones', path: '/operations/dashboard', icon: Cpu },
      { name: 'Pipelines', path: '/operations/pipelines', icon: Activity },
      { name: 'Scheduler', path: '/operations/scheduler', icon: Zap },
      { name: 'Health Center', path: '/operations/health', icon: HeartPulse },
      { name: 'Configuración', path: '/operations/settings', icon: Settings },
      { name: 'Workflows', path: '/operations/workflows', icon: RefreshCw },
      { name: 'Conexiones', path: '/integrations/connections', icon: Cable },
      { name: 'Copilot', path: '/copilot/assistant', icon: MessageCircle },
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

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(path + '/')
}

function navigate(path: string) {
  router.push(path)
  emit('close')
}

onMounted(async () => {
  hunt.fetchStatus()
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
  <!-- Mobile backdrop -->
  <Transition name="backdrop">
    <div
      v-if="open && !collapsed"
      class="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
      @click="emit('close')"
    />
  </Transition>

  <aside
    :class="[
      'flex flex-col border-r border-border/50 bg-background/80 backdrop-blur-xl transition-all duration-200 z-30',
      'fixed inset-y-0 left-0 lg:relative lg:inset-auto',
      collapsed ? 'w-16' : 'w-60',
      open || collapsed ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    ]"
  >
    <!-- Mobile close -->
    <button
      class="absolute right-2 top-3 z-10 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-surface/40 hover:text-foreground lg:hidden"
      @click="emit('close')"
    >
      <X class="h-4 w-4" />
    </button>

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
        <span class="font-mono text-[9px] text-muted-foreground">{{ hunt.status === 'running' ? 'ACTIVE' : hunt.status === 'paused' ? 'PAUSED' : 'IDLE' }}</span>
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
      <div v-for="(group, gi) in navSections" :key="gi" class="mb-3">
        <Transition name="fade">
          <div v-if="!collapsed" class="mb-1 flex items-center gap-2 px-2">
            <span class="font-mono text-[9px] font-bold uppercase tracking-[0.15em] text-muted-foreground">{{ group.section }}</span>
            <span class="flex-1 h-px bg-gradient-to-r from-border to-transparent" />
          </div>
        </Transition>
        <button
          v-for="item in group.items"
          :key="item.path"
          @click="navigate(item.path)"
          :title="collapsed ? item.name : undefined"
          :class="[
            'group relative flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200',
            isActive(item.path)
              ? 'text-primary font-semibold'
              : 'text-muted-foreground hover:bg-surface/30 hover:text-foreground',
          ]"
        >
          <span
            v-if="isActive(item.path)"
            class="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary shadow-[0_0_6px_rgba(255, 255, 255,0.5)]"
          />
          <component :is="item.icon" :class="['h-4 w-4 shrink-0', isActive(item.path) ? 'scale-110 text-primary' : '']" />
          <Transition name="fade">
            <span v-if="!collapsed" class="font-mono text-xs">{{ item.name }}</span>
          </Transition>
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
