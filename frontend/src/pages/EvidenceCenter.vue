<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Search, FileSearch, Eye, EyeOff, Code, Check, X, ChevronDown, ChevronUp, AlertTriangle } from '@lucide/vue'
import BarChart from '@/components/charts/BarChart.vue'

interface EvidenceItem {
  id: number
  finding_id: number | null
  attempt_label: string
  request_url: string
  request_method: string
  request_headers: string | null
  request_body: string | null
  response_status: number
  response_headers: string | null
  response_body: string | null
  curl_command: string | null
  body_diff_ratio: number
  consistent: boolean
  created_at: string
}

const items = ref<EvidenceItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const expanded = ref<Record<number, boolean>>({})
const total = ref(0)
/** Filtro server-side por veredicto (GET /evidence?verdict_id=). */
const verdictFilter = ref<number | null>(null)
const verdictOptions = ref<Array<{ id: number; label: string }>>([])

async function loadEvidence(): Promise<void> {
  loading.value = true
  try {
    const params: Record<string, string | number> = { limit: 50 }
    if (verdictFilter.value != null) params.verdict_id = verdictFilter.value
    const res = await api.get<{ items: EvidenceItem[]; total: number }>('/evidence', params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error al cargar evidencia'
  } finally {
    loading.value = false
  }
}

async function loadVerdictOptions(): Promise<void> {
  try {
    const vs = await api.get<Array<{ id: number; status?: string; created_at?: string | null }>>('/verdicts', { limit: 100 })
    verdictOptions.value = (Array.isArray(vs) ? vs : []).slice(0, 100).map((v) => ({
      id: v.id,
      label: `#${v.id}${v.status ? ' · ' + v.status : ''}`,
    }))
  } catch { /* selector vacío: el filtro manual por ID sigue disponible */ }
}

function onVerdictFilterChange(): void {
  void loadEvidence()
}

onMounted(async () => {
  await Promise.allSettled([loadEvidence(), loadVerdictOptions()])
})

const filtered = computed(() => {
  if (!search.value) return items.value
  const q = search.value.toLowerCase()
  return items.value.filter(i =>
    i.attempt_label?.toLowerCase().includes(q) ||
    i.request_url?.toLowerCase().includes(q) ||
    i.request_method?.toLowerCase().includes(q)
  )
})

function toggleExpand(id: number) {
  expanded.value[id] = !expanded.value[id]
}

function tryFormatJson(raw: string | null): string {
  if (!raw) return '(empty)'
  try { return JSON.stringify(JSON.parse(raw), null, 2) }
  catch { return raw }
}

function diffColor(ratio: number) {
  if (ratio > 0.3) return 'destructive' as const
  if (ratio > 0.1) return 'warning' as const
  return 'default' as const
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Technical Evidence</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Evidence Center</h1>
      <p class="text-sm text-muted-foreground">Captured request/response pairs for validated findings</p>
    </div>

    <template v-if="loading">
      <div class="space-y-3">
        <Skeleton v-for="i in 4" :key="i" class="h-16 rounded-xl" />
      </div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <button @click="$router.go(0)" class="mt-4 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white">Reintentar</button>
      </div>
    </template>

    <template v-else-if="items.length === 0">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <FileSearch class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">No hay evidencia técnica</p>
        <p class="mt-1 text-xs text-muted-foreground">Validá hallazgos para generar evidencia de request/response</p>
      </div>
    </template>

    <template v-else>
      <!-- Filtros: búsqueda client-side + veredicto server-side -->
      <div class="flex flex-wrap items-center gap-3">
        <div class="relative max-w-xs flex-1 min-w-[220px] animate-in">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input v-model="search" placeholder="Buscar evidencia..."
            class="w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
          />
        </div>
        <select
          v-model.number="verdictFilter"
          class="rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-sm text-foreground focus:border-primary/30 focus:outline-none"
          @change="onVerdictFilterChange"
        >
          <option :value="null">Todos los veredictos</option>
          <option v-for="v in verdictOptions" :key="v.id" :value="v.id">{{ v.label }}</option>
          <option v-if="verdictFilter != null && !verdictOptions.some(o => o.id === verdictFilter)" :value="verdictFilter">
            Veredicto #{{ verdictFilter }}
          </option>
        </select>
      </div>

      <!-- Evidence Type Chart -->
      <Card class="animate-in p-4">
        <h3 class="text-xs font-semibold text-foreground mb-3">Tipos de Evidencia</h3>
        <BarChart
          :labels="['Consistente', 'Inconsistente']"
          :datasets="[{ label: 'Evidencia', data: [items.filter(i => i.consistent).length, items.filter(i => !i.consistent).length] }]"
          :height="200"
        />
      </Card>

      <!-- Summary -->
      <Card class="animate-in p-4">
        <div class="grid grid-cols-1 gap-4 text-center sm:grid-cols-3">
          <div>
            <p class="text-xs text-muted-foreground">Total</p>
            <p class="text-lg font-bold text-foreground">{{ total }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Consistentes</p>
            <p class="text-lg font-bold text-success">{{ items.filter(i => i.consistent).length }}</p>
          </div>
          <div>
            <p class="text-xs text-muted-foreground">Inconsistentes</p>
            <p class="text-lg font-bold text-destructive">{{ items.filter(i => !i.consistent).length }}</p>
          </div>
        </div>
      </Card>

      <!-- Evidence list -->
      <div class="space-y-2">
        <div v-for="item in filtered" :key="item.id" class="animate-in">
          <button
            @click="toggleExpand(item.id)"
            class="w-full rounded-xl border border-border/40 bg-surface/40 px-4 py-3 text-left transition-all hover:border-primary/30"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                :class="item.consistent ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'"
              >
                <component :is="item.consistent ? Check : X" class="h-4 w-4" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-semibold text-foreground">{{ item.attempt_label || `Evidence #${item.id}` }}</span>
                  <span class="rounded bg-surface/50 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">{{ item.request_method }}</span>
                  <Badge :variant="diffColor(item.body_diff_ratio)" class="text-[10px]">
                    {{ (item.body_diff_ratio * 100).toFixed(1) }}% diff
                  </Badge>
                </div>
                <p class="mt-0.5 text-xs text-muted-foreground truncate">{{ item.request_url }}</p>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="font-mono text-muted-foreground">{{ item.response_status }}</span>
                <component :is="expanded[item.id] ? ChevronUp : ChevronDown" class="h-3.5 w-3.5 text-muted-foreground" />
              </div>
            </div>
          </button>

          <!-- Expanded detail -->
          <Transition name="fade">
            <div v-if="expanded[item.id]" class="mt-1 rounded-xl border border-border/30 bg-background p-4 space-y-3">
              <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div>
                  <p class="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Request</p>
                  <pre class="rounded-lg bg-black/40 p-3 text-[11px] text-foreground font-mono overflow-auto max-h-60">{{ item.request_method }} {{ item.request_url }}{{ item.request_headers ? '\n' + tryFormatJson(item.request_headers) : '' }}{{ item.request_body ? '\n\n' + tryFormatJson(item.request_body) : '' }}</pre>
                </div>
                <div>
                  <p class="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Response ({{ item.response_status }})</p>
                  <pre class="rounded-lg bg-black/40 p-3 text-[11px] text-foreground font-mono overflow-auto max-h-60">{{ item.response_headers ? tryFormatJson(item.response_headers) + '\n' : '' }}{{ item.response_body ? tryFormatJson(item.response_body) : '(empty)' }}</pre>
                </div>
              </div>
              <div v-if="item.curl_command" class="mt-3">
                <div class="flex items-center gap-2 mb-1.5">
                  <Code class="h-3 w-3 text-muted-foreground" />
                  <span class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">cURL</span>
                </div>
                <pre class="rounded-lg bg-black/40 p-3 text-[10px] text-foreground font-mono overflow-auto">{{ item.curl_command }}</pre>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
