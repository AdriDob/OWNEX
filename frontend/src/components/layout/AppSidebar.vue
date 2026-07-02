<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useHuntStore } from '@/stores/hunt'
import { api } from '@/lib/api'
import type { PlatformStatus, BankAccount } from '@/lib/api'
import {
  LayoutDashboard, Radar, Route, Bug, FileText, Settings,
  ChevronLeft, ChevronRight, Play, Square, DollarSign,
  Wallet, Banknote, ExternalLink, RefreshCw, Unlink,
  ListChecks, Brain, Globe, Link2, Activity, Cpu, FileSearch,
  BarChart3, History, Sun,
  Target, Zap, Search, Lightbulb, GitCompare, BrainCircuit,
  UserCircle, Shield, PlayCircle, Camera, RotateCcw,
  GraduationCap, Bell, Clock,
} from '@lucide/vue'

const hunt = useHuntStore()
const emit = defineEmits<{ 'toggleCopilot': [] }>()
const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const platforms = ref<PlatformStatus[]>([])
const bank = ref<BankAccount | null>(null)
const totalEarned = ref(0)
const totalPending = ref(0)
const loading = ref(true)

const navItems = [
  { section: 'Inteligencia', items: [
    { name: 'Panel Económico', path: '/', icon: LayoutDashboard },
    { name: 'Money Radar', path: '/money-radar', icon: DollarSign },
    { name: 'Radar de Oportunidades', path: '/radar', icon: Radar },
    { name: 'Dashboard Principal', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Oportunidades', path: '/opportunities', icon: Target },
    { name: 'Bounties', path: '/bounties', icon: DollarSign },
    { name: 'Catálogo Programas', path: '/program-catalog', icon: Globe },
    { name: 'Próxima Acción', path: '/next-action', icon: Zap },
  ]},
  { section: 'Operaciones', items: [
    { name: 'Rutas Críticas', path: '/hot-paths', icon: Route },
    { name: 'Pipeline Hallazgos', path: '/findings', icon: Bug },
    { name: 'Monitor Pipelines', path: '/pipelines', icon: Activity },
    { name: 'Centro Reportes', path: '/reports', icon: FileText },
    { name: 'Cola Priorizada', path: '/report-queue', icon: ListChecks },
    { name: 'Patrones Aprendidos', path: '/memory-patterns', icon: Brain },
    { name: 'Investigaciones', path: '/investigations', icon: Search },
    { name: 'Hipótesis', path: '/hypotheses', icon: Lightbulb },
    { name: 'Análisis Diferencial', path: '/differential', icon: GitCompare },
    { name: 'Insights', path: '/insights', icon: BrainCircuit },
    { name: 'Tareas', path: '/tasks', icon: ListChecks },
    { name: 'Billeteras', path: '/wallets', icon: Wallet },
    { name: 'Identidad', path: '/identity', icon: UserCircle },
    { name: 'Operaciones', path: '/operations', icon: Activity },
  ]},
  { section: 'Sistema', items: [
    { name: 'Centro Agentes', path: '/agents', icon: Cpu },
    { name: 'Centro Evidencia', path: '/evidence', icon: FileSearch },
    { name: 'Hoy', path: '/daily', icon: Sun },
    { name: 'Conexiones', path: '/connections', icon: Link2 },
    { name: 'Configuración', path: '/settings', icon: Settings },
    { name: 'Superficie Ataque', path: '/attack-surface', icon: Shield },
    { name: 'Acciones', path: '/actions', icon: PlayCircle },
    { name: 'Inteligencia Adaptativa', path: '/intelligence', icon: Brain },
    { name: 'Capturas', path: '/screenshots', icon: Camera },
    { name: 'Reproducir', path: '/replay', icon: RotateCcw },
    { name: 'Perfil Aprendizaje', path: '/personal-intelligence', icon: GraduationCap },
    { name: 'Notificaciones', path: '/notifications', icon: Bell },
    { name: 'Dashboard Proyecto', path: '/project-dashboard', icon: BarChart3 },
    { name: 'Historial Reportes', path: '/report-history', icon: Clock },
  ]},
]

const platformColors: Record<string, string> = {
  hackerone: 'text-hackerone',
  bugcrowd: 'text-bugcrowd',
  intigriti: 'text-intigriti',
  synack: 'text-synack',
  yeswehack: 'text-yeswehack',
}

const connectedCount = computed(() => platforms.value.filter(p => p.connected).length)

function isActive(path: string) { return route.path === path }
function navigate(path: string) { router.push(path) }

onMounted(async () => {
  hunt.fetchStatus()
  try {
    const [pRes, bRes, ctxRes] = await Promise.allSettled([
      api.get<{ platforms: PlatformStatus[] }>('/platforms/status'),
      api.get<BankAccount>('/economic/bank-account'),
      api.get<{ total_earned: number; total_pending: number }>('/economic/financial-summary'),
    ])
    if (pRes.status === 'fulfilled') platforms.value = pRes.value.platforms || []
    if (bRes.status === 'fulfilled') bank.value = bRes.value
    if (ctxRes.status === 'fulfilled') {
      totalEarned.value = (ctxRes.value as any).total_collected || 0
      totalPending.value = (ctxRes.value as any).total_pending || 0
    }
  } catch {
    // graceful degradation — platforms/bank are optional
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
      'flex flex-col border-r border-border/50 bg-background/80 backdrop-blur-xl transition-all duration-200 relative z-30',
      collapsed ? 'w-16' : 'w-60',
    ]"
  >
    <!-- Logo -->
    <div class="flex h-14 items-center gap-3 border-b border-border/40 px-4">
      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/20">
        <span class="font-display text-sm font-bold">O</span>
      </div>
      <Transition name="fade">
        <span v-if="!collapsed" class="font-display text-sm font-semibold tracking-wide text-foreground">ORION</span>
      </Transition>
      <div v-if="!collapsed" class="ml-auto flex items-center gap-1">
        <span
          :class="[
            'h-1.5 w-1.5 rounded-full',
            hunt.status === 'running' ? 'bg-success animate-pulse' : hunt.status === 'paused' ? 'bg-warning' : 'bg-muted',
          ]"
        />
        <span
          v-if="hunt.status === 'running'"
          class="relative flex h-1.5 w-1.5"
        >
          <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-40" />
          <span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
        </span>
        <span class="text-[9px] text-muted-foreground">{{ hunt.status === 'running' ? 'VIVO' : hunt.status === 'paused' ? 'PAUSA' : 'OFF' }}</span>
      </div>
    </div>

    <!-- Balance summary -->
    <Transition name="fade">
      <div v-if="!collapsed && !loading" class="border-b border-border/30 px-4 py-3">
        <div class="rounded-lg bg-gradient-to-br from-primary/5 via-transparent to-transparent px-3 py-2.5 ring-1 ring-primary/10">
          <p class="text-[9px] font-semibold uppercase tracking-widest text-muted-foreground">Balance</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-foreground">{{ formatCompact(totalEarned) }}</p>
          <div class="mt-1 flex items-center justify-between text-[10px]">
            <span class="text-muted-foreground">Pendiente</span>
            <span class="font-medium text-warning">{{ formatCompact(totalPending) }}</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Platforms -->
    <Transition name="fade">
      <div v-if="!collapsed" class="border-b border-border/30 px-3 py-2.5">
        <div class="mb-1.5 flex items-center justify-between px-1">
          <span class="text-[8px] font-bold uppercase tracking-widest text-muted-foreground">Plataformas</span>
          <span class="text-[8px] text-muted-foreground">{{ connectedCount }}/{{ platforms.length || 4 }}</span>
        </div>
        <div class="space-y-1">
          <div
            v-for="p in (platforms.length ? platforms : [
              { name: 'HackerOne', connected: false },
              { name: 'Bugcrowd', connected: false },
              { name: 'Intigriti', connected: false },
              { name: 'Synack', connected: false },
            ])"
            :key="p.name"
            class="flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-surface/30"
          >
            <div class="relative flex h-2 w-2 shrink-0">
              <span
                v-if="p.connected"
                class="absolute inline-flex h-full w-full animate-ping rounded-full opacity-40"
                :class="platformColors[p.name.toLowerCase()]?.replace('text-', 'bg-') || 'bg-primary'"
              />
              <span
                :class="[
                  'h-2 w-2 rounded-full',
                  p.connected ? (platformColors[p.name.toLowerCase()] || 'bg-primary') + ' ' + (platformColors[p.name.toLowerCase()]?.replace('text-', 'bg-') || 'bg-primary') : 'bg-muted',
                ]"
              />
            </div>
            <span class="flex-1 text-[11px] font-medium text-foreground">{{ p.name }}</span>
            <span v-if="p.connected && p.earnings !== undefined" class="text-[9px] tabular-nums text-primary">{{ formatCompact(p.earnings) }}</span>
            <Unlink v-else class="h-2.5 w-2.5 text-muted-foreground" />
          </div>
        </div>
      </div>
    </Transition>

    <!-- Bank account -->
    <Transition name="fade">
      <div v-if="!collapsed" class="border-b border-border/30 px-3 py-2">
        <button
          class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] transition-all hover:bg-surface/30"
        >
          <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
            <Banknote class="h-3 w-3" />
          </div>
          <div class="flex-1 text-left">
            <p class="text-[10px] text-muted-foreground">Cuenta bancaria</p>
            <p class="text-xs font-medium" :class="bank?.connected ? 'text-foreground' : 'text-muted-foreground'">
              {{ bank?.connected ? bank.bank_name + ' ••' + bank.last_four : 'Conectar cuenta' }}
            </p>
          </div>
          <ExternalLink v-if="bank?.connected" class="h-3 w-3 text-muted-foreground" />
          <span v-else class="flex h-2 w-2 rounded-full bg-warning" />
        </button>
      </div>
    </Transition>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-2 py-3 scrollbar-none">
      <div v-for="(group, gi) in navItems" :key="gi" class="mb-3">
        <Transition name="fade">
          <p v-if="!collapsed" class="mb-1 px-2 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
            {{ group.section }}
          </p>
        </Transition>
        <button
          v-for="item in group.items"
          :key="item.path"
          @click="navigate(item.path)"
          :class="[
            'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200 hover-scale',
            isActive(item.path)
              ? 'bg-primary/10 text-primary font-semibold shadow-sm'
              : 'text-muted-foreground hover:bg-surface/40 hover:text-foreground',
          ]"
        >
          <component :is="item.icon" class="h-4 w-4 shrink-0" />
          <Transition name="fade">
            <span v-if="!collapsed">{{ item.name }}</span>
          </Transition>
        </button>
      </div>
    </nav>

    <!-- Bottom actions -->
    <div class="border-t border-border/30 p-2 space-y-1">
      <button
        @click="emit('toggleCopilot')"
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-all duration-200 hover:bg-surface/40 hover:text-foreground"
      >
        <svg class="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <Transition name="fade">
          <span v-if="!collapsed">Copiloto</span>
        </Transition>
      </button>
      <button
        @click="collapsed = !collapsed"
        class="flex w-full items-center justify-center rounded-lg px-3 py-2 text-muted-foreground transition-all duration-200 hover:bg-surface/40"
      >
        <ChevronLeft v-if="!collapsed" class="h-4 w-4" />
        <ChevronRight v-else class="h-4 w-4" />
      </button>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scrollbar-none { scrollbar-width: none; }
.scrollbar-none::-webkit-scrollbar { display: none; }
</style>