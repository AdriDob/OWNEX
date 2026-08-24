<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import TitleBar from './TitleBar.vue'
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
        copilotOpen ? 'xl:mr-80' : 'mr-0',
        sidebarOpen ? 'lg:ml-0' : '',
      ]"
    >
      <!-- Desktop titlebar -->
      <TitleBar />

      <!-- Mobile top bar (shown when sidebar is closed on small screens) -->
      <div v-if="!route.meta?.public" class="sticky top-0 z-20 flex items-center justify-between border-b border-border/20 bg-background/80 px-3 py-1.5 backdrop-blur-xl lg:hidden">
        <button
          class="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface/40 hover:text-foreground"
          @click="emit('toggleSidebar')"
        >
          <Menu class="h-4 w-4" />
        </button>
        <div class="flex items-center gap-2">
          <span :class="['h-1.5 w-1.5 rounded-full', notifications.wsConnected ? 'bg-success' : 'bg-destructive']" />
          <NotificationPanel />
        </div>
      </div>

      <!-- Content area -->
      <div class="flex flex-1 flex-col px-3 sm:px-6 py-4 sm:py-6">
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
