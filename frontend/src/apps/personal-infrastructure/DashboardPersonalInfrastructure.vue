<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'

interface Objective {
  id: string
  category: string
  title: string
  description: string
  estimated_duration_hours: number
  dependencies: string[]
  required_integrations_count: number
}

interface ObjectiveProgress {
  objective_id: string
  completion_percentage: number
  completed_tasks: string[]
  pending_tasks: string[]
  current_step: string
}

const objectives = ref<Objective[]>([])
const objectivesProgress = ref<Record<string, ObjectiveProgress>>({})
const overallCompletion = ref(0)
const nextRecommendedAction = ref('')
const loading = ref(true)

const fetchObjectives = async () => {
  try {
    const response = await fetch('/api/personal-infrastructure/objectives')
    const data = await response.json()
    objectives.value = data.objectives
  } catch (error) {
    console.error('Error fetching objectives:', error)
  }
}

const fetchSnapshot = async () => {
  try {
    const response = await fetch('/api/personal-infrastructure/snapshot')
    const data = await response.json()
    overallCompletion.value = data.overall_completion
    nextRecommendedAction.value = data.next_recommended_action
    objectivesProgress.value = data.objectives_progress
  } catch (error) {
    console.error('Error fetching snapshot:', error)
  }
}

const startObjective = async (objectiveId: string) => {
  try {
    const response = await fetch(`/api/personal-infrastructure/objectives/${objectiveId}/start`, {
      method: 'POST',
    })
    const data = await response.json()
    await fetchSnapshot()
  } catch (error) {
    console.error('Error starting objective:', error)
  }
}

const getCategoryColor = (category: string) => {
  const colors: Record<string, string> = {
    development: 'bg-primary',
    bug_bounty: 'bg-intigriti',
    dev_bounty: 'bg-success',
    freelance: 'bg-warning',
    wealth: 'bg-warning',
  }
  return colors[category] || 'bg-muted'
}

const getCategoryLabel = (category: string) => {
  const labels: Record<string, string> = {
    development: 'Desarrollo',
    bug_bounty: 'Bug Bounty',
    dev_bounty: 'Dev Bounty',
    freelance: 'Freelance',
    wealth: 'Finanzas',
  }
  return labels[category] || category
}

onMounted(async () => {
  loading.value = true
  await Promise.all([fetchObjectives(), fetchSnapshot()])
  loading.value = false
})
</script>

<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-white">Personal Infrastructure Manager</h1>
        <p class="text-muted-foreground mt-1">Configura tu infraestructura digital sin conocimientos técnicos</p>
      </div>
      <div class="flex items-center gap-4">
        <div class="text-right">
          <div class="text-sm text-muted-foreground">Progreso General</div>
          <div class="text-2xl font-bold text-white">{{ overallCompletion.toFixed(0) }}%</div>
        </div>
      </div>
    </div>

    <!-- Next Action Banner -->
    <Card class="bg-gradient-to-r from-primary to-intigriti border-0">
      <CardContent class="p-6">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div class="flex-1">
            <div class="text-sm text-white/80">Próxima Acción Recomendada</div>
            <div class="text-lg font-semibold text-white">{{ nextRecommendedAction }}</div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div class="text-muted-foreground">Cargando objetivos...</div>
    </div>

    <!-- Objectives Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card v-for="objective in objectives" :key="objective.id" class="bg-surface-hover border-border-light">
        <CardHeader>
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <CardTitle class="text-white">{{ objective.title }}</CardTitle>
              <CardDescription class="text-muted-foreground mt-1">{{ objective.description }}</CardDescription>
            </div>
            <Badge :class="getCategoryColor(objective.category)" class="text-white">
              {{ getCategoryLabel(objective.category) }}
            </Badge>
          </div>
        </CardHeader>
        <CardContent class="space-y-4">
          <!-- Progress -->
          <div v-if="objectivesProgress[objective.id]">
            <div class="flex items-center justify-between text-sm mb-2">
              <span class="text-muted-foreground">Progreso</span>
              <span class="text-white font-semibold">{{ objectivesProgress[objective.id].completion_percentage.toFixed(0) }}%</span>
            </div>
            <Progress :value="objectivesProgress[objective.id].completion_percentage" class="h-2" />
          </div>

          <!-- Integrations Count -->
          <div class="flex items-center gap-2 text-sm text-muted-foreground">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>{{ objective.required_integrations_count }} integraciones requeridas</span>
          </div>

          <!-- Duration -->
          <div class="flex items-center gap-2 text-sm text-muted-foreground">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{{ objective.estimated_duration_hours }}h estimadas</span>
          </div>

          <!-- Action Button -->
          <Button
            v-if="!objectivesProgress[objective.id]"
            @click="startObjective(objective.id)"
            class="w-full bg-primary hover:bg-primary/90"
          >
            Iniciar Objetivo
          </Button>
          <Button
            v-else
            :disabled="objectivesProgress[objective.id].completion_percentage >= 100"
            class="w-full bg-success hover:bg-success/90"
          >
            {{ objectivesProgress[objective.id].completion_percentage >= 100 ? 'Completado' : 'En Progreso' }}
          </Button>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
