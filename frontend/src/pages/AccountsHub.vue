<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  AlertTriangle, Banknote, Bitcoin, Cable, CheckCircle2,
  ExternalLink, Globe, Link2, Loader2, RefreshCw, RotateCw,
} from '@lucide/vue'

interface AccountEntry {
  id: string
  type: 'platform' | 'crypto'
  label: string
  connected: boolean | string
  health?: string
  has_credentials?: boolean
  last_checked?: string
  total_usd?: number
  last_sync?: string
}

interface HubData {
  accounts: AccountEntry[]
  summary: {
    total_platforms: number
    connected_platforms: number
    total_wallets: number
    crypto_total_usd: number
    verified_balance: number
    pending_balance: number
  }
}

const data = ref<HubData | null>(null)
const loading = ref(true)
const error = ref('')
const syncing = ref<string | null>(null)

const accounts = computed(() => data.value?.accounts || [])
const platforms = computed(() => accounts.value.filter(a => a.type === 'platform'))
const wallets = computed(() => accounts.value.filter(a => a.type === 'crypto'))

function isConnected(entry: AccountEntry): boolean {
  if (entry.type === 'platform') return entry.connected === true
  return entry.connected === 'connected'
}

function statusColor(entry: AccountEntry): string {
  if (isConnected(entry)) return 'text-success'
  if (entry.type === 'crypto' && entry.connected === 'unconfigured') return 'text-muted-foreground/50'
  return 'text-destructive'
}

function connectionBadge(entry: AccountEntry): string {
  if (isConnected(entry)) return 'Conectado'
  if (entry.type === 'crypto') {
    if (entry.connected === 'unconfigured') return 'Sin configurar'
    if (entry.connected === 'error') return 'Error'
    if (entry.connected === 'rate_limited') return 'Limitado'
  }
  return 'Desconectado'
}

function chainIcon(chain: string) {
  if (chain.includes('ethereum') || chain.includes('evm')) return '⟠'
  if (chain.includes('bitcoin')) return '₿'
  if (chain.includes('exchange')) return '🏛'
  return '⛓'
}

async function fetchHub() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<any>('/accounts-hub/status')
    data.value = {
      accounts: res.accounts || [],
      summary: res.summary || {},
    }
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar cuentas'
  } finally {
    loading.value = false
  }
}

async function syncWallet(walletId: string) {
  syncing.value = walletId
  try {
    await api.post(`/crypto/wallets/${walletId}/sync`)
    await fetchHub()
  } catch (e: any) {
    console.error('Sync failed:', e)
  } finally {
    syncing.value = null
  }
}

async function syncAll() {
  syncing.value = 'all'
  try {
    await api.post('/crypto/sync-all')
    await fetchHub()
  } catch (e: any) {
    console.error('Sync all failed:', e)
  } finally {
    syncing.value = null
  }
}

function formatUSD(n: number): string {
  if (!n) return '$0.00'
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

onMounted(fetchHub)
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <Cable class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">ACCOUNTS HUB</span>
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Accounts Hub</h1>
        <p class="text-xs text-muted-foreground">Central de cuentas — plataformas, wallets y conexiones</p>
      </div>
      <Button variant="outline" size="sm" :disabled="syncing === 'all'" @click="syncAll">
        <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': syncing === 'all' }" />
        Sync All
      </Button>
    </div>

    <template v-if="loading">
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm font-semibold text-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchHub">
          <RotateCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="data">
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-success tracking-wider">Verificado</p>
          <p class="font-display text-xl font-bold text-foreground">{{ formatUSD(data.summary.verified_balance) }}</p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-warning tracking-wider">Pendiente</p>
          <p class="font-display text-xl font-bold text-foreground">{{ formatUSD(data.summary.pending_balance) }}</p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-primary tracking-wider">Crypto</p>
          <p class="font-display text-xl font-bold text-foreground">{{ formatUSD(data.summary.crypto_total_usd) }}</p>
        </Card>
        <Card class="p-4">
          <p class="font-mono text-[9px] uppercase text-muted-foreground tracking-wider">Retirado</p>
          <p class="font-display text-xl font-bold text-foreground">{{ formatUSD(data.summary.withdrawn_total || 0) }}</p>
        </Card>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="font-mono text-xs font-semibold text-foreground">
              <Globe class="h-3.5 w-3.5 inline mr-1" />
              Plataformas ({{ platforms.length }})
            </p>
            <span class="font-mono text-[9px] text-muted-foreground">
              {{ data.summary.connected_platforms }}/{{ data.summary.total_platforms }} conectadas
            </span>
          </div>
          <div v-if="platforms.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-6 text-center">
            <Link2 class="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
            <p class="font-mono text-xs text-muted-foreground">Sin plataformas conectadas</p>
          </div>
          <div v-for="p in platforms" :key="p.id" class="rounded-xl border border-border/30 bg-surface/20 p-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="h-2 w-2 rounded-full" :class="isConnected(p) ? 'bg-success' : 'bg-muted'" />
                <span class="font-mono text-xs font-medium text-foreground">{{ p.label }}</span>
              </div>
              <Badge :variant="isConnected(p) ? 'success' : 'outline'" class="text-[9px]">
                {{ connectionBadge(p) }}
              </Badge>
            </div>
            <p v-if="p.last_checked" class="mt-1 font-mono text-[9px] text-muted-foreground">
              Último check: {{ new Date(p.last_checked).toLocaleString('es-AR') }}
            </p>
          </div>
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="font-mono text-xs font-semibold text-foreground">
              <Bitcoin class="h-3.5 w-3.5 inline mr-1" />
              Crypto Wallets ({{ wallets.length }})
            </p>
            <span class="font-mono text-[9px] text-primary">{{ formatUSD(data.summary.crypto_total_usd) }}</span>
          </div>
          <div v-if="wallets.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-6 text-center">
            <Bitcoin class="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
            <p class="font-mono text-xs text-muted-foreground">Sin wallets conectadas — agregá wallets crypto en Conexiones</p>
          </div>
          <div v-for="w in wallets" :key="w.id" class="rounded-xl border border-border/30 bg-surface/20 p-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-lg">{{ chainIcon(w.id) }}</span>
                <div>
                  <p class="font-mono text-xs font-medium text-foreground">{{ w.id }}</p>
                  <p class="font-mono text-[9px]" :class="statusColor(w)">{{ connectionBadge(w) }}</p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-bold text-foreground">{{ formatUSD(w.total_usd || 0) }}</span>
                <Button variant="ghost" size="sm" :disabled="syncing === w.id" @click="syncWallet(w.id)">
                  <Loader2 v-if="syncing === w.id" class="h-3 w-3 animate-spin" />
                  <RefreshCw v-else class="h-3 w-3" />
                </Button>
              </div>
            </div>
            <p v-if="w.last_sync" class="mt-1 font-mono text-[9px] text-muted-foreground">
              Último sync: {{ new Date(w.last_sync).toLocaleString('es-AR') }}
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
