<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { dismissGuidedAction, fetchGuidedNextAction, snoozeGuidedAction, type GuidedNextAction, type GuidedNextActionItem } from '@/services/ownexData'
import { RefreshCw, ExternalLink, ArrowRight, AlertTriangle, CheckCircle2, Circle, Clock } from '@lucide/vue'

const router = useRouter()
const data = ref<GuidedNextAction | null>(null)
const loading = ref(true)
const error = ref('')
const showEvidence = ref(false)
const busy = ref(false)

const action = computed<GuidedNextActionItem | null>(() => data.value?.action ?? null)

const JOURNEY_LABELS: Record<string, string> = {
  discovery: 'Descubrimiento',
  eligibility: 'Elegibilidad',
  access: 'Acceso',
  preparation: 'Preparación',
  execution: 'Ejecución',
  delivery: 'Entrega',
  acceptance: 'Aceptación',
  payment: 'Pago',
  withdrawal: 'Retiro',
}

const REASON_LABELS: Record<string, string> = {
  access_pending: 'El acceso a la plataforma todavía está pendiente',
  reward_published: 'Existe una recompensa publicada por la fuente',
  no_reward_data: 'La fuente no informa recompensa verificable',
  low_barrier: 'Baja barrera de entrada según los filtros del Work Bank',
  barrier_present: 'Requiere preparación adicional',
  closest_to_payment: 'Es la acción más cercana a generar ingreso verificable',
}

const ELIGIBILITY_LABELS: Record<string, string> = {
  FULLY_ELIGIBLE: 'Elegible',
  CONDITIONALLY_ELIGIBLE: 'Elegible con condiciones',
  UNKNOWN: 'Elegibilidad desconocida',
  INELIGIBLE: 'No elegible',
}

const STATE_LABELS: Record<string, string> = {
  ACTION_AVAILABLE: 'Accionable',
  ACTION_IN_PROGRESS: 'En progreso',
  HUMAN_ACTION_REQUIRED: 'Requiere acción tuya',
  AUTOMATION_RUNNING: 'OWNEX ejecutando',
  EXTERNAL_WAITING: 'Esperando externo',
  BLOCKED: 'Bloqueado',
  NO_RECOMMENDATION: 'Sin recomendación',
}

const primaryCta = computed(() => {
  const a = action.value
  if (!a) return ''
  if (a.kind === 'resolve_access') return 'Comenzar verificación de cuenta'
  if (a.step_id === 'review-deliverables') return 'Revisar entrega'
  return 'Preparar trabajo'
})

function openPrimary() {
  const a = action.value
  if (!a) return
  // Access-resolution actions lead to the Account Verification flow;
  // everything else leads to the opportunity guide.
  if (a.kind === 'resolve_access' && a.verification_url) {
    router.push(a.verification_url)
  } else {
    router.push(a.guide_url)
  }
}

async function snooze() {
  const a = action.value
  if (!a) return
  busy.value = true
  try {
    await snoozeGuidedAction(a.item_id, 24)
    await load()
  } catch {
    /* non-fatal: recommendation stays */
  } finally {
    busy.value = false
  }
}

async function dismiss() {
  const a = action.value
  if (!a) return
  if (!window.confirm('¿Descartar esta recomendación? El trabajo queda en el Work Bank; solo deja de ser la acción prioritaria.')) return
  busy.value = true
  try {
    await dismissGuidedAction(a.item_id, 'owner_dismissed')
    await load()
  } catch {
    /* non-fatal */
  } finally {
    busy.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchGuidedNextAction()
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo cargar la recomendación.'
  } finally {
    loading.value = false
  }
}

