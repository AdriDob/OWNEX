<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import type { FindingItem } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { BarChart } from '@/components/charts'
import { Activity, AlertTriangle, ArrowLeft, BarChart3, Bug, DollarSign, Hash, RefreshCw, Server, Shield, Zap } from '@lucide/vue'

interface EndpointDetail {
  id: number
  target_id: number
  target_name: string
  path: string
  method: string
  risk_score: number
  vector: string
  reason: string
  ownership_risk: boolean
  parameter_count: number
  created_at: string | null
}

const route = useRoute()
const router = useRouter()
const endpointId = computed(() => Number(route.params.id))

const endpoint = ref<EndpointDetail | null>(null)
const findings = ref<FindingItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const validating = ref(false)
const scanning = ref(false)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [ep, f] = await Promise.all([
      api.get<EndpointDetail>(`/endpoints/${endpointId.value}`),
      api.get<{ items: FindingItem[]; total: number }>('/findings', { endpoint_id: endpointId.value }),
    ])
    endpoint.value = ep
    findings.value = f.items || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el endpoint'
  } finally {
    loading.value = false
  }
}

async function handleValidate() {
  if (!endpoint.value) return
  validating.value = true
  try {
    // POST /api/validation/validate (ValidateHotPathRequest)
    await api.post('/validation/validate', {
      hot_path_id: `endpoint-${endpoint.value.id}`,
      endpoint_id: endpoint.value.id,
      target_id: endpoint.value.target_id,
      url: endpoint.value.path,
      method: endpoint.value.method,
    })
  } catch { /* surfaced via status polling / toast elsewhere */ }
  finally { validating.value = false }
}

async function handleIdorScan() {
  if (!endpoint.value) return
  scanning.value = true
  try {
    // POST /api/idor/idor (IDORScanRequest) — identity_baseline_id=0 usa el
    // resolver sin sesión autenticada (baseline anónima).
    await api.post('/idor/idor', {
      target_id: endpoint.value.target_id,
      endpoint_id: endpoint.value.id,
      url: endpoint.value.path,
      method: endpoint.value.method,
      identity_baseline_id: 0,
    })
  } catch { /* ignore */ }
  finally { scanning.value = false }
}

const riskColor = computed(() => {
  if (!endpoint.value) return 'text-muted-foreground'
  const s = endpoint.value.risk_score
  if (s >= 0.7) return 'text-destructive'
  if (s >= 0.4) return 'text-warning'
  if (s >= 0.2) return 'text-accent'
  return 'text-success'
})

const chartData = computed(() => {
  if (!endpoint.value) return { labels: [], datasets: [] }
  return {
    labels: ['Risk Score', 'Parameter Count'],
    datasets: [{
      label: 'Valor',
      data: [endpoint.value.risk_score * 10, endpoint.value.parameter_count],
      backgroundColor: ['rgba(0, 213, 255,0.7)', 'rgba(255, 255, 255,0.7)'],
    }],
  }
})

