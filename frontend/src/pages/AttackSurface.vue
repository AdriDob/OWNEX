<script setup lang="ts">
import { BarChart3, Globe, PieChart } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { BarChart, DoughnutChart } from '@/components/charts'
import Card from '@/components/ui/Card.vue'
import Select from '@/components/ui/Select.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface Endpoint {
  id: number
  path: string
  method: string
  risk_score: number
  vector: string
}

const router = useRouter()
const surfaces = ref<Record<string, Endpoint[]>>({})
const selected = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get<Record<string, Endpoint[]>>('/attack-surface')
    surfaces.value = res || {}
    const keys = Object.keys(surfaces.value)
    if (keys.length > 0 && !selected.value) selected.value = keys[0]
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
})

const keys = computed(() => Object.keys(surfaces.value))
const currentKey = computed(() => selected.value || keys.value[0] || '')
const currentEndpoints = computed(() => surfaces.value[currentKey.value] || [])

function formatLabel(k: string) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())
}
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Recon</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Attack Surface Map</h1>
      <p class="text-sm text-muted-foreground">Endpoints grouped by attack surface category</p>
    </div>

    <template v-if="loading">
      <Skeleton class="h-12 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="keys.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <Globe class="h-10 w-10 text-muted-foreground/50 mb-2" />
        <p class="text-sm text-muted-foreground">No attack surface data available</p>
      </div>
    </template>

    <template v-else>
      <!-- Category distribution chart -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <PieChart class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Superficies</p>
          </div>
          <DoughnutChart
            :labels="keys.map(formatLabel)"
            :data="keys.map(k => surfaces[k].length)"
            :height="200"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Riesgo por endpoint</p>
          </div>
          <BarChart
            :labels="currentEndpoints.slice(0, 10).map(e => e.path.length > 18 ? e.path.slice(0, 16) + '…' : e.path)"
            :datasets="[{ label: 'Risk', data: currentEndpoints.slice(0, 10).map(e => e.risk_score), backgroundColor: 'var(--ownex-yellow)' }]"
            :horizontal="true"
            :height="220"
            yLabel="Endpoint"
            xLabel="Risk"
            :showLegend="false"
          />
        </Card>
      </div>

      <Select
        :options="keys.map(k => ({ value: k, label: formatLabel(k) }))"
        :model-value="selected"
        @update:model-value="selected = $event as string"
        class="max-w-xs"
      />

      <Card v-if="currentEndpoints.length === 0" class="p-6 text-center text-xs text-muted-foreground">
        No endpoints in this category
      </Card>

      <Card v-else class="animate-in overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-border/20 text-left text-muted-foreground">
              <th class="px-4 py-3 font-semibold">Path</th>
              <th class="px-4 py-3 font-semibold">Method</th>
              <th class="px-4 py-3 font-semibold">Risk</th>
              <th class="px-4 py-3 font-semibold">Vector</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ep in currentEndpoints" :key="ep.id"
              class="cursor-pointer border-t border-border/10 transition-colors hover:bg-surface/30"
              @click="router.push(`/endpoint/${ep.id}`)"
            >
              <td class="px-4 py-3 font-mono text-foreground">{{ ep.path }}</td>
              <td class="px-4 py-3"><span class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">{{ ep.method }}</span></td>
              <td class="px-4 py-3">
                <span class="font-semibold" :class="ep.risk_score > 70 ? 'text-destructive' : ep.risk_score > 40 ? 'text-warning' : 'text-muted-foreground'">
                  {{ Math.round(ep.risk_score) }}
                </span>
              </td>
              <td class="px-4 py-3 text-muted-foreground">{{ ep.vector }}</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </template>
  </div>
</template>
