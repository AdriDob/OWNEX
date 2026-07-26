<script setup lang="ts">
import { DollarSign, TrendingUp, Wallet } from '@lucide/vue'

interface Props {
  totalCollected?: number
  totalPending?: number
  monthlyEarnings?: number
  usdPerHour?: number
  bestProgram?: string | null
  loading?: boolean
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  totalCollected: 0,
  totalPending: 0,
  monthlyEarnings: 0,
  usdPerHour: 0,
  bestProgram: null,
  loading: false,
})

const formatUSD = (n: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

const formatUSDCompact = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`
  return `$${n.toLocaleString()}`
}
</script>

<template>
  <div :class="['panel rounded-xl p-4', className]">
    <div class="flex items-center gap-2 mb-3">
      <Wallet class="h-4 w-4 text-gold" />
      <span class="font-mono text-xs font-semibold text-foreground">Revenue Snapshot</span>
    </div>

    <div v-if="loading" class="grid grid-cols-2 gap-3">
      <div v-for="i in 4" :key="i" class="h-16 animate-pulse rounded-lg bg-surface/50" />
    </div>

    <template v-else>
      <!-- Row 1: Main KPIs -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
        <div class="rounded-lg bg-surface/30 p-3">
          <div class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">Total Cobrado</div>
          <div class="font-display text-lg font-bold text-gold mt-0.5">{{ formatUSD(totalCollected) }}</div>
        </div>
        <div class="rounded-lg bg-surface/30 p-3">
          <div class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">Pendiente</div>
          <div class="font-display text-lg font-bold text-warning mt-0.5">{{ formatUSD(totalPending) }}</div>
        </div>
        <div class="rounded-lg bg-surface/30 p-3">
          <div class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">Este Mes</div>
          <div class="font-display text-lg font-bold text-success mt-0.5">{{ formatUSD(monthlyEarnings) }}</div>
        </div>
        <div class="rounded-lg bg-surface/30 p-3">
          <div class="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">USD/h</div>
          <div class="font-display text-lg font-bold text-primary mt-0.5">{{ formatUSDCompact(usdPerHour) }}</div>
        </div>
      </div>

      <!-- Row 2: Best program -->
      <div v-if="bestProgram" class="flex items-center gap-2 rounded-lg bg-primary/5 border border-primary/10 px-3 py-2">
        <TrendingUp class="h-3.5 w-3.5 text-primary" />
        <span class="font-mono text-[10px] text-muted-foreground">Mejor programa</span>
        <span class="font-mono text-xs font-medium text-primary ml-auto">{{ bestProgram }}</span>
      </div>
      <div v-else class="py-2 text-center">
        <span class="font-mono text-[10px] text-muted-foreground">Sin datos de programas</span>
      </div>
    </template>
  </div>
</template>