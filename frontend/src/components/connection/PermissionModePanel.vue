<script setup lang="ts">
/**
 * PermissionModePanel — Escalera de autonomía por conexión (Investment Hub §H).
 *
 * Contratos backend (api/routers/connection_manager.py):
 *  - GET  /permissions/matrix                    → ladder + capability matrix
 *  - GET  /accounts                              → mode/capabilities por conexión
 *  - POST /accounts/{provider}/permissions       → {mode, reason?, acknowledge_risk?}
 *  - POST /accounts/{provider}/permissions/revoke
 *
 * Reglas que la UI refleja, nunca relaja:
 *  - deny-by-default: sin registro la conexión está DISCONNECTED
 *  - escalado contiguo: solo se sube un peldaño por vez
 *  - LIVE_TRADING_AUTHORIZED exige check de riesgo explícito del usuario
 *  - fondos/retiros no existen en ningún modo
 */
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, ArrowDown, ArrowUp, Loader2, ShieldCheck, ShieldOff } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { useToast } from '@/composables/useToast'

interface ModeRow {
  mode: string
  description: string
  capabilities: string[]
  live_orders: boolean
  requires_human_ack: boolean
}

interface ConnAccount {
  provider: string
  domain?: string
  state: string
  permission_mode?: string
  permissions?: string[]
  live_orders_allowed?: boolean
}

// Conexiones con ruta de órdenes reales en OWNEX (mirror de permissions.EXECUTION_PROVIDERS).
const EXECUTION_PROVIDERS = ['alpaca', 'ibkr', 'ccxt', 'binance', 'iol', 'ppi']

const toast = useToast()

const loading = ref(true)
const error = ref<string | null>(null)
const ladder = ref<string[]>([])
const matrix = ref<ModeRow[]>([])
const forbidden = ref<string[]>([])
const connections = ref<ConnAccount[]>([])

const busy = ref<Record<string, boolean>>({})
const reasons = ref<Record<string, string>>({})
const acks = ref<Record<string, boolean>>({})

const modeIndex = computed(() => {
  const map: Record<string, number> = {}
  ladder.value.forEach((m, i) => {
    map[m] = i
  })
  return map
})

function modeOf(provider: string): string {
  return connections.value.find(c => c.provider === provider)?.permission_mode || 'DISCONNECTED'
}

function capsOf(provider: string): string[] {
  return connections.value.find(c => c.provider === provider)?.permissions || []
}

function nextMode(provider: string): string | null {
  const idx = modeIndex.value[modeOf(provider)] ?? 0
  return ladder.value[idx + 1] || null
}

function prevMode(provider: string): string | null {
  const idx = modeIndex.value[modeOf(provider)] ?? 0
  return idx > 0 ? ladder.value[idx - 1] : null
}

function modeVariant(mode: string): 'destructive' | 'warning' | 'info' | 'default' | 'offline' {
  if (mode === 'LIVE_TRADING_AUTHORIZED') return 'destructive'
  if (mode === 'CONFIRMATION_REQUIRED') return 'warning'
  if (mode === 'PRE_TRADE_VALIDATION' || mode === 'PAPER_TRADING') return 'info'
  if (mode === 'DISCONNECTED') return 'offline'
  return 'default'
}

