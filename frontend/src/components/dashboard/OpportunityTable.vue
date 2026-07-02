<script setup lang="ts">
import { ref, computed } from 'vue'
import { cn } from '@/lib/utils'
import { triggerScan } from '@/lib/api'
import {
  ArrowUpDown, ArrowUp, ArrowDown,
  ChevronLeft, ChevronRight, Zap,
  Download, Filter, X, Check,
  TrendingUp, DollarSign, Target,
} from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'

interface Opportunity {
  id: number
  name: string
  domain: string
  opportunity_score: number
  endpoints: number
  competition: number
  freshness: number
}

const props = defineProps<{ opportunities: Opportunity[] }>()

const sortColumn = ref<string>('opportunity_score')
const sortDirection = ref<'asc' | 'desc'>('desc')
const currentPage = ref(1)
const pageSize = 10
const scanningId = ref<number | null>(null)

// Filters
const showFilters = ref(false)
const filterMinScore = ref<number | null>(null)
const filterMaxCompetition = ref<number | null>(null)
const filterSearch = ref('')

// Bulk selection
const selectedIds = ref<Set<number>>(new Set())
const selectAll = ref(false)

const filtered = computed(() => {
  let arr = [...props.opportunities]

  if (filterMinScore.value !== null) {
    arr = arr.filter(o => o.opportunity_score >= filterMinScore.value!)
  }
  if (filterMaxCompetition.value !== null) {
    arr = arr.filter(o => o.competition <= filterMaxCompetition.value!)
  }
  if (filterSearch.value.trim()) {
    const q = filterSearch.value.toLowerCase()
    arr = arr.filter(o => o.name.toLowerCase().includes(q) || o.domain.toLowerCase().includes(q))
  }

  arr.sort((a, b) => {
    const aVal = a[sortColumn.value as keyof Opportunity] as number
    const bVal = b[sortColumn.value as keyof Opportunity] as number
    return sortDirection.value === 'asc' ? aVal - bVal : bVal - aVal
  })
  return arr
})

const paginated = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

const totalPages = computed(() => Math.ceil(filtered.value.length / pageSize))

function toggleSort(col: string) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortDirection.value = 'desc'
  }
}

async function handleScan(opp: Opportunity) {
  scanningId.value = opp.id
  try {
    await triggerScan(opp.id, 'quick')
  } catch { /* toast handled by parent */ }
  finally { scanningId.value = null }
}

function ScoreBadge(score: number) {
  if (score >= 8) return 'gold'
  if (score >= 6) return 'success'
  if (score >= 4) return 'warning'
  return 'default'
}

function CompetitionBadge(score: number) {
  if (score <= 2) return 'success'
  if (score <= 5) return 'warning'
  return 'destructive'
}

function SortIcon(col: string) {
  if (sortColumn.value !== col) return ArrowUpDown
  return sortDirection.value === 'asc' ? ArrowUp : ArrowDown
}

// Bulk selection
function toggleSelect(id: number) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
  selectAll.value = s.size === filtered.value.length
}

function toggleSelectAll() {
  if (selectAll.value) {
    selectedIds.value = new Set()
    selectAll.value = false
  } else {
    selectedIds.value = new Set(filtered.value.map(o => o.id))
    selectAll.value = true
  }
}

const hasSelection = computed(() => selectedIds.value.size > 0)

async function bulkScan() {
  for (const id of selectedIds.value) {
    scanningId.value = id
    try { await triggerScan(id, 'quick') } catch { /* */ }
  }
  scanningId.value = null
  selectedIds.value = new Set()
  selectAll.value = false
}

