<script setup lang="ts">
import { Monitor, Zap, Clock, TrendingUp } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'

const router = useRouter()

interface CUStatus {
  available: boolean
  capabilities: {
    screenshot: boolean
    pyautogui: boolean
    ollama: boolean | string
    vision_provider: string
    model: string
  }
}

interface PlatformStats {
  platform: string
  total_attempts: number
  success_rate: number
  avg_duration_ms: number
  best_duration_ms: number | null
}

const status = ref<CUStatus | null>(null)
const platforms = ref<PlatformStats[]>([])
const loading = ref(true)

const hasAnyData = computed(() => platforms.value.length > 0)
const bestPlatform = computed(() => {
  if (!platforms.value.length) return null
  return platforms.value.reduce((best, p) =>
    p.success_rate > (best?.success_rate ?? 0) ? p : best
  , platforms.value[0])
})
const totalAttempts = computed(() => platforms.value.reduce((s, p) => s + p.total_attempts, 0))
const overallSuccessRate = computed(() => {
  const total = platforms.value.reduce((s, p) => s + p.total_attempts, 0)
  const success = platforms.value.reduce((s, p) => s + Math.round(p.success_rate * p.total_attempts), 0)
  return total > 0 ? Math.round((success / total) * 100) : 0
})

async function load() {
  loading.value = true
  try {
    const [statusRes, statsRes] = await Promise.allSettled([
      api.get<CUStatus>('/copilot/computer-use/status'),
      api.get<{ platforms: PlatformStats[] }>('/copilot/computer-use/learning/stats'),
    ])
    if (statusRes.status === 'fulfilled') status.value = statusRes.value
    if (statsRes.status === 'fulfilled') platforms.value = statsRes.value.platforms || []
  } catch { /* silent */ }
  loading.value = false
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

onMounted(load)
</script>

<template>
  <div
    class="group cursor-pointer rounded-xl border border-border/40 bg-surface/50 p-4 transition-all duration-200 hover:border-primary/30 hover:bg-surface/70"
    @click="router.push('/copilot/computer-use')"
  >
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
          <Monitor class="h-3.5 w-3.5 text-primary" />
        </div>
        <div>
          <p class="font-mono text-xs font-semibold uppercase tracking-wider text-foreground">Computer Use</p>
          <p class="font-mono text-[9px] text-muted-foreground">Desktop automation</p>
        </div>
      </div>
      <span
        class="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-mono text-[9px]"
        :class="status?.available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-yellow-500/10 text-yellow-400'"
      >
        <span class="h-1 w-1 rounded-full" :class="status?.available ? 'bg-emerald-400' : 'bg-yellow-400'" />
        {{ status?.available ? 'ONLINE' : 'OFFLINE' }}
      </span>
    </div>

    <!-- Stats row -->
    <div v-if="!loading && hasAnyData" class="mt-3 grid grid-cols-3 gap-2">
      <div class="rounded-md border border-border/20 p-2 text-center">
        <p class="font-mono text-[9px] uppercase text-muted-foreground">Attempts</p>
        <p class="font-mono text-sm font-semibold tabular-nums">{{ totalAttempts }}</p>
      </div>
      <div class="rounded-md border border-border/20 p-2 text-center">
        <p class="font-mono text-[9px] uppercase text-muted-foreground">Success</p>
        <p
          class="font-mono text-sm font-semibold tabular-nums"
          :class="overallSuccessRate >= 80 ? 'text-emerald-400' : overallSuccessRate >= 50 ? 'text-yellow-400' : 'text-red-400'"
        >
          {{ overallSuccessRate }}%
        </p>
      </div>
      <div v-if="bestPlatform" class="rounded-md border border-border/20 p-2 text-center">
        <p class="font-mono text-[9px] uppercase text-muted-foreground">Best</p>
        <p class="font-mono text-sm font-semibold tabular-nums text-primary">{{ bestPlatform.platform }}</p>
      </div>
    </div>

    <!-- Platform pills -->
    <div v-if="!loading && platforms.length" class="mt-2 flex flex-wrap gap-1">
      <span
        v-for="p in platforms.slice(0, 4)"
        :key="p.platform"
        class="inline-flex items-center gap-1 rounded-full border border-border/20 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground"
      >
        <span
          class="h-1 w-1 rounded-full"
          :class="p.success_rate >= 0.8 ? 'bg-emerald-400' : p.success_rate >= 0.5 ? 'bg-yellow-400' : 'bg-red-400'"
        />
        {{ p.platform }}
        <span class="text-muted-foreground/60">{{ Math.round(p.success_rate * 100) }}%</span>
      </span>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && !hasAnyData" class="mt-3">
      <p class="font-mono text-[10px] text-muted-foreground/70">
        No fills recorded yet. Execute a task to start learning.
      </p>
    </div>

    <!-- Footer link -->
    <div class="mt-3 flex items-center justify-between border-t border-border/20 pt-2">
      <span class="font-mono text-[9px] text-muted-foreground/50 group-hover:text-primary transition-colors">
        Open Computer Use →
      </span>
      <div v-if="status?.capabilities" class="flex items-center gap-1.5">
        <span v-if="status.capabilities.screenshot" class="h-1.5 w-1.5 rounded-full bg-emerald-400" title="Screenshot" />
        <span v-if="status.capabilities.pyautogui" class="h-1.5 w-1.5 rounded-full bg-emerald-400" title="pyautogui" />
        <span v-if="status.capabilities.ollama" class="h-1.5 w-1.5 rounded-full bg-emerald-400" title="Ollama" />
      </div>
    </div>
  </div>
</template>
