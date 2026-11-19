<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useDiscoveryStore } from '@/stores/discovery'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import { Radio, Play, Wrench, DollarSign, Plug, FlaskConical, Check, Mail, Flag } from "@lucide/vue"

const store = useDiscoveryStore()
const busyKey = ref<string | null>(null)

const statusCounts = computed(() => {
  const byStatus: Record<string, number> = {}
  for (const o of store.liveOpportunities.value) {
    byStatus[o.status] = (byStatus[o.status] ?? 0) + 1
  }
  return byStatus
})

const verifiedIncome = computed(() => {
  const fin = store.liveRevenue.value?.financial
  return fin?.verified_income_total_usd ?? 0
})

const advertisedTotal = computed(() => {
  const fin = store.liveRevenue.value?.financial?.by_bucket?.advertised ?? {}
  return Object.values(fin).reduce((a: number, b: any) => a + (b ?? 0), 0)
})

const connectionCounts = computed(() => store.liveConnections.value?.counts ?? {})

const STATUS_ORDER = ['ready', 'in_progress', 'submitted', 'accepted', 'paid', 'eligibility_checked', 'discovered', 'expired', 'rejected']

function statusColor(s: string): string {
  if (s === 'ready' || s === 'paid') return 'text-success'
  if (s === 'in_progress' || s === 'submitted' || s === 'accepted') return 'text-info'
  if (s === 'rejected') return 'text-destructive'
  if (s === 'expired') return 'text-muted-foreground'
  return 'text-warning'
}

function oppKey(o: any): string {
  return `${o.platform}:${o.id}`
}

async function run(key: string, fn: () => Promise<any>) {
  busyKey.value = key
  try {
    const res = await fn()
    if (res && res.error) window.alert(`Error: ${res.error}`)
    await Promise.all([
      store.fetchLiveOpportunities(),
      store.fetchLiveStats(),
      store.fetchLiveRevenue(),
      store.fetchLiveRank(20),
    ])
  } finally {
    busyKey.value = null
  }
}

const handlePrepare = (key: string) => run(key, () => store.prepareLiveOpportunity(key))
const handleAnalyze = (key: string) => run(key, () => store.analyzeLiveOpportunity(key, true))
const handleApprove = (key: string) => {
  const note = window.prompt('Nota de aprobación (opcional):', '') ?? ''
  return run(key, () => store.approveLiveOpportunity(key, true, note))
}
const handlePaymentInquiry = (key: string) => run(key, () => store.paymentInquiryLive(key))

// External lifecycle transitions — evidence is mandatory, nothing is inferred.
const NEXT_STATUS: Record<string, string[]> = {
  in_progress: ['submitted', 'rejected'],
  submitted: ['accepted', 'rejected', 'expired'],
  accepted: ['paid'],
}

