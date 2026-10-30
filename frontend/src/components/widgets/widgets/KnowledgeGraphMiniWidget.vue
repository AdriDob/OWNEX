<script setup lang="ts">
import { defineAsyncComponent } from 'vue'

const KnowledgeGraphMini = defineAsyncComponent(() => import('@/components/charts/KnowledgeGraphMini.vue'))

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

defineProps<Props>()
</script>

<template>
  <div class="flex flex-col gap-2">
    <KnowledgeGraphMini :height="140" class="bg-dots rounded-lg" />
    <div class="flex items-center gap-3 font-mono text-[9px] text-muted-foreground">
      <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-primary" /> Targets</span>
      <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-gold" /> Findings</span>
      <span class="flex items-center gap-1"><span class="h-1.5 w-1.5 rounded-full bg-info" /> Endpoints</span>
    </div>
  </div>
</template>
