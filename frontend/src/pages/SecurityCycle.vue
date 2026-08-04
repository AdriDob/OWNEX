<template>
  <div class="space-y-6 animate-in">
    <!-- Header -->
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-1 min-w-0">
        <div class="flex items-center gap-2">
          <Shield class="h-6 w-6 text-primary" />
          <h1 class="font-display text-2xl font-bold text-foreground">Security Cycle</h1>
          <Badge variant="secondary" class="text-xs">Rastro v5</Badge>
        </div>
        <p class="text-muted-foreground text-sm max-w-2xl">
          Pipeline de investigación: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning.
          Automatizado con 30-min intervals por scheduler.
        </p>
      </div>

      <div class="flex gap-2">
        <Button
          v-if="cycleStatus?.cycle.status === 'idle' || cycleStatus?.cycle.status === 'inactive'"
          @click="startCycle"
          class="gap-2"
        >
          <Activity class="h-4 w-4" />
          Iniciar Pipeline
        </Button>
        <Button
          v-if="currentStage"
          variant="outline"
          @click="advanceStage(currentStage.id)"
          class="gap-2"
        >
          <TrendingUp class="h-4 w-4" />
          Avanzar {{ currentStage.name }}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          @click="loadSecurityCycle"
          :disabled="loading"
        >
          <FileText class="h-4 w-4" />
          Refrescar
        </Button>
      </div>
    </div>

    <!-- Error Banner -->
    <div
      v-if="error"
      class="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/30 px-4 py-3 text-sm text-destructive"
    >
      <AlertTriangle class="h-4 w-4 shrink-0" />
      <span>{{ error }}</span>
    </div>

    <!-- Loading State -->
    <LoadingState v-if="loading" />

    <!-- Main Grid -->
    <template v-else>
      <!-- Pipeline Visualization -->
      <Card>
        <CardContent class="p-6">
          <h2 class="font-display text-lg font-semibold mb-4">Pipeline del Ciclo</h2>

          <!-- Progress Bar -->
          <div class="mb-6">
            <div class="flex justify-between text-sm mb-2">
              <span>Progreso</span>
              <span>{{ progressPercent }}% completado</span>
            </div>
            <div class="w-full bg-muted rounded-full h-2">
              <div
                class="bg-primary h-2 rounded-full transition-all duration-300"
                :style="`width: ${progressPercent}%`"
              ></div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Stage Details (visible during progression) -->
      <Card v-if="currentStage">
        <CardContent class="p-6">
          <h2 class="font-display text-lg font-semibold mb-4">Detalles de la Etapa Actual</h2>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 class="text-sm font-medium text-muted-foreground mb-2">Nombre</h3>
              <p class="text-lg font-semibold">{{ currentStage.name }}</p>
            </div>
            <div>
              <h3 class="text-sm font-medium text-muted-foreground mb-2">Orden</h3>
              <p class="text-lg font-semibold">{{ currentStage.order || currentStage.id }}</p>
            </div>
            <div class="md:col-span-2">
              <h3 class="text-sm font-medium text-muted-foreground mb-2">Descripción</h3>
              <p class="text-sm">{{ currentStage.description || 'Aún no hay descripción disponible.' }}</p>
            </div>
            <div class="md:col-span-2">
              <h3 class="text-sm font-medium text-muted-foreground mb-2">Estado</h3>
              <div class="flex items-center gap-2">
                <div class="h-2 w-2 rounded-full" :class="{
                  'bg-success': currentStage.status === 'completed',
                  'bg-warning': currentStage.status === 'active',
                  'bg-muted': currentStage.status === 'pending' || currentStage.status === 'inactive'
                }"/>
                <span class="text-sm font-medium" :class="{
                  'text-success': currentStage.status === 'completed',
                  'text-warning': currentStage.status === 'active',
                  'text-muted-foreground/70': currentStage.status === 'pending' || currentStage.status === 'inactive'
                }">{{ currentStage.status }}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Cycle Information -->
      <Card>
        <CardContent class="p-6">
          <h2 class="font-display text-lg font-semibold mb-4">Información del Ciclo</h2>
          
          <div class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <h3 class="text-sm font-medium text-muted-foreground mb-1">Nombre</h3>
                <p class="font-medium">{{ cycleStatus?.cycle.name || 'Security Research' }}</p>
              </div>
              <div>
                <h3 class="text-sm font-medium text-muted-foreground mb-1">Etapa Actual</h3>
                <p class="font-medium">{{ currentStage?.name || 'Aún no iniciada' }}</p>
              </div>
              <div>
                <h3 class="text-sm font-medium text-muted-foreground mb-1">Estado</h3>
                <p class="font-medium">{{ cycleStatus?.cycle.status || 'unknown' }}</p>
              </div>
            </div>
            
            <div v-if="cycleStatus?.cycle.target_domains?.length">
              <h3 class="text-sm font-medium text-muted-foreground mb-2">Dominios Objetivo</h3>
              <div class="flex flex-wrap gap-2">
                <Badge 
                  v-for="(domain, idx) in cycleStatus.cycle.target_domains" 
                  :key="idx" 
                  variant="secondary"
                  class="text-xs"
                >
                  {{ domain }}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Last Update Info -->
      <Card v-if="cycleStatus?.cycle.last_check">
        <CardContent class="p-4">
          <div class="text-sm text-muted-foreground">
            Última actualización: {{ new Date(cycleStatus.cycle.last_check).toLocaleString() }}
          </div>
        </CardContent>
      </Card>

      <!-- Error Details -->
      <Card v-if="error">
        <CardContent class="p-4">
          <div class="flex items-center gap-2 text-destructive">
            <AlertTriangle class="h-4 w-4" />
            <span class="text-sm font-medium">Error: {{ error }}</span>
          </div>
        </CardContent>
      </Card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Shield, Activity, TrendingUp, AlertTriangle, FileText } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'

