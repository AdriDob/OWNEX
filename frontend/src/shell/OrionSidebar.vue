<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import {
  Activity, Bug, ChevronLeft, ChevronRight, Dices, LayoutDashboard,
  Bell, Settings, TrendingUp, X,
} from '@lucide/vue'
import Skeleton from '@/components/ui/Skeleton.vue'

interface AppInfo {
  id: string
  name: string
  description: string
  icon: string
  version: string
  has_agent: boolean
  hidden: boolean
  widgets: number
}

const route = useRoute()
const router = useRouter()
const { toast } = useToast()
const collapsed = ref(false)
const apps = ref<AppInfo[]>([])
const loading = ref(true)
const error = ref('')

const coreNav = [
  { section: 'Sistema', items: [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Notificaciones', path: '/notifications', icon: Bell },
    { name: 'Configuración', path: '/settings', icon: Settings },
  ]},
]

const appIcons: Record<string, string> = {
  cateye: '🐛',
  atlas: '📈',
  odyssey: '🎲',
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/core/apps')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    apps.value = await res.json()
  } catch (e) {
    error.value = 'No se pudieron cargar las aplicaciones'
    toast.error('Error de conexión', 'No se pudo conectar con el servidor ORION')
    apps.value = [
      { id: 'cateye', name: 'ORION', description: 'Bug Bounty', icon: 'Bug', version: '', has_agent: false, hidden: false, widgets: 0 },
      { id: 'atlas', name: 'ATLAS', description: 'Inversiones', icon: 'TrendingUp', version: '', has_agent: false, hidden: false, widgets: 0 },
      { id: 'odyssey', name: 'ODYSSEY', description: 'Analytics', icon: 'Dices', version: '', has_agent: false, hidden: false, widgets: 0 },
    ]
  } finally {
    loading.value = false
  }
})

function navigate(path: string) { router.push(path) }
function isActive(path: string) { return route.path === path || route.path.startsWith(path + '/') }
function appPath(id: string) { return `/${id}/` }
</script>

<template>
  <aside
    class="flex flex-col border-r border-border bg-background/80 backdrop-blur-xl transition-all duration-200"
    :class="collapsed ? 'w-16' : 'w-56'"
  >
    <!-- Logo -->
    <div class="flex items-center gap-2 px-4 h-14 border-b border-border/40">
      <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/30">
        <Activity class="h-4 w-4" />
      </div>
      <Transition name="fade">
        <span v-if="!collapsed" class="font-mono text-sm font-bold tracking-[0.15em] text-foreground">ORION</span>
      </Transition>
      <button v-if="!collapsed" class="ml-auto text-muted-foreground hover:text-foreground" @click="collapsed = !collapsed">
        <ChevronLeft class="h-4 w-4" />
      </button>
      <button v-else class="mx-auto text-muted-foreground hover:text-foreground" @click="collapsed = !collapsed">
        <ChevronRight class="h-4 w-4" />
      </button>
    </div>

    <!-- Navigation -->
    <div class="flex-1 overflow-y-auto p-2 space-y-4 scrollbar-thin">
      <!-- Skeleton loading -->
      <div v-if="loading" class="space-y-2 px-2">
        <Skeleton class="h-4 w-20 rounded" />
        <Skeleton class="h-8 w-full rounded-lg" />
        <Skeleton class="h-8 w-full rounded-lg" />
        <div class="border-t border-border/30 my-3" />
        <Skeleton class="h-4 w-16 rounded" />
        <Skeleton class="h-8 w-full rounded-lg" />
        <Skeleton class="h-8 w-full rounded-lg" />
      </div>

      <!-- Error state -->
      <div v-if="error && !loading" class="px-2 py-4 text-center">
        <p class="text-xs text-destructive">{{ error }}</p>
        <button @click="onMounted" class="mt-2 text-xs text-primary hover:underline">Reintentar</button>
      </div>

      <!-- System nav -->
      <div v-for="section in coreNav" :key="section.section">
        <div v-if="!collapsed" class="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
          {{ section.section }}
        </div>
        <button
          v-for="item in section.items"
          :key="item.path"
          class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors"
          :class="isActive(item.path) ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          @click="navigate(item.path)"
        >
          <component :is="item.icon" class="h-4 w-4 shrink-0" />
          <span v-if="!collapsed">{{ item.name }}</span>
        </button>
      </div>

      <!-- Separator -->
      <div v-if="apps.length > 0 && !collapsed" class="border-t border-border/30" />

      <!-- Apps section -->
      <div v-if="apps.length > 0 && !loading">
        <div v-if="!collapsed" class="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
          Apps
        </div>
        <button
          v-for="app in apps"
          :key="app.id"
          v-show="!app.hidden"
          class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors"
          :class="isActive(appPath(app.id)) ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          @click="navigate(appPath(app.id))"
        >
          <span class="text-lg">{{ appIcons[app.id] || '📦' }}</span>
          <div v-if="!collapsed" class="flex flex-col items-start">
            <span>{{ app.name }}</span>
            <span class="text-xs text-muted-foreground/60">{{ app.description }}</span>
          </div>
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
