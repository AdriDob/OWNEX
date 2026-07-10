<script setup lang="ts">
import { computed } from 'vue'
import { useUIStore } from '@/stores/ui'
import { X, ArrowRight } from '@lucide/vue'
import ScrollArea from './ScrollArea.vue'
import Badge from './Badge.vue'

const store = useUIStore()

const left = computed(() => store.compareEntities[0])
const right = computed(() => store.compareEntities[1])

function close() {
  store.clearCompare()
}

function diffClass(leftVal: any, rightVal: any, key: string): string {
  if (key === 'id' || key === 'type') return ''
  return JSON.stringify(leftVal) !== JSON.stringify(rightVal) ? 'bg-warning/10 border border-warning/20 rounded px-1' : ''
}
</script>

<template>
  <Teleport to="body">
    <Transition name="compare">
      <div v-if="left && right" class="fixed inset-0 z-50 flex flex-col bg-background/80 backdrop-blur-sm">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-3 border-b border-[var(--color-border)]">
          <h2 class="text-sm font-semibold text-foreground">Compare</h2>
          <button
            class="flex items-center justify-center w-7 h-7 rounded-md text-muted hover:text-foreground hover:bg-surface-hover transition-colors"
            @click="close"
            aria-label="Close comparison"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- Columns -->
        <div class="flex flex-1 min-h-0">
          <!-- Left -->
          <div class="flex-1 border-r border-[var(--color-border)]/40">
            <div class="px-4 py-2 border-b border-[var(--color-border)]/20 bg-surface/50">
              <p class="text-sm font-semibold text-foreground">{{ left.label }}</p>
              <p class="text-[10px] font-mono text-primary">#{{ left.id }}</p>
            </div>
            <ScrollArea class="p-4 h-full">
              <div v-for="(val, key) in left.fields ?? {}" :key="String(key)" class="flex items-center justify-between py-1.5 border-b border-[var(--color-border)]/10">
                <span class="text-[10px] font-mono text-muted uppercase">{{ key }}</span>
                <span class="text-xs text-right" :class="diffClass(val, right?.fields?.[key], String(key))">{{ val }}</span>
              </div>
            </ScrollArea>
          </div>

          <!-- Center indicator -->
          <div class="flex items-center justify-center w-8 shrink-0">
            <ArrowRight class="w-4 h-4 text-muted" />
          </div>

          <!-- Right -->
          <div class="flex-1">
            <div class="px-4 py-2 border-b border-[var(--color-border)]/20 bg-surface/50">
              <p class="text-sm font-semibold text-foreground">{{ right.label }}</p>
              <p class="text-[10px] font-mono text-primary">#{{ right.id }}</p>
            </div>
            <ScrollArea class="p-4 h-full">
              <div v-for="(val, key) in right.fields ?? {}" :key="String(key)" class="flex items-center justify-between py-1.5 border-b border-[var(--color-border)]/10">
                <span class="text-[10px] font-mono text-muted uppercase">{{ key }}</span>
                <span class="text-xs text-right" :class="diffClass(left?.fields?.[key], val, String(key))">{{ val }}</span>
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.compare-enter-active, .compare-leave-active {
  transition: opacity 0.2s ease;
}
.compare-enter-from, .compare-leave-to { opacity: 0; }
</style>
