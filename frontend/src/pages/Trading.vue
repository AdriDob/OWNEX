<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import { TrendingUp, BarChart3, DollarSign, RefreshCw, Play, Shield, Activity, Wallet } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import Input from '@/components/ui/Input.vue'

const loading = ref(true)
const backtesting = ref(false)
const error = ref('')
const status = ref<any>(null)

const symbol = ref('BTC-USD')
const shortMa = ref(20)
const longMa = ref(50)
const initialCapital = ref(10000)
const backtestResult = ref<any>(null)
const backtestError = ref('')

onMounted(loadStatus)

async function loadStatus() {
  loading.value = true
  try {
    const res = await api.get('/investment/status') as any
    if (res.success) status.value = res.status
  } catch { /* silent */ }
  finally { loading.value = false }
}

async function runBacktest() {
  backtesting.value = true
  backtestResult.value = null
  backtestError.value = ''
  try {
    const res = await api.post('/investment/backtest', {
      symbol: symbol.value,
      short_ma: shortMa.value,
      long_ma: longMa.value,
      initial_capital: initialCapital.value,
    }) as any
    if (res.success) backtestResult.value = res.result
    else backtestError.value = res.error || 'Error en backtest'
  } catch (e: any) {
    backtestError.value = e?.message || 'Error de conexión'
  } finally {
    backtesting.value = false
  }
}

function usd(n: number) {
  return '$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function pct(n: number) {
  return (n >= 0 ? '+' : '') + (n || 0).toFixed(1) + '%'
}

function badgeVariant(value: number, goodIfAbove = 0) {
  if (value >= goodIfAbove) return value >= 50 ? 'default' : 'warning'
  return 'destructive'
}
</script>