// Component state and interfaces
const loading = ref(true)
const error = ref('')
const progressPercent = ref(0)
const currentStage = ref<any>(null)
const cycleStatus = ref<any>(null)

const initializeSecurityCycle = () => {
  // Initialize with default values to simulate active cycle
  cycleStatus.value = {
    cycle: {
      name: 'Security Research Pipeline',
      status: 'active',
      target_domains: ['api.ownex.io', 'admin.ownex.io', 'auth.ownex.io'],
      last_check: new Date().toISOString(),
    }
  }
  
  currentStage.value = {
    id: 'stage-1',
    name: 'Attack Surface Analysis',
    order: 1,
    status: 'active',
    description: 'Systematic reconnaissance of exposed attack surfaces, identifying vulnerabilities, open ports, and security misconfigurations.'
  }
  
  progressPercent.value = 42
}

const startCycle = () => {
  if (cycleStatus.value?.cycle.status === 'active') return
  
  cycleStatus.value = {
    ...cycleStatus.value,
    cycle: {
      ...cycleStatus.value.cycle,
      status: 'active'
    }
  }
  
  currentStage.value = {
    id: 'stage-1',
    name: 'Attack Surface Analysis',
    order: 1,
    status: 'active',
    description: 'Systematic reconnaissance of exposed attack surfaces, identifying vulnerabilities, open ports, and security misconfigurations.'
  }
  
  progressPercent.value = 25
}

const advanceStage = (stageId: string) => {
  // Simulate stage progression
  const stages = ['stage-1', 'stage-2', 'stage-3', 'stage-4', 'stage-5', 'stage-6']
  const currentIndex = stages.indexOf(currentStage.value?.id || '')
  const nextIndex = Math.min(currentIndex + 1, stages.length - 1)
  
  if (nextIndex >= stages.length) {
    cycleStatus.value = {
      ...cycleStatus.value,
      cycle: {
        ...cycleStatus.value.cycle,
        status: 'completed'
      }
    }
    currentStage.value = null
    progressPercent.value = 100
    return
  }
  
  currentStage.value = {
    id: stages[nextIndex],
    name: ['Attack Surface Analysis', 'Hypothesis Generation', 'Exploitation Testing', 'Validation', 'Evidence Collection', 'Report Generation'][nextIndex],
    order: nextIndex + 1,
    status: 'active',
    description: getStageDescription(nextIndex)
  }
  
  progressPercent.value = (nextIndex + 1) * (100 / stages.length)
}

const getStageDescription = (stageIndex: number): string => {
  const descriptions = [
    'Systematic reconnaissance of exposed attack surfaces, identifying vulnerabilities, open ports, and security misconfigurations.',
    'Generate systematic security hypotheses based on discovered endpoints, using pattern analysis and historical data.',
    'Execute controlled exploitation attempts to validate identified vulnerabilities in isolated, controlled environments.',
    'Validate exploit findings through multiple verification methods and confirm vulnerability presence.',
    'Collect comprehensive evidence including screenshots, logs, and technical details for each validated vulnerability.',
    'Generate formal security reports with comprehensive findings, risk assessments, and remediation recommendations.'
  ]
  return descriptions[stageIndex] || ''
}

const loadSecurityCycle = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // Simulate API call to load security cycle state
    await new Promise(resolve => setTimeout(resolve, 500))
    
    initializeSecurityCycle()
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el ciclo de seguridad'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSecurityCycle()
})
</script>

<style scoped>
.animate-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
