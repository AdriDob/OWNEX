<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  AlertTriangle, Database, FileText, RotateCw,
  Search, TrendingUp,
} from '@lucide/vue'

interface LedgerEntry {
  id: string
  event: string
  amount: number
  currency: string
  description: string
  source: string
  source_id: string
  platform: string
  timestamp: string
  reconciled: boolean
  metadata: Record<string, any>
}

const entries = ref<LedgerEntry[]>([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')
const limit = ref(100)
const viewMode = ref<'list' | 'detail'>('list')
const selectedEntry = ref<LedgerEntry | null>(null)

const filteredEntries = computed(() => {
  if (!searchQuery.value) return entries.value
  const q = searchQuery.value.toLowerCase()
  return entries.value.filter(e =>
    e.event.toLowerCase().includes(q) ||
    e.source.toLowerCase().includes(q) ||
    e.platform.toLowerCase().includes(q) ||
    e.description.toLowerCase().includes(q) ||
    e.id.toLowerCase().includes(q)
  )
})

function eventColor(event: string): string {
  if (event.includes('payout') || event.includes('completed') || event.includes('deposit') || event.includes('reward') || event.includes('yield')) return 'text-success'
  if (event.includes('pending') || event.includes('processing') || event.includes('requested')) return 'text-warning'
  if (event.includes('failed') || event.includes('rejected') || event.includes('error')) return 'text-destructive'
  if (event.includes('manual') || event.includes('adjustment')) return 'text-primary'
  return 'text-muted-foreground'
}

function eventBadge(event: string): 'success' | 'warning' | 'destructive' | 'outline' {
  if (event.includes('payout') || event.includes('completed') || event.includes('deposit') || event.includes('reward') || event.includes('yield')) return 'success'
  if (event.includes('pending') || event.includes('processing') || event.includes('requested')) return 'warning'
  if (event.includes('failed') || event.includes('rejected') || event.includes('error')) return 'destructive'
  return 'outline'
}

function formatAmount(n: number, currency: string): string {
  const sym = currency === 'USD' ? '$' : currency + ' '
  return sym + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 })
}

function formatTime(ts: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  return isNaN(d.getTime()) ? ts : d.toLocaleString('es-AR')
}

async function loadEntries() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<any>('/financial/ledger', { limit: limit.value })
    entries.value = res || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar ledger'
  } finally {
    loading.value = false
  }
}

function viewDetail(entry: LedgerEntry) {
  selectedEntry.value = entry
  viewMode.value = 'detail'
}

function backToList() {
  selectedEntry.value = null
  viewMode.value = 'list'
}

onMounted(loadEntries)
</script>

<template>
  <div class="space-y-6 animate-in">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Database class="h-4 w-4 text-primary" />
          <span class="font-mono text-[10px] font-bold tracking-widest text-primary">TRUTH INSPECTOR</span>
        </div>
        <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Truth Inspector</h1>
        <p class="text-xs text-muted-foreground">Ledger inmutable — cada entrada tiene procedencia, categoría y confianza</p>
      </div>
      <Button variant="outline" size="sm" @click="loadEntries">
        <RotateCw class="h-3.5 w-3.5" :class="{ 'animate-spin': loading }" />
        Recargar
      </Button>
    </div>

    <div class="flex items-center gap-3">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar en ledger..."
          class="w-full rounded-lg border border-border/60 bg-surface/30 pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none font-mono"
        />
      </div>
      <span class="font-mono text-[9px] text-muted-foreground">{{ filteredEntries.length }} entradas</span>
    </div>

    <template v-if="loading && entries.length === 0">
      <Skeleton class="h-96 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center">
        <AlertTriangle class="h-8 w-8 text-destructive mb-4" />
        <p class="text-sm text-foreground">{{ error }}</p>
      </div>
    </template>

    <!-- Detail view -->
    <template v-else-if="viewMode === 'detail' && selectedEntry">
      <Card class="p-4 space-y-4">
        <div class="flex items-center justify-between">
          <Button variant="ghost" size="sm" @click="backToList">
            ← Volver
          </Button>
          <Badge :variant="eventBadge(selectedEntry.event)" class="text-[9px]">
            {{ selectedEntry.event }}
          </Badge>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Entry ID</p>
            <p class="font-mono text-xs text-foreground break-all">{{ selectedEntry.id }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Source ID</p>
            <p class="font-mono text-xs text-foreground break-all">{{ selectedEntry.source_id || '—' }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Monto</p>
            <p class="font-mono text-sm font-bold text-foreground">{{ formatAmount(selectedEntry.amount, selectedEntry.currency) }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Moneda</p>
            <p class="font-mono text-xs text-foreground">{{ selectedEntry.currency }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Source</p>
            <p class="font-mono text-xs text-foreground">{{ selectedEntry.source }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Platform</p>
            <p class="font-mono text-xs text-foreground">{{ selectedEntry.platform }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Timestamp</p>
            <p class="font-mono text-xs text-foreground">{{ formatTime(selectedEntry.timestamp) }}</p>
          </div>
          <div>
            <p class="font-mono text-[9px] text-muted-foreground uppercase">Reconciled</p>
            <p class="font-mono text-xs" :class="selectedEntry.reconciled ? 'text-success' : 'text-muted-foreground'">
              {{ selectedEntry.reconciled ? '✓ Sí' : '✗ No' }}
            </p>
          </div>
        </div>

        <div>
          <p class="font-mono text-[9px] text-muted-foreground uppercase mb-1">Descripción</p>
          <p class="font-mono text-xs text-foreground bg-surface/30 rounded-lg px-3 py-2">{{ selectedEntry.description }}</p>
        </div>

        <div>
          <p class="font-mono text-[9px] text-muted-foreground uppercase mb-1">Metadata</p>
          <pre class="font-mono text-[9px] text-muted-foreground bg-surface/30 rounded-lg px-3 py-2 overflow-x-auto">{{ JSON.stringify(selectedEntry.metadata, null, 2) }}</pre>
        </div>
      </Card>
    </template>

    <!-- List view -->
    <template v-else>
      <div class="space-y-1">
        <div
          v-for="entry in filteredEntries"
          :key="entry.id"
          class="rounded-xl border border-border/20 bg-surface/10 p-3 cursor-pointer hover:bg-surface/30 transition-colors"
          @click="viewDetail(entry)"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <Badge :variant="eventBadge(entry.event)" class="text-[8px] shrink-0 uppercase">
                {{ entry.event.replace(/_/g, ' ') }}
              </Badge>
              <span class="font-mono text-[10px] text-muted-foreground truncate">{{ entry.source }}</span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="font-mono text-xs font-bold tabular-nums" :class="eventColor(entry.event)">
                {{ entry.amount >= 0 ? '+' : '' }}{{ formatAmount(entry.amount, entry.currency) }}
              </span>
              <TrendingUp class="h-3 w-3 text-muted-foreground/50" />
            </div>
          </div>
          <div class="mt-1 flex items-center gap-3 font-mono text-[9px] text-muted-foreground">
            <span>{{ entry.platform }}</span>
            <span>{{ formatTime(entry.timestamp) }}</span>
            <span v-if="entry.reconciled" class="text-success">✓ reconciliado</span>
          </div>
          <p class="mt-0.5 font-mono text-[9px] text-muted-foreground/70 truncate">{{ entry.description }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
