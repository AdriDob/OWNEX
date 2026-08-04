<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import type { PlatformAccount, PayoutAccount, Withdrawal, SubmissionRecord } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Globe, Unlink, Link, Banknote, Wallet, History, CheckCircle2,
  XCircle, Clock, DollarSign, ExternalLink, RefreshCw, Plus,
  ArrowRight, Building2, CreditCard, AlertTriangle, Trash2,
  Coins, ChevronDown, ChevronUp, Loader2, Info, Scan, Settings,
} from '@lucide/vue'

const loading = ref(true)
const error = ref<string | null>(null)
const accounts = ref<PlatformAccount[]>([])
const payoutAccounts = ref<PayoutAccount[]>([])
const submissions = ref<SubmissionRecord[]>([])
const withdrawals = ref<Withdrawal[]>([])
const syncing = ref(false)
const syncingPlatform = ref<string | null>(null)
const syncError = ref<string | null>(null)
const lastSyncAll = ref<string | null>(null)

// ── Platform connect wizard ──
const showConnectForm = ref<string | null>(null)
const connectEmail = ref('')
const connectToken = ref('')
const connectPassword = ref('')
const connectUsername = ref('')
const showPlatformWizard = ref(false)
const platformWizardStep = ref(1)
const newPlatform = ref({ provider: '', email: '', token: '', password: '', username: '' })
const platformSaving = ref(false)
const platformError = ref('')
const platformSuccess = ref('')

// ── Payout recommendations ──
const payoutMethods = ref<any[]>([])
const platformPayouts = ref<Record<string, any>>({})
const expandedPlatformPayout = ref<string | null>(null)
const showPayoutGuide = ref(false)

const methodTypeIcon: Record<string, string> = {
  crypto: 'text-warning',
  wallet: 'text-primary',
  bank: 'text-accent',
  p2p: 'text-success',
}

const methodTypeLabel: Record<string, string> = {
  crypto: 'Crypto',
  wallet: 'Billetera virtual',
  bank: 'Transferencia bancaria',
  p2p: 'P2P Exchange',
}

async function loadPayoutRecommendations() {
  try {
    const res = await api.get<{ methods: any[] }>('/connections/payout-recommendations')
    payoutMethods.value = res.methods || []
  } catch { /* optional */ }
}

async function loadPlatformPayout(platformId: string) {
  if (platformPayouts.value[platformId]) return
  try {
    const res = await api.get<any>(`/connections/payout-recommendations/${platformId}`)
    platformPayouts.value[platformId] = res
  } catch { /* optional */ }
}

// ── Payout account wizard ──
const showPayoutWizard = ref(false)
const payoutStep = ref(1)
const payoutType = ref<'bank' | 'crypto' | 'paypal'>('bank')
const newPayout = ref({
  label: '',
  type: 'bank',
  address: '',
  network: '',
  currency: 'USD',
  bank_name: '',
  last_four: '',
  is_default: false,
})
const payoutSaving = ref(false)
const payoutError = ref('')
const payoutSuccess = ref('')

const platformMeta: Record<string, { color: string; bg: string }> = {
  hackerone: { color: 'text-success', bg: 'bg-success/10' },
  bugcrowd: { color: 'text-warning', bg: 'bg-warning/10' },
  intigriti: { color: 'text-intigriti', bg: 'bg-intigriti/10' },
  synack: { color: 'text-primary', bg: 'bg-primary/10' },
  yeswehack: { color: 'text-destructive', bg: 'bg-destructive/10' },
  immunefi: { color: 'text-muted-foreground', bg: 'bg-muted/10' },
  code4rena: { color: 'text-warning', bg: 'bg-warning/10' },
  huntr: { color: 'text-intigriti', bg: 'bg-intigriti/10' },
}

const statusColor = (s: string) => {
  if (s === 'paid' || s === 'completed') return 'success'
  if (s === 'submitted' || s === 'processing') return 'info'
  if (s === 'pending') return 'warning'
  if (s === 'rejected' || s === 'failed') return 'destructive'
  return 'default'
}

