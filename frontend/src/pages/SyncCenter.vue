<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  Activity, AlertTriangle, CheckCircle2, Clock, ExternalLink,
  Loader2, RefreshCw, RotateCw, XCircle,
} from '@lucide/vue'

interface SyncHistoryEntry {
  source: string
  type: 'crypto' | 'platform'
  timestamp: string | number
  status: string
  total_usd?: number
  error?: string
  balance_count?: number
  tx_count?: number
  consecutive_failures?: number
  total_syncs?: number
}

const history = ref<SyncHistoryEntry[]>([])
const loading = ref(true)
const error = ref('')
const refreshing = ref(false)

function statusIcon(status: string) {
  if (status === 'connected' || status === 'healthy') return CheckCircle2
  if (status === 'degraded' || status === 'stale') return Clock
  if (status === 'failed' || status === 'error') return XCircle
  return AlertTriangle
}

function statusColor(status: string): string {
  if (status === 'connected' || status === 'healthy') return 'text-success'
  if (status === 'degraded') return 'text-warning'
  if (status === 'stale') return 'text-muted-foreground'
  if (status === 'failed' || status === 'error') return 'text-destructive'
  return 'text-muted-foreground/50'
}

function formatTime(ts: string | number): string {
  if (!ts) return '—'
  const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString('es-AR')
}

async function loadHistory() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<any>('/accounts-hub/sync-history')
    history.value = res || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar historial'
  } finally {
    loading.value = false
  }
}

async function refresh() {
  refreshing.value = true
  await loadHistory()
  refreshing.value = false
}

async function syncSource(source: string) {
  try {
    await api.post(`/crypto/wallets/${source}/sync`)
    await loadHistory()
  } catch (e) {
    console.error('Sync failed:', e)
  }
}

onMounted(loadHistory)
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Activity class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">SYNC CENTER</span>
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Sync Center</h1>
        <p class="text-xs text-muted-foreground">Historial de sincronización — plataformas y wallets</p>
      </div>
      <Button variant="outline" size="sm" :disabled="refreshing" @click="refresh">
        <RefreshCw class="h-3.5 w-3.5" :class="{ 'animate-spin': refreshing }" />
        Actualizar
      </Button>
    </div>

    <template v-if="loading">
      <Skeleton class="h-64 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm text-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="loadHistory">
          <RotateCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else>
      <div v-if="history.length === 0" class="rounded-xl border border-border/30 bg-surface/20 p-8 text-center">
        <Clock class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
        <p class="font-mono text-xs text-muted-foreground">No hay actividad de sincronización registrada</p>
      </div>

      <div class="space-y-2">
        <div
          v-for="(entry, i) in history"
          :key="`${entry.source}-${entry.timestamp}-${i}`"
          class="rounded-xl border border-border/30 bg-surface/20 p-3"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <component :is="statusIcon(entry.status)" class="h-3.5 w-3.5" :class="statusColor(entry.status)" />
              <span class="font-mono text-xs font-medium text-foreground">{{ entry.source }}</span>
              <Badge variant="outline" class="text-[9px]">{{ entry.type }}</Badge>
            </div>
            <div class="flex items-center gap-2">
              <span class="font-mono text-[9px]" :class="statusColor(entry.status)">{{ entry.status }}</span>
              <Button variant="ghost" size="sm" @click="syncSource(entry.source)">
                <Loader2 v-if="false" class="h-3 w-3 animate-spin" />
                <RefreshCw class="h-3 w-3" />
              </Button>
            </div>
          </div>

          <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[9px] text-muted-foreground">
            <span>{{ formatTime(entry.timestamp) }}</span>
            <span v-if="entry.total_usd !== undefined">${{ entry.total_usd.toFixed(2) }}</span>
            <span v-if="entry.balance_count !== undefined">{{ entry.balance_count }} balances</span>
            <span v-if="entry.tx_count !== undefined">{{ entry.tx_count }} txs</span>
            <span v-if="entry.consecutive_failures !== undefined">{{ entry.consecutive_failures }} fallos consecutivos</span>
            <span v-if="entry.total_syncs !== undefined">{{ entry.total_syncs }} syncs totales</span>
          </div>

          <p v-if="entry.error" class="mt-1 font-mono text-[9px] text-destructive/80">
            Error: {{ entry.error }}
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
