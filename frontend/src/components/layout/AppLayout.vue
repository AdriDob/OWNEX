<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import Breadcrumbs from './Breadcrumbs.vue'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import { useRoute } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'

const notifications = useNotificationsStore()

defineProps<{
  copilotOpen: boolean
}>()

const emit = defineEmits<{
  'toggleCopilot': []
}>()

const route = useRoute()
</script>

<template>
  <div class="flex h-full flex-1 overflow-hidden">
    <AppSidebar @toggle-copilot="emit('toggleCopilot')" />

    <!-- Main content -->
    <main
      :class="[
        'flex-1 overflow-y-auto transition-all duration-200',
        copilotOpen ? 'mr-80' : 'mr-0',
      ]"
    >
      <!-- Top bar -->
      <div v-if="!route.meta?.public" class="sticky top-0 z-20 flex items-center justify-between border-b border-border/20 bg-background/80 px-6 py-2 backdrop-blur-xl">
        <div class="flex items-center gap-3">
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

      <div class="mx-auto max-w-6xl px-6 py-6">
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <ErrorBoundary>
              <component :is="Component" />
            </ErrorBoundary>
          </Transition>
        </router-view>
      </div>
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
