<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import {
  Target, DollarSign, Sparkles, ArrowRight, RefreshCw,
  Zap, CheckCircle2, XCircle,
  Clock, Activity, Shield, FileText, Bug, TrendingUp,
  Loader2
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { toast } = useToast()

// ── State ──
const loading = ref(true)
const hunting = ref(false)
const huntStatus = ref<'idle' | 'running' | 'paused' | 'done' | 'error'>('idle')
const huntProgress = ref<string[]>([])
const targetsScanned = ref(0)
const findingsFound = ref(0)
const huntError = ref<string | null>(null)
const stats = ref({ revenue: 0, findings: 0, reports: 0, targets: 0 })
const currentHuntStage = ref('')

let statusPoll: ReturnType<typeof setInterval> | null = null

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Buenos días'
  if (h < 18) return 'Buenas tardes'
  return 'Buenas noches'
})

const stageLabel: Record<string, string> = {
  idle: 'Listo para cazar',
  running: '🏃 Cazando...',
  paused: '⏸️ Pausado',
  done: '✅ Cacería completa',
  error: '❌ Error durante la cacería',
}

const stageProgress = computed(() => {
  const stages = ['idle', 'running', 'done']
  const idx = stages.indexOf(huntStatus.value === 'done' ? 'done' : huntStatus.value === 'running' ? 'running' : 'idle')
  if (idx === -1) return 0
  return Math.round((idx / (stages.length - 1)) * 100)
})

const isHuntActive = computed(() => huntStatus.value === 'running')

// ── Fetch Stats ──
async function loadData() {
  loading.value = true
  try {
    const [capital, findingsRes, reportsRes] = await Promise.allSettled([
      api.get<any>('/api/revenue/capital-dashboard'),
      api.get<{ total: number }>('/findings', { limit: 1 }),
      api.get<{ total: number }>('/reports/submissions', { limit: 1 }),
    ])
    if (capital.status === 'fulfilled') {
      const cap = capital.value
      stats.value.revenue = cap?.payout_summary?.total_payout || 0
      stats.value.targets = cap?.targets?.total || 0
    }
    if (findingsRes.status === 'fulfilled') stats.value.findings = findingsRes.value.total
    if (reportsRes.status === 'fulfilled') stats.value.reports = reportsRes.value.total
  } catch { /* silent */ }
  finally { loading.value = false }
}

// ── Poll hunt status + pipeline stage ──
async function checkHuntStatus() {
  try {
    // Get hunt status
    const [huntRes, stageRes] = await Promise.allSettled([
      api.get<{ status: string; targets_scanned: number; findings_found: number }>('/api/hunt/status'),
      api.get<{ current_stage: string; scheduler_running: boolean }>('/api/pipeline/stages'),
    ])

    if (huntRes.status === 'fulfilled') {
      const res = huntRes.value
      targetsScanned.value = res.targets_scanned || 0
      findingsFound.value = res.findings_found || 0
      currentHuntStage.value = res.status

      if (res.status === 'idle') {
        if (huntStatus.value === 'running') {
          huntStatus.value = 'done'
          huntProgress.value.push('✅ Pipeline completado')
          toast.success('Cacería completa', 'Pipeline E2E ejecutado exitosamente')
          await loadData()
          stopPolling()
        }
        hunting.value = false
      } else if (res.status === 'running') {
        if (huntStatus.value === 'idle') {
          huntStatus.value = 'running'
        }
      } else if (res.status === 'paused') {
        huntStatus.value = 'paused'
      }
    }

    // Get pipeline stage for granular progress
    if (stageRes.status === 'fulfilled') {
      const stageInfo = stageRes.value
      if (stageInfo.current_stage && stageInfo.current_stage !== 'idle') {
        currentHuntStage.value = stageInfo.current_stage
      }
    }
  } catch { /* status poll silent */ }
}

function startPolling() {
  stopPolling()
  statusPoll = setInterval(checkHuntStatus, 3000)
}

function stopPolling() {
  if (statusPoll) {
    clearInterval(statusPoll)
    statusPoll = null
  }
}