const definitions = ref<{ platforms: { id: string; name: string }[]; osint_services: { id: string; name: string }[] }>({ platforms: [], osint_services: [] })
const allPlatforms = computed(() => definitions.value.platforms.map(p => p.name))

const connectedProvs = computed(() => accounts.value.map(a => a.provider.toLowerCase()))

function platformIcon(provider: string) {
  return platformMeta[provider.toLowerCase()]?.color || 'text-muted-foreground'
}

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const [acctRes, payoutRes, subRes, wdRes, defRes] = await Promise.allSettled([
      api.get<{ accounts: PlatformAccount[] }>('/opportunity/identity/accounts'),
      api.get<{ accounts: PayoutAccount[] }>('/connections/payout-accounts'),
      api.get<{ submissions: SubmissionRecord[]; total: number }>('/reports/submissions', { limit: 20 }),
      api.get<{ withdrawals: Withdrawal[] }>('/connections/withdrawals'),
      api.get<{ platforms: { id: string; name: string }[]; osint_services: { id: string; name: string }[] }>('/system/definitions'),
    ])
    if (acctRes.status === 'fulfilled') accounts.value = acctRes.value.accounts || []
    if (payoutRes.status === 'fulfilled') payoutAccounts.value = payoutRes.value.accounts || []
    if (subRes.status === 'fulfilled') submissions.value = subRes.value.submissions || []
    if (wdRes.status === 'fulfilled') withdrawals.value = wdRes.value.withdrawals || []
    if (defRes.status === 'fulfilled') definitions.value = defRes.value
  } catch (e: any) { error.value = e?.message || 'Error al cargar conexiones' }
  finally { loading.value = false }
}

async function syncAll() {
  syncing.value = true
  syncError.value = null
  try {
    await api.post('/connections/sync-all', {})
    await loadData()
    lastSyncAll.value = new Date().toISOString()
  } catch (e: any) {
    syncError.value = e?.message || 'Error al sincronizar plataformas'
  } finally {
    syncing.value = false
  }
}

async function syncPlatform(provider: string) {
  syncingPlatform.value = provider
  try {
    await api.post(`/connections/sync/${provider}`, {})
    await loadData()
  } catch { /* per-platform sync error handled silently */ }
  finally { syncingPlatform.value = null }
}

onMounted(() => {
  loadData()
  loadPayoutRecommendations()
})

// ── Connect platform (simple inline form) ──
async function connectPlatform(provider: string) {
  if (!connectEmail.value || !connectToken.value) return
  try {
    await api.post('/opportunity/identity/store', {
      provider, email: connectEmail.value, token: connectToken.value,
    })
    showConnectForm.value = null
    connectEmail.value = ''
    connectToken.value = ''
    const res = await api.get<{ accounts: PlatformAccount[] }>('/opportunity/identity/accounts')
    accounts.value = res.accounts || []
  } catch { /* ignore */ }
}

async function disconnectPlatform(provider: string) {
  try {
    await api.post(`/opportunity/identity/remove/${provider}`, {})
    accounts.value = accounts.value.filter((a: any) => a.provider !== provider)
  } catch { /* ignore */ }
}

// ── Full platform registration wizard ──
function openPlatformWizard() {
  newPlatform.value = { provider: '', email: '', token: '', password: '', username: '' }
  platformWizardStep.value = 1
  platformError.value = ''
  platformSuccess.value = ''
  showPlatformWizard.value = true
}

async function savePlatformRegistration() {
  const p = newPlatform.value
  if (!p.provider || !p.email) {
    platformError.value = 'Proveedor y email son requeridos'
    return
  }
  platformSaving.value = true
  platformError.value = ''
  platformSuccess.value = ''
  try {
    await api.post('/connections/platforms', {
      provider: p.provider,
      email: p.email,
      username: p.username,
      token: p.token,
      password: p.password,
    })
    if (p.token) {
      await api.post('/opportunity/identity/store', {
        provider: p.provider, email: p.email, token: p.token,
      })
    }
    platformSuccess.value = `${p.provider} registrada correctamente`
    setTimeout(() => { showPlatformWizard.value = false }, 1500)
    await loadData()
  } catch (e: any) {
    platformError.value = e.message || 'Error al registrar plataforma'
  } finally {
    platformSaving.value = false
  }
}

