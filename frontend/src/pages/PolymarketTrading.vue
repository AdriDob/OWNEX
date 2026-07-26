<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { api } from '@/lib/api'
import {
  Activity,
  BarChart3,
  Bitcoin,
  CheckCircle2,
  Clock,
  Cloud,
  Copy,
  ExternalLink,
  Globe,
  RefreshCw,
  Scan,
  Settings2,
  Sparkles,
  Thermometer,
  TrendingUp,
  TrendingDown,
  Wifi,
  Zap,
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const STRATEGY_DEFS: Record<string, {
  label: string
  icon: any
  accent: string
  bgGlow: string
  description: string
  whatItDoes: string
  needsKeys: boolean
  setupGuide: string
  repo: string
}> = {
  btc_arb: {
    label: 'BTC Latency Arbitrage',
    icon: Zap,
    accent: 'text-amber-400',
    bgGlow: 'bg-amber-500/5',
    description: 'Detecta micro-movimientos de BTC en Binance y entra en Polymarket antes de que el mercado reaccione',
    whatItDoes: 'Monitorea velas de 1s en Binance. Si BTC se mueve >$70 en 1 minuto, genera señal de compra/venta en el mercado 5m de Polymarket.',
    needsKeys: false,
    setupGuide: 'No requiere API keys. Usa APIs públicas de Binance + Polymarket.',
    repo: 'github.com/alsk1992/CloddsBot',
  },
  smart_money: {
    label: 'Smart Money Copy Trading',
    icon: Copy,
    accent: 'text-cyan-400',
    bgGlow: 'bg-cyan-500/5',
    description: 'Escanea y copia las posiciones de los traders más rentables de Polymarket',
    whatItDoes: 'Consulta el leaderboard de Polymarket, filtra traders por win rate >60%, y genera señales de copy trade basadas en sus posiciones abiertas.',
    needsKeys: false,
    setupGuide: 'Sin API keys. Datos del leaderboard público de Polymarket Gamma API.',
    repo: 'github.com/MrFadiAi/Polymarket-bot',
  },
  complete_arb: {
    label: 'Complete-Set Arbitrage',
    icon: BarChart3,
    accent: 'text-emerald-400',
    bgGlow: 'bg-emerald-500/5',
    description: 'Explota diferencias de precio cuando YES+NO no suman 1.0',
    whatItDoes: 'Escanea mercados buscando donde YES + NO != 1. Compra el lado barato, vende el caro. Riesgo mínimo, ganancia por spread.',
    needsKeys: false,
    setupGuide: 'Sin API keys. Usa CLOB prices públicos. Para ejecutar trades necesitás clave privada Polymarket.',
    repo: 'github.com/ent0n29/polybot',
  },
  weather: {
    label: 'Weather Prediction Markets',
    icon: Thermometer,
    accent: 'text-sky-400',
    bgGlow: 'bg-sky-500/5',
    description: 'Predice temperaturas de liquidación en mercados climáticos de Polymarket',
    whatItDoes: 'Obtiene datos de Open-Meteo (gratis, sin API key). Estima si la temperatura superará un umbral. Ideal para mercados "Hace más de 30°C en Buenos Aires".',
    needsKeys: false,
    setupGuide: 'Sin API keys. Datos de Open-Meteo (free, no requiere registro).',
    repo: 'github.com/yangyuan-zhen/PolyWeather',
  },
  lp_mm: {
    label: 'LP Market Making',
    icon: Activity,
    accent: 'text-violet-400',
    bgGlow: 'bg-violet-500/5',
    description: 'Coloca órdenes límite para ganar rewards de liquidez en Polymarket',
    whatItDoes: 'Calcula spreads óptimos (coarse tick + fine tick) para órdenes de compra/venta. Gana incentives del programa de liquidez de Polymarket CLOB.',
    needsKeys: true,
    setupGuide: 'Requiere: POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE, private key de wallet.',
    repo: 'github.com/lihanyu81/polymarket_lp_tool',
  },
}

interface StrategyResult {
  signal?: boolean
  reason?: string
  btc_move?: number
  btc_price?: number
  direction?: string
  opportunities?: any[]
  traders?: any[]
  signals?: any[]
  weather?: any
  data?: any
  binance?: boolean
  polymarket?: boolean
  ready?: boolean
  error?: string
  active_orders?: number
  strategy?: string
  note?: string
}

interface ScanResult {
  status: string
  result: Record<string, StrategyResult>
  strategy?: string
}

const loading = ref(true)
const error = ref<string | null>(null)
const scanResult = ref<ScanResult | null>(null)
const scanning = ref<Record<string, boolean>>({})
const lastUpdated = ref<string | null>(null)
let autoRefresh: ReturnType<typeof setInterval> | null = null

async function fetchAll() {
  loading.value = true
  error.value = null
  try {
    const res = await api.post<ScanResult>('/api/copilot/polymarket/scan?strategy=all', {})
    scanResult.value = res
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (e: any) {
    error.value = e?.message || 'Error al conectar con Polymarket'
  } finally {
    loading.value = false
  }
}

async function scanStrategy(name: string) {
  scanning.value[name] = true
  try {
    const res = await api.post<ScanResult>(`/api/copilot/polymarket/scan?strategy=${name}`, {})
    if (scanResult.value?.result) {
      scanResult.value.result[name] = res.result
    }
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (e: any) {
    console.warn(`Scan ${name} failed:`, e)
  } finally {
    scanning.value[name] = false
  }
}

const btcStatus = computed(() => {
  const btc = scanResult.value?.result?.btc_arb
  if (!btc) return null
  return {
    price: btc.btc_price ?? null,
    move: btc.btc_move ?? null,
    signal: btc.signal ?? false,
    direction: btc.direction ?? null,
    reason: btc.reason ?? null,
  }
})

const connectionStatus = computed(() => {
  const r = scanResult.value?.result
  if (!r) return { label: 'No Data', lamp: 'lamp-off', text: 'text-muted-foreground' }
  const binance = r.btc_arb?.binance
  const polymarket = r.btc_arb?.polymarket
  if (binance) return { label: 'Binance Connected', lamp: 'lamp-green', text: 'text-success' }
  return { label: 'No Connection', lamp: 'lamp-red', text: 'text-destructive' }
})

const signalCount = computed(() => {
  const r = scanResult.value?.result
  let count = 0
  if (r?.btc_arb?.signal) count++
  if (r?.complete_arb?.opportunities?.length) count++
  if (r?.smart_money?.signals?.length) count++
  return count
})

function statusForStrategy(key: string): { lamp: string; label: string; text: string } {
  const data = scanResult.value?.result?.[key]
  if (!data) return { lamp: 'lamp-off', label: 'Sin datos', text: 'text-muted-foreground' }
  if (data.error) return { lamp: 'lamp-red', label: 'Error', text: 'text-destructive' }
  if (key === 'btc_arb' && data.signal) return { lamp: 'lamp-green', label: '🔵 SEÑAL ACTIVA', text: 'text-success' }
  if (key === 'complete_arb' && data.opportunities?.length) return { lamp: 'lamp-green', label: `${data.opportunities.length} ops`, text: 'text-success' }
  if (key === 'smart_money' && data.traders?.length) return { lamp: 'lamp-amber', label: `${data.traders.length} traders`, text: 'text-warning' }
  if (key === 'weather' && data.data?.current_temp != null) return { lamp: 'lamp-green', label: `${data.data.current_temp}°C`, text: 'text-success' }
  if (key === 'lp_mm') return { lamp: 'lamp-amber', label: 'Configurar', text: 'text-warning' }
  return { lamp: 'lamp-off', label: 'Esperando...', text: 'text-muted-foreground' }
}

const strategyKeys = computed(() => Object.keys(STRATEGY_DEFS))
const weatherData = computed(() => scanResult.value?.result?.weather?.data)

onMounted(() => {
  fetchAll()
  autoRefresh = setInterval(fetchAll, 60000)
})
onUnmounted(() => {
  if (autoRefresh) clearInterval(autoRefresh)
})

function fmtUSD(v: number | null | undefined): string {
  if (v == null) return '—'
  return '$' + v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function openRepo(repo: string) {
  window.open('https://' + repo, '_blank')
}
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <BarChart3 class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">POLYMARKET TRADING</span>
          <span class="lamp" :class="connectionStatus.lamp" />
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">
          Centro de Trading Predictivo
        </h1>
        <p class="text-xs text-muted-foreground flex items-center gap-2">
          <Clock class="h-3 w-3" />
          Último scan: {{ lastUpdated || '—' }}
          <button @click="fetchAll" class="text-primary hover:underline flex items-center gap-1 ml-2">
            <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': loading }" /> Actualizar
          </button>
        </p>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <div class="tactical-panel rounded-xl px-4 py-2 flex items-center gap-3">
          <Wifi class="h-4 w-4" :class="connectionStatus.text" />
          <div class="text-right">
            <p class="text-xs font-mono font-bold" :class="connectionStatus.text">{{ connectionStatus.label }}</p>
            <p class="text-[10px] text-muted-foreground">{{ signalCount }} señal(es) activa(s)</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ LOADING / ERROR ═══ -->
    <LoadingState v-if="loading && !scanResult" />
    <ErrorState v-else-if="error && !scanResult" title="Error de conexión" :message="error" :retry="fetchAll" />

    <!-- ═══ MAIN CONTENT ═══ -->
    <template v-else>
      <!-- ═══ KPI STRIP ═══ -->
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">BTC/USD</span>
            <Bitcoin class="h-4 w-4 text-amber-400" />
          </div>
          <p class="font-mono text-xl font-bold text-amber-400">
            <template v-if="btcStatus">{{ fmtUSD(btcStatus.price) }}</template>
            <Skeleton v-else class="h-6 w-20 inline-block align-middle" />
          </p>
          <div v-if="btcStatus" class="flex items-center gap-1 mt-1">
            <component
              :is="btcStatus.direction === 'up' ? TrendingUp : TrendingDown"
              class="h-3 w-3"
              :class="btcStatus.direction === 'up' ? 'text-success' : 'text-destructive'"
            />
            <span
              class="font-mono text-xs font-bold"
              :class="btcStatus.direction === 'up' ? 'text-success' : 'text-destructive'"
            >
              {{ btcStatus.move != null ? '$' + btcStatus.move.toFixed(2) : '—' }}
            </span>
            <span class="text-[10px] text-muted-foreground">/1m</span>
          </div>
        </div>

        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">SEÑALES ACTIVAS</span>
            <Zap class="h-4 w-4 text-primary" />
          </div>
          <p class="font-mono text-xl font-bold phosphor">{{ signalCount }}</p>
          <p class="text-[10px] text-muted-foreground mt-1">Estrategias con oportunidad</p>
        </div>

        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">WEATHER</span>
            <Cloud class="h-4 w-4 text-sky-400" />
          </div>
          <p class="font-mono text-xl font-bold text-sky-400">
            {{ weatherData?.current_temp ?? '—' }}°C
          </p>
          <p class="text-[10px] text-muted-foreground mt-1">
            H {{ weatherData?.today_max ?? '—' }}° / L {{ weatherData?.today_min ?? '—' }}°
          </p>
        </div>

        <div class="tactical-panel rounded-xl p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="font-mono text-[10px] text-muted-foreground tracking-wider">ARBITRAJE</span>
            <BarChart3 class="h-4 w-4 text-emerald-400" />
          </div>
          <p class="font-mono text-xl font-bold text-emerald-400">
            {{ scanResult?.result?.complete_arb?.opportunities?.length ?? 0 }}
          </p>
          <p class="text-[10px] text-muted-foreground mt-1">Complete-set oportunidades</p>
        </div>
      </div>

      <!-- ═══ STRATEGY CARDS ═══ -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="key in strategyKeys"
          :key="key"
          class="card-base rounded-xl border border-border/30 overflow-hidden transition-all duration-300 hover:border-primary/30 hover:shadow-[0_0_20px_-8px_theme(colors.primary)]"
        >
          <div class="p-5">
            <!-- Card Header -->
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-2.5">
                <div class="w-9 h-9 rounded-lg flex items-center justify-center" :class="STRATEGY_DEFS[key].bgGlow">
                  <component :is="STRATEGY_DEFS[key].icon" class="h-5 w-5" :class="STRATEGY_DEFS[key].accent" />
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-foreground">{{ STRATEGY_DEFS[key].label }}</h3>
                  <p class="text-[10px] text-muted-foreground leading-tight mt-0.5 max-w-[200px]">
                    {{ STRATEGY_DEFS[key].description }}
                  </p>
                </div>
              </div>
              <span class="lamp shrink-0 mt-1" :class="statusForStrategy(key).lamp" />
            </div>

            <!-- Status Badge -->
            <div class="flex items-center gap-2 mb-3">
              <Badge
                :variant="statusForStrategy(key).lamp === 'lamp-green' ? 'success' : statusForStrategy(key).lamp === 'lamp-red' ? 'destructive' : 'outline'"
                size="sm"
                class="text-[10px]"
              >
                {{ statusForStrategy(key).label }}
              </Badge>
              <span v-if="STRATEGY_DEFS[key].needsKeys" class="text-[9px] text-warning flex items-center gap-1">
                <Settings2 class="h-3 w-3" /> Requiere API keys
              </span>
              <span v-else class="text-[9px] text-success flex items-center gap-1">
                <CheckCircle2 class="h-3 w-3" /> Público
              </span>
            </div>

            <!-- Dynamic Data Section -->
            <div class="space-y-1.5 mb-4 min-h-[80px]">
              <!-- BTC ARB -->
              <template v-if="key === 'btc_arb' && scanResult?.result?.btc_arb">
                <div class="flex justify-between text-[11px]">
                  <span class="text-muted-foreground">Movimiento BTC</span>
                  <span
                    class="font-mono font-bold"
                    :class="scanResult.result.btc_arb.direction === 'up' ? 'text-success' : 'text-destructive'"
                  >
                    {{ fmtUSD(scanResult.result.btc_arb.btc_move ?? 0) }}
                  </span>
                </div>
                <div class="flex justify-between text-[11px]">
                  <span class="text-muted-foreground">Dirección</span>
                  <span
                    class="font-mono font-bold"
                    :class="scanResult.result.btc_arb.direction === 'up' ? 'text-success' : 'text-destructive'"
                  >
                    {{ (scanResult.result.btc_arb.direction ?? '—').toUpperCase() }}
                  </span>
                </div>
                <div class="flex justify-between text-[11px]">
                  <span class="text-muted-foreground">Umbral</span>
                  <span class="font-mono">$70</span>
                </div>
                <p class="text-[10px] text-muted-foreground mt-1 leading-tight">
                  {{ scanResult.result.btc_arb.reason || 'Escaneando mercado...' }}
                </p>
              </template>

              <!-- SMART MONEY -->
              <template v-if="key === 'smart_money' && scanResult?.result?.smart_money">
                <div v-if="scanResult.result.smart_money.traders?.length" class="space-y-1">
                  <div
                    v-for="t in scanResult.result.smart_money.traders.slice(0, 3)"
                    :key="t.address"
                    class="flex justify-between text-[10px]"
                  >
                    <span class="text-muted-foreground font-mono">{{ (t.address ?? '').slice(0, 8) }}...</span>
                    <span
                      class="font-mono font-bold"
                      :class="(t.pnl ?? 0) > 0 ? 'text-success' : 'text-destructive'"
                    >
                      {{ fmtUSD(t.pnl ?? 0) }}
                    </span>
                  </div>
                  <p class="text-[10px] text-muted-foreground mt-1">
                    {{ scanResult.result.smart_money.signals?.length || 0 }} señal(es) de copy trade generadas
                  </p>
                </div>
                <div v-else class="flex items-center justify-center h-14">
                  <p class="text-[10px] text-muted-foreground text-center">
                    <Globe class="h-3 w-3 inline mr-1" />
                    Sin traders disponibles. Leaderboard no accesible sin API key.
                  </p>
                </div>
              </template>

              <!-- COMPLETE ARB -->
              <template v-if="key === 'complete_arb' && scanResult?.result?.complete_arb">
                <div v-if="scanResult.result.complete_arb.opportunities?.length" class="space-y-1">
                  <div
                    v-for="op in scanResult.result.complete_arb.opportunities.slice(0, 3)"
                    :key="op.market_id"
                    class="flex justify-between text-[10px]"
                  >
                    <span class="text-muted-foreground truncate max-w-[160px]">{{ op.question?.slice(0, 35) || (op.market_id ?? '').slice(0, 10) }}</span>
                    <span
                      class="font-mono font-bold"
                      :class="op.type === 'overpriced' ? 'text-destructive' : 'text-success'"
                    >
                      {{ op.type === 'overpriced' ? '🔥 ' : '💰 ' }}{{ ((op.spread ?? 0) * 100).toFixed(2) }}%
                    </span>
                  </div>
                </div>
                <div v-else class="flex items-center justify-center h-14">
                  <p class="text-[10px] text-muted-foreground text-center">
                    <BarChart3 class="h-3 w-3 inline mr-1" />
                    Sin oportunidades de arbitraje en este momento.
                  </p>
                </div>
              </template>

              <!-- WEATHER -->
              <template v-if="key === 'weather' && scanResult?.result?.weather">
                <div v-if="scanResult.result.weather.data" class="space-y-1">
                  <div class="flex justify-between text-[11px]">
                    <span class="text-muted-foreground">Temperatura actual</span>
                    <span class="font-mono font-bold text-sky-400">{{ scanResult.result.weather.data.current_temp ?? '—' }}°C</span>
                  </div>
                  <div class="flex justify-between text-[11px]">
                    <span class="text-muted-foreground">Pronóstico máxima</span>
                    <span class="font-mono font-bold">{{ scanResult.result.weather.data.today_max ?? '—' }}°C</span>
                  </div>
                  <p class="text-[10px] text-muted-foreground mt-1">
    Datos de Open-Meteo. Sin API key requerida.
                  </p>
                </div>
                <div v-else class="flex items-center justify-center h-14">
                  <p class="text-[10px] text-muted-foreground text-center">
                    <Cloud class="h-3 w-3 inline mr-1" />
                    No se pudieron obtener datos meteorológicos.
                  </p>
                </div>
              </template>

              <!-- LP MM -->
              <template v-if="key === 'lp_mm' && scanResult?.result?.lp_mm">
                <div class="space-y-1">
                  <div class="flex justify-between text-[11px]">
                    <span class="text-muted-foreground">Órdenes activas</span>
                    <span class="font-mono font-bold">{{ scanResult.result.lp_mm.active_orders ?? 0 }}</span>
                  </div>
                  <p class="text-[10px] text-muted-foreground mt-1 leading-tight">
                    {{ scanResult.result.lp_mm.note || 'Estrategia pasiva: coloca órdenes límite para ganar rewards de liquidez.' }}
                  </p>
                </div>
              </template>

              <!-- No data fallback -->
              <div
                v-if="!scanResult?.result?.[key]"
                class="flex items-center justify-center h-14"
              >
                <Skeleton class="h-3 w-32" />
              </div>
            </div>

            <!-- Card Actions -->
            <div class="flex items-center gap-2 pt-3 border-t border-border/20">
              <Button
                variant="outline"
                size="sm"
                class="flex-1 text-[11px] h-8"
                :loading="scanning[key]"
                @click="scanStrategy(key)"
              >
                <Scan class="h-3.5 w-3.5 mr-1" />
                Escanear
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="text-[11px] h-8"
                @click="openRepo(STRATEGY_DEFS[key].repo)"
              >
                <ExternalLink class="h-3.5 w-3.5 mr-1" />
                Repo
              </Button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ QUICK ACTIONS STRIP ═══ -->
      <div class="flex flex-wrap items-center gap-2 rounded-xl bg-data-grid-subtle border border-border/30 px-4 py-3">
        <span class="font-mono text-[9px] font-bold uppercase tracking-wider text-muted-foreground mr-1">
          <Zap class="h-3 w-3 inline mr-1 text-amber-400" />
          Acciones rápidas
        </span>
        <button
          v-for="key in strategyKeys"
          :key="key"
          @click="scanStrategy(key)"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-foreground/80 hover:text-foreground hover:bg-primary/10 border border-border/30 transition-colors"
        >
          <component :is="STRATEGY_DEFS[key].icon" class="h-3.5 w-3.5" :class="STRATEGY_DEFS[key].accent" />
          {{ STRATEGY_DEFS[key].label.split(' ').slice(0, 2).join(' ') }}
        </button>
        <span class="text-border/50 mx-1">|</span>
        <button
          @click="fetchAll"
          class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10 border border-border/30 transition-colors"
        >
          <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
          Refresh All
        </button>
      </div>

      <!-- ═══ FOOTER — Next Steps ═══ -->
      <Card>
        <div class="p-5">
          <div class="flex items-center gap-2 mb-3">
            <Sparkles class="h-4 w-4 text-primary" />
            <h3 class="text-sm font-semibold">Cómo usar esto</h3>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px]">
            <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
              <p class="font-semibold text-foreground flex items-center gap-1.5">
                <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
                Escaneá
              </p>
              <p class="text-muted-foreground leading-relaxed">
                Cada card muestra datos en vivo sin necesidad de API keys. Usá el botón <strong>Escanear</strong> para refrescar una estrategia individual.
              </p>
            </div>
            <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
              <p class="font-semibold text-foreground flex items-center gap-1.5">
                <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
                Evaluá señales
              </p>
              <p class="text-muted-foreground leading-relaxed">
                Si ves <span class="text-success font-semibold">SEÑAL ACTIVA</span> en BTC Arb o spread % en Complete-Set, hay oportunidad. Revisá los detalles en la card.
              </p>
            </div>
            <div class="space-y-1.5 p-3 rounded-lg bg-accent/20">
              <p class="font-semibold text-foreground flex items-center gap-1.5">
                <span class="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-[10px] font-bold">3</span>
                Ejecutá
              </p>
              <p class="text-muted-foreground leading-relaxed">
                Para ejecutar trades reales, cloná el repo indicado en cada card, configurá tus API keys de Polymarket, y corré el bot localmente.
              </p>
            </div>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>