function exportCsv() {
  const headers = ['Target', 'Domain', 'Score', 'Endpoints', 'Competition', 'Freshness']
  const rows = filtered.value.map(o => [
    o.name,
    o.domain || '',
    o.opportunity_score.toFixed(1),
    String(o.endpoints),
    String(o.competition),
    `${o.freshness}%`,
  ])
  const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c.replace(/"/g, '""')}"`).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `oportunidades-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function clearFilters() {
  filterMinScore.value = null
  filterMaxCompetition.value = null
  filterSearch.value = ''
}

const hasActiveFilters = computed(() =>
  filterMinScore.value !== null || filterMaxCompetition.value !== null || filterSearch.value.trim().length > 0
)

// Money Radar derived data
const totalPotentialValue = computed(() => {
  return filtered.value.reduce((sum, o) => sum + o.opportunity_score * 1000, 0)
})

const avgScore = computed(() => {
  if (filtered.value.length === 0) return 0
  return filtered.value.reduce((sum, o) => sum + o.opportunity_score, 0) / filtered.value.length
})

const bestTarget = computed(() => {
  if (filtered.value.length === 0) return null
  return filtered.value.reduce((best, o) => o.opportunity_score > best.opportunity_score ? o : best, filtered.value[0])
})
</script>

<template>
  <div class="space-y-3">
    <!-- Money Radar Summary -->
    <div v-if="filtered.length > 0" class="flex items-center gap-4 text-xs text-muted-foreground px-1">
      <span class="flex items-center gap-1">
        <Target class="h-3 w-3" />
        <span class="font-semibold text-foreground">{{ filtered.length }}</span> oportunidades
      </span>
      <span class="flex items-center gap-1">
        <TrendingUp class="h-3 w-3" />
        Score promedio: <span class="font-semibold text-foreground">{{ avgScore.toFixed(1) }}</span>
      </span>
      <span v-if="bestTarget" class="flex items-center gap-1">
        <DollarSign class="h-3 w-3 text-gold" />
        Mejor: <span class="font-semibold text-gold">{{ bestTarget.name }}</span>
        <Badge variant="gold" class="text-[10px] px-1.5 py-0">{{ bestTarget.opportunity_score.toFixed(1) }}</Badge>
      </span>
    </div>

    <!-- Filters Bar -->
    <div class="flex flex-wrap items-center gap-2">
      <Button variant="ghost" size="sm" @click="showFilters = !showFilters" class="gap-1.5">
        <Filter class="h-3.5 w-3.5" />
        Filtros
        <span v-if="hasActiveFilters" class="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground font-bold">!</span>
      </Button>

      <div v-if="showFilters" class="flex flex-wrap items-center gap-2 animate-in">
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] text-muted-foreground">Score min:</span>
          <Input v-model.number="filterMinScore" type="number" min="0" max="10" step="0.5" placeholder="0" class="w-16 h-7 text-xs" />
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] text-muted-foreground">Competencia max:</span>
          <Input v-model.number="filterMaxCompetition" type="number" min="0" max="10" step="1" placeholder="10" class="w-16 h-7 text-xs" />
        </div>
        <div class="flex items-center gap-1.5">
          <Input v-model="filterSearch" placeholder="Buscar target..." class="w-36 h-7 text-xs" />
        </div>
        <Button v-if="hasActiveFilters" variant="ghost" size="sm" @click="clearFilters" class="h-7 text-xs">
          <X class="h-3 w-3" /> Limpiar
        </Button>
      </div>

      <div class="flex-1" />

      <!-- Bulk Actions -->
      <div v-if="hasSelection" class="flex items-center gap-2 animate-in">
        <span class="text-xs text-muted-foreground">{{ selectedIds.size }} seleccionados</span>
        <Button variant="secondary" size="sm" @click="bulkScan" class="text-xs h-7">
          <Zap class="h-3 w-3" /> Escanear
        </Button>
      </div>

      <Button variant="ghost" size="sm" @click="exportCsv" class="text-xs h-7 gap-1.5">
        <Download class="h-3.5 w-3.5" /> CSV
      </Button>
    </div>

    <!-- Table -->
    <div class="glass-card rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-border/40">
              <th class="w-10 px-2 py-3">
                <input type="checkbox" :checked="selectAll" @change="toggleSelectAll"
                  class="h-4 w-4 rounded border-border bg-surface accent-primary cursor-pointer" />
              </th>
              <th @click="toggleSort('opportunity_score')" class="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                <div class="flex items-center gap-1.5">
                  <span>ORION Score</span>
                  <component :is="SortIcon('opportunity_score')" class="h-3 w-3" />
                </div>
              </th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Target</th>
              <th class="hidden sm:table-cell px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Domain</th>
              <th @click="toggleSort('endpoints')" class="cursor-pointer select-none px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                <div class="flex items-center justify-end gap-1.5">
                  <span>Endpoints</span>
                  <component :is="SortIcon('endpoints')" class="h-3 w-3" />
                </div>
              </th>
              <th @click="toggleSort('competition')" class="cursor-pointer select-none px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                <div class="flex items-center justify-end gap-1.5">
                  <span>Competition</span>
                  <component :is="SortIcon('competition')" class="h-3 w-3" />
                </div>
              </th>
              <th @click="toggleSort('freshness')" class="cursor-pointer select-none px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors">
                <div class="flex items-center justify-end gap-1.5">
                  <span>Freshness</span>
                  <component :is="SortIcon('freshness')" class="h-3 w-3" />
                </div>
              </th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(opp, i) in paginated" :key="opp.id"
              :class="[
                'animate-in border-b border-border/20 transition-colors',
                selectedIds.has(opp.id) ? 'bg-primary/5' : 'hover:bg-surface/30',
              ]"
              :style="{ animationDelay: `${i * 30}ms` }"
            >
              <td class="px-2 py-3">
                <input type="checkbox" :checked="selectedIds.has(opp.id)" @change="toggleSelect(opp.id)"
                  class="h-4 w-4 rounded border-border bg-surface accent-primary cursor-pointer" />
              </td>
              <td class="px-4 py-3">
                <Badge :variant="ScoreBadge(opp.opportunity_score)" class="font-mono font-bold text-xs min-w-[3rem] text-center">
                  {{ opp.opportunity_score.toFixed(1) }}
                </Badge>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-foreground text-sm">{{ opp.name }}</span>
                  <Badge v-if="opp.opportunity_score >= 8" variant="gold" class="text-[9px] px-1 py-0">TOP</Badge>
                </div>
              </td>
              <td class="hidden sm:table-cell px-4 py-3 text-muted-foreground text-xs">{{ opp.domain || '—' }}</td>
              <td class="px-4 py-3 text-right tabular-nums text-foreground text-sm">{{ opp.endpoints }}</td>
              <td class="px-4 py-3 text-right">
                <Badge :variant="CompetitionBadge(opp.competition)" class="text-xs">
                  {{ opp.competition }}/10
                </Badge>
              </td>
              <td class="px-4 py-3 text-right tabular-nums">
                <div class="flex items-center justify-end gap-1.5">
                  <div class="h-1.5 w-12 rounded-full bg-surface overflow-hidden">
                    <div class="h-full rounded-full transition-all duration-300"
                      :class="opp.freshness >= 70 ? 'bg-success' : opp.freshness >= 40 ? 'bg-warning' : 'bg-destructive'"
                      :style="{ width: `${opp.freshness}%` }"
                    />
                  </div>
                  <span class="text-xs text-muted-foreground">{{ opp.freshness }}%</span>
                </div>
              </td>
              <td class="px-4 py-3 text-right">
                <Button variant="ghost" size="sm" @click="handleScan(opp)" :loading="scanningId === opp.id" class="text-xs h-7" :disabled="scanningId === opp.id">
                  <Zap class="h-3 w-3" />
                  {{ scanningId === opp.id ? '...' : 'Scan' }}
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div v-if="filtered.length === 0" class="py-12 text-center text-sm text-muted-foreground">
        No se encontraron oportunidades con los filtros actuales
      </div>

      <!-- Footer -->
      <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-border/40 px-4 py-3">
        <div class="flex items-center gap-2">
          <p class="text-xs text-muted-foreground">{{ filtered.length }} oportunidades</p>
          <span v-if="hasActiveFilters" class="text-[10px] text-muted-foreground/50">(filtradas)</span>
        </div>
        <div class="flex items-center gap-2">
          <button :disabled="currentPage === 1" @click="currentPage--"
            class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-surface hover:text-foreground disabled:opacity-30 transition-colors"
          ><ChevronLeft class="h-3.5 w-3.5" /></button>
          <span class="text-xs text-muted-foreground tabular-nums">{{ currentPage }} / {{ totalPages }}</span>
          <button :disabled="currentPage === totalPages" @click="currentPage++"
            class="flex h-7 w-7 items-center justify-center rounded text-muted-foreground hover:bg-surface hover:text-foreground disabled:opacity-30 transition-colors"
          ><ChevronRight class="h-3.5 w-3.5" /></button>
        </div>
      </div>
    </div>
  </div>
</template>
