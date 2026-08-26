<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useSettingsStore } from '@/stores/settings'
import { onLoadingChange } from '@/lib/api'
import { useGlobalShortcuts } from '@/composables/useGlobalShortcuts'
import { useThemeEngine } from '@/composables/useThemeEngine'
import AppLayout from '@/components/layout/AppLayout.vue'
import CopilotPanel from '@/components/copilot/CopilotPanel.vue'
import CommandPalette from '@/components/ui/CommandPalette.vue'
import ContextMenu from '@/components/ui/ContextMenu.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import InspectorPanel from '@/components/ui/InspectorPanel.vue'
import MiniPreview from '@/components/ui/MiniPreview.vue'
import MultiSelectHandler from '@/components/ui/MultiSelectHandler.vue'
import CompareView from '@/components/ui/CompareView.vue'
import OnboardingWizard from '@/components/onboarding/OnboardingWizard.vue'
import AssistantBubble from '@/components/assistant/AssistantBubble.vue'
import AssistantHint from '@/components/assistant/AssistantHint.vue'
import SteamBigPictureSplash from '@/components/layout/SteamBigPictureSplash.vue'
import VoiceCommandPanel from '@/components/voice/VoiceCommandPanel.vue'
import VoiceAssistantListener from '@/components/voice/VoiceAssistantListener.vue'
import AlertPopup from '@/components/AlertPopup.vue'
import JarvisBackground from '@/components/JarvisBackground.vue'
import { useAssistant } from '@/composables/useAssistant'

declare global {
  interface Window {
    __PYWEBVIEW__?: { setTitle: (t: string) => void; minimize: () => void }
  }
}

const auth = useAuthStore()
const notifications = useNotificationsStore()
const settings = useSettingsStore()
const { initialize: initThemeEngine, currentTheme } = useThemeEngine()
const router = useRouter()
const route = useRoute()
const assistant = useAssistant()
const copilotOpen = ref(false)
const splashVisible = ref(true)
const showOnboarding = ref(false)
const globalLoading = ref(false)
const showGlobalLoading = ref(false)
let loadingTimeout: ReturnType<typeof setTimeout> | null = null

const { shortcuts } = useGlobalShortcuts({
  onCommand: () => window.dispatchEvent(new CustomEvent('toggle-command-palette')),
  onToggleCopilot: () => copilotOpen.value = !copilotOpen.value,
  onToggleNotifications: () => window.dispatchEvent(new CustomEvent('toggle-notifications')),
  onCloseModal: () => window.dispatchEvent(new CustomEvent('close-modal')),
  onCloseInspector: () => window.dispatchEvent(new CustomEvent('close-inspector')),
  onHideMiniPreview: () => window.dispatchEvent(new CustomEvent('hide-mini-preview')),
  onQuickSync: () => window.dispatchEvent(new CustomEvent('quick-sync')),
  onNavigateBack: () => router.go(-1),
  onNavigateForward: () => router.go(1),
  onShowShortcuts: () => window.dispatchEvent(new CustomEvent('toggle-shortcuts')),
})

function handleContextAction(_actionId: string, entity: any) {
  console.debug('Context action:', _actionId, entity)
}

let _unauthHandler: (() => void) | null = null
let _beforeunloadHandler: (() => void) | null = null
let _bubbleTimeout: ReturnType<typeof setTimeout> | null = null

function toggleCopilot() {
  copilotOpen.value = !copilotOpen.value
}

onMounted(async () => {
  await initThemeEngine()

  // Sync theme engine with settings store
  watch(() => currentTheme.value?.id, (newThemeId) => {
    if (newThemeId && settings.data.appearance.theme !== newThemeId) {
      settings.updateAppearance({ theme: newThemeId })
    }
  })

  _unauthHandler = () => {
    auth.logout()
    router.push('/')
  }
  window.addEventListener('auth:unauthorized', _unauthHandler)

  onLoadingChange((loading) => {
    if (loading) {
      loadingTimeout = setTimeout(() => { showGlobalLoading.value = true }, 500)
    } else {
      if (loadingTimeout) clearTimeout(loadingTimeout)
      showGlobalLoading.value = false
    }
    globalLoading.value = loading
  })

  notifications.connectWs()

  // Desktop integration
  if (typeof window.__PYWEBVIEW__ !== 'undefined') {
    try {
      window.__PYWEBVIEW__.setTitle('OWNEX Alpha — Autonomous Work Operating Platform')
    } catch { /* not in pywebview */ }
  }
  _beforeunloadHandler = () => {
    if (typeof window.__PYWEBVIEW__ !== 'undefined') {
      try { window.__PYWEBVIEW__.minimize() } catch { /* */ }
    }
  }
  window.addEventListener('beforeunload', _beforeunloadHandler)

  // Init assistant
  assistant.loadDefaults()
  if (assistant.assistantEnabled.value) {
    _bubbleTimeout = setTimeout(() => {
      assistant.showBubble('💡 Presioná Ctrl+K para abrir la paleta de comandos', 6000)
    }, 3000)
  }

  // Auto-show onboarding on first run
  if (settings.onboardingNeeded && settings.ready) {
    showOnboarding.value = true
  }
})

const pageHints = computed(() => {
  return assistant.getHintsForPage(route.name as string || '')
})

onUnmounted(() => {
  if (_unauthHandler) window.removeEventListener('auth:unauthorized', _unauthHandler)
  if (_beforeunloadHandler) window.removeEventListener('beforeunload', _beforeunloadHandler)
  if (loadingTimeout) clearTimeout(loadingTimeout)
  if (_bubbleTimeout) clearTimeout(_bubbleTimeout)
})
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden bg-background">
    <!-- Jarvis Background -->
    <JarvisBackground />

    <!-- Splash screen -->
    <SteamBigPictureSplash :visible="splashVisible" @done="splashVisible = false" />

    <!-- Voice assistant listener (ALPHA desktop speaks replies from OMEGA) -->
    <VoiceAssistantListener />

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
    <ContextMenu @action="handleContextAction" />
    <ToastContainer />
    <InspectorPanel />
    <MiniPreview />
    <MultiSelectHandler />
    <CompareView />
    <OnboardingWizard :open="showOnboarding" @close="showOnboarding = false" />
    <VoiceCommandPanel />
    <AlertPopup />
    </template>

    <!-- Assistant Layer -->
    <template v-if="!route.meta?.public">
      <!-- Hints -->
      <div v-if="assistant.hintsEnabled.value && pageHints.length" class="fixed bottom-5 right-5 z-[80] flex flex-col gap-2 max-w-sm">
        <AssistantHint
          v-for="h in pageHints" :key="h.id"
          :title="h.title" :message="h.message"
          @dismiss="assistant.dismissHint(h.id)"
        />
      </div>
      <!-- Bubble -->
      <AssistantBubble :message="assistant.bubbleMessage.value" @dismiss="assistant.showBubble(null as unknown as string)" />
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
