<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import {
  Search, ChevronLeft, ChevronRight, SlidersHorizontal, X,
  AlertTriangle, RefreshCw, Globe, Database, Code2, Layers,
  Star, Target, TrendingUp, Filter, BarChart3,
} from '@lucide/vue'

interface CatalogProgram {
  id: number
  name: string
  platform: string
  cms?: string
  framework?: string
  technologies?: string[]
  quality_score: number
  roi_score: number
  opportunity_score: number
  url?: string
}

const loading = ref(true)
const error = ref('')
const programs = ref<CatalogProgram[]>([])
const total = ref(0)
const search = ref('')
const platformFilter = ref('')
const page = ref(1)
const pageSize = 20

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const platforms = computed(() => {
  const set = new Set(programs.value.map(p => p.platform).filter(Boolean))
  return Array.from(set)
})

const platformColors: Record<string, string> = {
  hackerone: '#16a34a',
  bugcrowd: '#b45309',
  intigriti: '#9CA3AF',
  yeswehack: '#dc2626',
  synack: '#ffffff',
  immunefi: '#9CA3AF',
  code4rena: '#e82127',
}

const platformDistributionData = computed(() => {
  const counts: Record<string, number> = {}
  for (const p of programs.value) {
    counts[p.platform] = (counts[p.platform] || 0) + 1
  }
  return {
    labels: Object.keys(counts),
    data: Object.values(counts),
  }
})

function scoreColor(score: number) {
  if (score >= 80) return 'text-success'
  if (score >= 50) return 'text-warning'
  return 'text-muted-foreground'
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function onSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    loadPrograms()
  }, 400)
}

function clearFilters() {
  search.value = ''
  platformFilter.value = ''
  page.value = 1
  loadPrograms()
}

async function loadPrograms() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = {
      page: page.value,
    }
    if (search.value) params.search = search.value
    if (platformFilter.value) params.platform = platformFilter.value
    const res = await api.get<{ items: CatalogProgram[]; total: number }>('/opportunity/catalog', params as any)
    programs.value = res.items || []
    total.value = res.total || 0
  } catch (e: any) {
    error.value = e.message || 'Failed to load program catalog'
  } finally {
    loading.value = false
  }
}

function prevPage() {
  if (page.value > 1) { page.value--; loadPrograms() }
}

function nextPage() {
  if (page.value < totalPages.value) { page.value++; loadPrograms() }
}