function severityVariant(sev: string) {
  const map: Record<string, 'destructive' | 'warning' | 'info' | 'success' | 'default'> = {
    critical: 'destructive', high: 'warning', medium: 'info', low: 'success', info: 'default',
  }
  return map[sev.toLowerCase()] || 'default'
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 animate-in">
      <Button variant="ghost" size="icon" @click="router.back()">
        <ArrowLeft class="h-4 w-4" />
      </Button>
      <div>
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Endpoint</p>
        <h1 class="font-display text-2xl font-bold text-foreground truncate max-w-lg">
          {{ endpoint ? `${endpoint.method} ${endpoint.path}` : 'Detalle de Endpoint' }}
        </h1>
      </div>
    </div>

    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton class="h-32 rounded-xl" />
        <Skeleton class="h-32 rounded-xl" />
        <Skeleton class="h-32 rounded-xl" />
      </div>
      <Skeleton class="h-64 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar el endpoint</p>
        <p class="mt-1 text-xs text-muted-foreground max-w-md">{{ error }}</p>
        <Button variant="outline" class="mt-4" @click="fetchData">
          <RefreshCw class="h-3.5 w-3.5" /> Reintentar
        </Button>
      </div>
    </template>

    <template v-else-if="!endpoint">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Shield class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Endpoint no encontrado</p>
        <p class="mt-1 text-xs text-muted-foreground">El endpoint solicitado no existe o fue eliminado</p>
        <Button variant="outline" class="mt-4" @click="router.push('/attack-surface')">
          Volver a Superficie de Ataque
        </Button>
      </div>
    </template>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 animate-in">
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Server class="h-4 w-4 text-primary" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Target</span>
          </div>
          <p class="text-sm font-semibold text-foreground">{{ endpoint.target_name }}</p>
          <p class="text-xs text-muted-foreground mt-0.5">ID: {{ endpoint.target_id }}</p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Hash class="h-4 w-4 text-accent" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk Score</span>
          </div>
          <p :class="['text-2xl font-bold', riskColor]">
            {{ (endpoint.risk_score * 100).toFixed(0) }}%
          </p>
        </Card>
        <Card class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <Activity class="h-4 w-4 text-gold" />
            <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Parámetros</span>
          </div>
          <p class="text-2xl font-bold text-foreground">{{ endpoint.parameter_count }}</p>
        </Card>
      </div>

      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Shield class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Información del Endpoint</span>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-muted-foreground">Path</p>
            <p class="font-mono text-foreground font-semibold mt-0.5">{{ endpoint.path }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Method</p>
            <Badge variant="info" class="mt-0.5 font-mono">{{ endpoint.method }}</Badge>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Vector</p>
            <p class="text-foreground mt-0.5">{{ endpoint.vector }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Ownership Risk</p>
            <Badge :variant="endpoint.ownership_risk ? 'destructive' : 'success'" class="mt-0.5">
              {{ endpoint.ownership_risk ? 'Sí' : 'No' }}
            </Badge>
          </div>
        </div>
        <p v-if="endpoint.reason" class="mt-3 text-xs text-muted-foreground/70 italic">{{ endpoint.reason }}</p>
      </Card>

      <div class="flex gap-3 animate-in">
        <Button @click="handleValidate" :disabled="validating" :loading="validating">
          <Activity class="h-4 w-4" /> {{ validating ? 'Validando...' : 'Validar Endpoint' }}
        </Button>
        <Button variant="secondary" @click="handleIdorScan" :disabled="scanning" :loading="scanning">
          <Zap class="h-4 w-4" /> {{ scanning ? 'Escaneando...' : 'Ejecutar IDOR Scan' }}
        </Button>
      </div>

      <Card class="p-4 animate-in" v-if="endpoint">
        <div class="flex items-center gap-2 mb-3">
          <BarChart3 class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk Assessment</span>
        </div>
        <BarChart
          :labels="chartData.labels"
          :datasets="chartData.datasets"
          :height="200"
          yLabel="Valor"
          :show-legend="false"
        />
      </Card>

      <div class="animate-in">
        <div class="flex items-center gap-2 mb-3">
          <Bug class="h-4 w-4 text-primary" />
          <h2 class="text-sm font-semibold text-foreground">Findings Asociados ({{ findings.length }})</h2>
        </div>
        <div v-if="findings.length === 0" class="py-12 text-center text-sm text-muted-foreground">
          No hay findings asociados a este endpoint
        </div>
        <div v-else class="space-y-2">
          <Card v-for="f in findings" :key="f.id" class="p-3 animate-in cursor-pointer hover:border-primary/30 transition-colors" @click="router.push(`/findings/${f.id}`)">
            <div class="flex items-start gap-2">
              <div class="mt-0.5">
                <Bug class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-semibold text-foreground">{{ f.title }}</span>
                  <Badge :variant="severityVariant(f.severity)" class="text-[10px] px-1.5 py-0">{{ f.severity }}</Badge>
                </div>
                <div class="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{{ f.target_name }}</span>
                  <span v-if="f.payout" class="text-gold font-semibold flex items-center gap-1">
                    <DollarSign class="h-3 w-3" /> ${{ f.payout.toLocaleString() }}
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>
