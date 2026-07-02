<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import { AlertTriangle, BarChart3, CreditCard, DollarSign, PiggyBank, Plus, RotateCw, Save, TrendingUp, Wallet } from '@lucide/vue'

interface PlatformWithEarnings {
  provider: string
  earned: number
  pending: number
}

interface WalletEntry {
  id: string
  platform: string
  address: string
  label?: string
  is_default: boolean
  network?: string
  currency?: string
}

interface ReportStats {
  total: number
  status_counts: Record<string, number>
  paid_count: number
  total_rewards: number
  estimated_rewards: number
}

interface WalletsData {
  wallets: WalletEntry[]
  stats: ReportStats | null
  platformEarnings: PlatformWithEarnings[]
}

const data = ref<WalletsData | null>(null)
const loading = ref(true)
const error = ref('')
const editingWallet = ref<string | null>(null)
const editAddress = ref('')
const savingAddress = ref(false)

const payoutStatusLabels = computed(() => {
  if (!data.value?.stats?.status_counts) return []
  return Object.keys(data.value.stats.status_counts)
})
const payoutStatusData = computed(() => {
  if (!data.value?.stats?.status_counts) return []
  return Object.values(data.value.stats.status_counts)
})

const earningsByPlatformLabels = computed(() => {
  return data.value?.platformEarnings?.map(p => p.provider) || []
})
const earningsByPlatformData = computed(() => {
  return data.value?.platformEarnings?.map(p => p.earned) || []
})

function platformIcon(platform: string) {
  const p = platform.toLowerCase()
  if (p.includes('bank') || p.includes('banco')) return '🏦'
  if (p.includes('paypal') || p.includes('pay')) return '💳'
  if (p.includes('crypto') || p.includes('wallet')) return '₿'
  return '💰'
}

function startEdit(wallet: WalletEntry) {
  editingWallet.value = wallet.id
  editAddress.value = wallet.address || ''
}

function cancelEdit() {
  editingWallet.value = null
  editAddress.value = ''
}

async function saveAddress(walletId: string) {
  savingAddress.value = true
  try {
    await api.put(`/identity-center/wallets/${walletId}`, { address: editAddress.value })
    if (data.value) {
      const w = data.value.wallets.find(w => w.id === walletId)
      if (w) w.address = editAddress.value
    }
    editingWallet.value = null
  } catch (e: any) {
    alert(e?.message || 'Error al guardar dirección')
  } finally {
    savingAddress.value = false
  }
}

async function fetchWallets() {
  loading.value = true
  error.value = ''
  try {
    const [walletsRes, statsRes, platformsRes] = await Promise.all([
      api.get<{ wallets: WalletEntry[] }>('/identity-center/wallets'),
      api.get<ReportStats>('/reports/stats').catch(() => null),
      api.get<{ accounts: PlatformWithEarnings[] }>('/opportunity_intelligence/identity/accounts').catch(() => null),
    ])
    data.value = {
      wallets: walletsRes.wallets || [],
      stats: statsRes,
      platformEarnings: platformsRes?.accounts?.filter(a => a.earned)?.map(a => ({
        provider: a.provider,
        earned: a.earned || 0,
        pending: a.pending || 0,
      })) || [],
    }
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar billeteras'
  } finally {
    loading.value = false
  }
}

function formatCurrency(n: number) {
  if (!n) return '$0'
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

onMounted(fetchWallets)
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Finanzas</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Wallets</h1>
      <p class="text-sm text-muted-foreground">Gestión de billeteras y pagos</p>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" />
      </div>
      <Skeleton class="h-48 rounded-xl" />
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <!-- Error -->
    <template v-else-if="error && !data">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchWallets">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Empty -->
    <template v-else-if="!data || !data.wallets.length">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Wallet class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin billeteras configuradas</p>
        <p class="mt-1 text-xs text-muted-foreground">Agregá una billetera para comenzar a recibir pagos</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchWallets">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <DollarSign class="h-4 w-4 text-primary" />
            <span class="text-[10px] text-muted-foreground">Total Reportes</span>
          </div>
          <p class="text-xl font-bold text-foreground">{{ data.stats?.total || 0 }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <CreditCard class="h-4 w-4 text-success" />
            <span class="text-[10px] text-muted-foreground">Pagados</span>
          </div>
          <p class="text-xl font-bold text-foreground">{{ data.stats?.paid_count || 0 }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <TrendingUp class="h-4 w-4 text-warning" />
            <span class="text-[10px] text-muted-foreground">Total Earned</span>
          </div>
          <p class="text-xl font-bold text-foreground">{{ formatCurrency(data.stats?.total_rewards || 0) }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-1">
            <PiggyBank class="h-4 w-4 text-accent" />
            <span class="text-[10px] text-muted-foreground">Estimated</span>
          </div>
          <p class="text-xl font-bold text-foreground">{{ formatCurrency(data.stats?.estimated_rewards || 0) }}</p>
        </Card>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <Wallet class="h-4 w-4 text-primary" />
            <p class="text-xs font-semibold text-foreground">Payout Status</p>
          </div>
          <DoughnutChart
            :labels="payoutStatusLabels"
            :data="payoutStatusData"
            :height="220"
          />
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-3">
            <BarChart3 class="h-4 w-4 text-accent" />
            <p class="text-xs font-semibold text-foreground">Earnings por Plataforma</p>
          </div>
          <BarChart
            :labels="earningsByPlatformLabels"
            :datasets="[{ label: 'Earnings', data: earningsByPlatformData, backgroundColor: ['#7c3aed', '#3b82f6', '#22c55e', '#eab308', '#ef4444'] }]"
            :height="220"
            yLabel="USD"
            horizontal
          />
        </Card>
      </div>

      <!-- Wallets List -->
      <div class="space-y-3 animate-in">
        <p class="text-xs font-semibold text-foreground">Billeteras ({{ data.wallets.length }})</p>
        <div class="grid grid-cols-1 gap-3">
          <Card v-for="(wallet, i) in data.wallets" :key="wallet.id" class="p-4 stagger-item" :style="{ '--i': i }">
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-start gap-3 flex-1 min-w-0">
                <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-surface/50 text-lg shrink-0">
                  {{ platformIcon(wallet.platform) }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-semibold text-foreground">{{ wallet.platform }}</p>
                    <Badge v-if="wallet.is_default" variant="success" class="text-[9px]">Default</Badge>
                    <Badge v-if="wallet.network" variant="outline" class="text-[9px]">{{ wallet.network }}</Badge>
                  </div>
                  <div v-if="editingWallet === wallet.id" class="mt-2 flex items-center gap-2">
                    <input
                      v-model="editAddress"
                      type="text"
                      :placeholder="`${wallet.platform} address`"
                      class="flex-1 rounded-lg border border-border/60 bg-surface/50 px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none"
                    />
                    <Button variant="default" size="sm" :disabled="savingAddress" @click="saveAddress(wallet.id)">
                      <Save class="h-3 w-3" />
                    </Button>
                    <Button variant="ghost" size="sm" @click="cancelEdit">Cancel</Button>
                  </div>
                  <p v-else class="text-xs font-mono text-muted-foreground mt-1 truncate">
                    {{ wallet.address || 'Sin dirección configurada' }}
                  </p>
                  <p v-if="wallet.label" class="text-[10px] text-muted-foreground mt-0.5">{{ wallet.label }}</p>
                </div>
              </div>
              <Button v-if="editingWallet !== wallet.id" variant="ghost" size="sm" @click="startEdit(wallet)">
                <Plus class="h-3.5 w-3.5" />
                {{ wallet.address ? 'Edit' : 'Add' }}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