function handleStatus(key: string, status: string) {
  const ref = window.prompt(
    `Evidencia externa para marcar "${status}" (URL, ID de pago, referencia de entrega):`,
    '',
  )
  if (!ref) return
  const evidence: Record<string, any> = { reference: ref }
  if (/^https?:\/\//.test(ref)) evidence.url = ref
  let amount: number | undefined
  let currency: string | undefined
  if (status === 'paid') {
    const amt = window.prompt('Monto REAL cobrado (número, vacío = usar recompensa anunciada):', '')
    if (amt) {
      const n = Number(amt.replace(',', '.'))
      if (Number.isFinite(n) && n > 0) amount = n
    }
    currency = window.prompt('Moneda del pago (USD/EUR/ARS...):', 'USD') ?? undefined
  }
  return run(key, () => store.recordLiveStatus(key, status, evidence, amount, currency))
}

onMounted(async () => {
  await Promise.all([
    store.fetchLiveStats(),
    store.fetchLiveOpportunities(undefined, 100),
    store.fetchLiveConnections(),
    store.fetchLiveRevenue(),
    store.fetchLiveRank(20),
  ])
})
</script>

<template>
  <Card class="p-4">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <Radio class="h-3.5 w-3.5 text-primary" />
        <p class="font-mono text-xs font-semibold text-foreground">Live Opportunity Pipeline</p>
      </div>
      <Button variant="outline" size="sm" :disabled="store.liveLoading" @click="store.runLiveScan()">
        <Play v-if="!store.liveLoading" class="h-3 w-3" />
        <span v-else class="animate-pulse">...</span>
        Live Scan
      </Button>
    </div>

    <!-- Lifecycle counts -->
    <div class="grid grid-cols-3 gap-2 sm:grid-cols-9 mb-3">
      <div v-for="s in STATUS_ORDER" :key="s" class="rounded-lg border border-border/30 bg-surface/10 px-2 py-1.5 text-center">
        <p class="font-display text-sm font-bold" :class="statusColor(s)">{{ statusCounts[s] ?? 0 }}</p>
        <p class="font-mono text-[8px] uppercase text-muted-foreground">{{ s.replace('_', ' ') }}</p>
      </div>
    </div>

    <!-- Money honesty row -->
    <div class="flex flex-wrap gap-4 mb-3 font-mono text-[9px]">
      <span class="text-muted-foreground">
        Ingresos verificados: <span class="text-success font-bold">USD {{ verifiedIncome.toFixed(2) }}</span>
      </span>
      <span class="text-muted-foreground">
        Recompensas anunciadas: <span class="text-warning">USD {{ advertisedTotal.toFixed(0) }}</span>
        <span class="text-muted-foreground/60">(no es ingreso)</span>
      </span>
      <span class="text-muted-foreground">
        <Plug class="inline h-2.5 w-2.5" />
        Conexiones: {{ connectionCounts.configured ?? 0 }} configuradas ·
        {{ connectionCounts.pending ?? 0 }} pendientes ·
        {{ connectionCounts.public ?? 0 }} públicas
      </span>
    </div>

    <!-- Revenue-first ranking -->
    <div v-if="store.liveRank.value?.length" class="mb-3">
      <p class="font-mono text-[9px] uppercase text-muted-foreground mb-1">
        Top viabilidad (score · confianza · USD/h estimado)
      </p>
      <div class="space-y-1">
        <div
          v-for="r in store.liveRank.value.slice(0, 5)"
          :key="r.opportunity_id"
          class="flex items-center gap-2 rounded border border-border/20 bg-surface/5 px-2 py-1"
        >
          <span class="font-display text-xs font-bold text-primary w-8">{{ r.score.toFixed(0) }}</span>
          <span class="font-mono text-[8px] text-muted-foreground w-10">{{ (r.confidence * 100).toFixed(0) }}%</span>
          <span class="font-mono text-[8px] text-muted-foreground w-12">${{ r.estimated_net_per_hour_usd }}/h</span>
          <span class="font-mono text-[9px] text-foreground truncate flex-1">{{ r.opportunity_id }}</span>
          <Badge variant="outline" class="text-[8px]" :class="statusColor(r.status)">{{ r.status }}</Badge>
        </div>
      </div>
    </div>

    <!-- Actionable items -->
    <div v-if="store.liveOpportunities.value.length === 0" class="font-mono text-[10px] text-muted-foreground py-2">
      Sin oportunidades live persistidas — corré un Live Scan.
    </div>
    <div v-else class="space-y-1.5 max-h-80 overflow-y-auto">
      <div
        v-for="o in store.liveOpportunities.value.slice(0, 30)"
        :key="oppKey(o)"
        class="flex items-center gap-2 rounded-lg border border-border/20 bg-surface/10 px-2 py-1.5"
      >
        <Badge variant="outline" class="text-[8px] shrink-0" :class="statusColor(o.status)">{{ o.status }}</Badge>
        <div class="min-w-0 flex-1">
          <p class="font-mono text-[10px] text-foreground truncate">{{ o.title }}</p>
          <p class="font-mono text-[8px] text-muted-foreground truncate">
            {{ o.platform }}<span v-if="o.reward"> · {{ o.reward }} {{ o.currency }}</span>
          </p>
        </div>
        <div class="flex items-center gap-0.5 shrink-0">
          <Button
            v-if="o.status === 'ready'"
            variant="ghost" size="sm"
            title="Preparar workspace de ejecución"
            :disabled="busyKey === oppKey(o)"
            @click="handlePrepare(oppKey(o))"
          >
            <Wrench class="h-3 w-3" />
          </Button>
          <template v-if="o.status === 'in_progress'">
            <Button variant="ghost" size="sm" title="Analizar repo + correr tests" :disabled="busyKey === oppKey(o)" @click="handleAnalyze(oppKey(o))">
              <FlaskConical class="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="sm" title="Registrar aprobación humana" :disabled="busyKey === oppKey(o)" @click="handleApprove(oppKey(o))">
              <Check class="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="sm" title="Draft consulta de términos de pago (no envía)" :disabled="busyKey === oppKey(o)" @click="handlePaymentInquiry(oppKey(o))">
              <Mail class="h-3 w-3" />
            </Button>
          </template>
          <template v-for="ns in (NEXT_STATUS[o.status] ?? [])" :key="ns">
            <Button
              variant="ghost" size="sm"
              :title="`Marcar ${ns} (requiere evidencia)`"
              :disabled="busyKey === oppKey(o)"
              @click="handleStatus(oppKey(o), ns)"
            >
              <Flag class="h-3 w-3" :class="ns === 'paid' ? 'text-success' : ns === 'rejected' || ns === 'expired' ? 'text-destructive' : 'text-info'" />
            </Button>
          </template>
          <a
            v-if="o.url" :href="o.url" target="_blank" rel="noopener"
            class="text-muted-foreground hover:text-primary shrink-0"
          >
            <DollarSign class="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  </Card>
</template>
