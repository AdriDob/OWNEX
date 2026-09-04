<script setup lang="ts">
import { Bot, Compass, DollarSign, Globe, Shield } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCycles } from '@/services/ownexData'

interface WorkCycle {
  id: string
  name: string
  icon: string
  color: string
  description: string
  status: 'active' | 'monitoring' | 'available' | 'tracking'
  statusLabel: string
  route: string
  badge: string
  badgeColor: string
}

const router = useRouter()
const cycles = ref<WorkCycle[]>([])
const loading = ref(false)

const iconMap: Record<string, any> = { Shield, Globe, Bot, DollarSign, Compass }

const statusDotClass: Record<string, string> = {
  active: 'status-dot-green',
  monitoring: 'status-dot-amber',
  available: 'status-dot-off',
  tracking: 'status-dot-green',
}

const statusTextClass: Record<string, string> = {
  active: 'text-success',
  monitoring: 'text-warning',
  available: 'text-muted-foreground',
  tracking: 'text-success',
}

async function loadCycles() {
  loading.value = true
  try {
    const data = await fetchCycles()
    cycles.value = data
  } finally {
    loading.value = false
  }
}

function navigate(cycle: WorkCycle) {
  if (cycle.route) router.push(cycle.route)
}

onMounted(() => {
  loadCycles()
})
</script>

<template>
  <div>
    <h2 class="font-mono text-xs font-semibold text-foreground mb-3">Work Cycles</h2>
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <div
        v-for="cycle in cycles"
        :key="cycle.id"
        :class="[
          'rounded-xl border border-border/30 bg-surface/30 p-4 transition-all cursor-pointer',
          cycle.route ? 'hover:bg-surface/50 hover:border-primary/30' : 'opacity-60',
        ]"
        @click="navigate(cycle)"
      >
        <div class="flex items-center gap-2 mb-2">
          <component :is="iconMap[cycle.icon]" :class="['h-4 w-4', cycle.color]" />
          <span class="text-sm font-semibold text-foreground">{{ cycle.name }}</span>
          <span :class="['text-[8px] font-mono px-1.5 py-0.5 rounded-full', cycle.badgeColor]">
            {{ cycle.badge }}
          </span>
        </div>
        <p class="text-[10px] text-muted-foreground line-clamp-2">{{ cycle.description }}</p>
        <div class="mt-2 flex items-center gap-2">
          <span class="status-dot" :class="statusDotClass[cycle.status]" />
          <span :class="['text-[8px] font-mono', statusTextClass[cycle.status]]">{{ cycle.statusLabel }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
