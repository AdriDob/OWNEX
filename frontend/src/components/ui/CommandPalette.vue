<script setup lang="ts">
/**
 * CommandPalette — Ctrl+K operational command center.
 * Executes real actions via API, not just navigation.
 */

import {
  ArrowRight,
  Bot,
  CheckCircle,
  CircleDollarSign,
  FileText,
  Lightbulb,
  Radio,
  Search,
  Shield,
  Target,
  TrendingUp,
  X,
  Zap,
  Send,
  ExternalLink,
  RefreshCw,
  Clock,
  Brain,
  Database,
  Settings,
  Terminal,
  Play,
  Pause,
  RotateCcw,
  AlertTriangle,
  Link2,
  Globe,
} from '@lucide/vue'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { useHuntStore } from '@/stores/hunt'
import { useNotificationsStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

interface CommandItem {
  id: string
  label: string
  description?: string
  icon: any
  category: string
  action?: () => Promise<void>
  route?: string
  shortcut?: string
  confirm?: boolean
  dangerous?: boolean
}

const router = useRouter()
const hunt = useHuntStore()
const notifications = useNotificationsStore()
const auth = useAuthStore()

const isOpen = ref(false)
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const executing = ref<string | null>(null)
const searchResults = ref<CommandItem[]>([])
const isSearching = ref(false)
let searchTimeout: ReturnType<typeof setTimeout> | null = null

const commands: CommandItem[] = [
  // ── OWNEX OPERATIONS ──
  {
    id: 'own:start',
    label: 'Iniciar OWNEX',
    description: 'Arrancar scheduler + workers + pipelines',
    icon: Play,
    category: 'OWNEX',
    action: async () => {
      await api.post('/hunt/start')
      notifications.success('OWNEX iniciado')
    },
    shortcut: 'S',
  },
  {
    id: 'own:stop',
    label: 'Pausar OWNEX',
    description: 'Detener todos los workers (mantiene estado)',
    icon: Pause,
    category: 'OWNEX',
    action: async () => {
      await api.post('/hunt/pause')
      notifications.success('OWNEX pausado')
    },
    shortcut: 'P',
    dangerous: true,
  },
  {
    id: 'own:restart',
    label: 'Reiniciar OWNEX',
    description: 'Full restart: scheduler + pipelines + workers',
    icon: RotateCcw,
    category: 'OWNEX',
    action: async () => {
      await api.post('/hunt/restart')
      notifications.success('OWNEX reiniciado')
    },
    shortcut: 'R',
    dangerous: true,
  },
  {
    id: 'own:diagnose',
    label: 'Diagnóstico completo',
    description: 'Health check de todos los subsistemas',
    icon: Shield,
    category: 'OWNEX',
    action: async () => {
      const res = await api.get('/system/health')
      notifications.info(`Sistema: ${res.status} (${res.health}%)`)
    },
    shortcut: 'D',
  },

  // ── WORK (Money-making actions) ──
  {
    id: 'work:next',
    label: '¿Qué hago ahora?',
    description: 'Muestra la mejor acción inmediata (IncomeHome)',
    icon: Target,
    category: 'Trabajo',
    route: '/',
    shortcut: 'N',
  },
  {
    id: 'work:queue',
    label: 'Ver cola de trabajo',
    description: 'Trabajos listos para entregar / necesitan acceso',
    icon: Send,
    category: 'Trabajo',
    route: '/operations/work-queue',
    shortcut: 'Q',
  },
  {
    id: 'work:opportunities',
    label: 'Oportunidades > $100',
    description: 'Top oportunidades rankeadas por EV/hora humana',
    icon: CircleDollarSign,
    category: 'Trabajo',
    action: async () => {
      const res = await api.post('/direct-work/recommend', { min_expected_value: 100 })
      notifications.info(`${res.recommendations?.length || 0} oportunidades encontradas`)
      router.push('/targets/prioritization')
    },
    shortcut: 'O',
  },
  {
    id: 'work:scan',
    label: 'Escanear targets',
    description: 'Ejecutar discovery + recon en targets activos',
    icon: Radio,
    category: 'Trabajo',
    action: async () => {
      await api.post('/hunt/scan')
      notifications.success('Escaneo iniciado')
    },
    shortcut: 'E',
  },
  {
    id: 'work:approve',
    label: 'Aprobar pendientes',
    description: 'Revisar y aprobar entregas / reportes en cola',
    icon: CheckCircle,
    category: 'Trabajo',
    route: '/operations/work-queue',
    shortcut: 'A',
  },

  // ── INTELLIGENCE ──
  {
    id: 'intel:findings',
    label: 'Hallazgos críticos',
    description: 'Findings con severity high/critical sin validar',
    icon: AlertTriangle,
    category: 'Inteligencia',
    action: async () => {
      const res = await api.get('/findings?severity=high,critical&status=unconfirmed')
      notifications.info(`${res.total} hallazgos críticos`)
      router.push('/intelligence/findings')
    },
    shortcut: 'F',
  },
  {
    id: 'intel:hypotheses',
    label: 'Hipótesis pendientes',
    description: 'Hipótesis generadas esperando validación',
    icon: Lightbulb,
    category: 'Inteligencia',
    route: '/intelligence/hypotheses',
    shortcut: 'H',
  },
  {
    id: 'intel:evidence',
    label: 'Evidencia faltante',
    description: 'Findings que necesitan más evidencia para confirmar',
    icon: FileText,
    category: 'Inteligencia',
    route: '/intelligence/evidence',
  },
  {
    id: 'intel:memory',
    label: 'Buscar en memoria',
    description: 'Query en UnifiedMemoryStore (findings, decisions, patterns)',
    icon: Brain,
    category: 'Inteligencia',
    action: async () => {
      const q = prompt('Buscar en memoria:')
      if (q) {
        const res = await api.get(`/memory/query?q=${encodeURIComponent(q)}`)
        notifications.info(`${res.results?.length || 0} resultados`)
      }
    },
    shortcut: 'M',
  },

  // ── MONEY ──
  {
    id: 'money:earnings',
    label: 'Ver ingresos',
    description: 'Total cobrado + pendiente + por plataforma',
    icon: CircleDollarSign,
    category: 'Dinero',
    route: '/capital',
    shortcut: '$',
  },
  {
    id: 'money:goals',
    label: 'Objetivo de ingresos',
    description: 'Setear meta: "quiero ganar 10k este mes"',
    icon: Target,
    category: 'Dinero',
    action: async () => {
      const goal = prompt('Meta (ej: "quiero ganar 10k este mes"):')
      if (goal) {
        const res = await api.post('/copilot/income-goal', { message: goal })
        notifications.success(`Plan generado: ${res.required_opportunities} ops, ${res.required_hours_per_week}h/sem`)
      }
    },
    shortcut: 'G',
  },
  {
    id: 'money:payouts',
    label: 'Payouts pendientes',
    description: 'Plataformas con dinero por cobrar',
    icon: ExternalLink,
    category: 'Dinero',
    action: async () => {
      const res = await api.get('/payment-tracker')
      notifications.info(`Pendiente: $${res.total_pending || 0}`)
      router.push('/capital')
    },
  },

  // ── SYSTEM ──
  {
    id: 'sys:terminal',
    label: 'Terminal',
    description: 'Shell real en el backend',
    icon: Terminal,
    category: 'Sistema',
    route: '/terminal',
    shortcut: 'T',
  },
  {
    id: 'sys:health',
    label: 'System Health',
    description: 'Estado detallado: CPU, RAM, workers, queue, errors',
    icon: Shield,
    category: 'Sistema',
    action: async () => {
      const res = await api.get('/system/health')
      notifications.info(`Health: ${res.health}% | Workers: ${res.workers} | Queue: ${res.queue}`)
    },
  },
  {
    id: 'sys:logs',
    label: 'Ver logs recientes',
    description: 'Últimos eventos del sistema (activity feed)',
    icon: Database,
    category: 'Sistema',
    action: async () => {
      const res = await api.get('/activity?limit=20')
      notifications.info(`${res.events?.length || 0} eventos recientes`)
    },
  },
  {
    id: 'sys:settings',
    label: 'Configuración',
    description: 'Settings panel',
    icon: Settings,
    category: 'Sistema',
    route: '/operations/settings',
  },

  // ── MERLIN / AI ──
  {
    id: 'ai:merlin',
    label: 'Hablar con MERLIN',
    description: 'Abrir chat del asistente',
    icon: Bot,
    category: 'IA',
    action: () => {
      window.dispatchEvent(new CustomEvent('toggle-copilot'))
    },
    shortcut: 'C',
  },
  {
    id: 'ai:briefing',
    label: 'Daily Briefing',
    description: 'Resumen matutino: oportunidades, skill gaps, sistema',
    icon: Lightbulb,
    category: 'IA',
    action: async () => {
      const res = await api.post('/direct-work/daily-brief')
      notifications.success('Briefing generado')
      router.push('/')
    },
  },
  {
    id: 'ai:learn',
    label: 'Aprender de outcomes',
    description: 'Feedback loop: accepted/paid/failed → mejora scoring',
    icon: CheckCircle,
    category: 'IA',
    action: async () => {
      await api.post('/direct-work/learn')
      notifications.success('Learning aplicado')
    },
  },
]

const filteredCommands = computed(() => {
  const q = query.value.toLowerCase()
  
  // Static command matches
  const staticMatches = !q ? commands : commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(q) ||
      cmd.description?.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q),
  )
  
  // Dynamic search results
  const dynamicMatches = searchResults.value.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(q) ||
      cmd.description?.toLowerCase().includes(q),
  )
  
  return [...dynamicMatches, ...staticMatches]
})

