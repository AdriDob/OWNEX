<script setup lang="ts">
/**
 * Trading — Consolidated page with tabs.
 * Combines: Trading + TradingIntelligence + TradingLab
 */
import { ref, computed, onMounted } from 'vue'
import { TrendingUp, Brain, FlaskConical, DollarSign, RefreshCw } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

const activeTab = ref('dashboard')
const loading = ref(true)
const portfolio = ref<any>(null)
const strategies = ref<any[]>([])

async function fetchData() {
  loading.value = true
  try {
    const [pRes, sRes] = await Promise.allSettled([
      fetch('/api/trading/dashboard/summary').then(r => r.json()),
      fetch('/api/polymarket/strategies').then(r => r.json()),
    ])
    if (pRes.status === 'fulfilled') portfolio.value = pRes.value
    if (sRes.status === 'fulfilled') strategies.value = sRes.value.strategies || []
  } catch { /* silent */ }
  loading.value = false
}

const tabs = computed(() => [
  { id: 'dashboard', label: 'Dashboard', icon: TrendingUp },
  { id: 'intelligence', label: 'Inteligencia', icon: Brain },
  { id: 'lab', label: 'Lab', icon: FlaskConical },
])

function formatUsd(n: number) {
  return `$${Math.round(n).toLocaleString()}`
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Trading</h1>
        <p class="text-sm text-muted-foreground">Inversiones, estrategias y análisis</p>
      </div>
      <button
        class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        @click="fetchData"
      >
        <RefreshCw class="h-3 w-3" /> Refresh
      </button>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Dashboard -->
      <template #dashboard>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-24 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Portfolio</p>
              <p class="mt-1 font-mono text-xl font-bold">{{ formatUsd(portfolio?.total_value || 0) }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">P&L</p>
              <p class="mt-1 font-mono text-xl font-bold" :class="(portfolio?.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'">
                {{ formatUsd(portfolio?.pnl || 0) }}
              </p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Positions</p>
              <p class="mt-1 font-mono text-xl font-bold">{{ portfolio?.positions?.length || 0 }}</p>
            </div>
            <div class="rounded-xl border border-border/30 bg-surface/50 p-4">
              <p class="font-mono text-[10px] uppercase text-muted-foreground">Strategies</p>
              <p class="mt-1 font-mono text-xl font-bold">{{ strategies.length }}</p>
            </div>
          </div>

          <!-- Positions -->
          <div v-if="portfolio?.positions?.length" class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Positions</h3>
            <div class="space-y-2">
              <div
                v-for="pos in portfolio.positions"
                :key="pos.symbol"
                class="flex items-center justify-between rounded-lg border border-border/20 p-3"
              >
                <div>
                  <p class="font-mono text-sm font-medium">{{ pos.symbol }}</p>
                  <p class="text-[10px] text-muted-foreground">{{ pos.amount }} units</p>
                </div>
                <div class="text-right">
                  <p class="font-mono text-sm font-medium">{{ formatUsd(pos.value || 0) }}</p>
                  <p class="text-[10px]" :class="(pos.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'">
                    {{ pos.pnl >= 0 ? '+' : '' }}{{ formatUsd(pos.pnl || 0) }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="rounded-xl border border-dashed border-border/30 p-8 text-center">
            <DollarSign class="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p class="mt-2 text-sm text-muted-foreground">Sin posiciones activas</p>
            <p class="mt-1 text-xs text-muted-foreground/60">Configurá exchanges en Settings para empezar</p>
          </div>
        </div>
      </template>

      <!-- Intelligence -->
      <template #intelligence>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-foreground">Estrategias Disponibles</h3>
          <div v-if="strategies.length" class="space-y-2">
            <div
              v-for="s in strategies"
              :key="s.name"
              class="rounded-lg border border-border/20 p-3"
            >
              <p class="text-sm font-medium text-foreground">{{ s.name }}</p>
              <p class="mt-1 text-xs text-muted-foreground">{{ s.description || 'No description' }}</p>
            </div>
          </div>
          <div v-else class="text-center py-8">
            <Brain class="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p class="mt-2 text-sm text-muted-foreground">Sin estrategias configuradas</p>
          </div>
        </div>
      </template>

      <!-- Lab -->
      <template #lab>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-5 text-center">
          <FlaskConical class="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p class="mt-2 text-sm text-muted-foreground">Trading Lab</p>
          <p class="mt-1 text-xs text-muted-foreground/60">Backtesting y experimentación de estrategias</p>
        </div>
      </template>
    </Tabs>
  </div>
</template>
