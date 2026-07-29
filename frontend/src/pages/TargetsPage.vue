<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Target, Search, Filter, AlertTriangle, RefreshCw, TrendingUp,
  Shield, ShieldAlert, ExternalLink, Star, Clock,
} from '@lucide/vue'

interface MoneyRadarItem {
  id: number; name: string; platform: string; program_url: string | null
  private: boolean; status: string
  orion_score: number; priority: string
  max_reward: number | null; min_reward: number | null; reward_currency: string | null
  total_reports: number; confirmed_reports: number; total_earned: number
  competition: number; effort_hours: number; evh: number
  technologies_summary: string | null
}

const router = useRouter()
const items = ref<MoneyRadarItem[]>([])
const total = ref(0)
const loading = ref(true)
const error = ref('')
const search = ref('')
const platformFilter = ref('')
const statusFilter = ref('')
const sortBy = ref<'orion_score' | 'evh' | 'max_reward'>('evh')
const generatedAt = ref('')

const platforms = computed(() => {
  const set = new Set(items.value.map(i => i.platform))
  return Array.from(set).sort()
})

const sorted = computed(() => {
  const list = [...items.value]
  if (search.value) {
    const q = search.value.toLowerCase()
    return list.filter(i => i.name.toLowerCase().includes(q) || (i.technologies_summary || '').toLowerCase().includes(q))
  }
  return list
})

async function fetchData() {
  loading.value = true; error.value = ''
  try {
    const params: Record<string, any> = { limit: 200 }
    if (platformFilter.value) params.platform = platformFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await api.get<{ items: MoneyRadarItem[]; total: number; generated_at: string }>('/economic/money-radar', params)
    items.value = res.items || []
    total.value = res.total || 0
    generatedAt.value = res.generated_at || ''
  } catch (e: any) {
    error.value = e?.message || 'Error loading targets'
  } finally { loading.value = false }
}

onMounted(fetchData)

function platformColor(p: string) {
  const map: Record<string, string> = {
    hackerone: 'text-[#00A98F]', bugcrowd: 'text-[#6333FF]',
    intigriti: 'text-[#0D90F4]', synack: 'text-[#FF6B35]',
    immunefi: 'text-[#FF6B35]', yeswehack: 'text-[#E74C3C]',
    code4rena: 'text-[#00A98F]',
  }
  return map[p?.toLowerCase()] || 'text-primary'
}

function scoreColor(s: number) {
  if (s >= 80) return 'text-success'
  if (s >= 50) return 'text-warning'
  return 'text-muted-foreground'
}

