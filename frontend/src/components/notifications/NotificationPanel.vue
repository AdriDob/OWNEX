<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { Bell, X, CheckCheck, Trash2, Info, CheckCircle2, AlertTriangle, AlertOctagon } from '@lucide/vue'

const store = useNotificationsStore()
const router = useRouter()
const open = ref(false)
const panelRef = ref<HTMLElement | null>(null)

function toggle() { open.value = !open.value }

function handleAction(action: { label: string; route: string } | undefined, id: string) {
  store.markRead(id)
  if (action?.route) router.push(action.route)
  open.value = false
}

function formatTime(ts: number) {
  const diff = Date.now() - ts
  if (diff < 60000) return 'ahora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return new Date(ts).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
}

function iconFor(type: string) {
  if (type === 'success') return CheckCircle2
  if (type === 'warning') return AlertTriangle
  if (type === 'error') return AlertOctagon
  return Info
}

function colorFor(type: string) {
  if (type === 'success') return 'text-success'
  if (type === 'warning') return 'text-warning'
  if (type === 'error') return 'text-destructive'
  return 'text-info'
}

function bgFor(type: string) {
  if (type === 'success') return 'bg-success/10'
  if (type === 'warning') return 'bg-warning/10'
  if (type === 'error') return 'bg-destructive/10'
  return 'bg-info/10'
}

// Close on click outside
function onDocumentClick(e: MouseEvent) {
  if (open.value && panelRef.value && !panelRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('click', onDocumentClick)
}
</script>

<template>
  <div ref="panelRef" class="relative">
    <!-- Bell button -->
    <button
      @click.stop="toggle"
      class="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface/30 hover:text-foreground transition-all"
      title="Notificaciones"
    >
      <Bell class="h-4 w-4" />
      <span
        v-if="store.unreadCount > 0"
        class="absolute -right-0.5 -top-0.5 flex h-4 min-w-[14px] items-center justify-center rounded-full bg-destructive px-1 text-[8px] font-bold text-white"
      >
        {{ store.unreadCount > 9 ? '9+' : store.unreadCount }}
      </span>
    </button>

    <!-- Dropdown -->
    <Transition name="panel">
      <div
        v-if="open"
        class="absolute right-0 top-full mt-2 w-80 rounded-xl border border-border/40 bg-surface/95 p-2 shadow-2xl backdrop-blur-xl z-50"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-2 py-1.5">
          <span class="text-xs font-semibold text-foreground">Notificaciones</span>
          <div class="flex items-center gap-1">
            <button
              v-if="store.notifications.length > 0"
              @click.stop="store.markAllRead()"
              class="flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] text-muted-foreground hover:text-foreground transition-colors"
              title="Marcar todo leído"
            >
              <CheckCheck class="h-3 w-3" />
              Leer todo
            </button>
            <button
              @click.stop="open = false"
              class="flex items-center justify-center rounded px-1 py-0.5 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X class="h-3 w-3" />
            </button>
          </div>
        </div>

        <!-- List -->
        <div class="mt-1 max-h-80 overflow-y-auto space-y-0.5 scrollbar-thin">
          <div v-if="store.notifications.length === 0" class="py-8 text-center">
            <Bell class="mx-auto h-6 w-6 text-muted-foreground/40" />
            <p class="mt-2 text-xs text-muted-foreground/60">Sin notificaciones</p>
          </div>

          <div
            v-for="(group) in store.groupedByDate"
            :key="group.label"
          >
            <p class="px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/50">
              {{ group.label }}
            </p>
            <div
              v-for="n in group.items"
              :key="n.id"
              @click.stop="handleAction(n.action, n.id)"
              :class="[
                'flex items-start gap-2.5 rounded-lg px-3 py-2.5 cursor-pointer transition-all',
                n.read ? 'opacity-60 hover:opacity-80' : 'bg-primary/[0.02] hover:bg-primary/5',
              ]"
            >
              <div :class="['mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', bgFor(n.type)]">
                <component :is="iconFor(n.type)" :class="['h-3 w-3', colorFor(n.type)]" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between gap-2">
                  <p :class="['text-[11px] font-medium leading-snug', n.read ? 'text-muted-foreground' : 'text-foreground']">
                    {{ n.title }}
                  </p>
                  <span class="shrink-0 text-[9px] text-muted-foreground/50">{{ formatTime(n.timestamp) }}</span>
                </div>
                <p class="mt-0.5 text-[10px] leading-relaxed text-muted-foreground/70 line-clamp-2">{{ n.message }}</p>
                <div v-if="n.action" class="mt-1">
                  <span class="text-[9px] font-medium text-primary hover:underline">{{ n.action.label }}</span>
                </div>
              </div>
              <button
                @click.stop="store.remove(n.id)"
                class="shrink-0 self-start mt-0.5 rounded p-0.5 text-muted-foreground/30 hover:text-muted-foreground transition-colors"
              >
                <Trash2 class="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div v-if="store.notifications.length > 0" class="mt-1 border-t border-border/20 pt-1.5 text-center">
          <button
            @click.stop="store.clearAll()"
            class="text-[9px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
          >
            Limpiar todas
          </button>
        </div>
      </div>
    </Transition>
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