<template>
  <div class="flex flex-col items-center justify-start min-h-[80vh] px-4 py-8 animate-in">
    <div class="flex items-center gap-3 mb-2">
      <TrendingUp class="w-8 h-8 text-primary" />
      <h1 class="text-3xl font-bold text-foreground">Trading</h1>
    </div>
    <p class="text-muted-foreground mb-8 text-center max-w-md">
      Backtest de estrategias, capital desplegado y rendimiento.
    </p>

    <!-- Status Metrics -->
    <template v-if="!loading && status">
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-4xl mb-8">
        <Card class="card-base">
          <CardContent class="p-3 text-center">
            <p class="text-xs text-muted-foreground">Capital total</p>
            <p class="text-lg font-bold text-success">{{ usd(status.total_capital || 0) }}</p>
          </CardContent>
        </Card>
        <Card class="card-base">
          <CardContent class="p-3 text-center">
            <p class="text-xs text-muted-foreground">Desplegado</p>
            <p class="text-lg font-bold text-primary">{{ usd(status.deployed || 0) }}</p>
          </CardContent>
        </Card>
        <Card class="card-base">
          <CardContent class="p-3 text-center">
            <p class="text-xs text-muted-foreground">P&L total</p>
            <p :class="['text-lg font-bold', (status.summary?.total_pnl || 0) >= 0 ? 'text-success' : 'text-destructive']">
              {{ usd(status.summary?.total_pnl || 0) }}
            </p>
          </CardContent>
        </Card>
        <Card class="card-base">
          <CardContent class="p-3 text-center">
            <p class="text-xs text-muted-foreground">Sharpe</p>
            <p :class="['text-lg font-bold', (status.summary?.sharpe || 0) >= 1 ? 'text-success' : 'text-warning']">
              {{ (status.summary?.sharpe || 0).toFixed(2) }}
            </p>
          </CardContent>
        </Card>
      </div>
    </template>

    <LoadingState v-if="loading" class="mb-8" />

    <!-- Backtest Section -->
    <Card class="card-base w-full max-w-4xl mb-8">
      <CardContent class="p-4">
        <div class="flex items-center gap-2 mb-4">
          <BarChart3 class="w-5 h-5 text-muted-foreground" />
          <h3 class="text-sm font-semibold text-foreground">Backtest — SMA Crossover</h3>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
          <div>
            <label class="text-xs text-muted-foreground block mb-1">Símbolo</label>
            <Input v-model="symbol" placeholder="BTC-USD" class="h-9 text-sm" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground block mb-1">MA corta</label>
            <Input v-model.number="shortMa" type="number" class="h-9 text-sm" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground block mb-1">MA larga</label>
            <Input v-model.number="longMa" type="number" class="h-9 text-sm" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground block mb-1">Capital inicial</label>
            <Input v-model.number="initialCapital" type="number" class="h-9 text-sm" />
          </div>
          <div class="flex items-end">
            <Button class="w-full h-9" :disabled="backtesting" @click="runBacktest">
              <Play class="w-4 h-4 mr-1" />
              {{ backtesting ? 'Corriendo...' : 'Ejecutar' }}
            </Button>
          </div>
        </div>

        <!-- Results -->
        <template v-if="backtestResult">
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div class="text-center p-2 rounded-lg bg-surface/30">
              <p class="text-xs text-muted-foreground">Retorno total</p>
              <p :class="['text-lg font-bold', backtestResult.total_return_pct >= 0 ? 'text-success' : 'text-destructive']">
                {{ pct(backtestResult.total_return_pct) }}
              </p>
            </div>
            <div class="text-center p-2 rounded-lg bg-surface/30">
              <p class="text-xs text-muted-foreground">Sharpe</p>
              <p :class="['text-lg font-bold', backtestResult.sharpe >= 1 ? 'text-success' : 'text-warning']">
                {{ backtestResult.sharpe.toFixed(2) }}
              </p>
            </div>
            <div class="text-center p-2 rounded-lg bg-surface/30">
              <p class="text-xs text-muted-foreground">Max drawdown</p>
              <p class="text-lg font-bold text-destructive">{{ pct(backtestResult.max_drawdown_pct) }}</p>
            </div>
            <div class="text-center p-2 rounded-lg bg-surface/30">
              <p class="text-xs text-muted-foreground">Win rate</p>
              <p class="text-lg font-bold text-foreground">{{ backtestResult.win_rate }}%</p>
            </div>
          </div>

          <div class="flex items-center gap-3 text-xs text-muted-foreground mb-3">
            <span>{{ backtestResult.total_trades }} trades ({{ backtestResult.winning_trades }}W / {{ backtestResult.losing_trades }}L)</span>
            <Badge variant="outline" size="sm">{{ backtestResult.data_source }}</Badge>
          </div>

          <!-- Trade log table -->
          <div v-if="backtestResult.trades?.length" class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="text-muted-foreground border-b border-border/40">
                  <th class="text-left py-1 pr-2">Entry</th>
                  <th class="text-left py-1 pr-2">Exit</th>
                  <th class="text-right py-1 pr-2">Entry $</th>
                  <th class="text-right py-1 pr-2">Exit $</th>
                  <th class="text-right py-1 pr-2">P&L</th>
                  <th class="text-right py-1 pr-2">Return</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(t, i) in backtestResult.trades" :key="i" class="border-b border-border/20">
                  <td class="py-1 pr-2 text-foreground">{{ t.entry_date }}</td>
                  <td class="py-1 pr-2 text-foreground">{{ t.exit_date }}</td>
                  <td class="py-1 pr-2 text-right font-mono">{{ usd(t.entry_price) }}</td>
                  <td class="py-1 pr-2 text-right font-mono">{{ usd(t.exit_price) }}</td>
                  <td :class="['py-1 pr-2 text-right font-mono', t.pnl >= 0 ? 'text-success' : 'text-destructive']">
                    {{ usd(t.pnl) }}
                  </td>
                  <td :class="['py-1 pr-2 text-right font-mono', t.pnl_pct >= 0 ? 'text-success' : 'text-destructive']">
                    {{ pct(t.pnl_pct) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <p v-if="backtestError" class="text-sm text-destructive mt-2">{{ backtestError }}</p>
      </CardContent>
    </Card>
  </div>
</template>