function modeDescription(mode: string): string {
  return matrix.value.find(m => m.mode === mode)?.description || ''
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [matrixRes, accountsRes, snapshotRes] = await Promise.all([
      api.get<{ matrix: ModeRow[]; ladder: string[]; forbidden: string[] }>(
        '/connection-manager/permissions/matrix',
      ),
      api.get<{ accounts: ConnAccount[] }>('/connection-manager/accounts'),
      api.get<{ providers: Record<string, { mode: string; capabilities: string[] }> }>(
        '/connection-manager/permissions',
      ),
    ])
    matrix.value = matrixRes.matrix || []
    ladder.value = matrixRes.ladder || []
    forbidden.value = matrixRes.forbidden || []

    const byProvider = new Map<string, ConnAccount>()
    for (const account of accountsRes.accounts || []) {
      if (account.domain === 'investment_ar' || EXECUTION_PROVIDERS.includes(account.provider)) {
        byProvider.set(account.provider, account)
      }
    }
    // Conexiones con ruta de órdenes que viven fuera del catálogo (alpaca/ibkr/ccxt):
    // se listan igual, en DISCONNECTED si todavía no tienen registro (deny-by-default).
    const records = snapshotRes.providers || {}
    for (const provider of EXECUTION_PROVIDERS) {
      if (byProvider.has(provider)) continue
      const caps = records[provider]?.capabilities || []
      byProvider.set(provider, {
        provider,
        domain: 'investment',
        state: '—',
        permission_mode: records[provider]?.mode || 'DISCONNECTED',
        permissions: caps,
        live_orders_allowed: caps.includes('LIVE_ORDER'),
      })
    }
    connections.value = [...byProvider.values()]
  } catch (e: any) {
    error.value = e?.message || 'No se pudieron cargar los permisos'
  } finally {
    loading.value = false
  }
}

async function applyMode(provider: string, mode: string) {
  if (!mode) return
  const row = matrix.value.find(m => m.mode === mode)
  if (row?.requires_human_ack && !acks.value[provider]) {
    toast.error('Confirmá el riesgo antes de autorizar órdenes reales')
    return
  }
  busy.value[provider] = true
  try {
    await api.post(`/connection-manager/accounts/${encodeURIComponent(provider)}/permissions`, {
      mode,
      reason: reasons.value[provider] || '',
      acknowledge_risk: !!acks.value[provider],
    })
    toast.success(`${provider}: modo ${mode}`)
    acks.value[provider] = false
    await load()
  } catch (e: any) {
    toast.error(e?.message || `No se pudo cambiar el modo de ${provider}`)
  } finally {
    busy.value[provider] = false
  }
}