onMounted(loadPrograms)
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading && programs.length === 0">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <Skeleton class="h-10 w-full rounded-lg" />
        <Skeleton class="h-64 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error loading program catalog</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadPrograms">
          <RefreshCw class="h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="animate-in space-y-1">
        <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Opportunities</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Program Catalog</h1>
        <p class="text-xs text-muted-foreground">{{ total }} programs · Searchable and sortable</p>
      </div>

      <div class="flex flex-col sm:flex-row gap-3 animate-in">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            v-model="search"
            placeholder="Search programs by name, technology..."
            @input="onSearchInput"
            class="w-full rounded-lg border border-border/60 bg-background/60 pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50"
          />
          <button
            v-if="search"
            @click="clearFilters"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X class="h-3 w-3" />
          </button>
        </div>
        <select
          v-model="platformFilter"
          @change="page = 1; loadPrograms()"
          class="rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-xs text-foreground"
        >
          <option value="">All Platforms</option>
          <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>

      <div v-if="programs.length === 0" class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Search class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No programs found</p>
        <p class="mt-1 text-xs text-muted-foreground">Try adjusting your search or filters</p>
        <Button variant="outline" size="sm" class="mt-4" @click="clearFilters">
          <Filter class="h-3.5 w-3.5" /> Clear Filters
        </Button>
      </div>

      <template v-else>
        <div class="glass-fintech rounded-xl overflow-hidden animate-in">
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-border/30 bg-surface/20">
                  <th class="text-left px-4 py-3 font-semibold text-foreground">Program</th>
                  <th class="text-left px-4 py-3 font-semibold text-foreground">Platform</th>
                  <th class="text-left px-4 py-3 font-semibold text-foreground">CMS</th>
                  <th class="text-left px-4 py-3 font-semibold text-foreground">Framework</th>
                  <th class="text-left px-4 py-3 font-semibold text-foreground">Technologies</th>
                  <th class="text-center px-4 py-3 font-semibold text-foreground">Quality</th>
                  <th class="text-center px-4 py-3 font-semibold text-foreground">ROI</th>
                  <th class="text-center px-4 py-3 font-semibold text-foreground">Opportunity</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/20">
                <tr
                  v-for="program in programs" :key="program.id"
                  class="hover:bg-surface/10 transition-colors"
                >
                  <td class="px-4 py-3">
                    <p class="font-semibold text-foreground whitespace-nowrap">{{ program.name }}</p>
                  </td>
                  <td class="px-4 py-3">
                    <Badge variant="outline" class="text-[8px]">{{ program.platform }}</Badge>
                  </td>
                  <td class="px-4 py-3 text-muted-foreground">{{ program.cms || '—' }}</td>
                  <td class="px-4 py-3 text-muted-foreground">{{ program.framework || '—' }}</td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-1">
                      <Badge v-for="t in (program.technologies || []).slice(0, 3)" :key="t" variant="outline" class="text-[8px]">
                        {{ t }}
                      </Badge>
                      <span v-if="(program.technologies?.length || 0) > 3" class="text-[8px] text-muted-foreground">
                        +{{ program.technologies!.length - 3 }}
                      </span>
                      <span v-if="!program.technologies?.length" class="text-muted-foreground">—</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="font-bold tabular-nums" :class="scoreColor(program.quality_score * 100)">
                      {{ (program.quality_score * 100).toFixed(0) }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="font-bold tabular-nums" :class="scoreColor(program.roi_score * 100)">
                      {{ (program.roi_score * 100).toFixed(0) }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="font-bold tabular-nums" :class="scoreColor(program.opportunity_score * 100)">
                      {{ (program.opportunity_score * 100).toFixed(0) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="flex items-center justify-between animate-in">
          <p class="text-[10px] text-muted-foreground">
            Page {{ page }} of {{ totalPages }} · {{ total }} total programs
          </p>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" :disabled="page <= 1" @click="prevPage">
              <ChevronLeft class="h-3.5 w-3.5" />
            </Button>
            <span class="text-[10px] text-muted-foreground">{{ page }} / {{ totalPages }}</span>
            <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="nextPage">
              <ChevronRight class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <div class="grid gap-6 lg:grid-cols-2 animate-in">
          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <BarChart3 class="h-3.5 w-3.5 text-primary" />
              Platform Distribution
            </h3>
            <DoughnutChart
              v-if="platformDistributionData.labels.length > 0"
              :labels="platformDistributionData.labels"
              :data="platformDistributionData.data"
              :height="220"
              :cutout="'60%'"
            />
            <div v-else class="py-8 text-center text-[10px] text-muted-foreground">No distribution data</div>
          </Card>

          <Card class="p-4 space-y-3">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Star class="h-3.5 w-3.5 text-primary" />
              Top Programs by Score
            </h3>
            <BarChart
              v-if="programs.length > 0"
              :labels="programs.slice(0, 10).map(p => p.name.slice(0, 20))"
              :datasets="[
                { label: 'Quality', data: programs.slice(0, 10).map(p => +(p.quality_score * 100).toFixed(0)) },
                { label: 'ROI', data: programs.slice(0, 10).map(p => +(p.roi_score * 100).toFixed(0)) },
                { label: 'Opportunity', data: programs.slice(0, 10).map(p => +(p.opportunity_score * 100).toFixed(0)) },
              ]"
              :height="220"
              y-label="Score"
            />
          </Card>
        </div>
      </template>
    </template>
  </div>
</template>
