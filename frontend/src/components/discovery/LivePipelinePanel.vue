<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useDiscoveryStore } from '@/stores/discovery'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import { Radio, Play, Wrench, DollarSign, Plug } from "@lucide/vue"

const store = useDiscoveryStore()

const statusCounts = computed(() => {
  const byStatus: Record<string, number> = {}
  for (const o of store.liveOpportunities.value) {
    byStatus[o.status] = (byStatus[o.status] ?? 0) + 1
  }
  return byStatus
})

const verifiedIncome = computed(() => {
  const fin = store.liveRevenue.value?.financial
  return fin?.verified_income_total_usd ?? 0
})

const advertisedTotal = computed(() => {
  const fin = store.liveRevenue.value?.financial?.by_bucket?.advertised ?? {}
  return Object.values(fin).reduce((a: number, b: any) => a + (b ?? 0), 0)
})

const connectionCounts = computed(() => store.liveConnections.value?.counts ?? {})

const STATUS_ORDER = ['ready', 'in_progress', 'eligibility_checked', 'discovered', 'expired', 'rejected']

function statusColor(s: string): string {
  if (s === 'ready') return 'text-success'
  if (s === 'in_progress') return 'text-info'
  if (s === 'rejected') return 'text-destructive'
  if (s === 'expired') return 'text-muted-foreground'
  return 'text-warning'
}

function oppKey(o: any): string {
  return `${o.platform}:${o.id}`
}

async function handlePrepare(key: string) {
  await store.prepareLiveOpportunity(key)
  await store.fetchLiveOpportunities()
}

onMounted(async () => {
  await Promise.all([
    store.fetchLiveStats(),
    store.fetchLiveOpportunities(undefined, 100),
    store.fetchLiveConnections(),
    store.fetchLiveRevenue(),
  ])
})
</script>

<template>
  <Card class="p-4">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <Radio class="h-3.5 w-3.5 text-primary" />
        <p class="font-mono text-xs font-semibold text-foreground">Live Opportunity Pipeline</p>
      </div>
      <Button variant="outline" size="sm" :disabled="store.liveLoading" @click="store.runLiveScan()">
        <Play v-if="!store.liveLoading" class="h-3 w-3" />
        <span v-else class="animate-pulse">...</span>
        Live Scan
      </Button>
    </div>

    <!-- Lifecycle counts -->
    <div class="grid grid-cols-3 gap-2 sm:grid-cols-6 mb-3">
      <div v-for="s in STATUS_ORDER" :key="s" class="rounded-lg border border-border/30 bg-surface/10 px-2 py-1.5 text-center">
        <p class="font-display text-sm font-bold" :class="statusColor(s)">{{ statusCounts[s] ?? 0 }}</p>
        <p class="font-mono text-[8px] uppercase text-muted-foreground">{{ s.replace('_', ' ') }}</p>
      </div>
    </div>

    <!-- Money honesty row -->
    <div class="flex flex-wrap gap-4 mb-3 font-mono text-[9px]">
      <span class="text-muted-foreground">
        Ingresos verificados: <span class="text-success font-bold">USD {{ verifiedIncome.toFixed(2) }}</span>
      </span>
      <span class="text-muted-foreground">
        Recompensas anunciadas: <span class="text-warning">USD {{ advertisedTotal.toFixed(0) }}</span>
        <span class="text-muted-foreground/60">(no es ingreso)</span>
      </span>
      <span class="text-muted-foreground">
        <Plug class="inline h-2.5 w-2.5" />
        Conexiones: {{ connectionCounts.configured ?? 0 }} configuradas ·
        {{ connectionCounts.pending ?? 0 }} pendientes ·
        {{ connectionCounts.public ?? 0 }} públicas
      </span>
    </div>

    <!-- Actionable items -->
    <div v-if="store.liveOpportunities.value.length === 0" class="font-mono text-[10px] text-muted-foreground py-2">
      Sin oportunidades live persistidas — corré un Live Scan.
    </div>
    <div v-else class="space-y-1.5 max-h-72 overflow-y-auto">
      <div
        v-for="o in store.liveOpportunities.value.slice(0, 30)"
        :key="oppKey(o)"
        class="flex items-center gap-2 rounded-lg border border-border/20 bg-surface/10 px-2 py-1.5"
      >
        <Badge variant="outline" class="text-[8px] shrink-0" :class="statusColor(o.status)">{{ o.status }}</Badge>
        <div class="min-w-0 flex-1">
          <p class="font-mono text-[10px] text-foreground truncate">{{ o.title }}</p>
          <p class="font-mono text-[8px] text-muted-foreground truncate">
            {{ o.platform }}<span v-if="o.reward"> · {{ o.reward }} {{ o.currency }}</span>
          </p>
        </div>
        <Button
          v-if="o.status === 'ready'"
          variant="ghost" size="sm"
          title="Preparar workspace de ejecución"
          @click="handlePrepare(oppKey(o))"
        >
          <Wrench class="h-3 w-3" />
        </Button>
        <a
          v-if="o.url" :href="o.url" target="_blank" rel="noopener"
          class="text-muted-foreground hover:text-primary shrink-0"
        >
          <DollarSign class="h-3 w-3" />
        </a>
      </div>
    </div>
  </Card>
</template>
