<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Zap, History } from '@lucide/vue'

const route = useRoute()
const targetId = route.params.id as string | undefined

interface ActionItem {
  id: string; label: string; action_type: string; route?: string
}
interface HistoryEntry {
  label?: string; action_id: string; status: string; duration_ms?: number
}

const actions = ref<ActionItem[]>([])
const history = ref<HistoryEntry[]>([])
const stats = ref<{ total_executions: number; by_type?: Record<string, any> } | null>(null)
const loading = ref(true)
const error = ref(false)

onMounted(async () => {
  try {
    const [aRes, hRes, sRes] = await Promise.allSettled([
      api.get<{ actions: ActionItem[] }>('/execution/actions'),
      api.get<{ history: HistoryEntry[] }>('/execution/actions/history', { limit: 20 }),
      api.get<{ total_executions: number; by_type?: Record<string, any> }>('/execution/tracker'),
    ])
    if (aRes.status === 'fulfilled') actions.value = aRes.value.actions || []
    if (hRes.status === 'fulfilled') history.value = hRes.value.history || []
    if (sRes.status === 'fulfilled') stats.value = sRes.value
  } catch { error.value = true }
  finally { loading.value = false }
})
</script>

<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Operations</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Actions</h1>
      <p class="text-sm text-muted-foreground">{{ targetId ? `Target #${targetId}` : 'Available system actions' }}</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-24 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error">
      <Card class="p-6 text-center">
        <p class="text-sm text-destructive">Error loading actions</p>
      </Card>
    </template>

    <template v-else>
      <div v-if="stats" class="flex flex-wrap gap-3 text-xs text-muted-foreground animate-in">
        <span>Executed: <strong class="text-foreground">{{ stats.total_executions }}</strong></span>
        <span v-for="(s, type) in (stats.by_type || {}).slice(0, 3)" :key="type">
          {{ type }}: <strong class="text-foreground">{{ s.count ?? s }}</strong>
        </span>
      </div>

      <div v-if="actions.length > 0" class="space-y-2 animate-in">
        <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Available Actions</p>
        <Card v-for="action in actions" :key="action.id"
          class="flex items-center justify-between p-4 transition-all hover:border-primary/30"
        >
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-0.5">
              <span class="text-sm font-semibold text-foreground">{{ action.label }}</span>
              <Badge class="text-[10px]">{{ action.action_type }}</Badge>
            </div>
            <p class="text-[11px] text-muted-foreground">{{ action.id }}</p>
          </div>
          <button
            class="shrink-0 rounded-md bg-primary px-3 py-1.5 text-[10px] font-semibold text-white transition-all hover:bg-primary/90"
          >Execute</button>
        </Card>
      </div>

      <div v-else class="flex flex-col items-center py-12 text-center animate-in">
        <Zap class="h-10 w-10 text-muted-foreground/50 mb-2" />
        <p class="text-sm text-muted-foreground">No actions available right now</p>
        <p class="text-xs text-muted-foreground/60">System is analyzing — check back shortly</p>
      </div>

      <details v-if="history.length > 0" class="animate-in">
        <summary class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground cursor-pointer py-2">
          Recent ({{ history.length }} entries)
        </summary>
        <div class="mt-2 space-y-1">
          <div v-for="(entry, i) in history.slice(0, 5)" :key="i"
            class="flex items-center justify-between rounded-lg bg-[#1a1e2b] border border-[#2a2e3d] px-3 py-2 text-xs transition-all hover:bg-[#252836]"
          >
            <span class="text-foreground">{{ entry.label || entry.action_id }}</span>
            <span class="font-semibold"
              :class="entry.status === 'error' ? 'text-destructive' : entry.status === 'completed' ? 'text-success' : 'text-warning'"
            >{{ entry.status }} · {{ entry.duration_ms?.toFixed(0) }}ms</span>
          </div>
        </div>
      </details>
    </template>
  </div>
</template>
