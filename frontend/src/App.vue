<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useSettingsStore } from '@/stores/settings'
import { onLoadingChange } from '@/lib/api'
import AppLayout from '@/components/layout/AppLayout.vue'
import CopilotPanel from '@/components/copilot/CopilotPanel.vue'
import CommandPalette from '@/components/ui/CommandPalette.vue'
import ToastContainer from '@/components/ToastContainer.vue'

declare global {
  interface Window {
    __PYWEBVIEW__?: { setTitle: (t: string) => void; minimize: () => void }
  }
}

const auth = useAuthStore()
const notifications = useNotificationsStore()
const settings = useSettingsStore()
const router = useRouter()
const route = useRoute()
const copilotOpen = ref(false)
const globalLoading = ref(false)
const showGlobalLoading = ref(false)
let loadingTimeout: ReturnType<typeof setTimeout> | null = null

// Apply theme/colors from settings to DOM
watch(() => [settings.data.appearance.theme, settings.data.appearance.colors], ([theme, colors]) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme || 'cyber')
    document.documentElement.setAttribute('data-colors', colors || 'default')
  }
}, { immediate: true })

watch(() => settings.data.appearance.density, (density) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-density', density || 'normal')
  }
}, { immediate: true })

// Listen for 401 events
if (typeof window !== 'undefined') {
  window.addEventListener('auth:unauthorized', () => {
    auth.logout()
    router.push({ name: 'login' })
  })
}

function toggleCopilot() {
  copilotOpen.value = !copilotOpen.value
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
    e.preventDefault()
    toggleCopilot()
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('toggle-command-palette'))
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)

  onLoadingChange((loading) => {
    if (loading) {
      loadingTimeout = setTimeout(() => { showGlobalLoading.value = true }, 500)
    } else {
      if (loadingTimeout) clearTimeout(loadingTimeout)
      showGlobalLoading.value = false
    }
    globalLoading.value = loading
  })

  // Connect notifications WebSocket
  notifications.connectWs()

  // Desktop integration
  if (typeof window.__PYWEBVIEW__ !== 'undefined') {
    try {
      window.__PYWEBVIEW__.setTitle('CATEYE — Security Intelligence OS')
    } catch { /* not in pywebview */ }
  }
  window.addEventListener('beforeunload', () => {
    if (typeof window.__PYWEBVIEW__ !== 'undefined') {
      try { window.__PYWEBVIEW__.minimize() } catch { /* */ }
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
    <div class="flex h-screen w-screen overflow-hidden bg-background">
    <!-- Scanline overlay -->
    <div class="pointer-events-none fixed inset-0 z-[60] opacity-[0.03]" style="background: repeating-linear-gradient(0deg, transparent, transparent 2px, color-mix(in srgb, var(--primary) 8%, transparent) 2px, color-mix(in srgb, var(--primary) 8%, transparent) 4px);" />

    <!-- Global loading bar -->
    <div v-if="showGlobalLoading" class="fixed top-0 left-0 right-0 z-[100] h-0.5">
      <div class="h-full bg-primary animate-pulse" style="width: 30%; animation: loadingSlide 1.5s ease-in-out infinite" />
    </div>

    <template v-if="route.meta?.public && !auth.isAuthenticated">
      <router-view />
    </template>
    <template v-else>
    <AppLayout :copilot-open="copilotOpen" @toggle-copilot="toggleCopilot" />
    <CopilotPanel :open="copilotOpen" @close="copilotOpen = false" />
    <CommandPalette />
    <ToastContainer />
    </template>
  </div>
</template>

<style>
@keyframes loadingSlide {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(200%); }
  100% { transform: translateX(400%); }
}
</style>
