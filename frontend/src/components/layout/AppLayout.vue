<script setup lang="ts">
import CommandPalette from '@/components/ui/CommandPalette.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'
import AutonomyBadge from '@/components/ui/AutonomyBadge.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { ref } from 'vue'
import AppFooter from './AppFooter.vue'
import AppSidebar from './AppSidebar.vue'
import TitleBar from './TitleBar.vue'

const notifications = useNotificationsStore()
const commandPalette = ref<InstanceType<typeof CommandPalette>>()

defineProps<{
  copilotOpen: boolean
}>()

const emit = defineEmits<{
  toggleCopilot: []
}>()
</script>

<template>
  <div class="flex h-full flex-1 overflow-hidden">
    <AppSidebar @toggle-copilot="emit('toggleCopilot')" />

    <!-- Main content -->
    <main
      :class="[
        'flex flex-1 flex-col overflow-y-auto transition-all duration-200',
        copilotOpen ? 'xl:mr-80' : 'mr-0',
      ]"
    >
      <!-- Desktop titlebar -->
      <TitleBar />

      <!-- Toolbar: notifications always accessible -->
      <div v-if="!$route.meta?.public" class="sticky top-0 z-20 flex items-center justify-end gap-2 border-b border-border/20 bg-background/80 px-4 py-1.5 backdrop-blur-xl">
        <AutonomyBadge />
        <span :class="['h-1.5 w-1.5 rounded-full', notifications.wsConnected ? 'bg-success' : 'bg-destructive']" />
        <NotificationPanel />
      </div>

      <!-- Content area -->
      <div class="flex flex-1 flex-col px-6 py-6">
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

    <!-- Command Palette (Cmd+K) -->
    <CommandPalette ref="commandPalette" />
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
