<script setup lang="ts">
import { AlertTriangle, ExternalLink, Globe, Radar, Search, TrendingUp } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import BarChart from '@/components/charts/BarChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface Program {
  id: number
  name: string
  domain: string | null
  endpoint_count?: number
  opportunity_score?: number
  competition_score?: number
}

const programs = ref<Program[]>([])
const loading = ref(true)
const search = ref('')
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const res = await api.get<{ items: Program[]; total: number }>('/targets', {
      limit: 50,
      sort_by: 'opportunity_score',
      sort_order: 'desc',
    })
    programs.value = res.items || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar oportunidades'
  } finally {
    loading.value = false
  }
})

function scoreColor(s?: number) {
  if (!s) return 'default' as const
  if (s >= 7) return 'success' as const
  if (s >= 4) return 'warning' as const
  return 'default' as const
}

const filtered = computed(() => {
  if (!search.value) return programs.value
  const q = search.value.toLowerCase()
  return programs.value.filter(
    (p) => p.name.toLowerCase().includes(q) || (p.domain && p.domain.toLowerCase().includes(q)),
  )
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Discovery</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Opportunity Radar</h1>
      <p class="text-sm text-muted-foreground">Programas y objetivos disponibles para investigación</p>
    </div>

    <!-- Search -->
    <div class="relative max-w-md">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input v-model="search" placeholder="Buscar programas..." class="pl-10" />
    </div>

    <!-- Error -->
    <template v-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </div>
    </template>

    <!-- Loading -->
    <div v-else-if="loading" class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 6" :key="i" class="h-28 rounded-xl" />
    </div>

    <template v-else-if="filtered.length">
      <!-- Score Chart -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Oportunity Scores</h3>
        <BarChart
          :labels="filtered.slice(0, 10).map(p => p.name)"
          :datasets="[{ label: 'Score', data: filtered.slice(0, 10).map(p => p.opportunity_score || 0) }]"
          :height="200"
        />
      </Card>

      <!-- Grid -->
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <Card v-for="(p, i) in filtered" :key="p.id" class="p-4 stagger-item" :style="{ '--i': i }">
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <h3 class="text-sm font-semibold text-foreground truncate">{{ p.name }}</h3>
            <p v-if="p.domain" class="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
              <Globe class="h-3 w-3" />
              {{ p.domain }}
            </p>
          </div>
          <Badge v-if="p.opportunity_score" :variant="scoreColor(p.opportunity_score)" class="shrink-0">
            {{ p.opportunity_score.toFixed(1) }}
          </Badge>
        </div>
        <div class="mt-3 flex items-center justify-between">
          <span class="text-xs text-muted-foreground">{{ p.endpoint_count || 0 }} endpoints</span>
          <Button variant="ghost" size="sm" class="gap-1">
            <span>Analizar</span>
            <ExternalLink class="h-3 w-3" />
          </Button>
        </div>
      </Card>
    </div>

    </template>

    <!-- Empty -->
    <div v-else class="flex flex-col items-center py-20 text-center">
      <Radar class="h-10 w-10 text-muted-foreground mb-4" />
      <p class="text-sm text-muted-foreground">No se encontraron programas</p>
    </div>
  </div>
</template>
