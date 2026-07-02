<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useHuntStore } from '@/stores/hunt'
import { getTargets } from '@/lib/api'
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
  Sparkles,
  FileDown,
  Globe,
  Zap,
} from '@lucide/vue'

const router = useRouter()
const hunt = useHuntStore()
const open = ref(false)
const search = ref('')
const selectedIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const activeGroup = ref<'navigation' | 'actions' | 'targets'>('navigation')

const navItems = [
  { name: 'Mission Control', path: '/', icon: LayoutDashboard },
  { name: 'Opportunity Radar', path: '/radar', icon: Radar },
  { name: 'Hot Paths', path: '/hot-paths', icon: Route },
  { name: 'Findings Pipeline', path: '/findings', icon: Bug },
  { name: 'Report Center', path: '/reports', icon: FileText },
  { name: 'Settings', path: '/settings', icon: Settings },
]

const actionItems = [
  { name: 'Iniciar Caza Autónoma', action: 'start-hunt', icon: Play },
  { name: 'Exportar Findings', action: 'export-findings', icon: Download },
  { name: 'Generar Reporte', action: 'generate-report', icon: FileDown },
  { name: 'Análisis Rápido', action: 'quick-analysis', icon: Zap },
]

const targetResults = ref<Array<{ id: number; name: string; domain: string; score: number }>>([])
const searchingTargets = ref(false)

const allItems = computed(() => {
  const items: Array<{
    type: 'nav' | 'action' | 'target'
    name: string
    icon?: any
    path?: string
    action?: string
    target?: { id: number; domain: string; score: number }
  }> = []

  const q = search.value.toLowerCase()

  if (activeGroup.value === 'navigation' || activeGroup.value === 'actions') {
    for (const item of navItems) {
      if (!q || item.name.toLowerCase().includes(q) || item.path.toLowerCase().includes(q)) {
        items.push({ type: 'nav', ...item })
      }
    }
    for (const item of actionItems) {
      if (!q || item.name.toLowerCase().includes(q)) {
        items.push({ type: 'action', ...item })
      }
    }
  }

  if (activeGroup.value === 'targets') {
    for (const t of targetResults.value) {
      const match = !q || t.name.toLowerCase().includes(q) || (t.domain && t.domain.toLowerCase().includes(q))
      if (match) {
        items.push({ type: 'target', name: t.name, target: t, icon: Globe })
      }
    }
  }

  return items
})

const flatItems = computed(() => {
  return allItems.value
})

function onToggle() {
  open.value = !open.value
  if (open.value) {
    search.value = ''
    selectedIndex.value = 0
    targetResults.value = []
    activeGroup.value = 'navigation'
    nextTick(() => inputRef.value?.focus())
  }
}

function execute(item: any) {
  open.value = false
  if (item.type === 'nav' && item.path) {
    router.push(item.path)
  } else if (item.type === 'action') {
    handleAction(item.action)
  } else if (item.type === 'target' && item.target) {
    router.push(`/target/${item.target.id}`)
  }
}

