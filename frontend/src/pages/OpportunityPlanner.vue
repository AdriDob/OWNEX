<script setup lang="ts">
import {
  AlertTriangle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Clock,
  DollarSign,
  ExternalLink,
  Lightbulb,
  ListChecks,
  Route,
  Target,
  TrendingUp,
  Zap,
} from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface Plan {
  program_id: number
  program_name: string
  platform: string
  orion_score: number
  where_to_start: string
  endpoints_to_review: string[]
  recommended_techniques: string[]
  best_vuln_types: string[]
  estimated_time_hours: number
  expected_return_min: number
  expected_return_max: number
  expected_value_per_hour: number
  checklist: string[]
  generated_at: string
}

const route = useRoute()
const router = useRouter()
const programId = Number(route.params.id)
const plan = ref<Plan | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    plan.value = await api.get<Plan>(`/economic/programs/${programId}/plan`)
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar el plan'
  } finally {
    loading.value = false
  }
})

function formatMoney(n: number) {
  if (n >= 1000) return '$' + (n / 1000).toFixed(1) + 'k'
  return '$' + n.toLocaleString()
}

function openIntel() {
  router.push({ name: 'program-intel', params: { id: programId } })
}
</script>

<template>
  <div class="space-y-6">
    <button class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground" @click="openIntel()">
      <ArrowLeft class="h-3 w-3" /> Volver al programa
    </button>

    <template v-if="loading">
      <div class="space-y-4"><Skeleton class="h-8 w-64" /><Skeleton class="h-40 rounded-xl" /><Skeleton class="h-60 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="$router.go(0)">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="plan">
      <!-- Header -->
      <div class="animate-in space-y-1">
        <div class="flex items-center gap-2">
          <h1 class="font-display text-2xl font-bold text-foreground">{{ plan.program_name }}</h1>
          <Badge variant="info" class="text-xs">Score {{ (plan.orion_score * 100).toFixed(0) }}</Badge>
        </div>
        <p class="text-xs text-muted-foreground">{{ plan.platform }} · Plan generado {{ new Date(plan.generated_at).toLocaleString() }}</p>
      </div>

      <!-- Distribution Chart -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Distribución del Plan</h3>
        <DoughnutChart
          :labels="['Retorno Min', 'Retorno Max', 'Valor/Hora']"
          :data="[plan.expected_return_min, plan.expected_return_max, plan.expected_value_per_hour * 10]"
          :height="200"
        />
      </Card>

      <!-- ROI Summary Card -->
      <Card class="p-5 animate-in border-l-2 border-l-gold">
        <p class="text-xs font-bold uppercase tracking-wider text-gold mb-3">Retorno Estimado</p>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p class="text-[10px] text-muted-foreground">Retorno min</p>
            <p class="text-lg font-bold text-foreground">{{ formatMoney(plan.expected_return_min) }}</p>
          </div>
          <div>
            <p class="text-[10px] text-muted-foreground">Retorno max</p>
            <p class="text-lg font-bold text-foreground">{{ formatMoney(plan.expected_return_max) }}</p>
          </div>
          <div>
            <p class="text-[10px] text-muted-foreground">Valor por hora</p>
            <p class="text-lg font-bold text-success">{{ formatMoney(plan.expected_value_per_hour) }}/h</p>
          </div>
          <div>
            <p class="text-[10px] text-muted-foreground">Tiempo estimado</p>
            <p class="text-lg font-bold text-foreground">{{ plan.estimated_time_hours.toFixed(1) }}h</p>
          </div>
        </div>
      </Card>

      <!-- Where to Start -->
      <Card class="p-5 animate-in">
        <div class="flex items-start gap-3">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary"><Target class="h-4 w-4" /></div>
          <div class="flex-1">
            <h2 class="text-sm font-semibold text-foreground mb-2">Por dónde empezar</h2>
            <div class="space-y-1">
              <p v-for="(point, i) in plan.where_to_start.split('\n').filter(Boolean)" :key="i"
                class="flex items-start gap-2 text-sm text-muted-foreground">
                <span class="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                {{ point }}
              </p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Endpoints to review -->
      <Card v-if="plan.endpoints_to_review.length" class="p-5 animate-in">
        <div class="flex items-start gap-3">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-warning/15 text-warning"><Route class="h-4 w-4" /></div>
          <div class="flex-1">
            <h2 class="text-sm font-semibold text-foreground mb-2">Endpoints a revisar primero</h2>
            <div class="flex flex-wrap gap-2">
              <span v-for="ep in plan.endpoints_to_review" :key="ep"
                class="rounded-md bg-surface/40 px-2.5 py-1 text-xs font-mono text-foreground">
                {{ ep }}
              </span>
            </div>
          </div>
        </div>
      </Card>

      <!-- Techniques & Vuln Types -->
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 animate-in">
        <Card class="p-5">
          <div class="flex items-center gap-2 mb-3">
            <Zap class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-semibold text-foreground">Técnicas recomendadas</h2>
          </div>
          <ul class="space-y-2">
            <li v-for="(t, i) in plan.recommended_techniques" :key="i" class="flex items-start gap-2 text-xs text-muted-foreground">
              <CheckCircle2 class="mt-0.5 h-3 w-3 shrink-0 text-success" />
              {{ t }}
            </li>
          </ul>
        </Card>
        <Card class="p-5">
          <div class="flex items-center gap-2 mb-3">
            <Brain class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-semibold text-foreground">Mejores vulnerabilidades</h2>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge v-for="vt in plan.best_vuln_types" :key="vt" variant="info" class="text-xs">
              {{ vt }}
            </Badge>
          </div>
          <p class="mt-3 text-xs text-muted-foreground">Estos tipos tienen el mejor Expected Value en este programa</p>
        </Card>
      </div>

      <!-- Checklist -->
      <Card class="p-5 animate-in border-l-2 border-l-primary">
        <div class="flex items-center gap-2 mb-3">
          <ListChecks class="h-4 w-4 text-primary" />
          <h2 class="text-sm font-semibold text-foreground">Checklist de cacería</h2>
        </div>
        <div class="space-y-2">
          <div v-for="(item, i) in plan.checklist" :key="i" class="flex items-start gap-3 rounded-lg bg-surface/20 p-2.5">
            <div class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary">{{ i + 1 }}</div>
            <p class="text-sm text-foreground">{{ item }}</p>
          </div>
        </div>
      </Card>
    </template>

    <div v-else class="flex flex-col items-center py-20 text-center">
      <Target class="mb-4 h-10 w-10 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No se pudo generar el plan para este programa</p>
      <Button variant="outline" class="mt-3" @click="openIntel()">Volver al programa</Button>
    </div>
  </div>
</template>
