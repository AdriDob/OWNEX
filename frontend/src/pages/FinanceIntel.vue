<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import { RefreshCw, ArrowUpRight, ArrowDownRight, TrendingUp, DollarSign, Target, Gauge, Lightbulb, ExternalLink } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import GlassCard from '@/components/ui/GlassCard.vue'

interface DolarRate { nombre: string; compra: number | null; venta: number | null; variacion: number | null }
interface Opportunity { title: string; description: string; action: string; priority: string; category: string; roi_estimate: string; risk: string }

interface FinanceData {
  timestamp: string
  patrimonio_total: number
  ingresos_mes: number
  objetivo_libertad: number
  objetivo_progreso: number
  dolares: DolarRate[]
  inflacion: { mensual: number | null } | null
  crypto_precios: Record<string, number>
  crypto_24h: Record<string, number>
  riesgo: { overall: number; label: string }
  oportunidades: Opportunity[]
  health_score: number
}

const loading = ref(true)
const data = ref<FinanceData | null>(null)

async function load() {
  loading.value = true
  try { data.value = await api.get('/api/intel/finance') } catch { /* silent */ }
  finally { loading.value = false }
}
onMounted(load)

function usd(n: number) { return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }) }

function priceStr(sym: string): string {
  if (!data.value) return '—'
  const p = data.value.crypto_precios[sym]
  if (p === undefined) return '—'
  return p < 1 ? p.toFixed(4) : p.toFixed(0)
}

function changeStr(sym: string): { text: string; color: string; icon: any } | null {
  if (!data.value) return null
  const ch = data.value.crypto_24h[sym]
  if (ch === undefined) return null
  return { text: `${ch >= 0 ? '+' : ''}${ch.toFixed(1)}%`, color: ch >= 0 ? 'text-green-400' : 'text-red-400', icon: ch >= 0 ? ArrowUpRight : ArrowDownRight }
}

