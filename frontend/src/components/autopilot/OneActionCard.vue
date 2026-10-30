<script setup lang="ts">
/**
 * One Action Card — The single best action OWNEX recommends right now.
 * This is the primary interface for the Daily Autopilot.
 */

import {
  AlertTriangle,
  AlertTriangle as AlertTriangleIcon,
  BookOpen,
  Bot,
  Brain,
  Calendar,
  CheckCircle,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Clock,
  Code,
  Cpu,
  CreditCard,
  DollarSign,
  ExternalLink,
  GitMerge,
  PackageCheck,
  RefreshCw,
  RefreshCw as RefreshCwIcon,
  Search,
  Target,
  UserPlus,
  X,
} from '@lucide/vue'
import { computed, onMounted, ref, watch } from 'vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import { fetchOneAction, type OneAction } from '@/services/ownexData'

interface Props {
  autoRefresh?: boolean
  refreshInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  autoRefresh: true,
  refreshInterval: 300000, // 5 minutes
})

const emit = defineEmits<{
  actionExecuted: [actionId: string]
  actionDismissed: [actionId: string]
}>()

const action = ref<OneAction | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const dismissing = ref(false)

const urgencyColors: Record<string, string> = {
  immediate: 'bg-destructive/20 text-destructive border-destructive/30',
  today: 'bg-warning/20 text-warning border-warning/30',
  this_week: 'bg-primary/20 text-primary border-primary/30',
  this_month: 'bg-blue/20 text-blue border-blue/30',
  flexible: 'bg-muted/20 text-muted-foreground border-muted/30',
}

const urgencyIcons = {
  immediate: AlertTriangleIcon,
  today: Clock,
  this_week: Calendar,
  this_month: Calendar,
  flexible: Clock,
}

const confidenceColors: Record<string, string> = {
  high: 'bg-success/20 text-success border-success/30',
  medium: 'bg-warning/20 text-warning border-warning/30',
  low: 'bg-destructive/20 text-destructive border-destructive/30',
  unknown: 'bg-muted/20 text-muted-foreground border-muted/30',
}

const actionTypeColors: Record<string, string> = {
  deliver_work: 'bg-success/10',
  submit_bounty: 'bg-destructive/10',
  submit_dev_bounty: 'bg-primary/10',
  apply_platform: 'bg-blue/10',
  complete_onboarding: 'bg-purple/10',
  approve_pr: 'bg-primary/10',
  approve_delivery: 'bg-success/10',
  approve_rebalance: 'bg-amber/10',
  strategic_decision: 'bg-purple/10',
  complete_assessment: 'bg-blue/10',
  setup_payment: 'bg-amber/10',
  setup_api: 'bg-gray/10',
  review_finding: 'bg-destructive/10',
  strategic_review: 'bg-muted/10',
}

const actionTypeIcons: Record<string, any> = {
  deliver_work: CheckCircle,
  submit_bounty: AlertTriangleIcon,
  submit_dev_bounty: Code,
  apply_platform: UserPlus,
  complete_onboarding: BookOpen,
  approve_pr: GitMerge,
  approve_delivery: PackageCheck,
  approve_rebalance: RefreshCwIcon,
  strategic_decision: Brain,
  complete_assessment: ClipboardCheck,
  setup_payment: CreditCard,
  setup_api: Cpu,
  review_finding: Search,
  strategic_review: ClipboardList,
}

const urgencyLabels: Record<string, string> = {
  immediate: 'INMEDIATO',
  today: 'HOY',
  this_week: 'ESTA SEMANA',
  this_month: 'ESTE MES',
  flexible: 'FLEXIBLE',
}

const confidenceLabels: Record<string, string> = {
  high: 'ALTA',
  medium: 'MEDIA',
  low: 'BAJA',
  unknown: 'DESCONOCIDA',
}