// ── Payout account wizard ──
function openPayoutWizard(type: 'bank' | 'crypto' | 'paypal') {
  payoutType.value = type
  payoutStep.value = 1
  payoutError.value = ''
  payoutSuccess.value = ''
  newPayout.value = {
    label: '',
    type: type,
    address: '',
    network: '',
    currency: type === 'crypto' ? 'USDC' : 'USD',
    bank_name: '',
    last_four: '',
    is_default: payoutAccounts.value.length === 0,
  }
  showPayoutWizard.value = true
}

async function savePayoutAccount() {
  const p = newPayout.value
  if (!p.label || !p.address) {
    payoutError.value = 'Nombre y dirección son requeridos'
    return
  }
  payoutSaving.value = true
  payoutError.value = ''
  payoutSuccess.value = ''
  try {
    await api.post('/connections/payout-accounts', {
      label: p.label,
      type: p.type,
      address: p.address,
      network: p.network || undefined,
      currency: p.currency,
      bank_name: p.bank_name || undefined,
      last_four: p.last_four || undefined,
      is_default: p.is_default,
    })
    payoutSuccess.value = 'Cuenta registrada correctamente'
    setTimeout(() => { showPayoutWizard.value = false }, 1500)
    await loadData()
  } catch (e: any) {
    payoutError.value = e.message || 'Error al registrar cuenta'
  } finally {
    payoutSaving.value = false
  }
}

async function removePayoutAccount(id: string) {
  try {
    await api.delete(`/connections/payout-accounts/${id}`)
    payoutAccounts.value = payoutAccounts.value.filter((a: any) => a.id !== id)
  } catch { /* ignore */ }
}

function formatMoney(n: number | null | undefined) {
  if (!n) return '—'
  return '$' + n.toLocaleString()
}
</script>

