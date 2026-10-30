<script setup lang="ts">
import { Sparkles } from '@lucide/vue'
import { computed } from 'vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const nextAction = computed(() => props.data?.next_action ?? null)
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="nextAction" class="rounded-lg bg-primary/5 border border-primary/10 p-2.5">
      <div class="flex items-center gap-1.5 mb-1">
        <Sparkles class="h-3 w-3 text-primary" />
        <span class="font-mono text-[9px] font-bold text-primary uppercase tracking-wider">Next Action</span>
      </div>
      <p class="text-[11px] font-medium text-foreground leading-snug">{{ nextAction.title }}</p>
      <p v-if="nextAction.why_now" class="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">{{ nextAction.why_now }}</p>
      <div class="flex items-center gap-3 mt-1.5">
        <span class="font-mono text-[9px] text-muted-foreground">
          Effort: <span class="font-semibold" :class="nextAction.effort === 'low' ? 'text-success' : nextAction.effort === 'medium' ? 'text-warning' : 'text-destructive'">{{ nextAction.effort }}</span>
        </span>
        <span v-if="nextAction.estimated_reward" class="font-mono text-[9px] text-muted-foreground">
          Reward: <span class="font-semibold text-gold">${{ nextAction.estimated_reward }}</span>
        </span>
      </div>
    </div>
    <div v-else class="py-4 text-center">
      <p class="font-mono text-[10px] text-muted-foreground">No action recommended</p>
    </div>
  </div>
</template>
