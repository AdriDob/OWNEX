<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import Breadcrumbs from './Breadcrumbs.vue'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import { useRoute } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { Menu } from '@lucide/vue'

const notifications = useNotificationsStore()

defineProps<{
  copilotOpen: boolean
  sidebarOpen: boolean
}>()

const emit = defineEmits<{
  'toggleCopilot': []
  'toggleSidebar': []
}>()

const route = useRoute()
</script>

<template>
  <div class="flex h-full flex-1 overflow-hidden">
    <AppSidebar :open="sidebarOpen" @toggle-copilot="emit('toggleCopilot')" @close="emit('toggleSidebar')" />

    <!-- Main content -->
    <main
      :class="[
        'flex flex-1 flex-col overflow-y-auto transition-all duration-200',
        copilotOpen ? 'mr-80' : 'mr-0',
        sidebarOpen ? 'lg:ml-0' : '',
      ]"
    >
      <!-- Top bar -->
      <div v-if="!route.meta?.public" class="sticky top-0 z-20 flex items-center justify-between border-b border-border/20 bg-background/80 px-3 sm:px-6 py-2 backdrop-blur-xl">
        <div class="flex items-center gap-3">
          <button
            class="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface/40 hover:text-foreground lg:hidden"
            @click="emit('toggleSidebar')"
          >
            <Menu class="h-4 w-4" />
          </button>
          <Breadcrumbs />
        </div>
        <div class="flex items-center gap-2">
          <span class="hidden sm:inline-flex items-center gap-1 rounded-md border border-border/20 px-2 py-1 font-mono text-[9px] text-muted-foreground/60">
            <kbd class="rounded bg-surface/50 px-1 py-0.5 text-[8px]">⌘B</kbd> Copilot
          </span>
          <span class="hidden sm:inline-flex items-center gap-1 rounded-md border border-border/20 px-2 py-1 font-mono text-[9px] text-muted-foreground/60">
            <kbd class="rounded bg-surface/50 px-1 py-0.5 text-[8px]">⌘K</kbd> Comandos
          </span>
          <span :class="['h-1.5 w-1.5 rounded-full', notifications.wsConnected ? 'bg-success' : 'bg-destructive']" />
          <NotificationPanel />
        </div>
      </div>

      <div class="mx-auto flex w-full max-w-6xl flex-1 flex-col px-3 sm:px-6 py-4 sm:py-6">
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <ErrorBoundary>
              <component :is="Component" />
            </ErrorBoundary>
          </Transition>
        </router-view>
      </div>
      <AppFooter @toggle-copilot="emit('toggleCopilot')" />
    </main>
  </div>
</template>

<style scoped>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s cubic-bezier(0.16, 1, 0.3, 1), transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.99);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.995);
}
</style>
