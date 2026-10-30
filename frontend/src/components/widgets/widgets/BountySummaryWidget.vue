<script setup lang="ts">
import { TrendingUp } from '@lucide/vue'
import { computed } from 'vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const confirmed = computed(() => props.data?.confirmed ?? 0)
const pending = computed(() => props.data?.pending ?? 0)
const totalEarned = computed(() => props.data?.total_earned ?? 0)
</script>

<template>
  <div class="flex flex-col gap-2">
    <KPIBlock
      label="Total Earned"
      :value="totalEarned"
      format="currency"
      color="gold"
      size="sm"
    />
    <div class="flex items-center gap-3 mt-1">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 rounded-full bg-success" />
        <span class="font-mono text-[10px] text-muted-foreground">{{ confirmed }} confirmed</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 rounded-full bg-warning" />
        <span class="font-mono text-[10px] text-muted-foreground">{{ pending }} pending</span>
      </div>
    </div>
  </div>
</template>
