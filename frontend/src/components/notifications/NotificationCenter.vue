<script setup lang="ts">
/**
 * NotificationCenter — unified notification management interface.
 * 
 * Features:
 * - Category filtering (All, Important, Opportunities, Work, Finance, etc.)
 * - Priority-based display (CRITICAL, HIGH, MEDIUM, LOW, INFO)
 * - Read/Unread state
 * - Resolved state
 * - Grouping
 * - Quick actions
 * - Settings access
 */

import {
  AlertOctagon,
  AlertTriangle,
  Bell,
  Briefcase,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  DollarSign,
  Filter,
  Info,
  Settings,
  Shield,
  Sparkles,
  Star,
  Target,
  Trash2,
  X,
  XCircle,
} from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import NotificationSettings from './NotificationSettings.vue'

const store = useNotificationsStore()
const router = useRouter()

const isOpen = ref(false)
const activeCategory = ref('all')
const showSettings = ref(false)
const panelRef = ref<HTMLElement | null>(null)

// Categories
const categories = [
  { id: 'all', label: 'Todas', icon: Bell },
  { id: 'important', label: 'Importantes', icon: Star },
  { id: 'opportunities', label: 'Oportunidades', icon: Target },
  { id: 'work', label: 'Trabajo', icon: Briefcase },
  { id: 'finance', label: 'Finanzas', icon: DollarSign },
  { id: 'security', label: 'Seguridad', icon: Shield },
  { id: 'agents', label: 'Agentes', icon: Sparkles },
  { id: 'system', label: 'Sistema', icon: Info },
  { id: 'errors', label: 'Errores', icon: XCircle },
  { id: 'action_required', label: 'Requieren acción', icon: AlertTriangle },
]

// Filtered notifications
const filteredNotifications = computed(() => {
  if (activeCategory.value === 'all') {
    return store.notifications
  }
  
  if (activeCategory.value === 'important') {
    return store.notifications.filter(n => 
      n.priority === 'critical' || n.priority === 'high'
    )
  }
  
  return store.notifications.filter(n => n.category === activeCategory.value)
})

// Group by date
const groupedNotifications = computed(() => {
  const groups: { label: string; items: typeof store.notifications }[] = []
  const today = new Date()
  const todayStr = today.toDateString()
  const yesterdayStr = new Date(today.getTime() - 86400000).toDateString()

  for (const n of filteredNotifications.value) {
    const d = new Date(n.timestamp)
    const dateStr = d.toDateString()
    let label: string
    
    if (dateStr === todayStr) label = 'Hoy'
    else if (dateStr === yesterdayStr) label = 'Ayer'
    else label = d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })

    let group = groups.find((g) => g.label === label)
    if (!group) {
      group = { label, items: [] }
      groups.push(group)
    }
    group.items.push(n)
  }
  
  return groups
})

// Priority colors
function priorityColor(priority: string) {
  switch (priority) {
    case 'critical': return 'text-destructive'
    case 'high': return 'text-warning'
    case 'medium': return 'text-primary'
    case 'low': return 'text-muted-foreground'
    case 'info': return 'text-info'
    default: return 'text-muted-foreground'
  }
}

function priorityBg(priority: string) {
  switch (priority) {
    case 'critical': return 'bg-destructive/20'
    case 'high': return 'bg-warning/20'
    case 'medium': return 'bg-primary/20'
    case 'low': return 'bg-muted/20'
    case 'info': return 'bg-info/20'
    default: return 'bg-muted/20'
  }
}

function priorityLabel(priority: string) {
  switch (priority) {
    case 'critical': return 'CRITICAL'
    case 'high': return 'HIGH'
    case 'medium': return 'MEDIUM'
    case 'low': return 'LOW'
    case 'info': return 'INFO'
    default: return priority.toUpperCase()
  }
}

// Category icons
function categoryIcon(category: string) {
  const cat = categories.find(c => c.id === category)
  return cat?.icon || Bell
}

function categoryColor(category: string) {
  switch (category) {
    case 'opportunities': return 'text-success'
    case 'work': return 'text-primary'
    case 'finance': return 'text-warning'
    case 'security': return 'text-destructive'
    case 'agents': return 'text-info'
    case 'system': return 'text-muted-foreground'
    case 'errors': return 'text-destructive'
    case 'action_required': return 'text-warning'
    default: return 'text-muted-foreground'
  }
}

// Format time
function formatTime(ts: number) {
  const diff = Date.now() - ts
  if (diff < 60000) return 'ahora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return new Date(ts).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
}

// Actions
function handleNotificationClick(notification: any) {
  store.markRead(notification.id)
  if (notification.action?.route) {
    router.push(notification.action.route)
    isOpen.value = false
  }
}

function handleMarkAllRead() {
  store.markAllRead()
}

function handleClearAll() {
  store.clearAll()
}

function handleDelete(id: string) {
  store.remove(id)
}

function toggleSettings() {
  showSettings.value = !showSettings.value
}

// Close on click outside
function onDocumentClick(e: MouseEvent) {
  if (isOpen.value && panelRef.value && !panelRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})
</script>

