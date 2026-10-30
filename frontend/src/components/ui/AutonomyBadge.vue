<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Activity, Bot } from '@lucide/vue'
import { api } from '@/lib/api'

const systemStatus = ref<any>(null)
const loading = ref(true)

async function fetchStatus() {
  try {
    const res = await api.get('/api/system/status')
    systemStatus.value = res
  } catch {
    // Fallback to defaults
    systemStatus.value = { status: 'unknown', health: 0, workers: 0, queue: 0, errors: 0, uptime: '0h' }
  } finally {
    loading.value = false
  }
}

const statusColor = computed(() => {
  if (!systemStatus.value) return 'text-muted-foreground'
  const s = systemStatus.value.status?.toLowerCase()
  if (['healthy', 'operational', 'ready'].includes(s)) return 'text-success'
  if (['degraded', 'starting', 'scanning', 'processing', 'waiting'].includes(s)) return 'text-warning'
  return 'text-destructive'
})

const statusText = computed(() => {
  if (!systemStatus.value) return 'UNKNOWN'
  return systemStatus.value.status?.toUpperCase() || 'UNKNOWN'
})

onMounted(fetchStatus)
</script>

<template>
  <div class="flex items-center gap-2 rounded-lg border border-border/30 bg-surface/50 px-3 py-1.5">
    <Bot :class="['h-3.5 w-3.5', statusColor]" />
    <span class="font-mono text-[9px] font-semibold uppercase tracking-wider" :class="statusColor">
      {{ statusText }}
    </span>
    <span v-if="!loading && systemStatus" class="font-mono text-[9px] text-muted-foreground">
      {{ systemStatus.workers || 0 }}w
    </span>
  </div>
</template>
