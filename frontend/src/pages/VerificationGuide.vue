<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import {
  CheckCircle2, XCircle, AlertTriangle, HelpCircle, ChevronRight,
  ChevronLeft, Shield, ExternalLink, Camera, Terminal, FileText,
  RotateCcw, Flag,
} from '@lucide/vue'
import type { ZapHypothesisItem, VerificationStepItem } from '@/lib/api'
import BarChart from '@/components/charts/BarChart.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const verifying = ref(false)
const saving = ref(false)
const hypothesis = ref<ZapHypothesisItem | null>(null)
const result = ref<'pending' | 'confirmed' | 'rejected' | 'inconclusive'>('pending')
const notes = ref('')

const currentStep = ref(0)

const steps = ref<VerificationStepItem[]>([])

const totalSteps = computed(() => steps.value.length)
const progress = computed(() => totalSteps.value > 0 ? ((currentStep.value + 1) / totalSteps.value) * 100 : 0)

const canGoNext = computed(() => currentStep.value < totalSteps.value - 1)
const canGoPrev = computed(() => currentStep.value > 0)
const isLastStep = computed(() => currentStep.value >= totalSteps.value - 1 && totalSteps.value > 0)

onMounted(async () => {
  try {
    const hypParam = route.query.hypothesis
    if (hypParam) {
      const parsed = JSON.parse(decodeURIComponent(hypParam as string))
      hypothesis.value = parsed
      const howToVerify: string[] = parsed.how_to_verify || []
      const defaultSteps: VerificationStepItem[] = howToVerify.map((text: string, i: number) => {
        let type: VerificationStepItem['type'] = 'check'
        if (text.toLowerCase().includes('screenshot') || text.toLowerCase().includes('captura')) type = 'screenshot'
        else if (text.toLowerCase().includes('comando') || text.toLowerCase().includes('comand')) type = 'command'
        else if (text.toLowerCase().includes('documenta') || text.toLowerCase().includes('anota')) type = 'note'
        return {
          id: `step-${i}`,
          label: `Paso ${i + 1}`,
          description: text,
          status: 'pending',
          type,
        }
      })
      steps.value = defaultSteps
    }
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar la guía de verificación'
  } finally {
    loading.value = false
  }
})

function markStep(status: VerificationStepItem['status']) {
  if (steps.value[currentStep.value]) {
    steps.value[currentStep.value].status = status
  }
}

function nextStep() {
  if (canGoNext.value) currentStep.value++
}

function prevStep() {
  if (canGoPrev.value) currentStep.value--
}

async function finishVerification(finalResult: 'confirmed' | 'rejected' | 'inconclusive') {
  verifying.value = true
  result.value = finalResult
  saving.value = true
  try {
    const { saveVerificationResult } = await import('@/lib/api')
    const stepStatuses: Record<string, string> = {}
    for (const s of steps.value) stepStatuses[s.id] = s.status
    await saveVerificationResult(
      hypothesis.value?.id || '',
      finalResult,
      notes.value,
      stepStatuses,
    )
  } catch (e) {
    console.error('Failed to save result', e)
  } finally {
    saving.value = false
    verifying.value = false
  }
}

function reset() {
  currentStep.value = 0
  result.value = 'pending'
  notes.value = ''
  for (const s of steps.value) s.status = 'pending'
}

function formatType(type: VerificationStepItem['type']) {
  const labels: Record<string, string> = { check: 'Verificación', command: 'Comando', screenshot: 'Captura de pantalla', note: 'Anotación' }
  return labels[type] || type
}

function severityVariant(severity?: string) {
  const map: Record<string, 'destructive' | 'warning' | 'default' | 'info'> = { critical: 'destructive', high: 'destructive', medium: 'warning', low: 'default', info: 'info' }
  return map[(severity || '').toLowerCase()] || 'default'
}

function difficultyColor(diff?: string) {
  const map: Record<string, string> = { fácil: 'text-success', facil: 'text-success', media: 'text-warning', 'requiere experiencia': 'text-destructive' }
  return map[(diff || '').toLowerCase()] || 'text-muted-foreground'
}
</script>

