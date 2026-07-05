<script setup lang="ts">
import { computed, watch, onUnmounted } from 'vue'
import { useUIStore } from '@/stores/ui'
import { X, FileText, Activity, Code, List, History, Grid3X3, Link, Terminal, ExternalLink } from '@lucide/vue'
import Badge from './Badge.vue'
import ScrollArea from './ScrollArea.vue'

const store = useUIStore()

type Tab = 'summary' | 'metadata' | 'json' | 'activity' | 'logs'

const tabs: { id: Tab; label: string; icon: Component }[] = [
  { id: 'summary', label: 'Summary', icon: FileText },
  { id: 'metadata', label: 'Metadata', icon: Grid3X3 },
  { id: 'json', label: 'JSON', icon: Code },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'logs', label: 'Logs', icon: List },
]

const activeTab = computed<Tab>(() => store.inspectorTab ?? 'summary')

function close() {
  store.inspectorOpen = false
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

watch(() => store.inspectorOpen, (v) => {
  if (v) document.addEventListener('keydown', handleKeydown)
  else document.removeEventListener('keydown', handleKeydown)
}, { immediate: true })

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="inspector">
      <div v-if="store.inspectorOpen" class="fixed inset-0 z-50 flex">
        <div class="absolute inset-0 bg-black/50" @click="close" aria-label="Close overlay" />
        <div
          class="ml-auto w-96 h-full glass-terminal overflow-y-auto shadow-2xl"
          role="dialog"
          aria-label="Inspector panel"
        >
          <!-- Header -->
          <div class="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 backdrop-blur-sm">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-foreground truncate">
                {{ store.inspectorEntity?.label ?? 'Entity' }}
              </h2>
              <p v-if="store.inspectorEntity?.id" class="text-[10px] font-mono text-primary">
                #{{ store.inspectorEntity.id }}
              </p>
            </div>
            <button
              class="flex items-center justify-center w-7 h-7 rounded-md text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
              @click="close"
              aria-label="Close inspector"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- Quick Actions -->
          <div class="flex items-center gap-2 px-4 py-2 border-b border-[var(--color-border)]/40">
            <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
              <ExternalLink class="w-3 h-3" />
              Open
            </button>
            <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
              <Link class="w-3 h-3" />
              Copy Link
            </button>
            <button class="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-foreground/70 hover:text-foreground hover:bg-primary/10 rounded transition-colors">
              <Terminal class="w-3 h-3" />
              CLI
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-[var(--color-border)]/40">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="flex items-center gap-1.5 px-3 py-2 text-[10px] font-medium transition-colors border-b-2 border-transparent"
              :class="activeTab === tab.id
                ? 'text-primary border-primary bg-primary/5'
                : 'text-muted hover:text-foreground hover:bg-surface-hover'"
              @click="store.inspectorTab = tab.id"
            >
              <component :is="tab.icon" class="w-3 h-3" />
              {{ tab.label }}
            </button>
          </div>

          <!-- Tab Content -->
          <ScrollArea class="p-4">
            <!-- Summary -->
            <div v-if="activeTab === 'summary'" class="space-y-3">
              <div v-for="(val, key) in store.inspectorEntity?.summary ?? {}" :key="String(key)" class="flex items-start justify-between gap-2">
                <span class="text-[10px] font-mono text-muted uppercase tracking-wider">{{ key }}</span>
                <span class="text-xs text-right">{{ val }}</span>
              </div>
            </div>

            <!-- Metadata -->
            <div v-if="activeTab === 'metadata'" class="space-y-2">
              <div v-for="(val, key) in store.inspectorEntity?.metadata ?? {}" :key="String(key)" class="flex items-start justify-between gap-2 py-1 border-b border-[var(--color-border)]/20">
                <span class="text-[10px] font-mono text-muted">{{ key }}</span>
                <span class="text-xs text-right font-mono text-foreground/80">{{ val }}</span>
              </div>
            </div>

            <!-- JSON -->
            <div v-if="activeTab === 'json'">
              <pre class="text-[10px] font-mono text-foreground/70 leading-relaxed whitespace-pre-wrap">{{ store.inspectorEntity?.json ?? '{}' }}</pre>
            </div>

            <!-- Activity -->
            <div v-if="activeTab === 'activity'" class="space-y-2">
              <div v-for="evt in store.inspectorEntity?.activity ?? []" :key="evt.id" class="flex items-center gap-2 py-1.5">
                <span class="w-1.5 h-1.5 rounded-full" :class="evt.severity === 'error' ? 'bg-destructive' : evt.severity === 'warning' ? 'bg-warning' : 'bg-success'" />
                <span class="text-xs text-foreground/80 flex-1">{{ evt.description }}</span>
                <span class="text-[10px] text-muted">{{ evt.timestamp }}</span>
              </div>
              <p v-if="!(store.inspectorEntity?.activity?.length)" class="text-xs text-muted text-center py-4">No recent activity</p>
            </div>

            <!-- Logs -->
            <div v-if="activeTab === 'logs'" class="space-y-1">
              <div v-for="log in store.inspectorEntity?.logs ?? []" :key="log.id" class="flex items-start gap-2 py-1 font-mono text-[10px]">
                <span class="text-muted shrink-0">{{ log.level }}</span>
                <span class="text-foreground/70">{{ log.message }}</span>
              </div>
              <p v-if="!(store.inspectorEntity?.logs?.length)" class="text-xs text-muted text-center py-4">No logs available</p>
            </div>
          </ScrollArea>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.inspector-enter-active, .inspector-leave-active {
  transition: opacity 0.2s ease;
}
.inspector-enter-active > div:last-child,
.inspector-leave-active > div:last-child {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.inspector-enter-from, .inspector-leave-to { opacity: 0; }
.inspector-enter-from > div:last-child { transform: translateX(100%); }
.inspector-leave-to > div:last-child { transform: translateX(100%); }
</style>
