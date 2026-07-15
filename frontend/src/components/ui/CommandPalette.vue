<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useHuntStore } from '@/stores/hunt'
import { getTargets, getFindings, getReports } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Radar,
  Route,
  Bug,
  FileText,
  Settings,
  Search,
  Command,
  Play,
  Download,
  FileDown,
  Globe,
  Zap,
  Target,
  DollarSign,
  BookOpen,
  Shield,
  Activity,
  Link,
  Workflow,
  AlertTriangle,
  ChevronRight,
  Scan,
  Trophy,
  BarChart3,
  ShieldCheck,
  Layers,
  TrendingUp,
  Briefcase,
  LineChart,
  Map,
  Eye,
  Box,
  UserCheck,
  ListTodo,
  RefreshCw,
  CheckCircle,
  Camera,
  Bell,
  HelpCircle,
  AppWindow,
  Sliders,
  Stars,
  Bot,
  Lightbulb,
  Square,
  Trash2,
} from '@lucide/vue'

const router = useRouter()
const route = useRoute()
const hunt = useHuntStore()

const open = ref(false)
const search = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)

type Scope = 'all' | 'nav' | 'action' | 'target' | 'finding' | 'report'

const scopeMap: Record<string, { scope: Scope; label: string }> = {
  '>': { scope: 'action', label: 'Acciones' },
  '/': { scope: 'nav', label: 'Páginas' },
  '@': { scope: 'target', label: 'Targets' },
  '#': { scope: 'finding', label: 'Hallazgos' },
  $: { scope: 'report', label: 'Reportes' },
}

const currentScope = computed<{ scope: Scope; label: string }>(() => {
  const first = search.value[0]
  return scopeMap[first] || { scope: 'all', label: 'Todos' }
})

const query = computed(() => {
  const s = search.value
  if (s && s[0] in scopeMap) return s.slice(1).trim()
  return s.trim()
})

const navItems = computed(() => {
  const core: Array<{ name: string; path: string; icon: any; category: string }> = [
    { name: 'Mission Control', path: '/', icon: LayoutDashboard, category: 'core' },
    { name: 'Opportunity Radar', path: '/radar', icon: Radar, category: 'core' },
    { name: 'Hot Paths', path: '/hot-paths', icon: Route, category: 'core' },
    { name: 'Findings Pipeline', path: '/findings', icon: Bug, category: 'core' },
    { name: 'Report Center', path: '/reports', icon: FileText, category: 'core' },
    { name: 'Settings', path: '/settings', icon: Settings, category: 'core' },
    { name: 'Money Radar', path: '/money-radar', icon: DollarSign, category: 'finance' },
    { name: 'Financial Truth', path: '/financial-truth', icon: BarChart3, category: 'finance' },
    { name: 'Wallets', path: '/wallets', icon: Briefcase, category: 'finance' },
    { name: 'Agent Center', path: '/agents', icon: Bot, category: 'system' },
    { name: 'Workflows', path: '/workflows', icon: Workflow, category: 'system' },
    { name: 'Health Center', path: '/health-center', icon: Activity, category: 'system' },
    { name: 'Attack Surface', path: '/attack-surface', icon: Target, category: 'security' },
    { name: 'Agent Center', path: '/agents', icon: Shield, category: 'security' },
    { name: 'Intelligence Dashboard', path: '/intelligence', icon: TrendingUp, category: 'analytics' },
    { name: 'Opportunities', path: '/opportunities', icon: Zap, category: 'analytics' },
    { name: 'Pipeline Monitor', path: '/pipelines', icon: Activity, category: 'system' },
    { name: 'Evidence Center', path: '/evidence', icon: Scan, category: 'security' },
    { name: 'Truth Inspector', path: '/truth-inspector', icon: Eye, category: 'analytics' },
    { name: 'Hypothesis Queue', path: '/hypotheses', icon: Lightbulb, category: 'analytics' },
    { name: 'Investigations', path: '/investigations', icon: Search, category: 'security' },
    { name: 'Connections', path: '/connections', icon: Link, category: 'system' },
    { name: 'Daily Mode', path: '/daily', icon: CheckCircle, category: 'core' },
    { name: 'Next Action', path: '/next-action', icon: ChevronRight, category: 'core' },
    { name: 'Program Catalog', path: '/program-catalog', icon: BookOpen, category: 'discovery' },
    { name: 'Bounties', path: '/bounties', icon: Trophy, category: 'finance' },
    { name: 'Discovery', path: '/discovery', icon: Globe, category: 'discovery' },
  ]
  if (!query.value) return core
  const q = query.value.toLowerCase()
  return core.filter(i => i.name.toLowerCase().includes(q) || i.path.toLowerCase().includes(q))
})

