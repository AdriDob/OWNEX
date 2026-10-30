<script setup lang="ts">
import { DollarSign } from '@lucide/vue'
import { computed } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const totalPayout = computed(() => props.data?.total_payout ?? 0)
const pending = computed(() => props.data?.total_pending ?? 0)
const thisMonth = computed(() => props.data?.monthly_revenue ?? 0)
</script>

<template>
  <div class="flex flex-col gap-2">
    <KPIBlock
      label="Total Earned"
      :value="totalPayout"
      format="currency"
      color="gold"
      size="md"
    />
    <div class="grid grid-cols-2 gap-2 mt-1">
      <div class="rounded-lg bg-surface/30 p-2 text-center">
        <p class="font-mono text-[9px] text-muted-foreground">Pending</p>
        <p class="font-mono text-sm font-bold text-warning">${{ pending.toLocaleString() }}</p>
      </div>
      <div class="rounded-lg bg-surface/30 p-2 text-center">
        <p class="font-mono text-[9px] text-muted-foreground">This Month</p>
        <p class="font-mono text-sm font-bold text-success">${{ thisMonth.toLocaleString() }}</p>
      </div>
    </div>
  </div>
</template>
