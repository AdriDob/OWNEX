<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ChevronRight, ExternalLink, type Component } from '@lucide/vue'

interface CommandItem {
  id: string
  label: string
  description?: string
  icon?: Component
  section: string
  action: () => void
  keywords: string[]
  shortcut?: string
}

const router = useRouter()
const isOpen = ref(false)
const query = ref('')
const selectedIndex = ref(0)
const items = ref<CommandItem[]>([])

const NAV_ITEMS: CommandItem[] = [
  // Mission
  { id: 'mc', label: 'Mission Control', description: 'Dashboard principal', icon: Search, section: 'Misión', action: () => router.push('/'), keywords: ['mission', 'control', 'dashboard', 'home', 'inicio'] },
  { id: 'hunt', label: 'HUNT', description: 'Modo caza automático', icon: ExternalLink, section: 'Misión', action: () => router.push('/baby-mode'), keywords: ['hunt', 'caza', 'auto', 'automático'] },

  // Security / Rastro
  { id: 'targets', label: 'Targets', description: 'Gestión de objetivos', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/targets'), keywords: ['targets', 'objetivos', 'scope'] },
  { id: 'findings', label: 'Findings', description: 'Hallazgos detectados', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/intelligence/findings'), keywords: ['findings', 'hallazgos', 'vulnerabilidades'] },
  { id: 'hypotheses', label: 'Hipótesis', description: 'Hipótesis de ataque', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/intelligence/hypotheses'), keywords: ['hipotesis', 'hipótesis', 'ataque'] },
  { id: 'evidence', label: 'Evidencia', description: 'Centro de evidencias', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/intelligence/evidence'), keywords: ['evidencia', 'evidence', 'pruebas'] },
  { id: 'investigations', label: 'Investigaciones', description: 'Investigaciones activas', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/intelligence/investigations'), keywords: ['investigaciones', 'investigations'] },
  { id: 'confidence', label: 'Confianza', description: 'Scores de confianza', icon: ExternalLink, section: 'Seguridad', action: () => router.push('/intelligence/confidence'), keywords: ['confianza', 'confidence', 'score'] },

  // Reports
  { id: 'queue', label: 'Cola Priorizada', description: 'Reportes listos para enviar', icon: ExternalLink, section: 'Reportes', action: () => router.push('/reports/queue'), keywords: ['cola', 'queue', 'priorizada', 'reportes'] },
  { id: 'reports-center', label: 'Centro de Reportes', description: 'Gestión completa de reportes', icon: ExternalLink, section: 'Reportes', action: () => router.push('/reports/center'), keywords: ['centro', 'reports', 'reportes'] },
  { id: 'history', label: 'Historial', description: 'Historial de reportes', icon: ExternalLink, section: 'Reportes', action: () => router.push('/reports/history'), keywords: ['historial', 'history'] },
  { id: 'verification', label: 'Validación', description: 'Verificación de reportes', icon: ExternalLink, section: 'Reportes', action: () => router.push('/reports/verification'), keywords: ['validacion', 'validación', 'verificación'] },

  // Forge / Dev Bounty
  { id: 'prioritization', label: 'Priorización', description: 'Priorización de objetivos', icon: ExternalLink, section: 'Forja', action: () => router.push('/targets/prioritization'), keywords: ['priorizacion', 'priorización'] },
  { id: 'bounties', label: 'Bounties', description: 'Plataformas de bounties', icon: ExternalLink, section: 'Forja', action: () => router.push('/integrations/platforms'), keywords: ['bounties', 'plataformas', 'dev'] },

  // Vault / Wealth
  { id: 'capital', label: 'Capital Dashboard', description: 'Dashboard de capital', icon: ExternalLink, section: 'Vault', action: () => router.push('/capital'), keywords: ['capital', 'wealth', 'patrimonio'] },
  { id: 'investments', label: 'Investment Hub', description: 'Hub de inversiones', icon: ExternalLink, section: 'Vault', action: () => router.push('/investments'), keywords: ['inversiones', 'investments'] },
  { id: 'atlas-inv', label: 'ATLAS Inversiones', description: 'ATLAS de inversiones', icon: ExternalLink, section: 'Vault', action: () => router.push('/atlas/'), keywords: ['atlas'] },
  { id: 'trading', label: 'Trading', description: 'Trading y markets', icon: ExternalLink, section: 'Vault', action: () => router.push('/trading'), keywords: ['trading', 'markets'] },
  { id: 'polymarket', label: 'Polymarket', description: 'Predicciones Polymarket', icon: ExternalLink, section: 'Vault', action: () => router.push('/polymarket'), keywords: ['polymarket', 'predicciones'] },
  { id: 'wallets', label: 'Billeteras', description: 'Gestión de wallets', icon: ExternalLink, section: 'Vault', action: () => router.push('/integrations/wallets'), keywords: ['wallets', 'billeteras', 'crypto'] },

  // Atlas / Intelligence
  { id: 'knowledge', label: 'Knowledge Graph', description: 'Grafo de conocimiento', icon: ExternalLink, section: 'Atlas', action: () => router.push('/copilot/memory'), keywords: ['knowledge', 'grafo', 'memoria'] },
  { id: 'learning', label: 'Aprendizaje', description: 'Aprendizaje del sistema', icon: ExternalLink, section: 'Atlas', action: () => router.push('/copilot/learning'), keywords: ['aprendizaje', 'learning'] },
  { id: 'recommendations', label: 'Recomendaciones', description: 'Recomendaciones del copilot', icon: ExternalLink, section: 'Atlas', action: () => router.push('/copilot/recommendations'), keywords: ['recomendaciones', 'recommendations'] },

  // System
  { id: 'operations', label: 'Operaciones', description: 'Dashboard de operaciones', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/dashboard'), keywords: ['operaciones', 'operations'] },
  { id: 'pipelines', label: 'Pipelines', description: 'Gestión de pipelines', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/pipelines'), keywords: ['pipelines'] },
  { id: 'scheduler', label: 'Scheduler', description: 'Programador de tareas', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/scheduler'), keywords: ['scheduler', 'programador'] },
  { id: 'health', label: 'Health Center', description: 'Salud del sistema', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/health'), keywords: ['health', 'salud'] },
  { id: 'settings', label: 'Configuración', description: 'Ajustes del sistema', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/settings'), keywords: ['configuracion', 'configuración', 'settings'] },
  { id: 'workflows', label: 'Workflows', description: 'Gestión de workflows', icon: ExternalLink, section: 'Sistema', action: () => router.push('/operations/workflows'), keywords: ['workflows'] },
  { id: 'connections', label: 'Conexiones', description: 'Conexiones e integraciones', icon: ExternalLink, section: 'Sistema', action: () => router.push('/integrations/connections'), keywords: ['conexiones', 'conexiones', 'integraciones'] },
]

const filteredItems = computed(() => {
  if (!query.value.trim()) {
    return items.value
  }
  const q = query.value.toLowerCase()
  return items.value.filter(item =>
    item.label.toLowerCase().includes(q) ||
    item.description?.toLowerCase().includes(q) ||
    item.keywords.some(k => k.toLowerCase().includes(q)) ||
    item.section.toLowerCase().includes(q)
  )
})

/** Fetch live context items (top opportunity, pending work, setup) */
async function loadContextItems() {
  const api = (await import('@/lib/api')).api
  const dynamic: CommandItem[] = []

  try {
    // Top income plan action
    const plan = await api.get<{ next_action?: { title?: string; url?: string; ev_per_human_hour_usd?: number } }>('/applications/income-plan')
    if (plan.next_action?.title) {
      const na = plan.next_action
      dynamic.push({
        id: 'ctx-next-action',
        label: `→ ${na.title}`,
        description: na.ev_per_human_hour_usd ? `$${na.ev_per_human_hour_usd}/h — Best Next Action` : 'Best Next Action',
        icon: ExternalLink,
        section: '⚡ Ahora',
        action: () => { na.url ? window.open(na.url, '_blank') : router.push('/operations/applications') },
        keywords: ['next', 'action', 'ahora', 'mejor', 'oportunidad', 'work'],
      })
    }
  } catch { /* silent */ }

  try {
    const wb = await api.get<{ ready_to_deliver: number }>('/direct-work/workbank')
    if ((wb.ready_to_deliver || 0) > 0) {
      dynamic.push({
        id: 'ctx-workbank',
        label: `${wb.ready_to_deliver} entregas listas`,
        description: 'WorkBank — trabajos preparados para enviar',
        icon: ExternalLink,
        section: '⚡ Ahora',
        action: () => router.push('/operations/work-queue'),
        keywords: ['entregas', 'deliver', 'workbank', 'listas'],
      })
    }
  } catch { /* silent */ }

  try {
    const setup = await api.get<{ complete_pct: number; next_task?: { title?: string; est_minutes?: number } | null }>('/setup/checklist/status')
    if (!setup.complete && setup.next_task) {
      dynamic.push({
        id: 'ctx-setup',
        label: `Setup: ${setup.next_task.title ?? 'completar configuración'}`,
        description: `${setup.complete_pct}% completado`,
        icon: Search,
        section: '⚙️ Setup',
        action: () => router.push('/profile-kit'),
        keywords: ['setup', 'configurar', 'checklist', 'pendiente'],
      })
    }
  } catch { /* silent */ }

  // Prepend dynamic items so they appear at top
  items.value = [...dynamic, ...items.value]
}

const groupedItems = computed(() => {
  const groups: Record<string, CommandItem[]> = {}
  for (const item of filteredItems.value) {
    if (!groups[item.section]) groups[item.section] = []
    groups[item.section].push(item)
  }
  return groups
})

function openPalette() {
  isOpen.value = true
  query.value = ''
  selectedIndex.value = 0
  items.value = [...NAV_ITEMS]
  loadContextItems()
  nextTick(() => {
    const input = document.getElementById('command-input')
    input?.focus()
  })
}

function closePalette() {
  isOpen.value = false
  query.value = ''
  selectedIndex.value = 0
}

function selectItem(item: CommandItem) {
  item.action()
  closePalette()
}

function handleKeydown(e: KeyboardEvent) {
  const visible = Object.values(groupedItems.value).flat()
  if (!visible.length) return

  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, visible.length - 1)
      break
    case 'ArrowUp':
      e.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
      break
    case 'Enter':
      e.preventDefault()
      if (visible[selectedIndex.value]) selectItem(visible[selectedIndex.value])
      break
    case 'Escape':
      closePalette()
      break
  }
}

onMounted(() => {
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      openPalette()
    }
    if (e.key === 'Escape' && isOpen.value) {
      closePalette()
    }
  })
})
</script>

<template>
  <Transition name="command-fade">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-start justify-center pt-16">
      <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="closePalette" />
      
      <div class="relative w-full max-w-2xl mx-4 bg-background/95 backdrop-blur-xl border border-border/30 rounded-xl shadow-2xl overflow-hidden animate-in">
        <!-- Input -->
        <div class="relative p-4 border-b border-border/30">
          <Search class="absolute left-10 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            id="command-input"
            type="text"
            v-model="query"
            @keydown="handleKeydown"
            placeholder="Buscar comandos... (⌘K para abrir)"
            class="w-full pl-10 pr-4 py-3 bg-surface/50 border border-border/30 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono text-sm"
            autocomplete="off"
            spellcheck="false"
          />
          <kbd class="absolute right-3 top-1/2 -translate-y-1/2 px-2 py-0.5 text-[10px] font-mono text-muted-foreground bg-surface/50 rounded border border-border/30">⌘K</kbd>
        </div>

        <!-- Results -->
        <div class="max-h-[50vh] overflow-y-auto">
          <template v-if="Object.keys(groupedItems).length === 0">
            <div class="p-8 text-center">
              <Search class="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
              <p class="text-muted-foreground font-mono text-sm">No hay resultados para "{{ query }}"</p>
            </div>
          </template>

          <template v-else>
            <div v-for="(sectionItems, section) in groupedItems" :key="section" class="py-1">
              <div class="px-4 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground border-t border-border/30 first:border-t-0">
                {{ section }}
              </div>
              <div class="px-2 pb-1 space-y-0.5">
                <button
                  v-for="(item, idx) in sectionItems"
                  :key="item.id"
                  @click="selectItem(item)"
                  @mousemove="selectedIndex = Object.values(groupedItems).flat().indexOf(item)"
                  :class="[
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors',
                    Object.values(groupedItems).flat()[selectedIndex] === item
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-surface/30 hover:text-foreground'
                  ]"
                >
                  <component v-if="item.icon" :is="item.icon" class="h-4 w-4 shrink-0" />
                  <div class="flex-1 min-w-0">
                    <span class="font-mono text-sm font-medium truncate block">{{ item.label }}</span>
                    <span v-if="item.description" class="text-[11px] text-muted-foreground truncate block">{{ item.description }}</span>
                  </div>
                  <ChevronRight class="h-4 w-4 text-muted-foreground/50 shrink-0" />
                </button>
              </div>
            </div>
          </template>
        </div>

        <!-- Footer hint -->
        <div class="px-4 py-2 border-t border-border/30 bg-surface/30">
          <div class="flex items-center gap-4 text-[10px] font-mono text-muted-foreground">
            <kbd class="px-1.5 py-0.5 bg-background border border-border rounded">↑</kbd>
            <kbd class="px-1.5 py-0.5 bg-background border border-border rounded">↓</kbd>
            Navegar
            <span class="mx-1">|</span>
            <kbd class="px-1.5 py-0.5 bg-background border border-border rounded">⏎</kbd>
            Seleccionar
            <span class="mx-1">|</span>
            <kbd class="px-1.5 py-0.5 bg-background border border-border rounded">Esc</kbd>
            Cerrar
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.command-fade-enter-active,
.command-fade-leave-active {
  transition: opacity 0.15s ease;
}
.command-fade-enter-from,
.command-fade-leave-to {
  opacity: 0;
}
</style>