const actionTypeLabels: Record<string, string> = {
  deliver_work: 'Entregar trabajo',
  submit_bounty: 'Reportar bounty',
  submit_dev_bounty: 'Enviar dev bounty',
  apply_platform: 'Aplicar a plataforma',
  complete_onboarding: 'Completar onboarding',
  approve_pr: 'Aprobar PR',
  approve_delivery: 'Aprobar entrega',
  approve_rebalance: 'Aprobar rebalance',
  strategic_decision: 'Decisión estratégica',
  complete_assessment: 'Completar assessment',
  setup_payment: 'Configurar pago',
  setup_api: 'Configurar API',
  review_finding: 'Revisar hallazgo',
  strategic_review: 'Revisión estratégica',
}

const usd = (n: number | null | undefined): string => (n != null ? `$${Math.round(n).toLocaleString('es-AR')}` : '—')

const formatHours = (h: number | null | undefined): string => (h != null ? `${h}h` : '—')

const formatDays = (d: number | null | undefined): string => (d != null ? `${d}d` : '—')

const pct = (n: number | null | undefined): string => (n != null ? `${Math.round(n * 100)}%` : '—')

const formatExpiry = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = date.getTime() - now.getTime()
    if (diff <= 0) return 'Expirado'
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    if (hours > 0) return `en ${hours}h ${minutes}m`
    return `en ${minutes}m`
  } catch {
    return dateStr
  }
}

async function loadAction(force = false) {
  loading.value = true
  error.value = null
  try {
    const res = await fetchOneAction({ force_refresh: force })
    action.value = res.action || res
  } catch (e: any) {
    error.value = e.message || 'Error cargando la acción'
  } finally {
    loading.value = false
  }
}

async function dismissAction() {
  if (dismissing.value) return
  dismissing.value = true
  try {
    emit('actionDismissed', action.value?.action_id)
    action.value = null
  } finally {
    dismissing.value = false
  }
}

async function executeAction() {
  if (!action.value?.url) return
  window.open(action.value.url, '_blank')
  emit('actionExecuted', action.value?.action_id)
}

onMounted(() => {
  loadAction()
  if (props.autoRefresh) {
    setInterval(() => loadAction(true), props.refreshInterval)
  }
})

watch(
  () => props.autoRefresh,
  (val) => {
    if (val) loadAction(true)
  },
)
</script>

