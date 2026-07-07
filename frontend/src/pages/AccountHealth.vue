<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Activity, AlertTriangle, CheckCircle2, Clock, XCircle,
  RefreshCw, Cable, Globe, Bitcoin, Shield, Database,
} from '@lucide/vue'

interface HealthEntry {
  id: string
  type: 'platform' | 'crypto'
  label: string
  connected: boolean | string
  health?: string
  has_credentials?: boolean
  last_checked?: string
  total_usd?: number
  last_sync?: string
  consecutive_failures?: number
}

interface HubData {
  accounts: HealthEntry[]
  summary: {
    total_platforms: number
    connected_platforms: number
    total_wallets: number
    crypto_total_usd: number
    verified_balance: number
    pending_balance: number
  }
}

interface SyncEvent {
  id: string
  source: string
  status: string
  timestamp: string
  duration?: number
  error?: string
}

const data = ref<HubData | null>(null)
const syncHistory = ref<SyncEvent[]>([])
const loading = ref(true)
const error = ref('')
const syncing = ref<string | null>(null)

const accounts = computed(() => data.value?.accounts || [])
const platforms = computed(() => accounts.value.filter(a => a.type === 'platform'))
const wallets = computed(() => accounts.value.filter(a => a.type === 'crypto'))

const healthScore = computed(() => {
  const all = accounts.value
  if (all.length === 0) return 100
  const healthy = all.filter(a => {
    if (a.type === 'platform') return a.connected === true && (!a.health || a.health === 'healthy')
    return a.connected === 'connected' && (!a.health || a.health === 'healthy')
  }).length
  return Math.round((healthy / all.length) * 100)
})

