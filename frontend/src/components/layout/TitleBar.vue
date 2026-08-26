<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { ChevronRight, Home, Minus, Square, X } from '@lucide/vue'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const route = useRoute()
const router = useRouter()
const notifications = useNotificationsStore()

const isTauri = ref(false)
const isMaximized = ref(false)

const breadcrumbs = computed(() => {
  const segments = route.path.split('/').filter(Boolean)
  if (segments.length === 0) return [{ label: 'Panel Económico' }]
  if (segments.length <= 1) return []
  const crumbs: { label: string; path?: string }[] = [{ label: 'Inicio', path: '/' }]
  let accumulated = ''
  for (let i = 0; i < segments.length; i++) {
    accumulated += '/' + segments[i]
    const seg = segments[i]
    if (/^\d+$/.test(seg) && i > 0) continue
    const label = seg.replace(/-/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
    crumbs.push(i === segments.length - 1 ? { label: (route.meta?.title as string) || label } : { label, path: accumulated })
  }
  return crumbs
})

async function minimize() {
  if (!isTauri.value) return
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().minimize()
  } catch { /* */ }
}

async function toggleMaximize() {
  if (!isTauri.value) return
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const win = getCurrentWindow()
    if (isMaximized.value) {
      await win.unmaximize()
    } else {
      await win.maximize()
    }
    isMaximized.value = !isMaximized.value
  } catch { /* */ }
}

async function closeWindow() {
  if (!isTauri.value) return
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().close()
  } catch { /* */ }
}

async function checkMaximized() {
  if (!isTauri.value) return
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    isMaximized.value = await getCurrentWindow().isMaximized()
  } catch { /* */ }
}

onMounted(() => {
  isTauri.value = typeof window !== 'undefined' && !!(window as any).__TAURI_INTERNALS__
  if (isTauri.value) {
    checkMaximized()
    // Listen for resize events to update maximize state
    const handler = () => checkMaximized()
    window.addEventListener('resize', handler)
  }
})
</script>

<template>
  <div
    data-tauri-drag-region
    class="titlebar flex h-9 shrink-0 items-center justify-between border-b border-orion-border bg-orion-bg-glass/60 px-3 backdrop-blur-xl select-none"
  >
    <!-- Left: Brand + Breadcrumbs -->
    <div class="flex items-center gap-2 min-w-0 flex-1">
      <div class="flex items-center gap-1.5 shrink-0">
        <svg class="h-4 w-4" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="32" cy="32" r="28" stroke="url(#orbital)" stroke-width="1.5" opacity="0.6"/>
          <ellipse cx="32" cy="32" rx="20" ry="7" stroke="url(#orbital)" stroke-width="1" opacity="0.4" transform="rotate(-30 32 32)"/>
          <ellipse cx="32" cy="32" rx="20" ry="7" stroke="url(#orbital)" stroke-width="1" opacity="0.4" transform="rotate(30 32 32)"/>
          <circle cx="32" cy="32" r="3" fill="url(#core)" />
          <defs>
            <radialGradient id="core" cx="50%" cy="50%"><stop offset="0%" stop-color="#A855F7"/><stop offset="100%" stop-color="#7C3AED"/></radialGradient>
            <linearGradient id="orbital" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#7C3AED"/><stop offset="100%" stop-color="#A855F7"/></linearGradient>
          </defs>
        </svg>
        <span class="font-display text-[11px] font-semibold tracking-widest text-orion-text-secondary uppercase">OWNEX</span>
      </div>

      <nav v-if="!route.meta?.public && breadcrumbs.length > 0" class="hidden sm:flex items-center gap-0.5 ml-2 text-[10px] text-muted-foreground/60 font-mono">
        <button
          v-for="(crumb, i) in breadcrumbs"
          :key="i"
          @click="crumb.path ? router.push(crumb.path) : undefined"
          :class="[
            'flex items-center gap-0.5 px-1 py-0.5 rounded',
            i === breadcrumbs.length - 1 ? 'text-foreground/70 font-medium' : 'hover:text-foreground/60 transition-colors',
            crumb.path ? 'cursor-pointer' : 'cursor-default',
          ]"
        >
          <Home v-if="i === 0" class="h-2.5 w-2.5" />
          <ChevronRight v-else class="h-2 w-2 text-muted-foreground/20" />
          <span>{{ crumb.label }}</span>
        </button>
      </nav>
    </div>

    <!-- Right: Status + Shortcuts + Controls -->
    <div class="flex items-center gap-2 shrink-0">
      <!-- Keyboard shortcuts hints -->
      <div v-if="!route.meta?.public" class="hidden md:flex items-center gap-1.5 mr-1">
        <span class="inline-flex items-center gap-1 rounded border border-orion-border/20 px-1.5 py-0.5 font-mono text-[8px] text-muted-foreground/50">
          <kbd class="rounded bg-orion-bg-elevated/50 px-1 py-0.5 text-[7px]">⌘B</kbd> Copilot
        </span>
        <span class="inline-flex items-center gap-1 rounded border border-orion-border/20 px-1.5 py-0.5 font-mono text-[8px] text-muted-foreground/50">
          <kbd class="rounded bg-orion-bg-elevated/50 px-1 py-0.5 text-[7px]">⌘K</kbd> Comandos
        </span>
      </div>

      <!-- WS indicator — StatusBadge semántico (nunca solo color, spec §13) -->
      <StatusBadge
        compact
        :status="notifications.wsConnected ? 'OPERATIVO' : 'FUERA DE LÍNEA'"
        :reason="notifications.wsConnected ? 'WebSocket conectado' : 'WebSocket desconectado'"
      />

      <!-- Theme mode toggle -->
      <ThemeToggle />

      <!-- Window controls (Tauri only) -->
      <div v-if="isTauri" class="flex items-center gap-1 ml-2 -mr-1">
        <button
          class="win-btn flex h-5 w-5 items-center justify-center rounded text-muted-foreground/50 hover:bg-orion-bg-elevated hover:text-foreground transition-colors"
          @click="minimize"
          title="Minimizar"
        >
          <Minus class="h-2.5 w-2.5" />
        </button>
        <button
          class="win-btn flex h-5 w-5 items-center justify-center rounded text-muted-foreground/50 hover:bg-orion-bg-elevated hover:text-foreground transition-colors"
          @click="toggleMaximize"
          :title="isMaximized ? 'Restaurar' : 'Maximizar'"
        >
          <Square class="h-2 w-2" />
        </button>
        <button
          class="win-btn--close flex h-5 w-5 items-center justify-center rounded text-muted-foreground/50 hover:bg-destructive hover:text-white transition-colors"
          @click="closeWindow"
          title="Cerrar"
        >
          <X class="h-2.5 w-2.5" />
        </button>
      </div>

      <!-- Tooltip only for non-Tauri (web) -->
      <div v-else class="flex items-center gap-1">
        <NotificationPanel />
      </div>
    </div>
  </div>
</template>

<style scoped>
.titlebar {
  min-height: 36px;
}
</style>