const actionItems = [
  { name: 'Iniciar Caza Autónoma', action: 'start-hunt', icon: Play, category: 'hunt' },
  { name: 'Detener Caza', action: 'stop-hunt', icon: Square, category: 'hunt' },
  { name: 'Exportar Findings', action: 'export-findings', icon: Download, category: 'report' },
  { name: 'Generar Reporte', action: 'generate-report', icon: FileDown, category: 'report' },
  { name: 'Análisis Rápido', action: 'quick-analysis', icon: Zap, category: 'analysis' },
  { name: 'Verificar Hallazgos', action: 'verify-findings', icon: CheckCircle, category: 'analysis' },
  { name: 'Sincronizar Billeteras', action: 'sync-wallets', icon: RefreshCw, category: 'finance' },
  { name: 'Limpiar Caché', action: 'clear-cache', icon: Trash2, category: 'system' },
]

const targetResults = ref<Array<{ id: number; name: string; domain: string; score: number }>>([])
const findingResults = ref<Array<{ id: number; title: string; severity: string; status: string }>>([])
const reportResults = ref<Array<{ id: number; title: string; status: string }>>([])
const searching = ref(false)

interface PalNav { type: 'nav'; name: string; path: string; icon: any; category: string }
interface PalAction { type: 'action'; name: string; action: string; icon: any; category: string }
interface PalTarget { type: 'target'; name: string; target: { id: number; domain: string; score: number }; icon: any }
interface PalFinding { type: 'finding'; name: string; finding: { id: number; title: string; severity: string; status: string }; icon: any }
interface PalReport { type: 'report'; name: string; report: { id: number; title: string; status: string }; icon: any }

type PalItem = PalNav | PalAction | PalTarget | PalFinding | PalReport

const filteredNav = computed<PalNav[]>(() => {
  if (currentScope.value.scope !== 'all' && currentScope.value.scope !== 'nav') return []
  return navItems.value as PalNav[]
})

const filteredActions = computed<PalAction[]>(() => {
  if (currentScope.value.scope !== 'all' && currentScope.value.scope !== 'action') return []
  const q = query.value.toLowerCase()
  if (!q) return actionItems as PalAction[]
  return actionItems.filter(a => a.name.toLowerCase().includes(q)) as PalAction[]
})

const filteredTargets = computed<PalTarget[]>(() => {
  if (currentScope.value.scope !== 'all' && currentScope.value.scope !== 'target') return []
  return targetResults.value.map(t => ({ type: 'target' as const, name: t.name, target: t, icon: Globe }))
})

const filteredFindings = computed<PalFinding[]>(() => {
  if (currentScope.value.scope !== 'all' && currentScope.value.scope !== 'finding') return []
  return findingResults.value.map(f => ({ type: 'finding' as const, name: f.title, finding: f, icon: Bug }))
})

const filteredReports = computed<PalReport[]>(() => {
  if (currentScope.value.scope !== 'all' && currentScope.value.scope !== 'report') return []
  return reportResults.value.map(r => ({ type: 'report' as const, name: r.title, report: r, icon: FileText }))
})