function handleAction(action: string) {
  switch (action) {
    case 'start-hunt':
      hunt.start()
      router.push('/')
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
  }
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function onSearchInput() {
  const q = search.value.trim()
  if (q.length >= 2) {
    // Check if it looks like a target search
    activeGroup.value = 'targets'
    if (searchTimeout) clearTimeout(searchTimeout)
    searchTimeout = setTimeout(doSearchTargets, 300)
  } else if (q.length === 0) {
    activeGroup.value = 'navigation'
    targetResults.value = []
  } else {
    activeGroup.value = 'navigation'
  }
  selectedIndex.value = 0
}

async function doSearchTargets() {
  const q = search.value.trim()
  if (q.length < 2) return
  searchingTargets.value = true
  try {
    const res = await getTargets({ search: q, limit: 8, sort_by: 'opportunity_score', sort_order: 'desc' })
    targetResults.value = (res.items || []).map(t => ({
      id: t.id,
      name: t.name,
      domain: t.domain,
      score: t.opportunity_score || 0,
    }))
  } catch {
    targetResults.value = []
  } finally {
    searchingTargets.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    onToggle()
  }
  if (!open.value) return

  if (e.key === 'Escape') {
    open.value = false
    return
  }

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % Math.max(flatItems.value.length, 1)
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + flatItems.value.length) % Math.max(flatItems.value.length, 1)
  }
  if (e.key === 'Enter' && flatItems.value[selectedIndex.value]) {
    execute(flatItems.value[selectedIndex.value])
  }
}

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
        <div
          class="relative w-full max-w-lg animate-in"
          @click.stop
        >
          <div class="glass-strong rounded-xl overflow-hidden shadow-2xl shadow-black/40">
            <div class="flex items-center gap-3 border-b border-border/40 px-4 py-3">
              <Search class="h-4 w-4 text-muted-foreground shrink-0" />
              <input
                v-model="search"
                @input="onSearchInput"
                placeholder="Buscar páginas, acciones o targets..."
                class="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 outline-none"
                ref="inputRef"
              />
              <kbd class="hidden sm:inline-flex items-center gap-1 rounded border border-border/50 bg-surface/50 px-1.5 py-0.5 text-[10px] text-muted-foreground">
                <Command class="h-2.5 w-2.5" />
                K
              </kbd>
            </div>

            <div class="max-h-80 overflow-y-auto p-2">
              <!-- Navigation -->
              <div v-if="flatItems.filter(i => i.type === 'nav').length > 0">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Navegación</p>
                <div v-for="(item, i) in flatItems.filter(i => i.type === 'nav')" :key="item.path">
                  <div v-if="flatItems.indexOf(item) === selectedIndex"
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    :class="cn(
                      'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                      'bg-primary/10 text-primary',
                    )"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0 text-primary" />
                    <span>{{ item.name }}</span>
                    <span class="ml-auto text-xs text-muted-foreground">{{ item.path }}</span>
                  </div>
                  <div v-else
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-foreground hover:bg-surface/50 transition-colors"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>{{ item.name }}</span>
                    <span class="ml-auto text-xs text-muted-foreground">{{ item.path }}</span>
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div v-if="flatItems.filter(i => i.type === 'action').length > 0" class="mt-2">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Acciones</p>
                <div v-for="(item, i) in flatItems.filter(i => i.type === 'action')" :key="item.action">
                  <div v-if="flatItems.indexOf(item) === selectedIndex"
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    :class="cn(
                      'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                      'bg-primary/10 text-primary',
                    )"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0 text-primary" />
                    <span>{{ item.name }}</span>
                  </div>
                  <div v-else
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-foreground hover:bg-surface/50 transition-colors"
                  >
                    <component :is="item.icon" class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>{{ item.name }}</span>
                  </div>
                </div>
              </div>

              <!-- Targets -->
              <div v-if="flatItems.filter(i => i.type === 'target').length > 0" class="mt-2">
                <p class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Targets</p>
                <div v-for="(item, i) in flatItems.filter(i => i.type === 'target')" :key="item.target?.id">
                  <div v-if="flatItems.indexOf(item) === selectedIndex"
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    :class="cn(
                      'flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                      'bg-primary/10 text-primary',
                    )"
                  >
                    <Globe class="h-4 w-4 shrink-0 text-primary" />
                    <div class="flex-1 min-w-0">
                      <span class="truncate">{{ item.name }}</span>
                      <span v-if="item.target?.domain" class="ml-2 text-xs text-muted-foreground">{{ item.target.domain }}</span>
                    </div>
                    <span v-if="item.target?.score" class="text-xs font-semibold text-gold">Score {{ item.target.score.toFixed(1) }}</span>
                  </div>
                  <div v-else
                    @click="execute(item)"
                    @mouseenter="selectedIndex = flatItems.indexOf(item)"
                    class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-foreground hover:bg-surface/50 transition-colors"
                  >
                    <Globe class="h-4 w-4 shrink-0 text-muted-foreground" />
                    <div class="flex-1 min-w-0">
                      <span class="truncate">{{ item.name }}</span>
                      <span v-if="item.target?.domain" class="ml-2 text-xs text-muted-foreground">{{ item.target.domain }}</span>
                    </div>
                    <span v-if="item.target?.score" class="text-xs font-semibold text-gold">{{ item.target.score.toFixed(1) }}</span>
                  </div>
                </div>
              </div>

              <!-- Empty -->
              <div v-if="flatItems.length === 0" class="py-8 text-center text-sm text-muted-foreground">
                <span v-if="searchingTargets">Buscando targets...</span>
                <span v-else>Sin resultados para "{{ search }}"</span>
              </div>
            </div>

            <div class="border-t border-border/40 px-4 py-2 flex items-center gap-4 text-[10px] text-muted-foreground">
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">↑↓</kbd> Navegar</span>
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">↵</kbd> Abrir</span>
              <span><kbd class="rounded border border-border/50 bg-surface/50 px-1 py-0.5 text-[9px]">Esc</kbd> Cerrar</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay-enter-active,
.overlay-leave-active {
  transition: opacity 0.15s ease;
}
.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}
</style>