<template>
  <div class="max-w-4xl mx-auto py-6 px-4 space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="min-w-0">
        <h1 class="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
          <Shield class="w-6 h-6 text-muted-foreground" />
          Guía de Validación
        </h1>
        <p class="text-sm text-muted-foreground mt-1">Sigue estos pasos para verificar la hipótesis manualmente</p>
      </div>
      <Button variant="ghost" size="sm" @click="router.back()">
        <ChevronLeft class="w-4 h-4 mr-1" /> Volver
      </Button>
    </div>

    <!-- Loading State -->
    <template v-if="loading">
      <Card class="p-6 space-y-4">
        <Skeleton class="h-6 w-3/4" />
        <Skeleton class="h-4 w-1/2" />
        <Skeleton class="h-32 w-full" />
      </Card>
    </template>

    <!-- Error State -->
    <template v-else-if="error">
      <Card class="p-12 text-center">
        <AlertTriangle class="w-12 h-12 text-destructive mx-auto mb-4" />
        <h2 class="text-lg font-semibold text-foreground">Error de conexión</h2>
        <p class="text-muted-foreground mt-2">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </Card>
    </template>

    <!-- Empty State -->
    <template v-else-if="!hypothesis">
      <Card class="p-12 text-center">
        <HelpCircle class="w-12 h-12 text-muted-foreground mx-auto mb-4" />
        <h2 class="text-lg font-semibold text-foreground/80">No hay hipótesis para verificar</h2>
        <p class="text-muted-foreground mt-2">Selecciona una hipótesis desde la sección de hallazgos o ZAP scan.</p>
        <Button class="mt-4" @click="router.push('/findings')">
          Ir a Hallazgos
        </Button>
      </Card>
    </template>

    <!-- Verification Content -->
    <template v-else>
      <!-- Hypothesis Summary Card -->
      <Card class="p-5 space-y-3">
        <div class="flex items-start justify-between">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <Badge :variant="severityVariant(hypothesis.vector)">{{ hypothesis.vulnerability_type?.toUpperCase() || hypothesis.vector }}</Badge>
              <span v-if="hypothesis.estimated_difficulty" class="text-xs" :class="difficultyColor(hypothesis.estimated_difficulty)">
                {{ hypothesis.estimated_difficulty }}
              </span>
              <span v-if="hypothesis.estimated_time_minutes" class="text-xs text-muted-foreground">
                ~{{ hypothesis.estimated_time_minutes }} min
              </span>
            </div>
            <p class="text-sm text-foreground/80">{{ hypothesis.target_name }}</p>
          </div>
          <div v-if="hypothesis.estimated_reward_range" class="text-right">
            <p class="text-xs text-muted-foreground">Recompensa estimada</p>
            <p class="text-sm font-semibold text-gold">{{ hypothesis.estimated_reward_range }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          <div>
            <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">¿Qué es esto?</h3>
            <p class="text-sm text-foreground/80">{{ hypothesis.what_is_this || 'Sin descripción' }}</p>
          </div>
          <div>
            <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Impacto real</h3>
            <p class="text-sm text-foreground/80">{{ hypothesis.real_world_impact || 'Sin descripción' }}</p>
          </div>
        </div>

        <div>
          <h3 class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">¿Por qué se sospecha?</h3>
          <p class="text-sm text-foreground/80">{{ hypothesis.why_suspected || hypothesis.reasoning }}</p>
        </div>
      </Card>

      <!-- Progress Chart -->
      <Card class="p-4">
        <h3 class="text-xs font-semibold text-foreground mb-3">Progreso de Verificación</h3>
        <BarChart
          :labels="['Completados', 'Fallidos', 'Pendientes']"
          :datasets="[{ label: 'Pasos', data: [steps.filter(s => s.status === 'completed').length, steps.filter(s => s.status === 'failed').length, steps.filter(s => s.status === 'pending' || s.status === 'in_progress').length] }]"
          :height="200"
        />
      </Card>

      <!-- Progress Bar -->
      <div class="space-y-1">
        <div class="flex justify-between text-xs text-muted-foreground">
          <span>Progreso: {{ currentStep + 1 }} / {{ totalSteps }}</span>
          <span>{{ Math.round(progress) }}%</span>
        </div>
        <div class="w-full h-1.5 bg-surface-hover rounded-full overflow-hidden">
          <div class="h-full bg-primary rounded-full transition-all duration-500" :style="{ width: `${progress}%` }"></div>
        </div>
      </div>

      <!-- Current Step -->
      <Card class="p-6 space-y-4" v-if="steps.length > 0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span v-if="steps[currentStep].type === 'screenshot'"><Camera class="w-4 h-4 text-intigriti" /></span>
            <span v-else-if="steps[currentStep].type === 'command'"><Terminal class="w-4 h-4 text-success" /></span>
            <span v-else-if="steps[currentStep].type === 'note'"><FileText class="w-4 h-4 text-primary" /></span>
            <span v-else><CheckCircle2 class="w-4 h-4 text-muted-foreground" /></span>
            <Badge variant="outline">{{ formatType(steps[currentStep].type) }}</Badge>
          </div>
          <span class="text-xs text-muted-foreground">{{ steps[currentStep].status === 'completed' ? '✅ Completado' : steps[currentStep].status === 'failed' ? '❌ Falló' : steps[currentStep].status === 'in_progress' ? 'En progreso...' : 'Pendiente' }}</span>
        </div>

        <p class="text-foreground leading-relaxed">{{ steps[currentStep].description }}</p>

        <div class="flex gap-2 pt-2">
          <Button
            size="sm"
            variant="outline"
            :disabled="steps[currentStep].status === 'completed'"
            @click="markStep('completed')"
          >
            <CheckCircle2 class="w-4 h-4 mr-1 text-success" /> Hecho
          </Button>
          <Button
            size="sm"
            variant="outline"
            :disabled="steps[currentStep].status === 'failed'"
            @click="markStep('failed')"
          >
            <XCircle class="w-4 h-4 mr-1 text-destructive" /> No funciona
          </Button>
          <Button
            size="sm"
            variant="ghost"
            @click="markStep('in_progress')"
          >
            En progreso
          </Button>
        </div>
      </Card>

      <!-- Navigation Controls -->
      <div class="flex justify-between items-center" v-if="steps.length > 0">
        <Button variant="ghost" :disabled="!canGoPrev" @click="prevStep">
          <ChevronLeft class="w-4 h-4 mr-1" /> Anterior
        </Button>

        <template v-if="isLastStep">
          <div class="flex gap-2">
            <Button variant="destructive" size="sm" :disabled="verifying" @click="finishVerification('rejected')">
              <XCircle class="w-4 h-4 mr-1" /> Falso Positivo
            </Button>
            <Button variant="secondary" size="sm" :disabled="verifying" @click="finishVerification('inconclusive')">
              <HelpCircle class="w-4 h-4 mr-1" /> No concluyente
            </Button>
            <Button variant="default" size="sm" :disabled="verifying" @click="finishVerification('confirmed')">
              <CheckCircle2 class="w-4 h-4 mr-1" /> {{ saving ? 'Guardando...' : '¡Confirmado!' }}
            </Button>
          </div>
        </template>

        <Button v-else :disabled="!canGoNext" @click="nextStep">
          Siguiente <ChevronRight class="w-4 h-4 ml-1" />
        </Button>
      </div>

      <!-- Notes Area -->
      <Card class="p-4">
        <label class="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-2">
          <FileText class="w-3.5 h-3.5 inline mr-1" />
          Notas de validación
        </label>
        <textarea
          v-model="notes"
          placeholder="Anota cualquier observación durante la validación: comportamiento extraño, respuestas inesperadas, URLs alternativas..."
          class="w-full h-24 bg-surface/50 border border-border-light rounded-lg p-3 text-sm text-foreground placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-1 focus:ring-primary/30"
        ></textarea>
      </Card>

      <!-- Result Display -->
      <Card class="p-5" v-if="result !== 'pending'">
        <div class="flex items-center gap-3">
          <div v-if="result === 'confirmed'">
            <CheckCircle2 class="w-8 h-8 text-success" />
          </div>
          <div v-else-if="result === 'rejected'">
            <XCircle class="w-8 h-8 text-destructive" />
          </div>
          <div v-else>
            <AlertTriangle class="w-8 h-8 text-warning" />
          </div>
          <div class="flex-1">
            <h3 class="font-semibold text-white">
              {{ result === 'confirmed' ? '¡Vulnerabilidad confirmada!' : result === 'rejected' ? 'Falso positivo' : 'No concluyente' }}
            </h3>
            <p class="text-sm text-muted-foreground">
              {{ result === 'confirmed' ? 'La hipótesis ha sido validada manualmente. Se ha registrado el hallazgo y puedes proceder a crear el reporte.' : result === 'rejected' ? 'La hipótesis no se pudo reproducir. El sistema aprenderá de este resultado.' : 'No se pudo determinar con certeza. Revisa manualmente o intenta con otro enfoque.' }}
            </p>
          </div>
          <Button variant="outline" size="sm" @click="reset">
            <RotateCcw class="w-4 h-4 mr-1" /> Re-verificar
          </Button>
        </div>
      </Card>

      <!-- Step List (Summary) -->
      <details class="text-sm text-muted-foreground">
        <summary class="cursor-pointer hover:text-foreground/80">Ver todos los pasos ({{ totalSteps }})</summary>
        <ul class="mt-2 space-y-1 pl-4">
          <li v-for="(step, i) in steps" :key="step.id" class="flex items-center gap-2">
            <span v-if="step.status === 'completed'" class="text-success"><CheckCircle2 class="w-3.5 h-3.5" /></span>
            <span v-else-if="step.status === 'failed'" class="text-destructive"><XCircle class="w-3.5 h-3.5" /></span>
            <span v-else class="text-muted-foreground/70"><HelpCircle class="w-3.5 h-3.5" /></span>
            <span :class="{ 'text-success': step.status === 'completed', 'text-destructive': step.status === 'failed', 'text-muted-foreground': step.status === 'pending' }">
              Paso {{ i + 1 }}
            </span>
          </li>
        </ul>
      </details>
    </template>
  </div>
</template>

<style scoped>
.text-gold {
  color: #D97706;
}
</style>