const overallHealth = computed(() => {
  if (healthScore.value >= 80) return { label: 'Healthy', color: 'text-success', bg: 'bg-success/10 border-success/30', icon: CheckCircle2 }
  if (healthScore.value >= 40) return { label: 'Degraded', color: 'text-warning', bg: 'bg-warning/10 border-warning/30', icon: AlertTriangle }
  return { label: 'Critical', color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30', icon: XCircle }
})

const lastSyncTime = computed(() => {
  const timestamps = accounts.value
    .map(a => a.last_sync || a.last_checked)
    .filter(Boolean)
    .sort()
    .reverse()
  return timestamps[0] || null
})

const totalPlatforms = computed(() => data.value?.summary?.total_platforms || platforms.value.length || 5)
const connectedPlatforms = computed(() => data.value?.summary?.connected_platforms || platforms.value.filter(a => a.connected === true).length)
const totalWallets = computed(() => data.value?.summary?.total_wallets || wallets.value.length)

function isConnected(entry: HealthEntry): boolean {
  if (entry.type === 'platform') return entry.connected === true
  return entry.connected === 'connected'
}

function connectionBadge(entry: HealthEntry): string {
  if (isConnected(entry)) return 'Connected'
  if (entry.type === 'crypto') {
    if (entry.connected === 'unconfigured') return 'Unconfigured'
    if (entry.connected === 'error') return 'Error'
    if (entry.connected === 'rate_limited') return 'Rate Limited'
  }
  return 'Disconnected'
}

function statusVariant(entry: HealthEntry): 'success' | 'warning' | 'destructive' | 'outline' {
  if (isConnected(entry)) return 'success'
  if (entry.type === 'crypto' && entry.connected === 'unconfigured') return 'outline'
  return 'destructive'
}

function healthIndicator(entry: HealthEntry): { label: string; color: string; icon: any } {
  if (entry.health === 'healthy' || (isConnected(entry) && !entry.health)) {
    return { label: 'Healthy', color: 'text-success', icon: CheckCircle2 }
  }
  if (entry.health === 'degraded' || (entry.consecutive_failures && entry.consecutive_failures > 0)) {
    return { label: 'Degraded', color: 'text-warning', icon: AlertTriangle }
  }
  return { label: 'Error', color: 'text-destructive', icon: XCircle }
}

function chainIcon(chain: string) {
  if (chain.includes('ethereum') || chain.includes('evm')) return '⟠'
  if (chain.includes('bitcoin')) return '₿'
  if (chain.includes('exchange')) return '🏛'
  if (chain.includes('solana')) return '◎'
  if (chain.includes('tron')) return '◈'
  return '⛓'
}

function formatUSD(n: number): string {
  if (!n) return '$0.00'
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatTime(ts: string | number | null | undefined): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-AR')
}

async function fetchHub() {
  loading.value = true
  error.value = ''
  try {
    const [statusRes, historyRes] = await Promise.all([
      api.get<any>('/accounts-hub/status'),
      api.get<any[]>('/accounts-hub/sync-history'),
    ])
    data.value = {
      accounts: statusRes.accounts || [],
      summary: statusRes.summary || {},
    }
    syncHistory.value = (historyRes || []).slice(0, 10)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar health de cuentas'
  } finally {
    loading.value = false
  }
}

async function syncPlatform(platformId: string) {
  syncing.value = platformId
  try {
    await api.post(`/connections/sync/${platformId}`)
    await fetchHub()
  } catch { /* ignore */ }
  finally { syncing.value = null }
}

async function syncWallet(walletId: string) {
  syncing.value = walletId
  try {
    await api.post(`/crypto/wallets/${walletId}/sync`)
    await fetchHub()
  } catch { /* ignore */ }
  finally { syncing.value = null }
}

onMounted(fetchHub)
</script>

<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Activity class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">ACCOUNT HEALTH</span>
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Account Health</h1>
        <p class="text-xs text-muted-foreground">Estado de todas las conexiones del sistema</p>
      </div>
      <div
        v-if="!loading && data"
        class="flex items-center gap-2 rounded-xl border px-3 py-2"
        :class="overallHealth.bg"
      >
        <component :is="overallHealth.icon" class="h-4 w-4" :class="overallHealth.color" />
        <span class="font-mono text-xs font-semibold" :class="overallHealth.color">
          {{ overallHealth.label }}
        </span>
        <span class="font-mono text-[10px]" :class="overallHealth.color">
          {{ healthScore }}%
        </span>
      </div>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <!-- Error -->
    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchHub">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="data">
      <!-- Health Overview Cards -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-primary tracking-wider">Platforms</p>
          <p class="font-display text-xl font-bold text-foreground">
            {{ connectedPlatforms }}<span class="text-sm text-muted-foreground">/{{ totalPlatforms }}</span>
          </p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-primary tracking-wider">Wallets</p>
          <p class="font-display text-xl font-bold text-foreground">{{ totalWallets }}</p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-muted-foreground tracking-wider">Last Sync</p>
          <p class="font-mono text-xs font-bold text-foreground mt-1">{{ formatTime(lastSyncTime) }}</p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-muted-foreground tracking-wider">Health Score</p>
          <p class="font-display text-xl font-bold" :class="overallHealth.color">{{ healthScore }}%</p>
        </Card>
      </div>

      <!-- Platform Health Table -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <p class="font-mono text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Globe class="h-3.5 w-3.5 text-primary" />
            Platform Health
          </p>
          <span class="font-mono text-[9px] text-muted-foreground">
            {{ connectedPlatforms }}/{{ totalPlatforms }} connected
          </span>
        </div>
        <div v-if="platforms.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-6 text-center">
          <Cable class="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
          <p class="font-mono text-xs text-muted-foreground">No platforms configured</p>
        </div>
        <div v-for="p in platforms" :key="p.id" class="rounded-xl border border-border/30 bg-surface/20 p-3 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <component :is="healthIndicator(p).icon" class="h-3.5 w-3.5" :class="healthIndicator(p).color" />
              <span class="font-mono text-xs font-medium text-foreground">{{ p.label }}</span>
            </div>
            <div class="flex items-center gap-2">
              <Badge :variant="statusVariant(p)" class="text-[9px]">{{ connectionBadge(p) }}</Badge>
              <Button variant="ghost" size="sm" :disabled="syncing === p.id" @click="syncPlatform(p.id)">
                <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': syncing === p.id }" />
              </Button>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="font-mono text-[9px]" :class="healthIndicator(p).color">
                {{ healthIndicator(p).label }}
              </span>
              <span class="font-mono text-[9px] text-muted-foreground">
                Last sync: {{ formatTime(p.last_sync || p.last_checked) }}
              </span>
            </div>
          </div>
          <!-- Degradation visualization -->
          <div v-if="p.consecutive_failures && p.consecutive_failures > 0" class="space-y-1">
            <div class="flex items-center gap-1.5">
              <XCircle class="h-3 w-3 text-destructive" />
              <span class="font-mono text-[9px] text-destructive font-semibold">
                {{ p.consecutive_failures }} consecutive failure{{ p.consecutive_failures > 1 ? 's' : '' }}
              </span>
            </div>
            <div class="h-2 rounded-full bg-destructive/20 overflow-hidden">
              <div
                class="h-full rounded-full bg-destructive transition-all duration-500"
                :style="{ width: Math.min((p.consecutive_failures / 10) * 100, 100) + '%' }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Wallet Health Table -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <p class="font-mono text-xs font-semibold text-foreground flex items-center gap-1.5">
            <Bitcoin class="h-3.5 w-3.5 text-primary" />
            Wallet Health
          </p>
          <span class="font-mono text-[9px] text-muted-foreground">
            {{ data.summary.crypto_total_usd ? formatUSD(data.summary.crypto_total_usd) : '' }}
          </span>
        </div>
        <div v-if="wallets.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-6 text-center">
          <Bitcoin class="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
          <p class="font-mono text-xs text-muted-foreground">No wallets configured</p>
        </div>
        <div v-for="w in wallets" :key="w.id" class="rounded-xl border border-border/30 bg-surface/20 p-3 space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-lg">{{ chainIcon(w.id) }}</span>
              <div>
                <p class="font-mono text-xs font-medium text-foreground">{{ w.id }}</p>
                <p class="font-mono text-[9px]" :class="healthIndicator(w).color">{{ healthIndicator(w).label }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-mono text-xs font-bold text-foreground">{{ formatUSD(w.total_usd || 0) }}</span>
              <Badge :variant="statusVariant(w)" class="text-[9px]">{{ connectionBadge(w) }}</Badge>
              <Button variant="ghost" size="sm" :disabled="syncing === w.id" @click="syncWallet(w.id)">
                <RefreshCw class="h-3 w-3" :class="{ 'animate-spin': syncing === w.id }" />
              </Button>
            </div>
          </div>
          <div class="flex items-center justify-between">
            <span class="font-mono text-[9px] text-muted-foreground">
              Last sync: {{ formatTime(w.last_sync) }}
            </span>
          </div>
          <!-- Degradation visualization -->
          <div v-if="w.consecutive_failures && w.consecutive_failures > 0" class="space-y-1">
            <div class="flex items-center gap-1.5">
              <XCircle class="h-3 w-3 text-destructive" />
              <span class="font-mono text-[9px] text-destructive font-semibold">
                {{ w.consecutive_failures }} consecutive failure{{ w.consecutive_failures > 1 ? 's' : '' }}
              </span>
            </div>
            <div class="h-2 rounded-full bg-destructive/20 overflow-hidden">
              <div
                class="h-full rounded-full bg-destructive transition-all duration-500"
                :style="{ width: Math.min((w.consecutive_failures / 10) * 100, 100) + '%' }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Sync History Timeline -->
      <div class="space-y-3">
        <p class="font-mono text-xs font-semibold text-foreground flex items-center gap-1.5">
          <Database class="h-3.5 w-3.5 text-primary" />
          Sync History
        </p>
        <div v-if="syncHistory.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-6 text-center">
          <Clock class="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
          <p class="font-mono text-xs text-muted-foreground">No sync history available</p>
        </div>
        <div v-else class="rounded-xl border border-border/30 bg-surface/20 divide-y divide-border/20 overflow-hidden">
          <div
            v-for="(ev, i) in syncHistory"
            :key="ev.id || i"
            class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface/10 transition-colors"
          >
            <div class="flex h-7 w-7 items-center justify-center rounded-full shrink-0"
              :class="ev.status === 'success' ? 'bg-success/10' : 'bg-destructive/10'"
            >
              <CheckCircle2 v-if="ev.status === 'success'" class="h-3.5 w-3.5 text-success" />
              <XCircle v-else class="h-3.5 w-3.5 text-destructive" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-medium text-foreground truncate">{{ ev.source }}</span>
                <Badge
                  :variant="ev.status === 'success' ? 'success' : 'destructive'"
                  class="text-[8px]"
                >
                  {{ ev.status }}
                </Badge>
              </div>
              <p v-if="ev.error" class="font-mono text-[9px] text-destructive/80 truncate mt-0.5">{{ ev.error }}</p>
            </div>
            <div class="text-right shrink-0">
              <p class="font-mono text-[10px] text-muted-foreground">{{ formatTime(ev.timestamp) }}</p>
              <p v-if="ev.duration" class="font-mono text-[9px] text-muted-foreground/60">{{ ev.duration }}ms</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
