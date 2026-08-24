<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import BarChart from '@/components/charts/BarChart.vue'
import { AlertTriangle, BarChart3, Brain, ChevronRight, Play, RotateCw, Search, Shield, Target, Zap } from '@lucide/vue'

interface Hypothesis {
  id: string
  vulnerability_type: string
  target_id: number
  target_name: string
  endpoint?: Record<string, any>
  confidence: number
  impact: number
  likelihood: number
  priority_score: number
  evidence: string[]
  reasoning: string
  source: string
  vector: string
  estimated_difficulty: string
  estimated_reward_range: string
}

const hypotheses = ref<Hypothesis[]>([])
const loading = ref(true)
const error = ref('')
const running = ref(false)
const selectedTargetId = ref<number | null>(null)

const typeLabels: Record<string, string> = {
  idor: 'IDOR',
  auth_bypass: 'Auth Bypass',
  ssrf: 'SSRF',
  xss: 'XSS',
  sqli: 'SQLi',
  rce: 'RCE',
  lfi: 'LFI',
  open_redirect: 'Open Redirect',
  insecure_direct_object_reference: 'IDOR',
  server_side_request_forgery: 'SSRF',
  cross_site_scripting: 'XSS',
}

const typeVariants: Record<string, 'default' | 'destructive' | 'warning' | 'info' | 'success' | 'gold'> = {
  idor: 'warning',
  auth_bypass: 'destructive',
  ssrf: 'info',
  xss: 'destructive',
  sqli: 'destructive',
  rce: 'destructive',
  lfi: 'warning',
  open_redirect: 'default',
}

function typeVariant(type: string): 'default' | 'destructive' | 'warning' | 'info' | 'success' | 'gold' {
  const key = type.toLowerCase().replace(/\s+/g, '_')
  return typeVariants[key] || 'default'
}

function typeLabel(type: string): string {
  const key = type.toLowerCase().replace(/\s+/g, '_')
  return typeLabels[key] || type
}

const sortedByConfidence = computed(() => {
  return [...hypotheses.value].sort((a, b) => b.confidence - a.confidence)
})

const confidenceChartLabels = computed(() => sortedByConfidence.value.slice(0, 10).map(h => {
  const label = typeLabel(h.vulnerability_type)
  return `${label} (${h.target_name.slice(0, 12)})`
}))
const confidenceChartData = computed(() => sortedByConfidence.value.slice(0, 10).map(h => h.confidence))

async function fetchHypotheses() {
  loading.value = true
  error.value = ''
  try {
    // La cola se llena desde la generación real (POST /hypotheses/{target}).
    // Sin target generado aún → estado vacío honesto, no un fetch fantasma.
    if (hypotheses.value.length === 0 && !selectedTargetId.value) {
      hypotheses.value = []
      return
    }
    if (selectedTargetId.value) await generateFor(selectedTargetId.value)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar hipótesis'
  } finally {
    loading.value = false
  }
}

async function generateFor(targetId: number): Promise<void> {
  // POST /api/hypotheses/{target_id} → HypothesisEngineOutputOut
  const res = await api.post<{
    attack_queue: Hypothesis[]
    total_hypotheses: number
    summary?: string
  }>(`/hypotheses/${targetId}`)
  hypotheses.value = res.attack_queue || []
}

async function runHypotheses() {
  if (!selectedTargetId.value) return
  running.value = true
  try {
    await generateFor(selectedTargetId.value)
  } catch (e: any) {
    error.value = e?.message || 'Error al ejecutar hipótesis'
  } finally {
    running.value = false
  }
}

function scoreBarColor(score: number) {
  if (score >= 0.7) return 'bg-success'
  if (score >= 0.4) return 'bg-warning'
  return 'bg-destructive'
}

function difficultyColor(d: string) {
  if (d === 'easy') return 'text-success'
  if (d === 'medium') return 'text-warning'
  return 'text-destructive'
}

async function promoteToInvestigation(h: Hypothesis) {
  try {
    await api.post('/investigations', {
      title: `${typeLabel(h.vulnerability_type)} - ${h.target_name}`,
      hypothesis_id: h.id,
      target_id: h.target_id,
    })
    alert('Investigación creada')
  } catch {
    alert('Error al promover')
  }
}