// ── HUNT! ──
async function startHunt() {
  if (hunting.value) return
  hunting.value = true
  huntProgress.value = ['🚀 Lanzando cacería...']
  huntStatus.value = 'running'
  huntError.value = null

  try {
    const res = await api.post<{ status: string }>('/api/hunt/start', {})
    if (res.status === 'running' || res.status === 'started') {
      huntProgress.value[0] = '✅ Cacería iniciada'
      huntProgress.value.push('⏳ Escaneando targets...')
      toast.success('Hunt iniciado', 'Pipeline E2E ejecutándose en segundo plano')
      startPolling()
    } else if (res.status === 'already_running') {
      huntProgress.value[0] = '⚠️ Ya hay una cacería en curso'
      toast.warning('Ya en ejecución', 'Se unió a la cacería en curso')
      startPolling()
    } else {
      throw new Error(`Estado inesperado: ${res.status}`)
    }
  } catch (e: any) {
    huntProgress.value[0] = `❌ Error: ${e?.message || 'error al iniciar'}`
    huntStatus.value = 'error'
    huntError.value = e?.message || 'Error desconocido'
    hunting.value = false
    toast.error('HUNT falló', e?.message || 'Error al iniciar pipeline')
  }
}

onMounted(() => {
  loadData()
  checkHuntStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="space-y-6 p-6 animate-fade-in">
    <!-- Header -->
    <div class="text-center mb-4">
      <p class="text-lg text-muted-foreground mb-1">{{ greeting }},</p>
      <h1 class="text-3xl font-bold tracking-tight text-primary">¿Listo para cazar?</h1>
    </div>

    <!-- KPI Strip -->
    <LoadingState v-if="loading && !stats.revenue" />
    <div v-else class="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
      <KPIBlock
        label="Revenue Total"
        :value="'$' + stats.revenue.toLocaleString()"
        icon="DollarSign"
        color="text-success"
        bg="bg-success/10"
      />
      <KPIBlock
        label="Findings"
        :value="String(stats.findings)"
        icon="Bug"
        color="text-primary"
        bg="bg-primary/10"
      />
      <KPIBlock
        label="Reportes"
        :value="String(stats.reports)"
        icon="FileText"
        color="text-intigriti"
        bg="bg-intigriti/10"
      />
      <KPIBlock
        label="Targets"
        :value="String(stats.targets)"
        icon="Target"
        color="text-muted-foreground"
        bg="bg-muted/10"
      />
    </div>

    <!-- HUNT Button -->
    <div class="flex justify-center my-8">
      <button
        @click="startHunt"
        :disabled="isHuntActive"
        class="group relative flex flex-col items-center justify-center w-72 h-72 rounded-full
          bg-gradient-to-br from-primary/20 via-primary/10 to-transparent
          hover:from-primary/30 hover:via-primary/20 hover:to-primary/5
          border-2 border-primary/30 hover:border-primary/60
          transition-all duration-500 hover:scale-105
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
          shadow-[0_0_60px_rgba(255,255,255,0.1)] hover:shadow-[0_0_80px_rgba(255,255,255,0.2)]"
      >
        <div v-if="isHuntActive"
          class="absolute inset-0 rounded-full animate-ping bg-primary/10"
        />
        <div class="relative z-10 flex flex-col items-center">
          <template v-if="isHuntActive">
            <Loader2 class="w-16 h-16 text-primary animate-spin mb-4" />
            <span class="text-lg font-bold text-primary" v-if="currentHuntStage !== 'running' && currentHuntStage !== 'idle' && currentHuntStage !== ''">
              {{ currentHuntStage }}
            </span>
            <span class="text-lg font-bold text-primary" v-else>Cazando...</span>
          </template>
          <template v-else-if="huntStatus === 'done'">
            <CheckCircle2 class="w-16 h-16 text-success mb-4" />
            <span class="text-lg font-bold text-success">¡HECHO!</span>
          </template>
          <template v-else-if="huntStatus === 'error'">
            <XCircle class="w-16 h-16 text-destructive mb-4" />
            <span class="text-lg font-bold text-destructive">ERROR</span>
          </template>
          <template v-else>
            <Zap class="w-16 h-16 text-primary mb-4 group-hover:scale-110 transition-transform" />
            <span class="text-2xl font-bold text-primary tracking-wider">HUNT</span>
          </template>
        </div>
      </button>
    </div>

    <!-- Live Progress -->
    <div v-if="isHuntActive || huntStatus === 'done'" class="max-w-lg mx-auto text-center space-y-2">
      <p class="text-sm text-muted-foreground">
        <template v-if="isHuntActive && currentHuntStage !== 'running' && currentHuntStage !== 'idle' && currentHuntStage !== ''">
          Etapa actual: <span class="font-mono font-bold text-primary">{{ currentHuntStage }}</span>
        </template>
        <template v-else>
          {{ stageLabel[huntStatus] }}
        </template>
      </p>
      <div class="flex justify-center gap-6">
        <div class="text-center">
          <p class="font-mono text-xl font-bold text-primary">{{ targetsScanned }}</p>
          <p class="text-xs text-muted-foreground">Targets escaneados</p>
        </div>
        <div class="text-center">
          <p class="font-mono text-xl font-bold text-success">{{ findingsFound }}</p>
          <p class="text-xs text-muted-foreground">Findings encontrados</p>
        </div>
      </div>
      <!-- Progress log -->
      <div class="text-xs text-left space-y-1 mt-4 max-h-32 overflow-y-auto">
        <p v-for="(log, i) in huntProgress" :key="i" class="text-muted-foreground">{{ log }}</p>
      </div>
    </div>

    <!-- Quick Nav Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mt-8">
      <button @click="router.push('/capital')"
        class="group relative flex flex-col items-center justify-center p-8 rounded-2xl
          border border-success/30 bg-gradient-to-br from-success/10 to-success/20
          hover:from-success/20 hover:to-success/30 hover:scale-[1.02] hover:border-success/50
          transition-all duration-300">
        <DollarSign class="w-12 h-12 text-success mb-4" />
        <span class="text-xl font-bold text-success mb-2">CAPITAL</span>
        <p class="text-sm text-muted-foreground text-center">
          ${{ stats.revenue.toLocaleString() }} en payouts
        </p>
        <ArrowRight class="w-5 h-5 text-success absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity" />
      </button>

      <button @click="router.push('/intelligence/findings')"
        class="group relative flex flex-col items-center justify-center p-8 rounded-2xl
          border border-primary/30 bg-gradient-to-br from-primary/10 to-primary/20
          hover:from-primary/20 hover:to-primary/30 hover:scale-[1.02] hover:border-primary/50
          transition-all duration-300">
        <Bug class="w-12 h-12 text-primary mb-4" />
        <span class="text-xl font-bold text-primary mb-2">FINDINGS</span>
        <p class="text-sm text-muted-foreground">{{ stats.findings }} hallazgos registrados</p>
        <ArrowRight class="w-5 h-5 text-primary absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity" />
      </button>

      <button @click="router.push('/reports/queue')"
        class="group relative flex flex-col items-center justify-center p-8 rounded-2xl
          border border-intigriti/30 bg-gradient-to-br from-intigriti/10 to-intigriti/20
          hover:from-intigriti/20 hover:to-intigriti/30 hover:scale-[1.02] hover:border-intigriti/50
          transition-all duration-300">
        <FileText class="w-12 h-12 text-intigriti mb-4" />
        <span class="text-xl font-bold text-intigriti mb-2">REPORTES</span>
        <p class="text-sm text-muted-foreground">{{ stats.reports }} en cola de envío</p>
        <ArrowRight class="w-5 h-5 text-intigriti absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity" />
      </button>
    </div>

    <!-- Footer Nav -->
    <div class="flex justify-center gap-6 mt-6">
      <button @click="router.push('/targets')" class="text-sm text-muted-foreground hover:text-foreground transition-colors">Targets</button>
      <button @click="router.push('/operations/health')" class="text-sm text-muted-foreground hover:text-foreground transition-colors">Health</button>
      <button @click="router.push('/integrations/connections')" class="text-sm text-muted-foreground hover:text-foreground transition-colors">Conexiones</button>
      <button @click="router.push('/')" class="text-sm text-muted-foreground hover:text-foreground transition-colors">Mission Control</button>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>