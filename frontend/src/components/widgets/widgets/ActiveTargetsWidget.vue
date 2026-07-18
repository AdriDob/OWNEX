<script setup lang="ts">
import { computed } from 'vue'
import { Target } from '@lucide/vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import Badge from '@/components/ui/Badge.vue'

interface Props {
  data?: any
  widgetId?: string
  refreshKey?: number
}

const props = defineProps<Props>()

const targets = computed(() => props.data?.active_targets ?? 0)
const highPriority = computed(() => props.data?.high_priority ?? 0)
</script>

<template>
  <div class="flex flex-col gap-2">
    <KPIBlock
      label="Active Targets"
      :value="targets"
      icon="Activity"
      color="primary"
      size="md"
    />
    <div v-if="highPriority > 0" class="flex items-center gap-1.5">
      <Badge variant="warning" class="text-[9px]">
        {{ highPriority }} high priority
      </Badge>
    </div>
  </div>
</template>
