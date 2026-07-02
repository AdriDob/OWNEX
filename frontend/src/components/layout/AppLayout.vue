<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import Breadcrumbs from './Breadcrumbs.vue'
import NotificationPanel from '@/components/notifications/NotificationPanel.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import { useRoute } from 'vue-router'

defineProps<{
  copilotOpen: boolean
}>()

const emit = defineEmits<{
  'toggleCopilot': []
}>()

const route = useRoute()
const showNotifications = !route.meta?.public
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
        <Breadcrumbs />
        <div class="flex items-center gap-1">
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
