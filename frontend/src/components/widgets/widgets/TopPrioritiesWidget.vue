<script setup lang="ts">
import { computed } from 'vue'
import { Bell } from '@lucide/vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const priorities = computed(() => props.data?.priorities ?? [])
</script>

<template>
  <div class="flex flex-col gap-1">
    <div v-if="priorities.length === 0" class="py-4 text-center">
      <p class="font-mono text-[10px] text-muted-foreground">No pending priorities</p>
    </div>
    <div v-else class="space-y-1">
      <div
        v-for="(p, i) in priorities.slice(0, 5)"
        :key="i"
        class="flex items-center gap-2 rounded-lg bg-surface/20 px-2 py-1.5"
      >
        <div
          :class="[
            'h-1.5 w-1.5 shrink-0 rounded-full',
            p.severity === 'high' ? 'bg-destructive' : p.severity === 'warning' ? 'bg-warning' : 'bg-accent',
          ]"
        />
        <div class="flex-1 min-w-0">
          <p class="text-[11px] font-medium text-foreground truncate">{{ p.title }}</p>
          <p v-if="p.detail" class="text-[9px] text-muted-foreground truncate">{{ p.detail }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