function priorityBadge(p: string): 'destructive' | 'warning' | 'default' {
  const map: Record<string, 'destructive' | 'warning' | 'default'> = { critical: 'destructive', high: 'warning', medium: 'default', low: 'default' }
  return map[p?.toLowerCase()] || 'default'
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between animate-in">
      <div class="space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Target Intelligence</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Targets</h1>
        <p class="text-sm text-muted-foreground">Where should you put your time today? — ranked by expected value per hour</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3 animate-in">
      <div class="relative flex-1 min-w-[200px] max-w-xs">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input v-model="search" placeholder="Search targets, technologies..."
          class="w-full rounded-lg border border-border/60 bg-[#11131f]/60 py-2 pl-9 pr-3 text-xs text-foreground placeholder:text-muted-foreground/50" />
      </div>
      <select v-model="platformFilter" @change="fetchData"
        class="rounded-lg border border-border/60 bg-[#11131f]/60 px-3 py-2 text-xs text-foreground">
        <option value="">All platforms</option>
        <option v-for="p in platforms" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="statusFilter" @change="fetchData"
        class="rounded-lg border border-border/60 bg-[#11131f]/60 px-3 py-2 text-xs text-foreground">
        <option value="">All status</option>
        <option value="active">Active</option>
        <option value="paused">Paused</option>
        <option value="closed">Closed</option>
      </select>
      <Button variant="outline" size="sm" @click="fetchData" class="gap-2">
        <RefreshCw class="h-3.5 w-3.5" /> Refresh
      </Button>
    </div>

    <!-- Summary bar -->
    <div class="flex flex-wrap items-center gap-4 text-xs text-muted-foreground animate-in">
      <span>{{ total }} targets tracked</span>
      <span class="h-3 w-px bg-border/40" />
      <span>{{ items.filter(i => i.orion_score >= 70).length }} high-value</span>
      <span class="h-3 w-px bg-border/40" />
      <span>{{ items.filter(i => i.status === 'active').length }} active</span>
      <span v-if="generatedAt" class="h-3 w-px bg-border/40" />
      <span v-if="generatedAt" class="flex items-center gap-1">
        <Clock class="h-3 w-3" /> {{ new Date(generatedAt).toLocaleString() }}
      </span>
    </div>

    <template v-if="loading">
      <div class="space-y-2"><Skeleton v-for="i in 8" :key="i" class="h-16 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">Connection error</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button class="mt-4" @click="fetchData">Retry</Button>
      </div>
    </template>

    <template v-else-if="sorted.length === 0">
      <div class="flex flex-col items-center py-20 text-center">
        <Target class="mb-4 h-10 w-10 text-muted-foreground/50" />
        <p class="text-sm font-semibold text-foreground">No targets found</p>
        <p class="mt-1 text-xs text-muted-foreground">Try adjusting filters or run discovery first</p>
      </div>
    </template>

    <template v-else>
      <div class="space-y-2 animate-in">
        <div v-for="(item, i) in sorted" :key="item.id"
          class="flex items-center gap-4 rounded-xl border border-border/40 bg-[#11131f]/40 p-4 transition-all hover:border-primary/30 hover:bg-primary/5 cursor-pointer"
          :style="{ animationDelay: `${i * 20}ms` }"
          @click="router.push(`/programs/${item.id}`)">
          <!-- Rank -->
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold"
            :class="i < 3 ? 'bg-gold/15 text-gold ring-1 ring-gold/30' : 'bg-surface/40 text-muted-foreground'">
            {{ i + 1 }}
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-foreground truncate">{{ item.name }}</span>
              <Badge v-if="item.priority === 'critical' || item.priority === 'high'" :variant="priorityBadge(item.priority)" class="text-[8px] px-1.5">
                {{ item.priority }}
              </Badge>
            </div>
            <div class="flex items-center gap-2 mt-0.5">
              <span :class="['text-xs font-medium', platformColor(item.platform)]">{{ item.platform }}</span>
              <span class="text-[10px] text-muted-foreground">·</span>
              <Badge variant="outline" class="text-[9px]">{{ item.status }}</Badge>
              <span v-if="item.technologies_summary" class="text-[10px] text-muted-foreground truncate max-w-[200px]">{{ item.technologies_summary }}</span>
            </div>
          </div>
          <!-- Score -->
          <div class="hidden sm:flex items-center gap-6 text-xs">
            <div class="text-center min-w-[50px]">
              <p class="text-[9px] text-muted-foreground">Score</p>
              <p :class="['font-bold font-mono', scoreColor(item.orion_score)]">{{ Math.round(item.orion_score) }}</p>
            </div>
            <div class="text-center min-w-[60px]">
              <p class="text-[9px] text-muted-foreground">Max reward</p>
              <p class="font-semibold font-mono text-foreground">{{ item.max_reward ? '$' + item.max_reward.toLocaleString() : '—' }}</p>
            </div>
            <div class="text-center min-w-[60px]">
              <p class="text-[9px] text-muted-foreground">EV/h</p>
              <p class="font-semibold font-mono" :class="item.evh >= 50 ? 'text-success' : item.evh >= 20 ? 'text-warning' : 'text-muted-foreground'">
                ${{ item.evh.toFixed(1) }}
              </p>
            </div>
          </div>
          <!-- Arrow -->
          <ExternalLink class="h-4 w-4 shrink-0 text-muted-foreground/40" />
        </div>
      </div>
    </template>
  </div>
</template>
