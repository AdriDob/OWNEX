<script setup lang="ts">
/**
 * Availability Intelligence Card — muestra disponibilidad horaria y capacidad de acomodar tareas.
 * Datos de /api/availability/snapshot + profile kit.
 */

import { ref, onMounted } from 'vue'
import { Clock, Calendar, TrendingUp, Target, AlertTriangle, CheckCircle } from '@lucide/vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { api } from '@/lib/api'

const snapshot = ref<any>(null)
const availableToday = ref<number>(0)
const availableWeek = ref<number>(0)
const availableMonth = ref<number>(0)
const maxTaskToday = ref<number>(0)
const loading = ref(true)
const error = ref<string | null>(null)
const lastCheck = ref<{ can: boolean; remaining: number } | null>(null)

async function fetchData() {
  loading.value = true
  error.value = null
  try {
    const [snapRes, hoursTodayRes, maxTodayRes] = await Promise.allSettled([
      api.get('/api/availability/snapshot'),
      api.get('/api/availability/hours?horizon=today'),
      api.get('/api/availability/max-task-hours?horizon=today'),
    ])
    
    if (snapRes.status === 'fulfilled') {
      snapshot.value = snapRes.value
    }
    if (hoursTodayRes.status === 'fulfilled') {
      availableToday.value = hoursTodayRes.value.hours
    }
    if (maxTodayRes.status === 'fulfilled') {
      maxTaskToday.value = maxTodayRes.value.max_recommended_hours
    }
    
    const [weekRes, monthRes] = await Promise.allSettled([
      api.get('/api/availability/hours?horizon=this_week'),
      api.get('/api/availability/hours?horizon=this_month'),
    ])
    if (weekRes.status === 'fulfilled') availableWeek.value = weekRes.value.hours
    if (monthRes.status === 'fulfilled') availableMonth.value = monthRes.value.hours
    
  } catch (e: any) {
    error.value = e.message || 'Error al cargar disponibilidad'
  } finally {
    loading.value = false
  }
}

function formatHours(h: number): string {
  if (h >= 24) return `${(h / 24).toFixed(1)} días`
  return `${h.toFixed(1)}h`
}

function checkTask(hours: number) {
  if (hours <= availableToday.value) {
    lastCheck.value = { can: true, remaining: availableToday.value - hours }
  } else {
    lastCheck.value = { can: false, remaining: hours - availableToday.value }
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <OwnexCard title="Disponibilidad Inteligente" subtitle="Tu capacidad real para acomodar trabajo hoy">
    <template #header-actions>
      <div class="flex items-center gap-2">
        <span class="text-xs text-ownex-text-muted flex items-center gap-1">
          <Clock class="w-3 h-3" />
          <span v-if="snapshot">{{ snapshot.source }} · {{ new Date(snapshot.generated_at).toLocaleTimeString() }}</span>
        </span>
      </div>
    </template>

    <LoadingState v-if="loading" message="Cargando disponibilidad..." />

    <ErrorState v-else-if="error" :message="error" action-text="Reintentar" @action="fetchData" />

    <div v-else class="space-y-4">
      <!-- Horas disponibles resumen -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="bg-ownex-surface/50 rounded-xl p-4 border border-ownex-border/50">
          <div class="flex items-center gap-2 mb-1">
            <Clock class="w-4 h-4 text-ownex-text-muted" />
            <span class="text-xs font-medium text-ownex-text-muted">Hoy</span>
          </div>
          <div class="text-3xl font-bold text-ownex-text">{{ formatHours(availableToday) }}</div>
          <div class="text-xs text-ownex-text-muted">Máx tarea: {{ maxTaskToday }}h (regla 80%)</div>
        </div>
        <div class="bg-ownex-surface/50 rounded-xl p-4 border border-ownex-border/50">
          <div class="flex items-center gap-2 mb-1">
            <Calendar class="w-4 h-4 text-ownex-text-muted" />
            <span class="text-xs font-medium text-ownex-text-muted">Esta semana</span>
          </div>
          <div class="text-3xl font-bold text-ownex-text">{{ formatHours(availableWeek) }}</div>
          <div class="text-xs text-ownex-text-muted">Promedio {{ (availableWeek / 7).toFixed(1) }}h/día</div>
        </div>
        <div class="bg-ownex-surface/50 rounded-xl p-4 border border-ownex-border/50">
          <div class="flex items-center gap-2 mb-1">
            <Calendar class="w-4 h-4 text-ownex-text-muted" />
            <span class="text-xs font-medium text-ownex-text-muted">Este mes</span>
          </div>
          <div class="text-3xl font-bold text-ownex-text">{{ formatHours(availableMonth) }}</div>
          <div class="text-xs text-ownex-text-muted">Proyección mensual</div>
        </div>
      </div>

      <!-- Quick check: ¿puedo acomodar tarea X? -->
      <div class="bg-ownex-surface/50 rounded-xl p-4 border border-ownex-border/50">
        <div class="flex items-center justify-between mb-2">
          <span class="font-medium text-ownex-text">¿Puedo meter una tarea de...</span>
          <OwnexBadge variant="ghost" size="sm">
            <TrendingUp class="w-3 h-3 mr-1" /> 80% rule aplicada
          </OwnexBadge>
        </div>
        <div class="flex flex-wrap gap-2">
          <button 
            v-for="h in [2, 4, 6, 8]" 
            :key="h" 
            @click="checkTask(h)"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all
              bg-ownex-surface border border-ownex-border/50
              hover:bg-ownex-primary/10 hover:border-ownex-primary/50"
          >
            {{ h }}h
          </button>
        </div>
        <div v-if="lastCheck" class="mt-3 p-3 rounded-lg" :class="lastCheck.can ? 'bg-ownex-success/10 border border-ownex-success/30' : 'bg-ownex-error/10 border border-ownex-error/30'">
          <div class="flex items-center gap-2">
            <CheckCircle v-if="lastCheck.can" class="w-4 h-4 text-ownex-success" />
            <AlertTriangle v-else class="w-4 h-4 text-ownex-error" />
            <span class="font-medium">
              {{ lastCheck.can ? '✓ Cabe perfecto' : '✗ Se pasa' }}
              ({{ lastCheck.remaining > 0 ? formatHours(lastCheck.remaining) + ' libres' : formatHours(Math.abs(lastCheck.remaining)) + ' de más' }})
            </span>
          </div>
        </div>
      </div>

      <!-- Nota del snapshot -->
      <div v-if="snapshot?.note" class="text-xs text-ownex-text-muted italic border-t border-ownex-border/30 pt-2">
        {{ snapshot.note }}
      </div>
    </div>
  </OwnexCard>
</template>