<template>
  <div class="w-full">
    <!-- Loading State -->
    <OwnexCard v-if="loading" class="p-6 animate-pulse">
      <div class="space-y-4">
        <div class="h-4 bg-muted/50 rounded w-1/3 animate-pulse"></div>
        <div class="h-8 bg-muted/50 rounded w-1/2 animate-pulse"></div>
        <div class="grid grid-cols-3 gap-4">
          <div class="h-10 bg-muted/50 rounded animate-pulse"></div>
          <div class="h-10 bg-muted/50 rounded animate-pulse"></div>
          <div class="h-10 bg-muted/50 rounded animate-pulse"></div>
        </div>
      </div>
    </OwnexCard>

    <!-- Error State -->
    <OwnexCard v-else-if="error" class="p-6 border-destructive/30 bg-destructive/5">
      <div class="flex items-center gap-3">
        <AlertTriangle class="h-5 w-5 text-destructive" />
        <p class="text-sm text-destructive">{{ error }}</p>
        <OwnexButton variant="outline" size="sm" class="ml-auto" @click="loadAction(true)">
          <RefreshCw class="h-4 w-4 mr-1" />
          Reintentar
        </OwnexButton>
      </div>
    </OwnexCard>

    <!-- No Action Required -->
    <OwnexCard v-else-if="action && action.action_type === 'strategic_review' && action.title === 'NO ACTION REQUIRED'" class="p-6 border-success/30 bg-success/5">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-12 w-12 items-center justify-center rounded-full bg-success/20">
            <CheckCircle class="h-6 w-6 text-success" />
          </div>
          <div>
            <p class="font-semibold text-success">NO ACTION REQUIRED</p>
            <p class="text-sm text-muted-foreground">{{ action?.description }}</p>
          </div>
        </div>
        <OwnexButton variant="ghost" size="sm" @click="loadAction(true)">
          <RefreshCw class="h-4 w-4 mr-1" />
          Actualizar
        </OwnexButton>
      </div>
    </OwnexCard>

    <!-- The ONE ACTION CARD -->
    <OwnexCard v-else-if="action" class="relative overflow-hidden">
      <!-- Header with Urgency Badge -->
      <div class="flex items-start justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg" :class="[actionTypeColors[action?.action_type] || 'bg-primary/10']">
            <component :is="actionTypeIcons[action?.action_type]" class="h-5 w-5" :class="actionTypeColors[action?.action_type]?.replace('/10', '') || 'text-primary'" />
          </div>
          <div>
            <h2 class="font-semibold text-lg truncate">{{ action?.title }}</h2>
            <p class="text-xs text-muted-foreground">{{ actionTypeLabels[action?.action_type] }}</p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Urgency Badge -->
          <span class="px-2 py-1 text-xs font-medium rounded-full" :class="urgencyColors[action?.urgency]">
            <component :is="urgencyIcons[action?.urgency]" class="h-3 w-3 mr-1" />
            {{ urgencyLabels[action?.urgency] }}
          </span>

          <!-- Confidence Badge -->
          <span class="px-2 py-1 text-xs font-medium rounded-full" :class="confidenceColors[action?.confidence_band]">
            {{ confidenceLabels[action?.confidence_band] }}
          </span>

          <!-- Dismiss Button -->
          <button
            @click="dismissAction"
            :disabled="dismissing"
            class="p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
            :aria-label="dismissing ? 'Descartando...' : 'Descartar acción'"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
      </div>

      <!-- Why & Instruction -->
      <div class="space-y-3 mb-4">
        <div class="rounded-lg bg-blue/5 border border-blue/20 p-3">
          <div class="flex items-center gap-2 text-xs font-medium text-blue mb-1">
            <Bot class="h-3.5 w-3.5" />
            <span>POR QUÉ</span>
          </div>
          <p class="text-sm text-foreground/90">{{ action?.why }}</p>
        </div>

        <div class="rounded-lg bg-primary/5 border border-primary/20 p-3">
          <div class="flex items-center gap-2 text-xs font-medium text-primary mb-1">
            <Target class="h-3.5 w-3.5" />
            <span>CÓMO EJECUTAR</span>
          </div>
          <p class="text-sm text-foreground/90 whitespace-pre-line">{{ action?.instruction }}</p>
        </div>

        <!-- Economics Row -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
          <div class="rounded-lg border border-border/20 bg-surface/20 p-3 text-center">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">EV TOTAL</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-success">{{ usd(action?.expected_value_usd) }}</p>
          </div>
          <div class="rounded-lg border border-border/20 bg-surface/20 p-3 text-center">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">EV/HORA HUMANA</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums text-primary">{{ usd(action?.ev_per_human_hour_usd) }}/h</p>
          </div>
          <div class="rounded-lg border border-border/20 bg-surface/20 p-3 text-center">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">TIEMPO EST.</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums">{{ formatHours(action?.estimated_human_hours) }}</p>
          </div>
          <div class="rounded-lg border border-border/20 bg-surface/20 p-3 text-center">
            <p class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">A COBRO</p>
            <p class="mt-1 font-mono text-lg font-semibold tabular-nums">{{ formatDays(action?.cash_speed_days) }}</p>
          </div>
        </div>

        <!-- Probabilities Row -->
        <div class="grid grid-cols-3 gap-2 mb-4">
          <div class="rounded-lg border border-border/20 bg-surface/20 p-2 text-center">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Éxito</p>
            <p class="mt-0.5 font-mono text-lg font-semibold" :class="action?.success_probability >= 0.7 ? 'text-success' : action?.success_probability >= 0.4 ? 'text-warning' : 'text-destructive'">{{ pct(action?.success_probability) }}</p>
          </div>
          <div class="rounded-lg border border-border/20 bg-surface/20 p-2 text-center">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Aceptación</p>
            <p class="mt-0.5 font-mono text-lg font-semibold" :class="action?.acceptance_probability >= 0.7 ? 'text-success' : action?.acceptance_probability >= 0.4 ? 'text-warning' : 'text-destructive'">{{ pct(action?.acceptance_probability) }}</p>
          </div>
          <div class="rounded-lg border border-border/20 bg-surface/20 p-2 text-center">
            <p class="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Pago</p>
            <p class="mt-0.5 font-mono text-lg font-semibold" :class="action?.payment_probability >= 0.7 ? 'text-success' : action?.payment_probability >= 0.4 ? 'text-warning' : 'text-destructive'">{{ pct(action?.payment_probability) }}</p>
          </div>
        </div>

        <!-- Platform & Prerequisites -->
        <div v-if="action?.platform_name || action?.prerequisites?.length" class="space-y-2 mb-4">
          <div v-if="action?.platform_name" class="flex items-center gap-2 text-xs text-muted-foreground">
            <span class="px-2 py-0.5 rounded bg-muted/50 font-mono text-[10px]">{{ action.platform_name }}</span>
            <span v-if="action.platform_readiness_pct > 0" class="text-[10px]">{{ action.platform_readiness_pct }}% listo</span>
            <span v-if="action.platform_url" class="text-[10px] text-primary hover:underline cursor-pointer">Ver plataforma</span>
          </div>
          <div v-if="action?.prerequisites?.length" class="flex flex-wrap gap-1">
            <span class="text-[9px] text-muted-foreground">Prerrequisitos:</span>
            <span v-for="p in action.prerequisites" :key="p" class="px-1.5 py-0.5 rounded bg-muted/50 font-mono text-[9px]">{{ p }}</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-3 pt-4 border-t border-border/20">
          <OwnexButton
            v-if="action?.url"
            @click="executeAction"
            :disabled="!action.url"
            class="flex-1"
            size="lg"
          >
            <ExternalLink class="h-4 w-4 mr-2" />
            {{ actionTypeLabels[action?.action_type]?.includes('Entregar') ? 'Entregar ahora' : 
               actionTypeLabels[action?.action_type]?.includes('Reportar') ? 'Reportar ahora' :
               actionTypeLabels[action?.action_type]?.includes('Aplicar') ? 'Aplicar ahora' :
               actionTypeLabels[action?.action_type]?.includes('Aprobar') ? 'Aprobar ahora' : 'Ejecutar' }}
          </OwnexButton>

          <OwnexButton variant="outline" @click="dismissAction" :disabled="dismissing">
            <X class="h-4 w-4 mr-1" />
            Descartar
          </OwnexButton>

          <OwnexButton variant="ghost" size="sm" @click="loadAction(true)">
            <RefreshCw class="h-4 w-4 mr-1" />
            Actualizar
          </OwnexButton>
        </div>

        <!-- Expires indicator -->
        <div v-if="action?.expires_at" class="mt-3 text-xs text-muted-foreground flex items-center gap-1">
          <Clock class="h-3 w-3" />
          <span>Expira: {{ formatExpiry(action.expires_at) }}</span>
        </div>
      </div>
    </OwnexCard>

    <!-- Empty State -->
    <OwnexCard v-else class="p-6 text-center">
      <p class="text-sm text-muted-foreground">No hay acción disponible</p>
      <OwnexButton variant="outline" size="sm" class="mt-2" @click="loadAction(true)">
        <RefreshCw class="h-4 w-4 mr-1" />
        Buscar acción
      </OwnexButton>
    </OwnexCard>
  </div>
</template>