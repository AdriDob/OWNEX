<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { ArrowLeft, Brain, ExternalLink, TrendingUp, Clock, DollarSign, Shield, FileText, Lightbulb, Target, RefreshCw, Download, GitCompare, Globe, ListTree, AlertTriangle } from '@lucide/vue'
import BarChart from '@/components/charts/BarChart.vue'

interface ProgramDetail {
  id: number; name: string; platform: string; program_url: string | null
  private: boolean; status: string; scope_summary: string | null
  rewards_text: string | null; exclusions_text: string | null
  policy_text: string | null; technologies: string | null
  assets: string | null; orion_score: number; priority: string
  total_reports: number; confirmed_reports: number
  total_earned: number; total_hours_spent: number
  tier_count: number; last_scope_fetch: string | null
  created_at: string | null
}
interface IntelDetail {
  id: number; program_id: number; ai_summary: string | null
  technologies_list: string | null; recent_changes: string | null
  historical_bugs: string | null; public_reports: string | null
  hypotheses: string | null; interesting_endpoints: string | null
  notes: string | null; pending_ideas: string | null
  score: number; priority: string
  last_analyzed_at: string | null; updated_at: string | null
}
interface BountyTier {
  id: number; tier_name: string; min_reward: number
  max_reward: number | null; currency: string; requirements: string | null
}
interface ScopeDoc {
  id: number; program_id: number; original_url: string | null
  content_type: string | null; summary: string | null; hash: string | null
  assets_extracted: string | null; changes_from_previous: string | null
  fetched_at: string | null; created_at: string | null
}

const route = useRoute()
const router = useRouter()
const programId = Number(route.params.id)
const program = ref<ProgramDetail | null>(null)
const intel = ref<IntelDetail | null>(null)
const tiers = ref<BountyTier[]>([])
const scopes = ref<ScopeDoc[]>([])
const loading = ref(true)
const analyzing = ref(false)
const error = ref<string | null>(null)
const readingScope = ref(false)

onMounted(async () => {
  try {
    const [p, t, s] = await Promise.all([
      api.get<ProgramDetail>(`/economic/programs/${programId}`),
      api.get<BountyTier[]>(`/economic/programs/${programId}/tiers`),
      api.get<ScopeDoc[]>(`/economic/programs/${programId}/scopes`),
    ])
    program.value = p; tiers.value = t || []; scopes.value = s || []
  } catch (e: any) { error.value = e?.message || 'Programa no encontrado'; program.value = null }
  finally { loading.value = false }

  try {
    const i = await api.get<IntelDetail>(`/economic/programs/${programId}/intel`)
    intel.value = i
  } catch { /* no intel */ }
})

async function runAnalysis() {
  analyzing.value = true
  try {
    const i = await api.post<IntelDetail>(`/economic/programs/${programId}/analyze`)
    intel.value = i
  } catch { /* error */ }
  finally { analyzing.value = false }
}

async function readScope() {
  readingScope.value = true
  try {
    const result = await api.post<any>(`/economic/programs/${programId}/read-scope`)
    // Reload program + scopes
    const [p, s] = await Promise.all([
      api.get<ProgramDetail>(`/economic/programs/${programId}`),
      api.get<ScopeDoc[]>(`/economic/programs/${programId}/scopes`),
    ])
    program.value = p; scopes.value = s || []
  } catch { /* error */ }
  finally { readingScope.value = false }
}

function scoreColor(s: number) {
  if (s >= 0.8) return 'success' as const
  if (s >= 0.6) return 'info' as const
  if (s >= 0.4) return 'warning' as const
  return 'default' as const
}
function priorityBadge(p: string) {
  if (p === 'critical') return 'destructive' as const
  if (p === 'high') return 'warning' as const
  if (p === 'medium') return 'default' as const
  return 'outline' as const
}
function formatMoney(n: number | null | undefined) {
  if (!n) return '—'
  return '$' + n.toLocaleString()
}
function parseJsonList(val: string | null): string[] {
  if (!val) return []
  try { return JSON.parse(val) } catch { return [] }
}
function parseJsonObj(val: string | null): Record<string, any> {
  if (!val) return {}
  try { return JSON.parse(val) } catch { return {} }
}
function latestScope(): ScopeDoc | null {
  return scopes.value.length ? scopes.value[0] : null
}
</script>

