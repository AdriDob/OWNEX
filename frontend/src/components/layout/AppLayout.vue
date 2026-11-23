<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppFooter from './AppFooter.vue'
import TitleBar from './TitleBar.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

defineProps<{
  copilotOpen: boolean
}>()

const emit = defineEmits<{
  'toggle-copilot': []
}>()

function onToggleCopilot() {
  emit('toggle-copilot')
}
</script>

<template>
  <div class="flex h-full flex-1 overflow-hidden bg-background">
    <AppSidebar @toggle-copilot="onToggleCopilot" />

    <!-- Main content -->
    <main
      :class="[
        'flex flex-1 flex-col overflow-hidden transition-all duration-200',
        copilotOpen ? 'xl:mr-80' : 'mr-0',
      ]"
    >
      <!-- Desktop titlebar: breadcrumbs + status + notifications + window controls -->
      <TitleBar />

      <!-- Content area -->
      <div class="flex flex-1 flex-col overflow-y-auto px-6 py-6">
        <Transition name="page" mode="out-in">
          <ErrorBoundary>
            <router-view v-slot="{ Component }">
              <component :is="Component" />
            </router-view>
          </ErrorBoundary>
        </Transition>
      </div>

      <AppFooter @toggle-copilot="onToggleCopilot" />
    </main>
  </div>
</template>

<style scoped>
/* ═══ PAGE TRANSITIONS ═══ */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(8px) scale(0.99);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.995);
}

/* Reduce motion for reduced preferences */
@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: opacity 0.02s ease;
  }
  .page-enter-from,
  .page-leave-to {
    opacity: 1;
    transform: none;
  }
}
</style>