const groupedCommands = computed(() => {
  const groups: Record<string, CommandItem[]> = {}
  for (const cmd of filteredCommands.value) {
    if (!groups[cmd.category]) groups[cmd.category] = []
    groups[cmd.category].push(cmd)
  }
  return groups
})

const categoryOrder = ['Buscar', 'OWNEX', 'Trabajo', 'Dinero', 'Inteligencia', 'Sistema', 'IA']

function open() {
  isOpen.value = true
  query.value = ''
  selectedIndex.value = 0
  nextTick(() => inputRef.value?.focus())
}

function close() {
  isOpen.value = false
  query.value = ''
  executing.value = null
}

async function selectCommand(cmd: CommandItem) {
  if (cmd.confirm && !confirm(cmd.description || '¿Confirmar?')) return
  if (cmd.dangerous && !confirm(`⚠ ${cmd.label} — ¿Seguro?`)) return

  if (cmd.route) {
    router.push(cmd.route)
    close()
    return
  }

  if (cmd.action) {
    executing.value = cmd.id
    try {
      await cmd.action()
    } catch (e: any) {
      notifications.error(e?.message || 'Error ejecutando comando')
    } finally {
      executing.value = null
    }
    close()
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (!isOpen.value) return

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, filteredCommands.value.length - 1)
      break
    case 'ArrowUp':
      e.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
    case 'Enter':
      e.preventDefault()
      if (filteredCommands.value[selectedIndex.value]) {
        selectCommand(filteredCommands.value[selectedIndex.value])
      }
      break
    case 'Escape':
      close()
      break
  }
}

function handleGlobalKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (isOpen.value) {
      close()
    } else {
      open()
    }
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
})

watch(query, (val) => {
  selectedIndex.value = 0
  // Debounced global search
  if (searchTimeout) clearTimeout(searchTimeout)
  if (!val || val.length < 2) {
    searchResults.value = []
    isSearching.value = false
    return
  }
  isSearching.value = true
  searchTimeout = setTimeout(() => performGlobalSearch(val), 300)
})

async function performGlobalSearch(q: string) {
  try {
    const results: CommandItem[] = []
    const lowerQ = q.toLowerCase()
    
    // Search findings
    try {
      const findings = await api.get(`/findings?search=${encodeURIComponent(q)}&limit=5`)
      for (const f of (findings.findings || findings || []).slice(0, 5)) {
        results.push({
          id: `search:finding:${f.id}`,
          label: f.title || f.name || `Finding ${f.id}`,
          description: `Finding · ${f.severity || 'unknown'} · ${f.platform || ''}`,
          icon: Shield,
          category: 'Buscar',
          route: `/intelligence/findings`,
        })
      }
    } catch { /* skip */ }
    
    // Search targets
    try {
      const targets = await api.get(`/targets?search=${encodeURIComponent(q)}&limit=5`)
      for (const t of (targets.targets || targets || []).slice(0, 5)) {
        results.push({
          id: `search:target:${t.id}`,
          label: t.name || t.domain || `Target ${t.id}`,
          description: `Target · ${t.domain || ''}`,
          icon: Target,
          category: 'Buscar',
          route: `/targets/${t.id}`,
        })
      }
    } catch { /* skip */ }
    
    // Search reports
    try {
      const reports = await api.get(`/reports?search=${encodeURIComponent(q)}&limit=5`)
      for (const r of (reports.reports || reports || []).slice(0, 5)) {
        results.push({
          id: `search:report:${r.id}`,
          label: r.title || `Report ${r.id}`,
          description: `Report · ${r.status || ''} · ${r.platform || ''}`,
          icon: FileText,
          category: 'Buscar',
          route: `/reports/${r.id}`,
        })
      }
    } catch { /* skip */ }
    
    // Search hypotheses
    try {
      const hypotheses = await api.get(`/hypotheses?search=${encodeURIComponent(q)}&limit=5`)
      for (const h of (hypotheses.hypotheses || hypotheses || []).slice(0, 5)) {
        results.push({
          id: `search:hypothesis:${h.id}`,
          label: h.title || h.name || `Hypothesis ${h.id}`,
          description: `Hipótesis · ${h.status || 'pending'} · ${h.confidence || ''}%`,
          icon: Lightbulb,
          category: 'Buscar',
          route: `/intelligence/hypotheses`,
        })
      }
    } catch { /* skip */ }
    
    // Search investigations
    try {
      const investigations = await api.get(`/investigations?search=${encodeURIComponent(q)}&limit=5`)
      for (const inv of (investigations.investigations || investigations || []).slice(0, 5)) {
        results.push({
          id: `search:investigation:${inv.id}`,
          label: inv.title || `Investigation ${inv.id}`,
          description: `Investigación · ${inv.status || 'active'}`,
          icon: Search,
          category: 'Buscar',
          route: `/intelligence/investigations`,
        })
      }
    } catch { /* skip */ }
    
    // Search work items (queue)
    try {
      const workItems = await api.get(`/direct-work/queue?search=${encodeURIComponent(q)}&limit=5`)
      for (const w of (workItems.items || workItems || []).slice(0, 5)) {
        results.push({
          id: `search:work:${w.id}`,
          label: w.title || w.name || `Work Item ${w.id}`,
          description: `Trabajo · ${w.status || 'pending'} · ${w.platform || ''}`,
          icon: Send,
          category: 'Buscar',
          route: `/operations/work-queue`,
        })
      }
    } catch { /* skip */ }
    
    // Search programs
    try {
      const programs = await api.get(`/discovery/programs?search=${encodeURIComponent(q)}&limit=5`)
      for (const p of (programs.programs || programs || []).slice(0, 5)) {
        results.push({
          id: `search:program:${p.id}`,
          label: p.name || `Program ${p.id}`,
          description: `Program · ${p.platform || ''}`,
          icon: Globe,
          category: 'Buscar',
          route: `/targets`,
        })
      }
    } catch { /* skip */ }
    
    // Search scheduler jobs
    try {
      const jobs = await api.get(`/scheduler/jobs?search=${encodeURIComponent(q)}&limit=3`)
      for (const j of (jobs.jobs || jobs || []).slice(0, 3)) {
        results.push({
          id: `search:job:${j.id}`,
          label: j.name || j.id,
          description: `Scheduler · ${j.status || 'active'} · ${j.schedule || ''}`,
          icon: Clock,
          category: 'Buscar',
          route: `/operations/scheduler`,
        })
      }
    } catch { /* skip */ }
    
    searchResults.value = results
  } catch {
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

defineExpose({ open, close })
</script>

<template>
  <Teleport to="body">
    <Transition name="command-palette">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[var(--z-command-palette)] flex items-start justify-center pt-[15vh]"
        @click.self="close"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close" />

        <div
          class="relative w-full max-w-2xl mx-4 overflow-hidden border border-border rounded-xl bg-surface shadow-lg"
          @keydown="handleKeydown"
          role="combobox"
          aria-expanded="true"
          aria-haspopup="listbox"
        >
          <!-- Search Input -->
          <div class="flex items-center gap-3 px-4 py-3 border-b border-border">
            <Search class="h-4 w-4 text-muted-foreground shrink-0" />
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              placeholder="Comando operativo... (ej: 'iniciar', 'qué hago', 'ingresos', 'hallazgos')"
              class="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
              autocomplete="off"
              aria-label="Search commands"
              role="searchbox"
            />
            <kbd class="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted/30 rounded border border-border">
              ESC
            </kbd>
          </div>

          <!-- Results -->
          <div class="max-h-[65vh] overflow-y-auto py-2">
            <!-- Loading indicator -->
            <div v-if="isSearching" class="px-4 py-2 flex items-center gap-2 text-xs text-muted-foreground">
              <RefreshCw class="h-3 w-3 animate-spin" />
              <span>Buscando en findings, targets, reportes, hipótesis, investigaciones...</span>
            </div>

            <template v-if="filteredCommands.length === 0 && !isSearching">
              <div class="px-4 py-8 text-center">
                <p class="text-sm text-muted-foreground">Sin resultados</p>
                <p class="text-xs text-muted/60 mt-1">Probá: "iniciar", "qué hago", "ingresos", "escanear", "XSS", "hackerone"</p>
              </div>
            </template>

            <template v-else>
              <div v-for="category in categoryOrder" :key="category" v-if="groupedCommands[category]?.length" class="mb-2">
                <div class="px-4 py-1.5">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{{ category }}</p>
                </div>

                <button
                  v-for="cmd in groupedCommands[category]"
                  :key="cmd.id"
                  class="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors"
                  :class="[
                    filteredCommands.indexOf(cmd) === selectedIndex
                      ? 'bg-primary/10 text-foreground'
                      : 'text-foreground/80 hover:bg-muted/20',
                    cmd.dangerous ? 'text-destructive/80' : '',
                    executing === cmd.id ? 'opacity-50 cursor-wait' : '',
                  ]"
                  @click="selectCommand(cmd)"
                  @mouseenter="selectedIndex = filteredCommands.indexOf(cmd)"
                  :disabled="executing !== null && executing !== cmd.id"
                >
                  <component
                    :is="cmd.icon"
                    class="h-4 w-4 shrink-0"
                    :class="[
                      filteredCommands.indexOf(cmd) === selectedIndex ? 'text-primary' : 'text-muted-foreground',
                      cmd.dangerous && 'text-destructive',
                    ]"
                  />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ cmd.label }}</p>
                    <p v-if="cmd.description" class="text-[11px] text-muted-foreground truncate">{{ cmd.description }}</p>
                    <p v-if="executing === cmd.id" class="text-[10px] text-primary animate-pulse">Ejecutando…</p>
                  </div>
                  <ArrowRight
                    v-if="filteredCommands.indexOf(cmd) === selectedIndex"
                    class="h-3 w-3 text-primary shrink-0"
                  />
                  <kbd v-if="cmd.shortcut" class="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted/30 rounded border border-border">
                    {{ cmd.shortcut }}
                  </kbd>
                </button>
              </div>
            </template>
          </div>

          <!-- Footer -->
          <div class="flex items-center justify-between px-4 py-2 border-t border-border text-[10px] text-muted-foreground">
            <div class="flex items-center gap-3">
              <span class="flex items-center gap-1"><kbd class="px-1 py-0.5 bg-muted/30 rounded border border-border font-mono">↑↓</kbd> navegar</span>
              <span class="flex items-center gap-1"><kbd class="px-1 py-0.5 bg-muted/30 rounded border border-border font-mono">↵</kbd> ejecutar</span>
            </div>
            <span class="flex items-center gap-1"><kbd class="px-1 py-0.5 bg-muted/30 rounded border border-border font-mono">esc</kbd> cerrar</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.command-palette-enter-active,
.command-palette-leave-active {
  transition: opacity 0.15s ease;
}
.command-palette-enter-from,
.command-palette-leave-to {
  opacity: 0;
}
.command-palette-enter-active .relative,
.command-palette-leave-active .relative {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.command-palette-enter-from .relative {
  transform: scale(0.98) translateY(-8px);
  opacity: 0;
}
.command-palette-leave-to .relative {
  transform: scale(0.98) translateY(-8px);
  opacity: 0;
}
</style>