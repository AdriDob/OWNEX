<script setup lang="ts">
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Globe,
  Info,
  Key,
  Link,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Settings,
  Shield,
  ShieldOff,
  Unlink,
  Wallet,
  XCircle,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface PlatformAccount {
  provider: string
  connected: boolean
  username?: string
  email?: string
  earnings?: number
  pending?: number
  last_sync?: string
  has_credentials?: boolean
  health_status?: string
  session_state?: string
}

interface IdentitySettings {
  email: string
  wallet_address: string
  operational_mode: 'manual' | 'prepare' | 'automatic'
  approval_required: boolean
}

const loading = ref(true)
const error = ref('')
const accounts = ref<PlatformAccount[]>([])
const syncing = ref(false)
const syncingPlatform = ref<string | null>(null)
const lastSyncAll = ref<string | null>(null)
const settings = ref<IdentitySettings>({
  email: '',
  wallet_address: '',
  operational_mode: 'manual',
  approval_required: true,
})
const settingsSaving = ref(false)
const settingsError = ref('')
const settingsSuccess = ref('')

const showConnectForm = ref<string | null>(null)
const connectEmail = ref('')
const connectToken = ref('')
const connecting = ref(false)
const connectError = ref('')

const definitions = ref<{ platforms: { id: string; name: string }[] }>({ platforms: [] })
const platformList = computed(() => definitions.value.platforms.map((p) => p.name))

async function syncAll() {
  syncing.value = true
  try {
    await api.post('/platforms/sync', {})
    await loadData()
    lastSyncAll.value = new Date().toISOString()
  } catch {
    /* ignore */
  } finally {
    syncing.value = false
  }
}

async function syncPlatform(provider: string) {
  syncingPlatform.value = provider
  try {
    // No hay sync por-provider en el backend; el sync es global.
    await api.post('/platforms/sync', {})
    await loadData()
  } catch {
    /* ignore */
  } finally {
    syncingPlatform.value = null
  }
}

const platformColors: Record<string, string> = {
  hackerone: 'text-success',
  bugcrowd: 'text-warning',
  intigriti: 'text-intigriti',
  yeswehack: 'text-destructive',
  synack: 'text-muted-foreground',
}

const connectedCount = computed(() => accounts.value.filter((a) => a.connected).length)
const disconnectedCount = computed(() => accounts.value.filter((a) => !a.connected).length)

const doughnutLabels = computed(() => ['Connected', 'Disconnected'])
const doughnutData = computed(() => [connectedCount.value, disconnectedCount.value])

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    // identity-center no expone GET de settings: defaults locales + persistencia
    // granular al guardar (email/wallets/never-submit).
    const [accRes, defRes] = await Promise.allSettled([
      api.get<{ accounts: PlatformAccount[] }>('/opportunity/identity/accounts'),
      api.get<{ platforms: { id: string; name: string }[] }>('/system/definitions'),
    ])
    if (accRes.status === 'fulfilled') accounts.value = accRes.value.accounts || []
    if (defRes.status === 'fulfilled') definitions.value = defRes.value
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load identity data'
  } finally {
    loading.value = false
  }
}

async function connectPlatform(provider: string) {
  if (!connectEmail.value || !connectToken.value) return
  connecting.value = true
  connectError.value = ''
  try {
    await api.post(`/identity-center/platform/${provider}/connect`, {
      email: connectEmail.value,
      token: connectToken.value,
    })
    showConnectForm.value = null
    connectEmail.value = ''
    connectToken.value = ''
    await loadData()
  } catch (e: unknown) {
    connectError.value = e instanceof Error ? e.message : 'Failed to connect'
  } finally {
    connecting.value = false
  }
}

async function disconnectPlatform(provider: string) {
  try {
    await api.post(`/identity-center/platform/${provider}/disconnect`, {})
    accounts.value = accounts.value.filter((a) => a.provider !== provider)
  } catch {
    /* ignore */
  }
}

async function saveSettings() {
  settingsSaving.value = true
  settingsError.value = ''
  settingsSuccess.value = ''
  try {
    // Persistencia granular contra endpoints reales de identity-center.
    await Promise.all([
      settings.value.email ? api.post('/identity-center/email', { primary: settings.value.email }) : Promise.resolve(),
      settings.value.wallet_address
        ? api.post('/identity-center/wallets', { usdc: settings.value.wallet_address })
        : Promise.resolve(),
      api.post('/identity-center/never-submit', { enabled: settings.value.approval_required }),
    ])
    settingsSuccess.value = 'Settings saved'
    setTimeout(() => {
      settingsSuccess.value = ''
    }, 3000)
  } catch (e: unknown) {
    settingsError.value = e instanceof Error ? e.message : 'Failed to save settings'
  } finally {
    settingsSaving.value = false
  }
}

