<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import StatusDot from './StatusDot.vue'

interface Props {
  class?: string
}

const props = defineProps<Props>()

const scheduler = ref('checking...')
const agents = ref(0)
const events24h = ref(0)
const healthScore = ref(0)
const findingsPending = ref(0)
const wsConnected = ref(false)
let interval: ReturnType<typeof setInterval> | null = null

async function fetchStatus() {
  try {
    const [sys, health, findingsRes] = await Promise.allSettled([
      api.get<{ scheduler: string; agents: number; events_24h: number }>('/system/status'),
      api.get<{ health_score: number }>('/mission/status'),
      api.get<{ items: any[] }>('/findings?status=pending'),
    ])
    if (sys.status === 'fulfilled') {
      scheduler.value = sys.value.scheduler
      agents.value = sys.value.agents
      events24h.value = sys.value.events_24h
    }
    if (health.status === 'fulfilled') {
      healthScore.value = health.value.health_score
    }
    if (findingsRes.status === 'fulfilled') {
      findingsPending.value = (findingsRes.value.items || []).length
    }
  } catch {
    // keep last known values
  }
}

onMounted(() => {
  fetchStatus()
  interval = setInterval(fetchStatus, 15000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<template>
  <div :class="cn(
    'fixed bottom-0 left-0 right-0 z-50 h-7 border-t border-border/30 bg-background/90 backdrop-blur-xl',
    'flex items-center justify-between px-4 font-mono text-[10px] text-muted-foreground',
    props.class,
  )">
    <div class="flex items-center gap-4">
      <span class="flex items-center gap-1.5">
        <StatusDot :status="scheduler === 'running' ? 'online' : 'offline'" size="sm" />
        Scheduler: {{ scheduler === 'running' ? 'Active' : 'Idle' }}
      </span>
      <span class="hidden sm:flex items-center gap-1.5">
        <StatusDot status="online" size="sm" />
        {{ agents }} Agents
      </span>
      <span class="hidden md:flex items-center gap-1.5">
        {{ events24h }} Events/24h
      </span>
    </div>
    <div class="flex items-center gap-4">
      <span class="hidden sm:flex items-center gap-1.5">
        Findings pending: <span class="text-warning font-semibold">{{ findingsPending }}</span>
      </span>
      <span class="flex items-center gap-1.5">
        Health:
        <span :class="[
          'font-semibold',
          healthScore >= 80 ? 'text-success' : healthScore >= 60 ? 'text-warning' : 'text-destructive',
        ]">{{ healthScore }}</span>
      </span>
      <span class="flex items-center gap-1">
        <span :class="['h-1.5 w-1.5 rounded-full', wsConnected ? 'bg-success' : 'bg-destructive']" />
        WS
      </span>
    </div>
  </div>
</template>
