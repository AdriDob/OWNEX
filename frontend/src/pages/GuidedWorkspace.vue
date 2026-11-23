<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle2, Circle, Clock, ExternalLink, ShieldCheck } from '@lucide/vue'
import {
  completeGuideStep,
  fetchGuidedWorkspace,
  type GuidedStep,
  type GuidedWorkspace,
} from '@/services/ownexData'

const route = useRoute()
const router = useRouter()
const itemId = computed(() => String(route.params.id))

const data = ref<GuidedWorkspace | null>(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const notice = ref('')
const selectedStepId = ref<string | null>(null)

const JOURNEY_LABELS: Record<string, string> = {
  discovery: 'Descubrir',
  eligibility: 'Elegibilidad',
  access: 'Acceso',
  preparation: 'Preparar',
  execution: 'Ejecutar',
  delivery: 'Entregar',
  acceptance: 'Aceptación',
  payment: 'Cobrar',
  withdrawal: 'Retirar',
}

const ACTOR_LABELS: Record<string, string> = {
  HUMAN_REQUIRED: 'Requiere acción tuya',
  OWNEX_AUTOMATED: 'OWNEX puede ejecutarlo',
  OWNEX_ASSISTED: 'OWNEX prepara, vos confirmás',
  EXTERNAL_WAITING: 'Esperando a la plataforma',
  BLOCKED: 'Bloqueado',
  VERIFIED_COMPLETED: 'Completado',
}

const stepStatusIcon = (s: GuidedStep) =>
  s.status === 'completed' ? CheckCircle2 : s.status === 'blocked' ? Circle : s.status === 'pending' && s.id === selectedStepId.value ? Clock : Circle

const currentStep = computed<GuidedStep | null>(() => {
  const steps = data.value?.guide.steps ?? []
  if (!steps.length) return null
  const sel = selectedStepId.value
  return steps.find((s) => s.id === sel) ?? data.value?.resume.step ?? steps.find((s) => s.status === 'pending') ?? steps[steps.length - 1]
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await fetchGuidedWorkspace(itemId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar el workspace'
  } finally {
    loading.value = false
  }
}

async function completeStep(step: GuidedStep) {
  if (busy.value) return
  busy.value = true
  notice.value = ''
  try {
    await completeGuideStep(itemId.value, step.id)
    notice.value = `Paso "${step.title}" registrado. OWNEX recalculó el recorrido.`
    await load()
  } catch (e) {
    notice.value = `Error: ${e instanceof Error ? e.message : 'falló la operación'}`
  } finally {
    busy.value = false
  }
}

function selectStep(s: GuidedStep) {
  selectedStepId.value = s.id
}

function openUrl(url: string) {
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
    <header class="flex flex-wrap items-center gap-3">
      <button class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground" @click="router.push('/earning')">
        <ArrowLeft class="h-4 w-4" /> Siguiente acción
      </button>
      <div v-if="data" class="min-w-0 flex-1">
        <h1 class="truncate text-xl font-semibold">{{ data.guide.overview.title }}</h1>
        <p class="text-sm text-muted-foreground">
          {{ data.guide.overview.platform }}
          <span v-if="data.guide.overview.reward"> · recompensa publicada: {{ data.guide.overview.reward }}</span>
        </p>
      </div>
    </header>

    <p v-if="notice" class="rounded-md border border-border bg-muted/40 px-4 py-2 text-sm">{{ notice }}</p>
    <p v-if="error" class="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-400">{{ error }}</p>
    <p v-if="loading" class="text-sm text-muted-foreground">Cargando workspace…</p>

    <template v-if="data && !loading">
      <!-- Blockers -->
      <section v-if="data.blockers.length" class="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4">
        <h2 class="text-sm font-semibold text-amber-500">Bloqueos pendientes</h2>
        <ul class="mt-2 space-y-1.5">
          <li v-for="b in data.blockers" :key="b.label" class="flex flex-wrap items-center gap-2 text-sm">
            <span>{{ b.label }}</span>
            <button v-if="b.verification_url" class="text-xs underline" @click="router.push(b.verification_url)">Resolver acceso</button>
          </li>
        </ul>
      </section>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(0,4fr)]">
        <!-- Left: journey + steps -->
        <aside class="space-y-4">
          <section class="rounded-lg border border-border bg-card p-4">
            <h3 class="text-sm font-semibold">Recorrido</h3>
            <ol class="mt-3 space-y-1">
              <li v-for="(stage, i) in data.journey.stages" :key="stage" class="flex items-center gap-2 text-xs">
                <component :is="i < data.journey.position ? CheckCircle2 : i === data.journey.position ? Clock : Circle" class="h-3.5 w-3.5"
                  :class="i < data.journey.position ? 'text-emerald-500' : i === data.journey.position ? 'text-primary' : 'text-muted-foreground/40'" />
                <span :class="i === data.journey.position ? 'font-medium' : 'text-muted-foreground'">{{ JOURNEY_LABELS[stage] || stage }}</span>
              </li>
            </ol>
            <div class="mt-3 h-1.5 rounded bg-muted">
              <div class="h-1.5 rounded bg-primary transition-all" :style="{ width: `${data.guide.progress.pct}%` }" />
            </div>
            <p class="mt-1 text-xs text-muted-foreground">{{ data.guide.progress.completed }}/{{ data.guide.progress.total }} pasos · {{ data.guide.progress.pct }}%</p>
          </section>

          <section class="rounded-lg border border-border bg-card p-4">
            <h3 class="text-sm font-semibold">Pasos</h3>
            <ol class="mt-3 space-y-1">
              <li v-for="s in data.guide.steps" :key="s.id">
                <button class="flex w-full items-start gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-hover"
                  :class="s.id === currentStep?.id ? 'bg-primary/10' : ''" @click="selectStep(s)">
                  <component :is="stepStatusIcon(s)" class="mt-0.5 h-4 w-4 shrink-0"
                    :class="s.status === 'completed' ? 'text-emerald-500' : s.status === 'blocked' ? 'text-red-400' : 'text-muted-foreground'" />
                  <span :class="s.status === 'completed' ? 'text-muted-foreground line-through' : ''">{{ s.title }}</span>
                </button>
              </li>
            </ol>
          </section>
        </aside>

        <!-- Center: current step -->
        <section v-if="currentStep" class="rounded-lg border border-primary/30 bg-card p-6">
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="rounded bg-primary/15 px-2 py-0.5 font-medium text-primary">{{ currentStep.id }}</span>
            <span class="rounded bg-muted px-2 py-0.5">{{ ACTOR_LABELS[currentStep.actor] || currentStep.actor }}</span>
            <span class="rounded bg-muted px-2 py-0.5">{{ currentStep.evidence }}</span>
            <span v-if="currentStep.status" class="rounded bg-muted px-2 py-0.5">{{ currentStep.status }}</span>
          </div>
          <h2 class="mt-3 text-lg font-semibold">{{ currentStep.title }}</h2>
          <p class="mt-2 text-sm text-muted-foreground">{{ currentStep.instruction }}</p>
          <p v-if="currentStep.detail" class="mt-2 text-xs text-muted-foreground">{{ currentStep.detail }}</p>

          <div class="mt-4 flex flex-wrap gap-3">
            <button v-if="currentStep.status !== 'completed'" class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              :disabled="busy" @click="completeStep(currentStep)">
              Marcar completado
            </button>
            <button v-if="currentStep.url" class="inline-flex items-center gap-1 rounded-md border border-border px-4 py-2 text-sm" @click="openUrl(currentStep.url)">
              Abrir enlace <ExternalLink class="h-3.5 w-3.5" />
            </button>
          </div>

          <!-- Technical plan -->
          <details class="mt-5 rounded-md border border-border p-4">
            <summary class="cursor-pointer text-sm font-semibold">Plan técnico de ejecución</summary>
            <dl class="mt-3 space-y-2 text-sm">
              <div v-if="data.guide.technical_plan.deliverables_identified?.length">
                <dt class="text-xs uppercase text-muted-foreground">Entregables</dt>
                <dd class="mt-1 flex flex-wrap gap-1.5">
                  <span v-for="d in data.guide.technical_plan.deliverables_identified" :key="d" class="rounded bg-muted px-2 py-0.5 text-xs">{{ d }}</span>
                </dd>
              </div>
              <div><dt class="text-xs uppercase text-muted-foreground">Preparación</dt><dd class="mt-1 text-muted-foreground">{{ data.guide.technical_plan.preparation }}</dd></div>
              <div v-if="data.guide.technical_plan.file_formats"><dt class="text-xs uppercase text-muted-foreground">Formatos</dt><dd class="mt-1 text-muted-foreground">{{ data.guide.technical_plan.file_formats }}</dd></div>
            </dl>
          </details>

          <!-- Submission guide -->
          <details class="mt-3 rounded-md border border-border p-4">
            <summary class="cursor-pointer text-sm font-semibold">Guía de entrega</summary>
            <dl class="mt-3 space-y-2 text-sm">
              <div><dt class="text-xs uppercase text-muted-foreground">Canal</dt><dd class="mt-1">{{ data.guide.submission_guide.channel }} <button v-if="data.guide.submission_guide.channel_url" class="text-xs underline" @click="openUrl(data.guide.submission_guide.channel_url)">abrir</button></dd></div>
              <div><dt class="text-xs uppercase text-muted-foreground">Formato</dt><dd class="mt-1 text-muted-foreground">{{ data.guide.submission_guide.format_notes }}</dd></div>
              <div><dt class="text-xs uppercase text-muted-foreground">Debe incluir</dt><dd class="mt-1 text-muted-foreground">{{ (data.guide.submission_guide.must_include as string[] | undefined)?.join(' · ') }}</dd></div>
              <div><dt class="text-xs uppercase text-muted-foreground">Después del envío</dt><dd class="mt-1 text-muted-foreground">{{ data.guide.submission_guide.post_submission }}</dd></div>
            </dl>
          </details>
        </section>

        <!-- Right: context -->
        <aside class="space-y-4">
          <section class="rounded-lg border border-border bg-card p-4">
            <h3 class="text-sm font-semibold">Verificación de cuenta · {{ data.account_verification.platform }}</h3>
            <div class="mt-2 flex items-center gap-2 text-sm">
              <ShieldCheck class="h-4 w-4" :class="data.account_verification.platform_verified ? 'text-emerald-500' : 'text-amber-500'" />
              <span>{{ data.account_verification.platform_verified ? 'Cuenta verificada' : data.account_verification.stage }}</span>
              <span v-if="data.account_verification.paused" class="text-xs text-muted-foreground">(pausada)</span>
            </div>
            <ul class="mt-3 space-y-1.5">
              <li v-for="c in data.account_verification.checklist" :key="c.key" class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">{{ c.label }}</span>
                <span class="rounded bg-muted px-1.5 py-0.5">{{ c.status }}</span>
              </li>
            </ul>
            <button class="mt-3 text-xs underline" @click="router.push(data.account_verification.verification_url)">Abrir verificación</button>
          </section>

          <section class="rounded-lg border border-border bg-card p-4">
            <h3 class="text-sm font-semibold">Dónde ir</h3>
            <ul class="mt-3 space-y-2 text-sm">
              <li v-if="data.guide.where_to_go.platform_url"><a class="text-primary underline" :href="data.guide.where_to_go.platform_url" target="_blank" rel="noopener">Plataforma ↗</a></li>
              <li v-if="data.guide.where_to_go.opportunity_url"><a class="text-primary underline" :href="data.guide.where_to_go.opportunity_url" target="_blank" rel="noopener">Publicación original ↗</a></li>
              <li v-if="data.guide.where_to_go.register_url"><a class="text-primary underline" :href="data.guide.where_to_go.register_url" target="_blank" rel="noopener">Registro ↗</a></li>
              <li v-if="!data.guide.where_to_go.platform_url && !data.guide.where_to_go.opportunity_url" class="text-xs text-muted-foreground">Sin URLs verificadas — OWNEX no inventa enlaces.</li>
            </ul>
            <p class="mt-2 text-xs text-muted-foreground">{{ data.guide.where_to_go.notes }}</p>
          </section>

          <section class="rounded-lg border border-border bg-card p-4">
            <h3 class="text-sm font-semibold">Cobro</h3>
            <dl class="mt-3 space-y-2 text-sm">
              <div><dt class="text-xs uppercase text-muted-foreground">Recompensa</dt><dd class="mt-1">{{ data.guide.payment_guide.reward_reported ?? 'Desconocida' }} <span class="text-xs text-muted-foreground">({{ data.guide.payment_guide.evidence }})</span></dd></div>
              <div v-if="data.guide.payment_guide.payout_method_suggested"><dt class="text-xs uppercase text-muted-foreground">Método sugerido</dt><dd class="mt-1">{{ data.guide.payment_guide.payout_method_suggested }}</dd></div>
              <div v-if="data.guide.payment_guide.documented_methods?.length"><dt class="text-xs uppercase text-muted-foreground">Métodos documentados</dt><dd class="mt-1 text-muted-foreground">{{ (data.guide.payment_guide.documented_methods as string[]).join(' · ') }}</dd></div>
            </dl>
            <ul class="mt-3 space-y-1 text-xs text-muted-foreground">
              <li v-for="g in data.guide.payment_guide.guide" :key="g">· {{ g }}</li>
            </ul>
          </section>
        </aside>
      </div>
    </template>
  </main>
</template>