const flatItems = computed<(PalNav | PalAction | PalTarget | PalFinding | PalReport)[]>(() => {
  return [...filteredNav.value, ...filteredActions.value, ...filteredTargets.value, ...filteredFindings.value, ...filteredReports.value]
})

function onToggle() {
  open.value = !open.value
  if (open.value) {
    search.value = ''
    selectedIndex.value = 0
    targetResults.value = []
    findingResults.value = []
    reportResults.value = []
    nextTick(() => inputRef.value?.focus())
  }
}

function execute(item: PalItem) {
  open.value = false
  if (item.type === 'nav') {
    router.push(item.path)
  } else if (item.type === 'action') {
    handleAction(item.action)
  } else if (item.type === 'target') {
    router.push(`/target/${item.target.id}`)
  } else if (item.type === 'finding') {
    router.push(`/findings/${item.finding.id}`)
  } else if (item.type === 'report') {
    router.push(`/reports/${item.report.id}`)
  }
}

function handleAction(action: string) {
  switch (action) {
    case 'start-hunt':
      hunt.start()
      router.push('/')
      break
    case 'stop-hunt':
      hunt.stop()
      break
    case 'export-findings':
      window.dispatchEvent(new CustomEvent('export-findings'))
      router.push('/findings')
      break
    case 'generate-report':
      router.push('/reports')
      break
    case 'quick-analysis':
      router.push('/radar')
      break
    case 'verify-findings':
      router.push('/verify')
      break
    case 'sync-wallets':
      router.push('/wallets')
      break
    case 'clear-cache':
      window.dispatchEvent(new CustomEvent('clear-cache'))
      break
  }
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function onSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  selectedIndex.value = 0
  const scope = currentScope.value.scope
  if (scope === 'all' || scope === 'target' || scope === 'finding' || scope === 'report') {
    searchTimeout = setTimeout(doSearch, 300)
  }
}

async function doSearch() {
  const q = query.value
  const scope = currentScope.value.scope
  if (!q && scope === 'all') return

  searching.value = true
  const promises: Promise<void>[] = []

  if (scope === 'all' || scope === 'target') {
    promises.push((async () => {
      try {
        const res = await getTargets({ search: q, limit: 5, sort_by: 'opportunity_score', sort_order: 'desc' })
        targetResults.value = (res.items || []).map(t => ({
          id: t.id, name: t.name, domain: t.domain, score: t.opportunity_score || 0,
        }))
      } catch { targetResults.value = [] }
    })())
  } else { targetResults.value = [] }

  if (scope === 'all' || scope === 'finding') {
    promises.push((async () => {
      try {
        const res = await getFindings({ search: q, limit: 5 })
        findingResults.value = (res.items || []).map(f => ({
          id: f.id, title: f.title, severity: f.severity, status: f.severity,
        }))
      } catch { findingResults.value = [] }
    })())
  } else { findingResults.value = [] }

  if (scope === 'all' || scope === 'report') {
    promises.push((async () => {
      try {
        const res = await getReports({ search: q, limit: 5 })
        reportResults.value = (res.items || []).map(r => ({
          id: r.id, title: r.vulnerability || r.program, status: r.status,
        }))
      } catch { reportResults.value = [] }
    })())
  } else { reportResults.value = [] }

  await Promise.all(promises)
  searching.value = false
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    onToggle()
  }
  if (!open.value) return
  if (e.key === 'Escape') { open.value = false; return }
  if (e.key === 'ArrowDown') { e.preventDefault(); selectedIndex.value = (selectedIndex.value + 1) % Math.max(flatItems.value.length, 1) }
  if (e.key === 'ArrowUp') { e.preventDefault(); selectedIndex.value = (selectedIndex.value - 1 + flatItems.value.length) % Math.max(flatItems.value.length, 1) }
  if (e.key === 'Enter' && flatItems.value[selectedIndex.value]) execute(flatItems.value[selectedIndex.value])
}