<template>
  <div class="space-y-6">
    <!-- Back -->
    <button class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" @click="router.push({ name: 'money-radar' })">
      <ArrowLeft class="h-3 w-3" />
      Volver al Money Radar
    </button>

    <!-- Loading -->
    <div v-if="loading" class="space-y-4">
      <Skeleton class="h-8 w-64 rounded-lg" />
      <Skeleton class="h-40 rounded-xl" />
      <Skeleton class="h-60 rounded-xl" />
    </div>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="program">
      <!-- Header -->
      <div class="animate-in space-y-4">
        <div class="flex items-start justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <h1 class="font-display text-2xl font-bold text-foreground">{{ program.name }}</h1>
              <Badge :variant="scoreColor(program.orion_score)">{{ program.orion_score.toFixed(3) }}</Badge>
              <Badge :variant="priorityBadge(program.priority)" class="capitalize">{{ program.priority }}</Badge>
            </div>
            <div class="flex items-center gap-3 text-xs text-muted-foreground">
              <span class="capitalize">{{ program.platform }}</span>
              <Badge v-if="program.private" variant="outline">Privado</Badge>
              <Badge :variant="program.status === 'active' ? 'success' : 'default'">{{ program.status }}</Badge>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="default" size="sm" :disabled="analyzing" @click="runAnalysis">
              <Brain v-if="!analyzing" class="mr-1 h-3 w-3" />
              <span v-else class="mr-1 h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
              {{ analyzing ? 'Analizando...' : 'Analizar con IA' }}
            </Button>
            <Button v-if="program.program_url" variant="outline" size="sm" as="a" :href="program.program_url" target="_blank">
              <ExternalLink class="mr-1 h-3 w-3" />
              Abrir Programa
            </Button>
          </div>
        </div>
      </div>

      <!-- Stats row -->
      <div class="grid animate-in grid-cols-2 gap-3 sm:grid-cols-4">
        <Card class="p-3">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><DollarSign class="h-3 w-3" /> Ganado</div>
          <p class="mt-1 text-lg font-bold text-foreground">{{ formatMoney(program.total_earned) }}</p>
        </Card>
        <Card class="p-3">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><FileText class="h-3 w-3" /> Reportes</div>
          <p class="mt-1 text-lg font-bold text-foreground">{{ program.total_reports }} <span class="text-xs text-muted-foreground">({{ program.confirmed_reports }} ok)</span></p>
        </Card>
        <Card class="p-3">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><Clock class="h-3 w-3" /> Horas</div>
          <p class="mt-1 text-lg font-bold text-foreground">{{ program.total_hours_spent.toFixed(1) }}h</p>
        </Card>
        <Card class="p-3">
          <div class="flex items-center gap-2 text-xs text-muted-foreground"><Globe class="h-3 w-3" /> Último scope</div>
          <p class="mt-1 text-lg font-bold text-foreground text-xs">{{ program.last_scope_fetch ? new Date(program.last_scope_fetch).toLocaleDateString() : 'Nunca' }}</p>
        </Card>
      </div>

      <!-- Metrics Chart -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Métricas del Programa</h3>
        <BarChart
          :labels="['Reportes', 'Confirmados', 'Horas', 'Tiers']"
          :datasets="[{ label: 'Programa', data: [program.total_reports, program.confirmed_reports, program.total_hours_spent, program.tier_count] }]"
          :height="200"
        />
      </Card>

      <!-- AI Analysis -->
      <Card v-if="intel?.ai_summary" class="animate-in p-4">
        <div class="flex items-center gap-2 mb-3">
          <Brain class="h-4 w-4 text-primary" />
          <h2 class="text-sm font-semibold text-foreground">Intelligence Analysis</h2>
          <span v-if="intel.last_analyzed_at" class="text-xs text-muted-foreground">· {{ new Date(intel.last_analyzed_at).toLocaleDateString() }}</span>
        </div>
        <p class="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">{{ intel.ai_summary }}</p>
      </Card>
      <Card v-else class="animate-in p-6 text-center">
        <Brain class="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
        <p class="text-sm text-muted-foreground">Este programa todavía no tiene análisis de inteligencia</p>
        <Button variant="default" size="sm" class="mt-3" :disabled="analyzing" @click="runAnalysis">
          {{ analyzing ? 'Analizando...' : 'Generar análisis con IA' }}
        </Button>
      </Card>

      <!-- Scope Reader -->
      <Card class="animate-in p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <Target class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-semibold text-foreground">Scope Reader</h2>
            <span v-if="latestScope()?.fetched_at" class="text-xs text-muted-foreground">
              · Último: {{ new Date(latestScope()!.fetched_at!).toLocaleString() }}
            </span>
          </div>
          <Button v-if="program.program_url" variant="outline" size="sm" :disabled="readingScope" @click="readScope">
            <Download v-if="!readingScope" class="mr-1 h-3 w-3" />
            <span v-else class="mr-1 h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            {{ readingScope ? 'Leyendo...' : 'Leer Scope' }}
          </Button>
        </div>

        <!-- Latest scope summary -->
        <div v-if="latestScope()" class="space-y-3">
          <div v-if="latestScope()!.summary" class="rounded-lg bg-surface/30 p-3">
            <p class="text-sm text-muted-foreground">{{ latestScope()!.summary }}</p>
          </div>

          <!-- Changes -->
          <div v-if="latestScope()!.changes_from_previous" class="space-y-1">
            <p class="flex items-center gap-1 text-xs font-semibold text-foreground">
              <GitCompare class="h-3 w-3" /> Cambios detectados
            </p>
            <div v-for="(chg, i) in parseJsonList(latestScope()!.changes_from_previous)" :key="i"
              class="flex items-start gap-2 rounded-lg px-3 py-2 text-xs"
              :class="chg.includes('No se detectaron') ? 'bg-surface/20 text-muted-foreground' : 'bg-warning/10 text-warning'">
              <span v-if="!chg.includes('No se detectaron')" class="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
              {{ chg }}
            </div>
          </div>

          <!-- Extracted assets -->
          <div v-if="latestScope()!.assets_extracted" class="space-y-1">
            <p class="flex items-center gap-1 text-xs font-semibold text-foreground">
              <ListTree class="h-3 w-3" /> Assets extraídos
            </p>
            <div class="flex flex-wrap gap-2">
              <template v-for="(items, key) in parseJsonObj(latestScope()!.assets_extracted)" :key="key">
                <span v-for="item in (items as string[]).slice(0, 5)" :key="item"
                  class="rounded-md bg-surface/40 px-2 py-0.5 text-[11px] text-muted-foreground">
                  {{ item }}
                </span>
                <span v-if="(items as string[]).length > 5" class="text-[11px] text-muted-foreground">
                  +{{ (items as string[]).length - 5 }} más
                </span>
              </template>
              <span v-if="!Object.keys(parseJsonObj(latestScope()!.assets_extracted)).length" class="text-xs text-muted-foreground">
                (sin assets extraídos)
              </span>
            </div>
          </div>
        </div>

        <div v-else class="py-4 text-center">
          <Download class="mx-auto mb-2 h-6 w-6 text-muted-foreground" />
          <p class="text-xs text-muted-foreground">Scope no leído todavía. Presioná "Leer Scope" para descargar e indexar.</p>
        </div>
      </Card>

      <!-- Scope history (all docs) -->
      <div v-if="scopes.length > 1" class="animate-in space-y-2">
        <h2 class="text-sm font-semibold text-foreground">Historial de Scopes</h2>
        <div class="space-y-1">
          <div v-for="(s, i) in scopes" :key="s.id" class="flex items-center justify-between rounded-lg px-3 py-2 text-xs text-muted-foreground hover:bg-surface/20">
            <div class="flex items-center gap-2">
              <span class="font-mono">{{ s.hash?.slice(0, 8) || '—' }}</span>
              <span>{{ new Date(s.fetched_at!).toLocaleString() }}</span>
              <Badge v-if="i === 0" variant="success" class="text-[10px]">Actual</Badge>
            </div>
            <span class="text-muted-foreground">{{ s.content_type || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- Bounty Tiers -->
      <div v-if="tiers.length" class="animate-in space-y-2">
        <h2 class="text-sm font-semibold text-foreground">Bounty Tiers</h2>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Card v-for="t in tiers" :key="t.id" class="p-3">
            <Badge variant="outline" class="mb-2">{{ t.tier_name }}</Badge>
            <p class="text-lg font-bold text-foreground">
              {{ formatMoney(t.min_reward) }}<span v-if="t.max_reward"> – {{ formatMoney(t.max_reward) }}</span>
            </p>
            <p class="text-xs text-muted-foreground">{{ t.currency }}</p>
            <p v-if="t.requirements" class="mt-1 text-xs text-muted-foreground">{{ t.requirements }}</p>
          </Card>
        </div>
      </div>

      <!-- Intel Sections -->
      <div v-if="intel" class="grid animate-in grid-cols-1 gap-4 lg:grid-cols-2">
        <Card v-if="parseJsonList(intel.interesting_endpoints).length" class="p-4">
          <h3 class="mb-2 flex items-center gap-1 text-xs font-semibold text-foreground"><Target class="h-3 w-3" /> Endpoints</h3>
          <ul class="space-y-1">
            <li v-for="(ep, i) in parseJsonList(intel.interesting_endpoints)" :key="i" class="text-xs text-muted-foreground">{{ ep }}</li>
          </ul>
        </Card>
        <Card v-if="parseJsonList(intel.pending_ideas).length" class="p-4">
          <h3 class="mb-2 flex items-center gap-1 text-xs font-semibold text-foreground"><Lightbulb class="h-3 w-3" /> Ideas</h3>
          <ul class="space-y-1">
            <li v-for="(idea, i) in parseJsonList(intel.pending_ideas)" :key="i" class="text-xs text-muted-foreground">{{ idea }}</li>
          </ul>
        </Card>
      </div>
    </template>

    <!-- Not found -->
    <div v-else class="flex flex-col items-center py-20 text-center">
      <p class="text-sm text-muted-foreground">Programa no encontrado</p>
      <Button variant="outline" size="sm" class="mt-3" @click="router.push({ name: 'money-radar' })">Volver al Money Radar</Button>
    </div>
  </div>
</template>