<template>
  <div ref="panelRef" class="relative">
    <!-- Bell button with badge -->
    <button
      @click.stop="isOpen = !isOpen"
      class="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface/30 hover:text-foreground transition-all"
      title="Notification Center"
    >
      <Bell class="h-4 w-4" />
      <span
        v-if="store.unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-4 min-w-[14px] items-center justify-center rounded-full bg-destructive px-1 text-[8px] font-bold text-white"
      >
        {{ store.unreadCount > 9 ? '9+' : store.unreadCount }}
      </span>
    </button>

    <!-- Dropdown Panel -->
    <Transition name="panel">
      <div
        v-if="isOpen"
        class="absolute right-0 top-full mt-2 w-[420px] rounded-xl border border-border/40 bg-surface/95 shadow-2xl backdrop-blur-xl z-50 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-border/20">
          <div class="flex items-center gap-2">
            <Bell class="h-4 w-4 text-primary" />
            <span class="text-sm font-semibold text-foreground">Notification Center</span>
            <span 
              v-if="store.unreadCount > 0"
              class="px-1.5 py-0.5 text-[9px] font-bold bg-primary/20 text-primary rounded"
            >
              {{ store.unreadCount }} new
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              @click.stop="handleMarkAllRead"
              v-if="store.unreadCount > 0"
              class="flex items-center gap-1 rounded px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
              title="Mark all as read"
            >
              <CheckCheck class="h-3 w-3" />
              Read all
            </button>
            <button
              @click.stop="toggleSettings"
              class="flex items-center justify-center rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
              title="Settings"
            >
              <Settings class="h-3.5 w-3.5" />
            </button>
            <button
              @click.stop="isOpen = false"
              class="flex items-center justify-center rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
            >
              <X class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <!-- Category Tabs -->
        <div class="flex gap-1 px-3 py-2 border-b border-border/20 overflow-x-auto scrollbar-thin">
          <button
            v-for="cat in categories"
            :key="cat.id"
            @click.stop="activeCategory = cat.id"
            :class="[
              'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all whitespace-nowrap',
              activeCategory === cat.id
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-surface/50 hover:text-foreground',
            ]"
          >
            <component :is="cat.icon" class="h-3 w-3" />
            {{ cat.label }}
          </button>
        </div>

        <!-- Notifications List -->
        <div class="max-h-[400px] overflow-y-auto scrollbar-thin">
          <!-- Empty State -->
          <div v-if="filteredNotifications.length === 0" class="py-12 text-center">
            <Bell class="mx-auto h-8 w-8 text-muted-foreground/30" />
            <p class="mt-3 text-sm text-muted-foreground/60">No notifications</p>
            <p class="mt-1 text-[10px] text-muted-foreground/40">
              {{ activeCategory === 'all' ? 'All caught up!' : 'No notifications in this category' }}
            </p>
          </div>

          <!-- Grouped Notifications -->
          <div v-else>
            <div v-for="group in groupedNotifications" :key="group.label">
              <!-- Date Header -->
              <div class="sticky top-0 bg-surface/95 px-4 py-2 border-b border-border/10">
                <span class="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/50">
                  {{ group.label }}
                </span>
              </div>

              <!-- Notification Items -->
              <div
                v-for="n in group.items"
                :key="n.id"
                @click.stop="handleNotificationClick(n)"
                :class="[
                  'flex items-start gap-3 px-4 py-3 cursor-pointer transition-all border-b border-border/10',
                  n.read ? 'opacity-60 hover:opacity-80' : 'hover:bg-primary/[0.02]',
                ]"
              >
                <!-- Priority Indicator -->
                <div class="flex flex-col items-center gap-1 mt-0.5">
                  <div :class="['h-2 w-2 rounded-full', priorityBg(n.priority)]" />
                </div>

                <!-- Icon -->
                <div :class="['mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg', priorityBg(n.priority)]">
                  <component :is="categoryIcon(n.category)" :class="['h-3.5 w-3.5', categoryColor(n.category)]" />
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-2">
                      <p :class="['text-xs font-medium leading-snug', n.read ? 'text-muted-foreground' : 'text-foreground']">
                        {{ n.title }}
                      </p>
                      <span :class="['px-1.5 py-0.5 text-[8px] font-bold rounded', priorityBg(n.priority), priorityColor(n.priority)]">
                        {{ priorityLabel(n.priority) }}
                      </span>
                    </div>
                    <span class="shrink-0 text-[9px] text-muted-foreground/50">{{ formatTime(n.timestamp) }}</span>
                  </div>
                  <p class="mt-1 text-[10px] leading-relaxed text-muted-foreground/70 line-clamp-2">{{ n.message }}</p>
                  
                  <!-- Action Button -->
                  <div v-if="n.action" class="mt-2">
                    <span class="text-[10px] font-medium text-primary hover:underline cursor-pointer">
                      {{ n.action.label }} →
                    </span>
                  </div>
                </div>

                <!-- Delete Button -->
                <button
                  @click.stop="handleDelete(n.id)"
                  class="shrink-0 self-start mt-1 rounded p-1 text-muted-foreground/30 hover:text-muted-foreground transition-colors"
                >
                  <Trash2 class="h-3 w-3" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div v-if="filteredNotifications.length > 0" class="px-4 py-2 border-t border-border/20 flex items-center justify-between">
          <button
            @click.stop="handleClearAll"
            class="text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
          >
            Clear all
          </button>
          <span class="text-[9px] text-muted-foreground/40">
            {{ filteredNotifications.length }} notifications
          </span>
        </div>
      </div>
    </Transition>

    <!-- Settings Modal -->
    <NotificationSettings 
      v-if="showSettings" 
      @close="showSettings = false" 
    />
  </div>
</template>

<style scoped>
.panel-enter-active, .panel-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.panel-enter-from, .panel-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.96);
}
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.08) transparent;
}
.scrollbar-thin::-webkit-scrollbar { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 4px; }
</style>