function severityColor(s: string) {
  const map: Record<string, string> = { critical: 'text-red-400', high: 'text-orange-400', medium: 'text-yellow-400', low: 'text-blue-400', info: 'text-muted-foreground' }
  return map[s?.toLowerCase()] || 'text-muted-foreground'
}

function scopeHint(s: Scope) {
  const hints: Record<string, string> = { all: 'Escribí para buscar en todos los datos', nav: 'Buscá páginas...', action: 'Buscá acciones...', target: 'Buscá targets...', finding: 'Buscá hallazgos...', report: 'Buscá reportes...' }
  return hints[s] || ''
}

watch(() => route.fullPath, () => { open.value = false })

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('toggle-command-palette', onToggle as EventListener)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('toggle-command-palette', onToggle as EventListener)
  if (searchTimeout) clearTimeout(searchTimeout)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="overlay">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
        @click="open = false"
      >
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg animate-in fade-in-0 zoom-in-95" @click.stop>
          <div class="card-base rounded-xl overflow-hidden shadow-2xl shadow-black/40 border border-border/30">
            <!-- Search input -->
            <div class="flex items-center gap-3 border-b border-border/40 px-4 py-3">
              <Search class="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                v-model="search"
                @input="onSearchInput"
                :placeholder="scopeHint(currentScope.scope)"
                class="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/40 outline-none font-mono"
                ref="inputRef"
              />
              <div v-if="currentScope.scope !== 'all'" class="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                {{ currentScope.label }}
              </div>
              <kbd class="hidden sm:inline-flex items-center gap-1 rounded border border-border/50 bg-surface/50 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                <Command class="h-2.5 w-2.5" /> K
              </kbd>
            </div>

            <!-- Scope hints -->
            <div v-if="!query && currentScope.scope === 'all'" class="border-b border-border/20 px-4 py-2">
              <div class="flex flex-wrap gap-2 text-[10px] text-muted-foreground">
                <span><kbd class="rounded border border-border/30 bg-surface/30 px-1">&gt;</kbd> Acciones</span>
                <span><kbd class="rounded border border-border/30 bg-surface/30 px-1">/</kbd> Páginas</span>
                <span><kbd class="rounded border border-border/30 bg-surface/30 px-1">@</kbd> Targets</span>
                <span><kbd class="rounded border border-border/30 bg-surface/30 px-1">#</kbd> Hallazgos</span>
                <span><kbd class="rounded border border-border/30 bg-surface/30 px-1">$</kbd> Reportes</span>
              </div>
            </div>

            <!-- Results -->
            <div class="max-h-80 overflow-y-auto p-2">
              <!-- Searching indicator -->
              <div v-if="searching" class="py-8 text-center text-xs text-muted-foreground">
                Buscando...
              </div>

              <!-- Navigation group -->
              <div v-else-if="filteredNav.length > 0">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Navegación</p>
                <div v-for="item in filteredNav" :key="'nav-'+item.path">
                  <button
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    :class="cn(
                      'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                      flatItems.indexOf(item) === selectedIndex ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-surface/50',
                    )"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0" :class="flatItems.indexOf(item) === selectedIndex ? 'text-primary' : 'text-muted-foreground'" />
                    <span class="flex-1">{{ item.name }}</span>
                    <span class="text-[10px] text-muted-foreground/50">{{ item.path }}</span>
                  </button>
                </div>
              </div>

              <!-- Actions group -->
              <div v-if="filteredActions.length > 0" class="mt-1">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Acciones</p>
                <button
                  v-for="item in filteredActions" :key="'act-'+item.action"
                  @click="execute(item)"
                  @mouseenter="selectedIndex = flatItems.indexOf(item)"
                  :class="cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                    flatItems.indexOf(item) === selectedIndex ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-surface/50',
                  )"
                >
                  <component :is="item.icon" class="h-4 w-4 shrink-0" :class="flatItems.indexOf(item) === selectedIndex ? 'text-primary' : 'text-muted-foreground'" />
                  <span>{{ item.name }}</span>
                  <span class="ml-auto text-[10px] text-muted-foreground/50">{{ item.category }}</span>
                </button>
              </div>

              <!-- Targets group -->
              <div v-if="filteredTargets.length > 0" class="mt-1">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Targets</p>
                <button
                  v-for="item in filteredTargets" :key="'tgt-'+item.target.id"
                  @click="execute(item)"
                  @mouseenter="selectedIndex = flatItems.indexOf(item)"
                  :class="cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                    flatItems.indexOf(item) === selectedIndex ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-surface/50',
                  )"
                >
                  <Globe class="h-4 w-4 shrink-0" :class="flatItems.indexOf(item) === selectedIndex ? 'text-primary' : 'text-muted-foreground'" />
                  <div class="flex-1 min-w-0">
                    <span class="truncate">{{ item.name }}</span>
                    <span v-if="item.target.domain" class="ml-2 text-[10px] text-muted-foreground/60">{{ item.target.domain }}</span>
                  </div>
                  <span v-if="item.target.score" class="text-[10px] font-semibold text-gold shrink-0">{{ item.target.score.toFixed(1) }}</span>
                </button>
              </div>

              <!-- Findings group -->
              <div v-if="filteredFindings.length > 0" class="mt-1">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Hallazgos</p>
                <button
                  v-for="item in filteredFindings" :key="'fnd-'+item.finding.id"
                  @click="execute(item)"
                  @mouseenter="selectedIndex = flatItems.indexOf(item)"
                  :class="cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                    flatItems.indexOf(item) === selectedIndex ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-surface/50',
                  )"
                >
                  <Bug class="h-4 w-4 shrink-0" :class="flatItems.indexOf(item) === selectedIndex ? 'text-primary' : 'text-muted-foreground'" />
                  <div class="flex-1 min-w-0">
                    <span class="truncate">{{ item.name }}</span>
                  </div>
                  <span :class="['text-[10px] font-medium shrink-0 capitalize', severityColor(item.finding.severity)]">{{ item.finding.severity }}</span>
                </button>
              </div>

              <!-- Reports group -->
              <div v-if="filteredReports.length > 0" class="mt-1">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Reportes</p>
                <button
                  v-for="item in filteredReports" :key="'rpt-'+item.report.id"
                  @click="execute(item)"
                  @mouseenter="selectedIndex = flatItems.indexOf(item)"
                  :class="cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left',
                    flatItems.indexOf(item) === selectedIndex ? 'bg-primary/10 text-primary' : 'text-foreground hover:bg-surface/50',
                  )"
                >
                  <FileText class="h-4 w-4 shrink-0" :class="flatItems.indexOf(item) === selectedIndex ? 'text-primary' : 'text-muted-foreground'" />
                  <div class="flex-1 min-w-0">
                    <span class="truncate">{{ item.name }}</span>
                  </div>
                  <span class="text-[10px] capitalize text-muted-foreground/60 shrink-0">{{ item.report.status }}</span>
                </button>
              </div>

              <!-- Empty -->
              <div v-if="!searching && flatItems.length === 0 && (query || currentScope.scope !== 'all')" class="py-8 text-center text-sm text-muted-foreground">
                Sin resultados para "{{ query || search }}"
              </div>
            </div>

            <!-- Footer -->
            <div class="border-t border-border/40 px-4 py-2 flex items-center gap-4 text-[10px] text-muted-foreground">
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">↑↓</kbd> Navegar</span>
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">↵</kbd> Abrir</span>
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">Esc</kbd> Cerrar</span>
              <span class="ml-auto"><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">></kbd><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px] ms-0.5">/</kbd><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px] ms-0.5">@</kbd> Scopes</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay-enter-active, .overlay-leave-active { transition: opacity 0.15s ease; }
.overlay-enter-from, .overlay-leave-to { opacity: 0; }
</style>