const healthEmoji = (h: number) => h >= 80 ? '🟢' : h >= 50 ? '🟡' : '🔴'
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6 space-y-5 animate-in">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/20">
          <TrendingUp class="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">Finance Intel</h1>
          <p class="text-xs text-muted-foreground">Tu situación al instante</p>
        </div>
      </div>
      <Button variant="outline" size="sm" @click="load" :disabled="loading">
        <RefreshCw class="w-3.5 h-3.5 mr-1.5" :class="{ 'animate-spin': loading }" />
        Actualizar
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="loading && !data" class="flex items-center justify-center py-24 text-muted-foreground gap-2">
      <div class="w-4 h-4 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin" />
      <span class="text-sm">Cargando...</span>
    </div>

    <template v-if="data">
      <!-- KPI row -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <GlassCard class="p-4">
          <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Patrimonio</p>
          <p class="text-xl font-bold mt-1">{{ usd(data.patrimonio_total) }}</p>
        </GlassCard>
        <GlassCard class="p-4">
          <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Ingresos/mes</p>
          <p class="text-xl font-bold mt-1">{{ usd(data.ingresos_mes) }}</p>
        </GlassCard>
        <GlassCard class="p-4">
          <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Objetivo</p>
          <div class="flex items-center gap-2 mt-1">
            <p class="text-xl font-bold">{{ data.objetivo_progreso.toFixed(0) }}%</p>
            <div class="flex-1 bg-muted/30 rounded-full h-1.5">
              <div class="bg-purple-400 h-1.5 rounded-full transition-all" :style="{ width: data.objetivo_progreso + '%' }" />
            </div>
          </div>
        </GlassCard>
        <GlassCard class="p-4">
          <p class="text-[10px] text-muted-foreground uppercase tracking-wider">Riesgo</p>
          <p class="text-xl font-bold mt-1" :class="data.riesgo.overall <= 25 ? 'text-green-400' : data.riesgo.overall <= 50 ? 'text-yellow-400' : data.riesgo.overall <= 75 ? 'text-orange-400' : 'text-red-400'">{{ data.riesgo.label }}</p>
        </GlassCard>
      </div>

      <!-- Hoy + Acciones side by side -->
      <div class="grid lg:grid-cols-2 gap-5">
        <!-- HOY -->
        <GlassCard class="p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Hoy</h2>
          <div class="space-y-2">
            <div v-for="d in data.dolares" :key="d.nombre" class="flex items-center justify-between p-2 rounded-lg bg-muted/20 border text-sm">
              <span class="capitalize font-medium">{{ d.nombre }}</span>
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold">{{ d.venta?.toFixed(1) ?? '—' }}</span>
                <span v-if="d.variacion !== null" class="text-xs" :class="d.variacion >= 0 ? 'text-green-400' : 'text-red-400'">
                  {{ d.variacion >= 0 ? '+' : '' }}{{ d.variacion.toFixed(2) }}
                </span>
              </div>
            </div>
            <div v-for="(val, sym) in { btc: 'BTC', eth: 'ETH', sol: 'SOL' }" :key="sym" class="flex items-center justify-between p-2 rounded-lg bg-muted/20 border text-sm">
              <span class="font-medium">{{ val }}</span>
              <div class="flex items-center gap-2">
                <span class="font-mono font-bold">${{ priceStr(sym) }}</span>
                <span v-if="changeStr(sym)" class="flex items-center text-xs" :class="changeStr(sym)!.color">
                  <component :is="changeStr(sym)!.icon" class="w-3 h-3" />
                  {{ changeStr(sym)!.text }}
                </span>
              </div>
            </div>
            <div class="flex items-center justify-between p-2 rounded-lg bg-muted/20 border text-sm">
              <span class="font-medium">Inflación</span>
              <span class="font-mono font-bold">{{ data.inflacion?.mensual != null ? data.inflacion.mensual.toFixed(1) + '%' : '—' }}</span>
            </div>
          </div>
          <p class="text-[10px] text-muted-foreground mt-2">Fuentes: dolarapi.com · CoinGecko · INDEC</p>
        </GlassCard>

        <!-- ACCIONES -->
        <GlassCard class="p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Acciones</h2>
          <div v-if="data.oportunidades.length" class="space-y-2">
            <div v-for="op in data.oportunidades" :key="op.title"
              class="p-3 rounded-lg border transition-all hover:border-foreground/20"
              :class="op.priority === 'alta' ? 'bg-amber-500/5 border-amber-500/20' : 'bg-card'">
              <div class="flex items-start gap-2.5">
                <div class="p-1 rounded-lg shrink-0 mt-0.5"
                  :class="op.priority === 'alta' ? 'bg-amber-500/10' : op.priority === 'info' ? 'bg-gray-500/10' : 'bg-blue-500/10'">
                  <Lightbulb v-if="op.priority === 'alta'" class="w-3.5 h-3.5 text-amber-400" />
                  <TrendingUp v-else class="w-3.5 h-3.5 text-blue-400" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-0.5">
                    <span class="font-semibold text-sm">{{ op.title }}</span>
                    <Badge variant="outline" class="text-[10px]">{{ op.category }}</Badge>
                  </div>
                  <p class="text-xs text-muted-foreground">{{ op.description }}</p>
                  <div class="mt-2">
                    <span class="text-xs font-medium text-blue-400">{{ op.action }}</span>
                    <span v-if="op.roi_estimate !== '—'" class="text-xs text-emerald-400 ml-2">· {{ op.roi_estimate }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-muted-foreground py-4 text-center">Sin acciones destacadas</p>
        </GlassCard>
      </div>

      <!-- Health -->
      <GlassCard class="p-3">
        <div class="flex items-center justify-between text-sm">
          <span class="text-muted-foreground">Sistema financiero</span>
          <span>{{ healthEmoji(data.health_score) }} {{ data.health_score }}/100</span>
        </div>
      </GlassCard>
    </template>
  </div>
</template>
