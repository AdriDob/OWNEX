<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/lib/api'
import { Shield, Scan, Target, AlertTriangle, CheckCircle2, ChevronRight, Sparkles } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'

const scanning = ref(false)
const loadingOpps = ref(false)
const scanResult = ref<any>(null)
const opportunities = ref<any[]>([])
const error = ref('')
const activeTab = ref<'scan' | 'opportunities'>('scan')

async function scanLocal() {
  scanning.value = true
  error.value = ''
  scanResult.value = null
  try {
    scanResult.value = await api.post('/ai-security/scan-local', { model: 'qwen3-coder:8b' })
  } catch (e: any) {
    error.value = e?.message || 'Error al escanear'
  } finally {
    scanning.value = false
  }
}

async function loadOpportunities() {
  loadingOpps.value = true
  error.value = ''
  opportunities.value = []
  try {
    opportunities.value = await api.get('/ai-security/opportunities')
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar oportunidades'
  } finally {
    loadingOpps.value = false
  }
}

function severityBadge(s: string) {
  const map: Record<string, string> = { high: 'destructive', medium: 'warning', low: 'default' }
  return map[s] || 'default'
}

function actionBadge(action: string) {
  const map: Record<string, string> = {
    high_priority: 'destructive',
    worth_pursuing: 'warning',
    low_priority: 'default',
    skip: 'secondary',
  }
  return map[action] || 'default'
}
</script>

<template>
  <div class="flex flex-col items-center justify-start min-h-[80vh] px-4 py-8 animate-in">
    <div class="flex items-center gap-3 mb-2">
      <Shield class="w-8 h-8 text-intigriti" />
      <h1 class="text-3xl font-bold text-foreground">AI Security</h1>
    </div>
    <p class="text-muted-foreground mb-8 text-center max-w-md">
      Escaneá modelos de IA locales, detectá vulnerabilidades LLM y encontrá oportunidades en programas de bug bounty de IA.
    </p>

    <!-- Tab Switcher -->
    <div class="flex gap-2 mb-8">
      <Button :variant="activeTab === 'scan' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'scan'">
        <Scan class="w-4 h-4 mr-1" /> Escanear modelo
      </Button>
      <Button :variant="activeTab === 'opportunities' ? 'default' : 'ghost'" size="sm" @click="activeTab = 'opportunities'">
        <Target class="w-4 h-4 mr-1" /> Oportunidades
      </Button>
    </div>

    <!-- Scan Tab -->
    <template v-if="activeTab === 'scan'">
      <Button size="lg" class="mb-8" :disabled="scanning" @click="scanLocal">
        <Scan class="w-5 h-5 mr-2" />
        {{ scanning ? 'Escaneando...' : 'Escanear modelo local' }}
      </Button>

      <LoadingState v-if="scanning" class="mb-8" />

      <div v-if="scanResult" class="w-full max-w-2xl space-y-4">
        <Card class="card-base">
          <CardContent class="p-4">
            <div class="flex items-center justify-between mb-4">
              <span class="text-sm text-muted-foreground">Modelo: <span class="text-foreground font-mono">{{ scanResult.model }}</span></span>
              <Badge :variant="scanResult.summary.score >= 80 ? 'default' : 'destructive'">
                Score: {{ scanResult.summary.score }}%
              </Badge>
            </div>
            <div class="grid grid-cols-3 gap-3 mb-4">
              <div class="text-center p-2 rounded-lg bg-success/10">
                <p class="text-2xl font-bold text-success">{{ scanResult.summary.passed }}</p>
                <p class="text-xs text-muted-foreground">Pasaron</p>
              </div>
              <div class="text-center p-2 rounded-lg bg-destructive/10">
                <p class="text-2xl font-bold text-destructive">{{ scanResult.summary.failed }}</p>
                <p class="text-xs text-muted-foreground">Fallaron</p>
              </div>
              <div class="text-center p-2 rounded-lg bg-warning/10">
                <p class="text-2xl font-bold text-warning">{{ scanResult.summary.high_severity }}</p>
                <p class="text-xs text-muted-foreground">Críticos</p>
              </div>
            </div>
            <div class="text-xs text-muted-foreground">{{ scanResult.methodology }}</div>
          </CardContent>
        </Card>

        <Card v-for="c in scanResult.checks" :key="c.name" class="card-base">
          <CardContent class="p-3 flex items-start gap-3">
            <CheckCircle2 v-if="c.passed" class="w-5 h-5 text-success mt-0.5 shrink-0" />
            <AlertTriangle v-else class="w-5 h-5 text-destructive mt-0.5 shrink-0" />
            <div class="min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="font-medium text-sm">{{ c.name }}</span>
                <Badge :variant="severityBadge(c.severity)" size="sm">{{ c.severity }}</Badge>
              </div>
              <p class="text-xs text-muted-foreground">{{ c.detail }}</p>
              <p v-if="c.remediation" class="text-xs text-warning/80 mt-1">{{ c.remediation }}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </template>

    <!-- Opportunities Tab -->
    <template v-if="activeTab === 'opportunities'">
      <Button size="lg" class="mb-8" :disabled="loadingOpps" @click="loadOpportunities">
        <Target class="w-5 h-5 mr-2" />
        {{ loadingOpps ? 'Cargando...' : 'Buscar oportunidades AI bounty' }}
      </Button>

      <LoadingState v-if="loadingOpps" class="mb-8" />

      <div v-if="opportunities.length" class="w-full max-w-2xl space-y-3">
        <Card v-for="opp in opportunities" :key="opp.platform + '/' + opp.challenge_id" class="card-base">
          <CardContent class="p-4">
            <div class="flex items-start justify-between mb-2">
              <div>
                <h3 class="font-medium">{{ opp.title }}</h3>
                <p class="text-xs text-muted-foreground">{{ opp.platform }} / {{ opp.challenge_id }}</p>
              </div>
              <Badge :variant="actionBadge(opp.recommended_action)" size="sm">
                {{ opp.recommended_action.replace('_', ' ') }}
              </Badge>
            </div>
            <div class="grid grid-cols-3 gap-2 text-center text-sm">
              <div>
                <p class="font-mono text-success">${{ opp.estimated_payout.toLocaleString() }}</p>
                <p class="text-xs text-muted-foreground">Pago estimado</p>
              </div>
              <div>
                <p class="font-mono text-primary">{{ opp.effort_hours }}h</p>
                <p class="text-xs text-muted-foreground">Esfuerzo</p>
              </div>
              <div>
                <p class="font-mono text-warning">${{ opp.expected_value_per_hour }}/h</p>
                <p class="text-xs text-muted-foreground">Valor esperado</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </template>

    <p v-if="error" class="text-sm text-destructive mt-4">{{ error }}</p>
  </div>
</template>