async function revoke(provider: string) {
  busy.value[provider] = true
  try {
    await api.post(`/connection-manager/accounts/${encodeURIComponent(provider)}/permissions/revoke`, {
      reason: reasons.value[provider] || 'revocado desde la UI',
    })
    toast.success(`${provider} revocado — acceso cerrado`)
    await load()
  } catch (e: any) {
    toast.error(e?.message || `No se pudo revocar ${provider}`)
  } finally {
    busy.value[provider] = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div class="space-y-1">
        <h3 class="flex items-center gap-2 font-mono text-xs font-semibold text-foreground">
          <ShieldCheck class="h-3.5 w-3.5 text-primary" />
          Permisos por conexión
          <span class="text-[9px] font-normal text-muted-foreground">{{ connections.length }} conexiones</span>
        </h3>
        <p class="text-[10px] text-muted-foreground">
          Autonomía explícita, revocable y auditada. Denegado por defecto: una conexión sin permiso no opera.
        </p>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="load">Refrescar</Button>
    </div>

    <!-- Escalera -->
    <div v-if="ladder.length" class="flex flex-wrap items-center gap-1.5">
      <template v-for="(mode, i) in ladder" :key="mode">
        <span
          class="rounded-md border border-border/50 bg-surface/40 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground"
          :title="modeDescription(mode)"
        >
          {{ mode }}
        </span>
        <ArrowUp v-if="i < ladder.length - 1" class="h-3 w-3 rotate-90 text-muted-foreground/40" />
      </template>
    </div>

    <!-- Aviso de capacidades prohibidas -->
    <div v-if="forbidden.length" class="flex items-start gap-2 rounded-lg border border-border/40 bg-surface/20 px-3 py-2">
      <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
      <p class="text-[10px] text-muted-foreground">
        Nunca habilitado en ningún modo:
        <span class="font-mono text-foreground">{{ forbidden.join(' · ') }}</span>
        — OWNEX no mueve fondos ni retira.
      </p>
    </div>

    <!-- Loading / error -->
    <div v-if="loading" class="space-y-2">
      <Skeleton v-for="i in 3" :key="i" class="h-16 rounded-xl" />
    </div>
    <div v-else-if="error" class="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
      {{ error }}
    </div>

    <!-- Conexiones -->
    <div v-else-if="connections.length" class="space-y-2">
      <div
        v-for="conn in connections"
        :key="conn.provider"
        class="rounded-xl border border-border/50 bg-card p-3"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex min-w-0 items-center gap-2">
            <span class="truncate font-mono text-xs font-semibold text-foreground">{{ conn.provider }}</span>
            <Badge :variant="modeVariant(conn.permission_mode || 'DISCONNECTED')">
              {{ conn.permission_mode || 'DISCONNECTED' }}
            </Badge>
            <Badge v-if="conn.live_orders_allowed" variant="critical">ÓRDENES REALES</Badge>
            <span class="truncate text-[10px] text-muted-foreground">
              {{ modeDescription(conn.permission_mode || 'DISCONNECTED') }}
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            <Button
              v-if="prevMode(conn.provider)"
              variant="ghost"
              size="sm"
              :disabled="busy[conn.provider]"
              @click="applyMode(conn.provider, prevMode(conn.provider)!)"
            >
              <ArrowDown class="h-3 w-3" /> Bajar
            </Button>
            <Button
              v-if="nextMode(conn.provider)"
              variant="outline"
              size="sm"
              :disabled="busy[conn.provider]"
              @click="applyMode(conn.provider, nextMode(conn.provider)!)"
            >
              <ArrowUp class="h-3 w-3" /> Subir a {{ nextMode(conn.provider) }}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              :disabled="busy[conn.provider] || (conn.permission_mode || 'DISCONNECTED') === 'DISCONNECTED'"
              @click="revoke(conn.provider)"
            >
              <Loader2 v-if="busy[conn.provider]" class="h-3 w-3 animate-spin" />
              <ShieldOff v-else class="h-3 w-3" /> Revocar
            </Button>
          </div>
        </div>

        <!-- Confirmación explícita para órdenes reales -->
        <div
          v-if="nextMode(conn.provider) === 'LIVE_TRADING_AUTHORIZED'"
          class="mt-2 space-y-2 border-t border-border/30 pt-2"
        >
          <label class="flex items-start gap-2 text-[10px] text-muted-foreground">
            <input v-model="acks[conn.provider]" type="checkbox" class="mt-0.5 rounded border-border/60" />
            Entiendo que autorizo órdenes reales en {{ conn.provider }} con dinero efectivo, dentro de los límites de riesgo.
          </label>
          <div class="flex flex-wrap items-center gap-1.5">
            <input
              v-model="reasons[conn.provider]"
              placeholder="Motivo (queda en el audit log)"
              class="min-w-0 flex-1 rounded-lg border border-border/60 bg-surface/50 px-2 py-1 font-mono text-[10px] text-foreground"
            />
            <Button
              variant="destructive"
              size="sm"
              :disabled="busy[conn.provider] || !acks[conn.provider]"
              @click="applyMode(conn.provider, 'LIVE_TRADING_AUTHORIZED')"
            >
              Autorizar LIVE
            </Button>
          </div>
        </div>

        <!-- Capacidades otorgadas -->
        <p v-if="capsOf(conn.provider).length" class="mt-2 font-mono text-[9px] text-muted-foreground/70">
          {{ capsOf(conn.provider).join(' · ') }}
        </p>
        <p v-else class="mt-2 font-mono text-[9px] text-muted-foreground/50">
          sin capacidades otorgadas
        </p>
      </div>
    </div>

    <p v-else class="rounded-lg border border-border/40 bg-surface/20 px-3 py-4 text-center text-xs text-muted-foreground">
      No hay conexiones de inversión en el catálogo todavía.
    </p>
  </div>
</template>