onMounted(fetchHypotheses)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4 animate-in">
      <div class="space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Inteligencia</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Hypothesis Queue</h1>
        <p class="text-sm text-muted-foreground">{{ hypotheses.length }} hipótesis generadas</p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model.number="selectedTargetId"
          type="number"
          placeholder="Target ID"
          class="w-24 rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none"
        />
        <Button variant="default" size="sm" :disabled="running || !selectedTargetId" @click="runHypotheses">
          <Play v-if="!running" class="h-3.5 w-3.5" />
          <RotateCw v-else class="h-3.5 w-3.5 animate-spin" />
          {{ running ? 'Ejecutando...' : 'Run Hypotheses' }}
        </Button>
      </div>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 6" :key="i" class="h-48 rounded-xl" />
      </div>
    </template>

    <!-- Error -->
    <template v-else-if="error && !hypotheses.length">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
          <AlertTriangle class="h-8 w-8 text-destructive" />
        </div>
        <p class="text-sm font-semibold text-foreground">Error al cargar</p>
        <p class="mt-1 text-xs text-muted-foreground">{{ error }}</p>
        <Button variant="outline" size="sm" class="mt-4" @click="fetchHypotheses">
          <RotateCw class="h-3.5 w-3.5" />
          Reintentar
        </Button>
      </div>
    </template>

    <!-- Empty -->
    <template v-else-if="!hypotheses.length">
      <div class="flex flex-col items-center py-20 text-center animate-in">
        <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface/50 mb-4">
          <Brain class="h-8 w-8 text-muted-foreground/50" />
        </div>
        <p class="text-sm font-semibold text-foreground">Sin hipótesis</p>
        <p class="mt-1 text-xs text-muted-foreground">Ejecutá hypotheses run para generar hipótesis automáticas</p>
        <div class="flex items-center gap-2 mt-4">
          <input
            v-model.number="selectedTargetId"
            type="number"
            placeholder="Target ID"
            class="w-24 rounded-lg border border-border/60 bg-surface/50 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none"
          />
          <Button variant="default" size="sm" :disabled="!selectedTargetId" @click="runHypotheses">
            <Play class="h-3.5 w-3.5" /> Run Hypotheses
          </Button>
        </div>
      </div>
    </template>

    <!-- Content -->
    <template v-else>
      <!-- Confidence Chart -->
      <Card class="p-4 animate-in">
        <div class="flex items-center gap-2 mb-3">
          <BarChart3 class="h-4 w-4 text-primary" />
          <p class="text-xs font-semibold text-foreground">Confianza por Hipótesis (Top 10)</p>
        </div>
        <BarChart
          :labels="confidenceChartLabels"
          :datasets="[{ label: 'Confianza', data: confidenceChartData, backgroundColor: '#00d5ff' }]"
          :height="220"
          yLabel="Confianza"
          horizontal
        />
      </Card>

      <!-- Cards -->
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 animate-in">
        <Card v-for="h in hypotheses" :key="h.id" class="p-4 flex flex-col">
          <div class="flex items-start justify-between mb-2">
            <Badge :variant="typeVariant(h.vulnerability_type)" class="text-[10px]">
              {{ typeLabel(h.vulnerability_type) }}
            </Badge>
            <span class="text-[10px] font-mono text-muted-foreground">{{ h.source }}</span>
          </div>

          <div class="flex items-center gap-1.5 mb-3">
            <Target class="h-3 w-3 text-muted-foreground shrink-0" />
            <span class="text-xs font-semibold text-foreground truncate">{{ h.target_name }}</span>
            <span class="text-[10px] text-muted-foreground">#{{ h.target_id }}</span>
          </div>

          <!-- Scores -->
          <div class="space-y-2 mb-3 flex-1">
            <div>
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Confidence</span>
                <span class="font-semibold" :class="h.confidence >= 0.7 ? 'text-success' : h.confidence >= 0.4 ? 'text-warning' : 'text-destructive'">
                  {{ (h.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-surface">
                <div class="h-full rounded-full transition-all" :class="scoreBarColor(h.confidence)" :style="{ width: `${h.confidence * 100}%` }" />
              </div>
            </div>
            <div>
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Impact</span>
                <span class="font-semibold" :class="h.impact >= 0.7 ? 'text-success' : h.impact >= 0.4 ? 'text-warning' : 'text-destructive'">
                  {{ (h.impact * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-surface">
                <div class="h-full rounded-full transition-all" :class="scoreBarColor(h.impact)" :style="{ width: `${h.impact * 100}%` }" />
              </div>
            </div>
            <div>
              <div class="flex justify-between text-[10px] mb-0.5">
                <span class="text-muted-foreground">Exploitability</span>
                <span class="font-semibold" :class="h.likelihood >= 0.7 ? 'text-success' : h.likelihood >= 0.4 ? 'text-warning' : 'text-destructive'">
                  {{ (h.likelihood * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="h-1.5 overflow-hidden rounded-full bg-surface">
                <div class="h-full rounded-full transition-all" :class="scoreBarColor(h.likelihood)" :style="{ width: `${h.likelihood * 100}%` }" />
              </div>
            </div>
          </div>

          <!-- Evidence tags -->
          <div v-if="h.evidence?.length" class="flex flex-wrap gap-1 mb-3">
            <Badge v-for="ev in h.evidence.slice(0, 3)" :key="ev" variant="outline" class="text-[9px]">{{ ev }}</Badge>
            <Badge v-if="h.evidence.length > 3" variant="outline" class="text-[9px]">+{{ h.evidence.length - 3 }}</Badge>
          </div>

          <!-- Meta -->
          <div class="flex items-center justify-between text-[10px] text-muted-foreground mb-3">
            <span class="flex items-center gap-1">
              <Zap class="h-3 w-3" />
              {{ h.vector }}
            </span>
            <span :class="difficultyColor(h.estimated_difficulty)">{{ h.estimated_difficulty }}</span>
          </div>

          <!-- Action -->
          <Button variant="outline" size="sm" class="w-full" @click="promoteToInvestigation(h)">
            <ChevronRight class="h-3 w-3" />
            Promote to Investigation
          </Button>
        </Card>
      </div>
    </template>
  </div>
</template>
