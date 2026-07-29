<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import {
  LayoutDashboard, Target, Search, Bug, Shield, BarChart3,
  FileText, ClipboardList, DollarSign, Wallet, Coins, Link2,
  Settings, Cpu, Zap, Bell, ChevronLeft, ChevronRight,
  Brain, MessageSquare, Database, HardDrive, Globe, Activity,
  Users, Key, RefreshCw, Terminal, BookOpen, Sparkles, TrendingUp
} from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const route = useRoute()
const router = useRouter()
const { toast } = useToast()
const collapsed = ref(false)

const navSections = [
  {
    section: 'MISIÓN',
    items: [
      { name: 'Mission Control', path: '/', icon: LayoutDashboard, exact: true },
    ],
  },
  {
    section: 'SEGURIDAD ● Rastro',
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
    items: [
      { name: 'Cola Priorizada', path: '/reports/queue', icon: ClipboardList },
      { name: 'Centro de Reportes', path: '/reports/center', icon: FileText },
      { name: 'Historial', path: '/reports/history', icon: Database },
      { name: 'Validación', path: '/reports/verification', icon: Shield },
    ],
  },
  {
    section: 'VAULT ● Wealth',
    items: [
      { name: 'Capital Dashboard', path: '/capital', icon: DollarSign },
      { name: 'Investment Hub', path: '/investments', icon: Coins },
      { name: 'ATLAS Inversiones', path: '/atlas/', icon: TrendingUp },
      { name: 'Trading', path: '/trading', icon: Activity },
    ],
  },
  {
    section: 'OPERACIONES',
    items: [
      { name: 'Dashboard', path: '/operations/dashboard', icon: Activity },
      { name: 'Pipelines', path: '/operations/pipelines', icon: Cpu },
      { name: 'Scheduler', path: '/operations/scheduler', icon: Zap },
      { name: 'Herramientas', path: '/operations/tools', icon: Terminal },
      { name: 'Health Center', path: '/operations/health', icon: Activity },
      { name: 'Terminal', path: '/terminal', icon: Terminal },
      { name: 'Configuración', path: '/operations/settings', icon: Settings },
      { name: 'Workflows', path: '/operations/workflows', icon: RefreshCw },
      { name: 'Replay', path: '/operations/replay', icon: BookOpen },
      { name: 'Logs', path: '/operations/logs', icon: HardDrive },
    ],
  },
  {
    section: 'INTEGRACIONES',
    items: [
      { name: 'Conexiones', path: '/integrations/connections', icon: Link2 },
      { name: 'Billeteras', path: '/integrations/wallets', icon: Wallet },
      { name: 'Cuentas', path: '/integrations/accounts', icon: Users },
      { name: 'Plataformas', path: '/integrations/platforms', icon: Globe },
      { name: 'Sync Center', path: '/integrations/sync', icon: RefreshCw },
      { name: 'Identidad', path: '/integrations/identity', icon: Key },
    ],
  },
  {
    section: 'COPILOT',
    items: [
      { name: 'Asistente', path: '/copilot/assistant', icon: MessageSquare },
      { name: 'Memoria', path: '/copilot/memory', icon: Database },
      { name: 'Aprendizaje', path: '/copilot/learning', icon: Brain },
      { name: 'Recomendaciones', path: '/copilot/recommendations', icon: Sparkles },
      { name: 'Notificaciones', path: '/copilot/notifications', icon: Bell },
    ],
  },
  {
    section: 'APPS',
    items: [
      { name: 'OWNEX Platform', path: '/orion/', icon: LayoutDashboard },
      { name: 'ODYSSEY (Analytics)', path: '/odyssey/', icon: Activity },
      { name: 'AEGIS (Pentesting)', path: '/aegis/', icon: Shield },
      { name: 'Polymarket', path: '/polymarket', icon: DollarSign },
    ],
  },
]

interface NavItem {
  name: string
  path: string
  icon: any
  exact?: boolean
  children?: string[]
}

function isActive(item: NavItem): boolean {
  if (item.exact) {
    return route.path === item.path
  }
  if (item.children) {
    return item.children.some(child => route.path === child || route.path.startsWith(child + '/'))
  }
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

function navigate(path: string) {
  router.push(path)
}
</script>

<template>
  <aside
    class="flex flex-col border-r border-border bg-background/80 backdrop-blur-xl transition-all duration-200"
    :class="collapsed ? 'w-16' : 'w-56'"
  >
    <!-- Logo -->
    <div class="flex items-center gap-2 px-4 h-14 border-b border-border/40">
      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/30">
        <svg viewBox="0 0 512 512" width="20" height="20" fill="none">
          <polygon points="256,96 376,156 376,356 256,416 136,356 136,156" stroke="currentColor" stroke-width="6" fill="rgba(59,130,246,0.08)" />
          <circle cx="256" cy="256" r="24" fill="currentColor" opacity="0.8" />
        </svg>
      </div>
      <Transition name="fade">
        <span v-if="!collapsed" class="font-mono text-sm font-bold tracking-[0.15em] text-foreground">OWNEX</span>
      </Transition>
      <button v-if="!collapsed" class="ml-auto text-muted-foreground hover:text-foreground" @click="collapsed = !collapsed">
        <ChevronLeft class="h-4 w-4" />
      </button>
      <button v-else class="mx-auto text-muted-foreground hover:text-foreground" @click="collapsed = !collapsed">
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>

    <!-- Navigation -->
    <div class="flex-1 overflow-y-auto p-2 space-y-3 scrollbar-thin">
      <div v-for="section in navSections" :key="section.section">
        <div v-if="!collapsed" class="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
          {{ section.section }}
        </div>
        <button
          v-for="item in section.items"
          :key="item.path"
          class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors"
          :class="isActive(item) ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-surface/30'"
          @click="navigate(item.path)"
        >
          <component :is="item.icon" class="h-4 w-4 shrink-0" />
          <span v-if="!collapsed">{{ item.name }}</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.scrollbar-thin { scrollbar-width: thin; }
.scrollbar-thin::-webkit-scrollbar { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