function openPlatform() {
  const url = action.value?.url
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl space-y-6 p-5 md:p-8">
    <!-- Header -->
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-xs uppercase tracking-widest text-muted-foreground">Command Center / Guided Earning</p>
        <h1 class="mt-2 text-2xl font-semibold text-foreground">Siguiente acción</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          OWNEX analiza tus oportunidades, accesos, bloqueos y rentabilidad para recomendarte el próximo paso.
        </p>
        <p v-if="data?.generated_at" class="mt-1 text-xs text-muted-foreground">
          Recomendación generada {{ new Date(data.generated_at).toLocaleString() }}
        </p>
      </div>
      <button class="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm" :disabled="loading" @click="load">
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        Actualizar
      </button>
    </header>

    <p v-if="error" role="alert" class="rounded-lg border border-destructive/30 p-4 text-sm text-destructive">
      {{ error }} — se muestra la última información disponible.
    </p>

    <!-- Loading skeleton -->
    <div v-if="loading && !data" class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
      <div class="space-y-4 rounded-lg border border-border p-6">
        <div class="h-4 w-1/3 animate-pulse rounded bg-muted" />
        <div class="h-8 w-2/3 animate-pulse rounded bg-muted" />
        <div class="h-4 w-full animate-pulse rounded bg-muted" />
        <div class="h-24 w-full animate-pulse rounded bg-muted" />
      </div>
      <div class="space-y-4 rounded-lg border border-border p-6">
        <div class="h-4 w-1/2 animate-pulse rounded bg-muted" />
        <div class="h-24 w-full animate-pulse rounded bg-muted" />
      </div>
    </div>

    <!-- Empty state -->
    <section v-else-if="!action" class="rounded-lg border border-border bg-card p-8 text-center">
      <AlertTriangle class="mx-auto h-8 w-8 text-amber-500" />
      <h2 class="mt-3 font-semibold">No hay una siguiente acción confiable disponible.</h2>
      <p class="mt-2 text-sm text-muted-foreground">{{ data?.reason || 'El Work Bank no tiene oportunidades accionables en este momento.' }}</p>
      <p class="mt-1 text-xs text-muted-foreground">Si el motivo es falta de evidencia o discovery, corré un ciclo de descubrimiento primero.</p>
    </section>

    <template v-else-if="action">
      <div class="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,3fr)]">
        <!-- Zone A: NextActionCard -->
        <section class="rounded-lg border border-primary/30 bg-card p-6">
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="rounded bg-primary/15 px-2 py-0.5 font-medium text-primary">Acción #1</span>
            <span v-if="data?.state" class="rounded px-2 py-0.5" :class="data.state === 'ACTION_AVAILABLE' ? 'bg-emerald-500/15 text-emerald-500' : 'bg-muted text-muted-foreground'">{{ STATE_LABELS[data.state] || data.state }}</span>
            <span class="rounded bg-muted px-2 py-0.5 text-muted-foreground">{{ action.category || action.platform }}</span>
            <span class="rounded bg-muted px-2 py-0.5 text-muted-foreground">{{ ELIGIBILITY_LABELS[action.eligibility_status] || action.eligibility_status }}</span>
            <span class="rounded px-2 py-0.5" :class="action.actor === 'HUMAN_REQUIRED' ? 'bg-amber-500/15 text-amber-500' : 'bg-sky-500/15 text-sky-500'">{{ action.actor_label }}</span>
          </div>

          <h2 class="mt-4 text-xl font-semibold leading-snug">{{ action.title }}</h2>

          <div class="mt-3 rounded-md border border-border bg-muted/40 p-4">
            <p class="text-xs font-medium uppercase text-muted-foreground">Resultado esperado</p>
            <p class="mt-1 text-sm">{{ action.expected_outcome }}</p>
          </div>

          <!-- Economic context -->
          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div class="rounded-md border border-border p-3">
              <p class="text-xs text-muted-foreground">Recompensa publicada</p>
              <p class="mt-1 text-lg font-semibold">{{ action.reward_published ? `$${action.reward_published}` : 'Sin dato' }}</p>
              <p class="text-[11px] text-muted-foreground">{{ action.reward_caveat }}</p>
            </div>
            <div class="rounded-md border border-border p-3">
              <p class="text-xs text-muted-foreground">Neto estimado</p>
              <p class="mt-1 text-lg font-semibold text-muted-foreground">Desconocido</p>
              <p class="text-[11px] text-muted-foreground">{{ action.net_caveat }}</p>
            </div>
            <div class="rounded-md border border-border p-3">
              <p class="text-xs text-muted-foreground">Barrera</p>
              <p class="mt-1 text-lg font-semibold">{{ action.barrier_score }}/100</p>
              <p class="text-[11px] text-muted-foreground">Menor es mejor</p>
            </div>
          </div>

          <!-- Next step -->
          <div class="mt-4 rounded-md border border-border p-4">
            <p class="text-xs font-medium uppercase text-muted-foreground">Próximo paso · {{ action.step_id }}</p>
            <p class="mt-1 text-sm">{{ action.instruction }}</p>
            <div class="mt-2 flex flex-wrap items-center gap-3 text-sm">
              <span v-if="action.url" class="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <ExternalLink class="h-3 w-3" /> {{ action.url.replace(/^https?:\/\//, '').slice(0, 48) }}
              </span>
              <span class="text-xs text-muted-foreground">{{ action.actor_label }}</span>
            </div>
          </div>

          <!-- Evidence -->
          <div v-if="action.evidence?.length" class="mt-4 rounded-md border border-border p-4">
            <button class="text-xs font-medium uppercase text-muted-foreground" @click="showEvidence = !showEvidence">
              Ver evidencia {{ showEvidence ? '▾' : '▸' }}
            </button>
            <ul v-if="showEvidence" class="mt-2 space-y-2 text-xs">
              <li v-for="ev in action.evidence" :key="ev.label" class="flex flex-wrap items-baseline gap-2">
                <span class="font-medium">{{ ev.label }}:</span>
                <span class="break-all text-muted-foreground">{{ ev.value }}</span>
                <span class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{{ ev.status }}</span>
                <span v-if="ev.verified_at" class="text-muted-foreground">· {{ new Date(ev.verified_at).toLocaleDateString() }}</span>
              </li>
            </ul>
          </div>

          <!-- Primary + secondary actions -->
          <div class="mt-5 flex flex-wrap gap-3">
            <button class="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground" @click="openPrimary">
              {{ primaryCta }} <ArrowRight class="h-4 w-4" />
            </button>
            <button v-if="action.url" class="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2.5 text-sm" @click="openPlatform">
              Ir a la plataforma <ExternalLink class="h-4 w-4" />
            </button>
            <button class="rounded-md border border-border px-4 py-2.5 text-sm text-muted-foreground" @click="router.push(action.guide_url)">
              Ver detalles
            </button>
            <button class="rounded-md border border-border px-4 py-2.5 text-sm text-muted-foreground" :disabled="busy" @click="snooze">
              Posponer
            </button>
            <button class="rounded-md border border-border px-4 py-2.5 text-sm text-muted-foreground" :disabled="busy" @click="dismiss">
              Descartar
            </button>
          </div>
        </section>

        <!-- Zone B: context & diagnosis -->
        <aside class="space-y-4">
          <section class="rounded-lg border border-border bg-card p-5">
            <h3 class="text-sm font-semibold">¿Por qué esta acción?</h3>
            <p class="mt-2 text-sm text-muted-foreground">{{ action.justification }}</p>
            <ul class="mt-3 space-y-1.5">
              <li v-for="code in action.reason_codes" :key="code" class="flex items-start gap-2 text-xs text-muted-foreground">
                <CheckCircle2 class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                {{ REASON_LABELS[code] || code }}
              </li>
            </ul>
          </section>

          <section class="rounded-lg border border-border bg-card p-5">
            <h3 class="text-sm font-semibold">Requisitos pendientes</h3>
            <ul class="mt-3 space-y-2">
              <li v-for="req in action.pending_requirements" :key="req.key" class="flex items-center gap-2 text-sm">
                <Circle class="h-3.5 w-3.5" :class="req.status === 'pending' ? 'text-amber-500' : 'text-muted-foreground'" />
                <span>{{ req.label }}</span>
                <span class="text-xs text-muted-foreground">({{ req.status }})</span>
              </li>
              <li v-if="!action.pending_requirements.length" class="text-sm text-muted-foreground">Sin requisitos pendientes identificados.</li>
            </ul>
          </section>

          <section class="rounded-lg border border-border bg-card p-5">
            <h3 class="text-sm font-semibold">Estado del recorrido</h3>
            <ol class="mt-3 space-y-1.5">
              <li v-for="(stage, i) in action.journey.stages" :key="stage" class="flex items-center gap-2 text-xs">
                <component :is="i < action.journey.position ? CheckCircle2 : i === action.journey.position ? Clock : Circle" class="h-3.5 w-3.5 shrink-0"
                  :class="i < action.journey.position ? 'text-emerald-500' : i === action.journey.position ? 'text-primary' : 'text-muted-foreground/40'" />
                <span :class="i === action.journey.position ? 'font-medium text-foreground' : 'text-muted-foreground'">
                  {{ JOURNEY_LABELS[stage] || stage }}
                </span>
              </li>
            </ol>
          </section>
        </aside>
      </div>

      <!-- Blocked actions -->
      <section v-if="data?.blocked?.length" class="rounded-lg border border-border bg-card p-5">
        <h3 class="text-sm font-semibold">Acciones bloqueadas</h3>
        <p class="mt-1 text-xs text-muted-foreground">Oportunidades que necesitan acceso o información antes de ser accionables.</p>
        <div class="mt-3 grid gap-3 sm:grid-cols-3">
          <div v-for="b in data.blocked" :key="b.item_id" class="rounded-md border border-border p-4">
            <p class="text-sm font-medium leading-snug">{{ b.title }}</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ b.platform }}<span v-if="b.reward_published"> · ${{ b.reward_published }} publicado</span></p>
            <p class="mt-1 text-xs text-amber-500">{{ b.reason }}</p>
            <button class="mt-2 text-xs underline" @click="router.push(b.verification_url)">Resolver acceso</button>
          </div>
        </div>
      </section>

      <!-- Alternatives -->
      <section v-if="data?.alternatives?.length" class="rounded-lg border border-border bg-card p-5">
        <h3 class="text-sm font-semibold">Otras acciones disponibles</h3>
        <div class="mt-3 grid gap-3 sm:grid-cols-3">
          <button
            v-for="alt in data.alternatives"
            :key="alt.item_id"
            class="rounded-md border border-border p-4 text-left transition-colors hover:bg-hover"
            @click="router.push(alt.guide_url)"
          >
            <p class="text-sm font-medium leading-snug">{{ alt.title }}</p>
            <p class="mt-1 text-xs text-muted-foreground">
              {{ alt.reward_published ? `$${alt.reward_published} publicado · ` : '' }}{{ alt.actor }}
            </p>
          </button>
        </div>
      </section>
    </template>
  </main>
</template>