<template>
  <div class="space-y-6">
    <template v-if="loading">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <div class="grid grid-cols-2 gap-4"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div>
        <Skeleton class="h-48 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="loadData">Reintentar</Button>
      </div>
    </template>

    <template v-else>
      <!-- Header -->
      <div class="animate-in flex items-end justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Integraciones</p>
          <h1 class="font-display text-2xl font-bold text-foreground">Conexiones</h1>
          <p class="text-xs text-muted-foreground">Gestioná plataformas bug bounty, cuentas de cobro y registrá nuevas integraciones</p>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="lastSyncAll" class="text-[9px] text-muted-foreground/60">Última sync: {{ new Date(lastSyncAll).toLocaleTimeString() }}</span>
          <div v-if="syncError" class="text-[9px] text-destructive">{{ syncError }}</div>
          <Button
            variant="outline"
            size="sm"
            :disabled="syncing"
            @click="syncAll"
            class="flex items-center gap-1"
          >
            <RefreshCw :class="['h-3 w-3', syncing ? 'animate-spin' : '']" />
            {{ syncing ? 'Sincronizando...' : 'Sync All' }}
          </Button>
        </div>
      </div>

      <!-- Connection Status Chart -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Estado de Conexiones</h3>
        <DoughnutChart
          :labels="['Conectadas', 'No conectadas']"
          :data="[accounts.filter((a: any) => a.has_credentials).length, allPlatforms.length - accounts.filter((a: any) => a.has_credentials).length]"
          :height="200"
        />
      </Card>

      <!-- Action: Register new platform -->
      <div class="animate-in">
        <Button @click="openPlatformWizard" variant="default" class="w-full sm:w-auto">
          <Plus class="h-4 w-4" /> Registrar nueva plataforma
        </Button>
      </div>

      <!-- Platform Accounts -->
      <section class="animate-in space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <Globe class="h-3.5 w-3.5 text-primary" />
            Plataformas bug bounty
          </h2>
          <span class="text-[10px] text-muted-foreground">{{ accounts.filter((a: any) => a.has_credentials).length }}/{{ allPlatforms.length }} conectadas</span>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div
            v-for="platform in allPlatforms" :key="platform"
            class="card-base rounded-xl p-4"
          >
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-3">
                <div :class="['flex h-9 w-9 items-center justify-center rounded-lg', platformMeta[platform.toLowerCase()]?.bg || 'bg-surface/50']">
                  <Globe :class="['h-4 w-4', platformMeta[platform.toLowerCase()]?.color || 'text-muted-foreground']" />
                </div>
                <div>
                  <p class="text-sm font-semibold text-foreground">{{ platform }}</p>
                  <template v-if="accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.has_credentials">
                    <p class="text-xs text-success flex items-center gap-1">
                      <CheckCircle2 class="h-3 w-3" />
                      Conectado
                    </p>
                  </template>
                  <template v-else>
                    <p class="text-xs text-muted-foreground">No conectado</p>
                  </template>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <template v-if="accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.has_credentials">
                  <Badge variant="success" class="text-[9px]">ACTIVO</Badge>
                  <button
                    @click="disconnectPlatform(platform.toLowerCase())"
                    class="text-muted-foreground hover:text-destructive transition-colors"
                    title="Desconectar"
                  >
                    <XCircle class="h-4 w-4" />
                  </button>
                </template>
                <template v-else>
                  <Button variant="outline" size="sm" @click="showConnectForm = showConnectForm === platform ? null : platform">
                    <Plus class="h-3 w-3" /> Conectar
                  </Button>
                </template>
              </div>
            </div>

            <!-- Connect form -->
            <div v-if="showConnectForm === platform" class="mt-3 space-y-2 border-t border-border/30 pt-3">
              <input
                v-model="connectEmail"
                placeholder="Email en {{ platform }}"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-1.5 text-xs text-foreground"
              />
              <input
                v-model="connectToken"
                placeholder="API Key o token"
                type="password"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-1.5 text-xs text-foreground"
              />
              <div class="flex gap-2">
                <Button size="sm" @click="connectPlatform(platform.toLowerCase())">
                  <Link class="h-3 w-3" /> Vincular
                </Button>
                <Button variant="ghost" size="sm" @click="showConnectForm = null">Cancelar</Button>
              </div>
            </div>

            <!-- Account data -->
            <template v-if="accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.has_credentials">
              <div class="mt-3 grid grid-cols-2 gap-3 border-t border-border/30 pt-3">
                <div>
                  <p class="text-[9px] text-muted-foreground">Email</p>
                  <p class="text-xs font-medium text-foreground">
                    {{ accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.email || '—' }}
                  </p>
                </div>
                <div>
                  <p class="text-[9px] text-muted-foreground">Última sincronización</p>
                  <div class="flex items-center gap-1">
                    <p class="text-xs font-medium text-foreground">
                      {{ accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.last_sync?.slice(0, 10) || accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.last_checked?.slice(0, 10) || '—' }}
                    </p>
                    <button
                      @click="syncPlatform(platform.toLowerCase())"
                      :disabled="syncingPlatform === platform.toLowerCase()"
                      class="text-muted-foreground/50 hover:text-foreground transition-colors"
                      title="Sincronizar ahora"
                    >
                      <RefreshCw :class="['h-3 w-3', syncingPlatform === platform.toLowerCase() ? 'animate-spin' : '']" />
                    </button>
                  </div>
                </div>
                <div>
                  <p class="text-[9px] text-muted-foreground">Estado</p>
                  <p class="text-xs font-medium" :class="accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.session_state === 'connected' ? 'text-success' : 'text-muted-foreground'">
                    {{ accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.session_state || 'desconocido' }}
                  </p>
                </div>
                <div>
                  <p class="text-[9px] text-muted-foreground">Salud</p>
                  <p class="text-xs font-medium text-foreground">
                    {{ accounts.find((a: any) => a.provider_name?.toLowerCase() === platform.toLowerCase())?.health_status || '—' }}
                  </p>
                </div>
              </div>
            </template>

            <!-- Payout methods for this platform -->
            <div class="mt-3 border-t border-border/30 pt-3">
              <button
                @click="expandedPlatformPayout = expandedPlatformPayout === platform.toLowerCase() ? null : platform.toLowerCase(); if (expandedPlatformPayout === platform.toLowerCase()) loadPlatformPayout(platform.toLowerCase())"
                class="flex w-full items-center justify-between text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                <span class="flex items-center gap-1">
                  <DollarSign class="h-3 w-3" />
                  Métodos de retiro recomendados (Argentina)
                </span>
                <ChevronDown v-if="expandedPlatformPayout !== platform.toLowerCase()" class="h-3 w-3" />
                <ChevronUp v-else class="h-3 w-3" />
              </button>
              <div v-if="expandedPlatformPayout === platform.toLowerCase() && platformPayouts[platform.toLowerCase()]" class="mt-2 space-y-1.5">
                <p class="text-[9px] text-muted-foreground">KYC requerido: {{ platformPayouts[platform.toLowerCase()].kyc_required }}</p>
                <div v-for="m in platformPayouts[platform.toLowerCase()].recommended_methods" :key="m.id" class="rounded-lg bg-surface/20 px-2.5 py-2">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs font-semibold text-foreground">{{ m.name }}</p>
                      <p class="text-[9px]" :class="methodTypeIcon[m.type] || 'text-muted-foreground'">{{ methodTypeLabel[m.type] || m.type }} · KYC: {{ m.kyc_level }}</p>
                    </div>
                    <div class="text-right text-[9px] text-muted-foreground">
                      <p v-if="m.fee_percent > 0">{{ m.fee_percent }}% fee</p>
                      <p v-else>0% fee</p>
                      <p>{{ m.arrival_days }}</p>
                    </div>
                  </div>
                  <p class="mt-0.5 text-[9px] text-muted-foreground">{{ m.notes }}</p>
                </div>
                <p v-if="platformPayouts[platform.toLowerCase()].notes" class="mt-1 text-[9px] italic text-muted-foreground">{{ platformPayouts[platform.toLowerCase()].notes }}</p>
              </div>
              <div v-else-if="expandedPlatformPayout === platform.toLowerCase()" class="mt-2 text-[9px] text-muted-foreground animate-pulse">Cargando recomendaciones...</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Payout Guide for Argentina -->
      <section v-if="payoutMethods.length" class="animate-in space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <Info class="h-3.5 w-3.5 text-primary" />
            Guía de retiro para Argentina
          </h2>
          <Button variant="ghost" size="sm" @click="showPayoutGuide = !showPayoutGuide">
            {{ showPayoutGuide ? 'Ocultar' : 'Ver todos' }}
          </Button>
        </div>

        <div v-if="showPayoutGuide" class="card-base rounded-xl p-4">
          <p class="text-xs text-muted-foreground mb-3">Métodos de cobro ordenados por conveniencia desde Argentina. Con DNI alcanza para la mayoría.</p>
          <div class="space-y-2">
            <div v-for="(m, i) in payoutMethods" :key="m.id" class="flex items-start gap-3 rounded-lg bg-surface/10 px-3 py-2.5">
              <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[9px] font-bold text-primary">{{ i + 1 }}</span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <p class="text-xs font-semibold text-foreground">{{ m.name }}</p>
                  <Badge variant="outline" class="text-[8px]" :class="methodTypeIcon[m.type]">{{ methodTypeLabel[m.type] || m.type }}</Badge>
                </div>
                <p class="text-[9px] text-muted-foreground mt-0.5">
                  KYC: <strong>{{ m.kyc_level === 'dni' ? 'DNI (Argentina)' : m.kyc_level === 'none' ? 'No requiere' : m.kyc_level }}</strong>
                  · Fee: <strong>{{ m.fee_percent > 0 ? m.fee_percent + '%' : '0%' }}</strong>
                  · Llegada: <strong>{{ m.arrival_days }}</strong>
                  · Monedas: <strong>{{ m.currencies.join(', ') }}</strong>
                </p>
                <p class="text-[9px] text-muted-foreground mt-0.5">{{ m.notes }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Payout Accounts -->
      <section class="animate-in space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
            <Wallet class="h-3.5 w-3.5 text-primary" />
            Cuentas de cobro y retiros
          </h2>
          <div class="flex gap-1">
            <Button variant="outline" size="sm" @click="openPayoutWizard('bank')">
              <Building2 class="h-3 w-3" /> Banco
            </Button>
            <Button variant="outline" size="sm" @click="openPayoutWizard('crypto')">
              <Coins class="h-3 w-3" /> Crypto
            </Button>
            <Button variant="outline" size="sm" @click="openPayoutWizard('paypal')">
              <CreditCard class="h-3 w-3" /> PayPal
            </Button>
          </div>
        </div>

        <div v-if="payoutAccounts.length" class="grid gap-3">
          <div v-for="acct in payoutAccounts" :key="acct.id" class="card-base rounded-xl p-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="flex h-9 w-9 items-center justify-center rounded-lg" :class="acct.type === 'crypto' ? 'bg-warning/10 text-warning' : acct.type === 'paypal' ? 'bg-primary/10 text-primary' : 'bg-accent/10 text-accent'">
                  <Building2 v-if="acct.type === 'bank'" class="h-4 w-4" />
                  <Coins v-else-if="acct.type === 'crypto'" class="h-4 w-4" />
                  <CreditCard v-else class="h-4 w-4" />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-semibold text-foreground">{{ acct.label }}</p>
                    <Badge v-if="acct.is_default" variant="default" class="text-[8px]">PREDET.</Badge>
                  </div>
                  <p class="text-xs text-muted-foreground">
                    {{ acct.type === 'bank' ? acct.bank_name || acct.label : acct.type === 'crypto' ? acct.network || acct.currency : 'PayPal' }}
                    <span v-if="acct.last_four"> ••{{ acct.last_four }}</span>
                    <span class="ml-2 text-success">● Activa</span>
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="text-right">
                  <p class="text-lg font-bold tabular-nums text-foreground">{{ formatMoney(acct.withdrawable) }}</p>
                  <p class="text-[9px] text-muted-foreground">disponible</p>
                </div>
                <button @click="removePayoutAccount(acct.id)" class="text-muted-foreground hover:text-destructive transition-colors" title="Eliminar">
                  <Trash2 class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="card-base rounded-xl p-6 text-center">
          <Wallet class="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p class="mt-2 text-sm text-foreground">Sin cuentas de cobro registradas</p>
          <p class="text-xs text-muted-foreground">Registrá una cuenta bancaria, dirección crypto o PayPal para recibir pagos</p>
        </div>
      </section>

      <!-- Withdrawals History -->
      <section v-if="withdrawals.length" class="animate-in space-y-3">
        <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
          <History class="h-3.5 w-3.5 text-primary" />
          Historial de retiros
        </h2>

        <div class="card-base rounded-xl overflow-hidden">
          <div class="divide-y divide-border/30">
            <div v-for="wd in withdrawals" :key="wd.id" class="flex items-center justify-between px-4 py-3 hover:bg-surface/10 transition-colors">
              <div class="flex items-center gap-2">
                <Badge :variant="statusColor(wd.status)" class="text-[8px]">{{ wd.status }}</Badge>
                <span class="text-xs text-foreground">{{ wd.destination }}</span>
              </div>
              <div class="text-right">
                <span class="text-xs font-semibold tabular-nums text-foreground">{{ formatMoney(wd.amount) }}</span>
                <span class="ml-2 text-[10px] text-muted-foreground">{{ wd.created_at?.slice(0, 10) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Submission History -->
      <section class="animate-in space-y-3">
        <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
          <History class="h-3.5 w-3.5 text-primary" />
          Historial de envíos
        </h2>

        <div class="card-base rounded-xl overflow-hidden">
          <div v-if="submissions.length" class="divide-y divide-border/30">
            <div v-for="s in submissions" :key="s.id" class="flex items-center gap-3 px-4 py-3 hover:bg-surface/10 transition-colors">
              <Badge :variant="statusColor(s.status)" class="text-[8px] w-16 justify-center">{{ s.status }}</Badge>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-medium text-foreground truncate">{{ s.platform }}</p>
                <p class="text-[10px] text-muted-foreground truncate">Reporte #{{ s.report_id }} · {{ s.external_id ? 'ID: ' + s.external_id : 'Sin ID externo' }}</p>
              </div>
              <div class="text-right shrink-0">
                <p v-if="s.reward" class="text-xs font-semibold text-gold tabular-nums">{{ formatMoney(s.reward) }}</p>
                <p class="text-[9px] text-muted-foreground">{{ s.submitted_at?.slice(0, 10) || '—' }}</p>
              </div>
              <ExternalLink class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            </div>
          </div>
          <div v-else class="px-4 py-6 text-center">
            <History class="mx-auto h-6 w-6 text-muted-foreground/50" />
            <p class="mt-2 text-xs text-muted-foreground">No hay envíos registrados todavía</p>
          </div>
        </div>
      </section>
    </template>

    <!-- ══════════ Platform Registration Wizard Modal ══════════ -->
    <Teleport to="body">
      <div v-if="showPlatformWizard" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div class="w-full max-w-md rounded-2xl border border-border/50 bg-background p-6 shadow-2xl">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-foreground">Registrar plataforma</h3>
            <button @click="showPlatformWizard = false" class="text-muted-foreground hover:text-foreground">
              <XCircle class="h-4 w-4" />
            </button>
          </div>

          <!-- Step 1: Select platform -->
          <div v-if="platformWizardStep === 1" class="space-y-3">
            <p class="text-xs text-muted-foreground">Seleccioná la plataforma que querés conectar:</p>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="p in allPlatforms" :key="p"
                @click="newPlatform.provider = p.toLowerCase()"
                :class="[
                  'rounded-xl border px-3 py-2.5 text-left transition-all',
                  newPlatform.provider === p.toLowerCase()
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/30'
                    : 'border-border/40 hover:border-border'
                ]"
              >
                <p class="text-xs font-semibold text-foreground">{{ p }}</p>
              </button>
            </div>
            <div class="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" @click="showPlatformWizard = false">Cancelar</Button>
              <Button size="sm" :disabled="!newPlatform.provider" @click="platformWizardStep = 2">
                Siguiente <ArrowRight class="h-3 w-3" />
              </Button>
            </div>
          </div>

          <!-- Step 2: Credentials -->
          <div v-if="platformWizardStep === 2" class="space-y-3">
            <p class="text-xs text-muted-foreground">Ingresá tus credenciales de <strong class="text-foreground">{{ newPlatform.provider }}</strong>:</p>
            <input
              v-model="newPlatform.email"
              placeholder="Email registrado en la plataforma"
              class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
            />
            <input
              v-model="newPlatform.username"
              placeholder="Nombre de usuario (opcional)"
              class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
            />
            <input
              v-model="newPlatform.token"
              placeholder="API Key o token"
              type="password"
              class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
            />
            <input
              v-model="newPlatform.password"
              placeholder="Contraseña (opcional, para algunos servicios)"
              type="password"
              class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
            />
            <p class="text-[9px] text-muted-foreground">Las credenciales se almacenan cifradas con AES-256-GCM. Nunca se comparten.</p>

            <div v-if="platformError" class="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ platformError }}</div>
            <div v-if="platformSuccess" class="rounded-lg bg-success/10 px-3 py-2 text-xs text-success">{{ platformSuccess }}</div>

            <div class="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" @click="platformWizardStep = 1">Atrás</Button>
              <Button size="sm" :disabled="platformSaving" @click="savePlatformRegistration">
                <Loader2 v-if="platformSaving" class="h-3 w-3 animate-spin" />
                <Link v-else class="h-3 w-3" />
                {{ platformSaving ? 'Guardando...' : 'Guardar y conectar' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ══════════ Payout Account Wizard Modal ══════════ -->
    <Teleport to="body">
      <div v-if="showPayoutWizard" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <div class="w-full max-w-md rounded-2xl border border-border/50 bg-background p-6 shadow-2xl">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-foreground">
              {{ payoutType === 'bank' ? 'Registrar cuenta bancaria' : payoutType === 'crypto' ? 'Registrar dirección crypto' : 'Conectar PayPal' }}
            </h3>
            <button @click="showPayoutWizard = false" class="text-muted-foreground hover:text-foreground">
              <XCircle class="h-4 w-4" />
            </button>
          </div>

          <div class="space-y-3">
            <input
              v-model="newPayout.label"
              :placeholder="'Nombre para esta cuenta (ej: Mi banco, Wallet principal)'"
              class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
            />

            <template v-if="payoutType === 'bank'">
              <input
                v-model="newPayout.bank_name"
                placeholder="Nombre del banco"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
              <input
                v-model="newPayout.address"
                placeholder="CBU / Alias / Número de cuenta"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
              <input
                v-model="newPayout.last_four"
                placeholder="Últimos 4 dígitos"
                maxlength="4"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
            </template>

            <template v-else-if="payoutType === 'crypto'">
              <input
                v-model="newPayout.address"
                placeholder="Dirección de wallet (0x... o bc1...)"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
              <input
                v-model="newPayout.network"
                placeholder="Red (ej: Ethereum, Solana, Polygon)"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
              <select
                v-model="newPayout.currency"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              >
                <option value="USDC">USDC</option>
                <option value="USDT">USDT</option>
                <option value="ETH">ETH</option>
                <option value="BTC">BTC</option>
                <option value="DAI">DAI</option>
              </select>
            </template>

            <template v-else-if="payoutType === 'paypal'">
              <input
                v-model="newPayout.address"
                placeholder="Email de PayPal"
                type="email"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground"
              />
            </template>

            <label class="flex items-center gap-2 text-xs text-muted-foreground">
              <input v-model="newPayout.is_default" type="checkbox" class="rounded border-border/60" />
              Establecer como cuenta predeterminada
            </label>

            <div v-if="payoutError" class="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{{ payoutError }}</div>
            <div v-if="payoutSuccess" class="rounded-lg bg-success/10 px-3 py-2 text-xs text-success">{{ payoutSuccess }}</div>

            <div class="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" @click="showPayoutWizard = false">Cancelar</Button>
              <Button size="sm" :disabled="payoutSaving" @click="savePayoutAccount">
                <Loader2 v-if="payoutSaving" class="h-3 w-3 animate-spin" />
                <CheckCircle2 v-else class="h-3 w-3" />
                {{ payoutSaving ? 'Guardando...' : 'Guardar cuenta' }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ═══ OSINT INTELLIGENCE ═══ -->
    <div class="card-base rounded-xl p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2">
          <Scan class="h-4 w-4 text-warning" />
          <h3 class="font-mono text-xs font-semibold text-foreground">Inteligencia OSINT</h3>
        </div>
        <Button size="sm" variant="outline" @click="$router.push('/settings')">
          <Settings class="h-3.5 w-3.5" /> Configurar
        </Button>
      </div>
      <p class="text-xs text-muted-foreground mb-4">
        Las API keys de servicios OSINT (Shodan, Censys, VirusTotal, etc.) se configuran desde
        <span class="text-primary cursor-pointer hover:underline" @click="$router.push('/settings')">Configuración → OSINT</span>.
      </p>
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
        <div v-for="svc in definitions.osint_services" :key="svc.id"
          class="flex items-center gap-1.5 rounded-lg bg-surface/20 px-2 py-1.5"
        >
          <div class="h-1.5 w-1.5 rounded-full bg-muted-foreground/40" />
          <span class="font-mono text-[9px] text-muted-foreground">{{ svc.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