function getAccount(provider: string) {
  return accounts.value.find((a) => a.provider.toLowerCase() === provider.toLowerCase())
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <template v-if="loading">
      <div class="space-y-4">
        <Skeleton class="h-6 w-56" />
        <div class="grid grid-cols-2 gap-4"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div>
        <Skeleton class="h-48 rounded-xl" />
        <Skeleton class="h-32 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error loading identity data</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadData">
          <RefreshCw class="h-3.5 w-3.5" /> Retry
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="animate-in flex items-end justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-bold uppercase tracking-[0.15em] text-primary">Identity</p>
          <h1 class="font-display text-2xl font-bold text-foreground">Identity Center</h1>
          <p class="text-xs text-muted-foreground">Manage platform connections, operational preferences, and account settings</p>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="lastSyncAll" class="text-[9px] text-muted-foreground/60">Last sync: {{ new Date(lastSyncAll).toLocaleTimeString() }}</span>
          <Button variant="outline" size="sm" :disabled="syncing" @click="syncAll" class="flex items-center gap-1">
            <RefreshCw :class="['h-3 w-3', syncing ? 'animate-spin' : '']" />
            {{ syncing ? 'Syncing...' : 'Sync All' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-3">
        <div class="lg:col-span-2 space-y-6">
          <section class="animate-in space-y-3">
            <div class="flex items-center justify-between">
              <h2 class="text-xs font-semibold text-foreground flex items-center gap-2">
                <Globe class="h-3.5 w-3.5 text-primary" />
                Bug Bounty Platforms
              </h2>
              <span class="text-[10px] text-muted-foreground">{{ connectedCount }}/{{ platformList.length }} connected</span>
            </div>

            <div v-if="accounts.length === 0" class="glass-fintech rounded-xl p-6 text-center">
              <Globe class="mx-auto h-8 w-8 text-muted-foreground/50" />
              <p class="mt-2 text-sm text-foreground">No platforms connected</p>
              <p class="text-xs text-muted-foreground">Connect your bug bounty platform accounts to get started</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div
                v-for="platform in platformList" :key="platform"
                class="glass-fintech rounded-xl p-4"
              >
                <div class="flex items-start justify-between">
                  <div class="flex items-center gap-3">
                    <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-surface/50">
                      <Globe :class="['h-4 w-4', platformColors[platform.toLowerCase()] || 'text-muted-foreground']" />
                    </div>
                    <div>
                      <p class="text-sm font-semibold text-foreground">{{ platform }}</p>
                      <template v-if="getAccount(platform)?.connected">
                        <p class="text-xs text-success flex items-center gap-1">
                          <CheckCircle2 class="h-3 w-3" /> Connected
                        </p>
                      </template>
                      <template v-else>
                        <p class="text-xs text-muted-foreground">Not connected</p>
                      </template>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <template v-if="getAccount(platform)?.connected">
                      <Badge variant="success" class="text-[9px]">ACTIVO</Badge>
                      <button
                        @click="disconnectPlatform(platform.toLowerCase())"
                        class="text-muted-foreground hover:text-destructive transition-colors"
                        title="Disconnect"
                      >
                        <XCircle class="h-4 w-4" />
                      </button>
                    </template>
                    <template v-else>
                      <Button variant="outline" size="sm" @click="showConnectForm = showConnectForm === platform ? null : platform">
                        <Plus class="h-3 w-3" /> Connect
                      </Button>
                    </template>
                  </div>
                </div>

                <div v-if="showConnectForm === platform" class="mt-3 space-y-2 border-t border-border/30 pt-3">
                  <input
                    v-model="connectEmail"
                    placeholder="Email on {{ platform }}"
                    class="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-1.5 text-xs text-foreground"
                  />
                  <input
                    v-model="connectToken"
                    placeholder="API Key or token"
                    type="password"
                    class="w-full rounded-lg border border-border/60 bg-background/60 px-3 py-1.5 text-xs text-foreground"
                  />
                  <div v-if="connectError" class="text-[10px] text-destructive">{{ connectError }}</div>
                  <div class="flex gap-2">
                    <Button size="sm" :disabled="connecting" @click="connectPlatform(platform.toLowerCase())">
                      <Loader2 v-if="connecting" class="h-3 w-3 animate-spin" />
                      <Link v-else class="h-3 w-3" />
                      {{ connecting ? 'Connecting...' : 'Link' }}
                    </Button>
                    <Button variant="ghost" size="sm" @click="showConnectForm = null">Cancel</Button>
                  </div>
                </div>

                <template v-if="getAccount(platform)?.connected">
                  <div class="mt-3 grid grid-cols-2 gap-3 border-t border-border/30 pt-3">
                    <div>
                      <p class="text-[9px] text-muted-foreground">Email</p>
                      <p class="text-xs font-medium text-foreground">{{ getAccount(platform)?.email || '—' }}</p>
                    </div>
                    <div>
                      <p class="text-[9px] text-muted-foreground">Username</p>
                      <p class="text-xs font-medium text-foreground">{{ getAccount(platform)?.username || '—' }}</p>
                    </div>
                    <div>
                      <p class="text-[9px] text-muted-foreground">Last Sync</p>
                      <div class="flex items-center gap-1">
                        <p class="text-xs font-medium text-foreground">{{ getAccount(platform)?.last_sync?.slice(0, 10) || '—' }}</p>
                        <button
                          @click="syncPlatform(platform.toLowerCase())"
                          :disabled="syncingPlatform === platform.toLowerCase()"
                          class="text-muted-foreground/40 hover:text-foreground transition-colors"
                          title="Sync now"
                        >
                          <RefreshCw :class="['h-3 w-3', syncingPlatform === platform.toLowerCase() ? 'animate-spin' : '']" />
                        </button>
                      </div>
                    </div>
                    <div>
                      <p class="text-[9px] text-muted-foreground">Health</p>
                      <p class="text-xs font-medium" :class="getAccount(platform)?.health_status === 'healthy' ? 'text-success' : 'text-muted-foreground'">
                        {{ getAccount(platform)?.health_status || '—' }}
                      </p>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </section>
        </div>

        <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
          <Card class="p-4 animate-in">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2 mb-3">
              <Settings class="h-3.5 w-3.5 text-primary" />
              Platform Distribution
            </h3>
            <DoughnutChart
              v-if="accounts.length > 0"
              :labels="doughnutLabels"
              :data="doughnutData"
              :colors="['var(--ownex-green)', 'var(--ownex-text-muted)']"
              :height="200"
              :show-legend="true"
              :cutout="'65%'"
            />
            <div v-else class="py-8 text-center text-[10px] text-muted-foreground">
              No data to display
            </div>
          </Card>

          <Card class="p-4 animate-in space-y-4">
            <h3 class="text-xs font-semibold text-foreground flex items-center gap-2">
              <Settings class="h-3.5 w-3.5 text-primary" />
              Operational Settings
            </h3>

            <div class="space-y-3">
              <div>
                <p class="text-[10px] text-muted-foreground flex items-center gap-1"><Mail class="h-3 w-3" /> Email</p>
                <input
                  v-model="settings.email"
                  placeholder="your@email.com"
                  class="mt-1 w-full rounded-lg border border-border/60 bg-background/60 px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <p class="text-[10px] text-muted-foreground flex items-center gap-1"><Wallet class="h-3 w-3" /> Wallet Address</p>
                <input
                  v-model="settings.wallet_address"
                  placeholder="0x... or bc1..."
                  class="mt-1 w-full rounded-lg border border-border/60 bg-background/60 px-3 py-1.5 text-xs text-foreground"
                />
              </div>
              <div>
                <p class="text-[10px] text-muted-foreground flex items-center gap-1"><Shield class="h-3 w-3" /> Operational Mode</p>
                <!-- El backend solo expone modo por-plataforma
                     (identity-center/platform/{p}/mode); el selector global
                     se resuelve vía never-submit (aprobación obligatoria). -->
                <select
                  v-model="settings.operational_mode"
                  disabled
                  title="Configurá el modo por plataforma en cada conector"
                  class="mt-1 w-full cursor-not-allowed rounded-lg border border-border/60 bg-background/60 px-3 py-1.5 text-xs text-muted-foreground"
                >
                  <option value="manual">Manual (por plataforma)</option>
                </select>
              </div>
              <label class="flex items-center gap-2 text-xs text-muted-foreground">
                <input v-model="settings.approval_required" type="checkbox" class="rounded border-border/60" />
                Require approval before submission
              </label>

              <div v-if="settingsError" class="rounded-lg bg-destructive/10 px-3 py-2 text-[10px] text-destructive">{{ settingsError }}</div>
              <div v-if="settingsSuccess" class="rounded-lg bg-success/10 px-3 py-2 text-[10px] text-success">{{ settingsSuccess }}</div>

              <Button size="sm" class="w-full" :disabled="settingsSaving" @click="saveSettings">
                <Loader2 v-if="settingsSaving" class="h-3 w-3 animate-spin" />
                <CheckCircle2 v-else class="h-3 w-3" />
                {{ settingsSaving ? 'Saving...' : 'Save Settings' }}
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
