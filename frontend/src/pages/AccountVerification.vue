<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  confirmAccountVerification,
  fetchAccountVerification,
  setAccountVerificationPaused,
  type AccountVerificationView,
} from '@/services/ownexData'
import { CheckCircle2, Circle, ExternalLink, Pause, Play, ShieldAlert } from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const platform = String(route.params.platform || '')

const view = ref<AccountVerificationView | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const showEvents = ref(false)

const STAGE_LABELS: Record<string, string> = {
  REQUIREMENTS_CHECK: 'Revisión de requisitos',
  REGISTRATION_READY: 'Registro preparado',
  REGISTRATION_STARTED: 'Registro en curso',
  ACCOUNT_CREATED: 'Cuenta creada',
  EMAIL_VERIFICATION: 'Verificación de correo',
  IDENTITY_VERIFICATION: 'Verificación de identidad',
  ACCESS_CHECK: 'Comprobación de acceso',
  ACCOUNT_ACCESS_CONFIRMED: 'Acceso confirmado',
  PAYOUT_CHECK: 'Configuración de cobro',
  FULLY_CONFIGURED: 'Configuración completa',
  PARTIALLY_CONFIGURED: 'Configuración parcial',
  BLOCKED: 'Bloqueado',
}

const checklistStatusLabel: Record<string, string> = {
  PENDING: 'Pendiente',
  YES: 'Sí',
  NO: 'No',
  UNKNOWN: 'Desconocido',
}

const currentStepTitle = computed(() => {
  const v = view.value
  if (!v) return ''
  if (v.stage === 'FULLY_CONFIGURED') return 'Verificación completa'
  if (v.stage === 'PARTIALLY_CONFIGURED') return 'Falta verificar el cobro'
  if (v.stage === 'BLOCKED') return 'Acceso restringido'
  return STAGE_LABELS[v.stage] || v.stage
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    view.value = await fetchAccountVerification(platform)
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo cargar la verificación.'
  } finally {
    loading.value = false
  }
}

async function confirm(field: string, value: string, notes = '') {
  if (!view.value) return
  busy.value = true
  error.value = ''
  try {
    view.value = await confirmAccountVerification(platform, field, value, { notes })
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo registrar la confirmación.'
  } finally {
    busy.value = false
  }
}

async function togglePause() {
  if (!view.value) return
  busy.value = true
  try {
    await setAccountVerificationPaused(platform, !view.value.paused)
    await load()
  } finally {
    busy.value = false
  }
}

function openOfficial() {
  const url = view.value?.guide?.url || view.value?.research.source_url
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-6 p-5 md:p-8">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-xs uppercase tracking-widest text-muted-foreground">Guided Earning / Account Setup</p>
        <h1 class="mt-2 text-2xl font-semibold text-foreground">Verificación de cuenta · {{ platform }}</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Una cuenta verificada desbloquea todas las oportunidades de esta plataforma.
        </p>
      </div>
      <div class="flex gap-2">
        <button class="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="togglePause">
          <component :is="view?.paused ? Play : Pause" class="h-4 w-4" />
          {{ view?.paused ? 'Reanudar' : 'Pausar' }}
        </button>
        <button class="rounded-md border border-border px-3 py-2 text-sm" @click="router.push('/earning')">Volver</button>
      </div>
    </header>

    <p v-if="error" role="alert" class="rounded-lg border border-destructive/30 p-4 text-sm text-destructive">{{ error }}</p>
    <p v-if="loading" class="text-sm text-muted-foreground">Cargando estado de verificación...</p>

    <template v-if="view">
      <!-- Status header -->
      <section class="rounded-lg border border-border bg-card p-5">
        <div class="flex flex-wrap items-center gap-3">
          <span class="rounded bg-primary/15 px-3 py-1 text-sm font-medium text-primary">{{ currentStepTitle }}</span>
          <span v-if="view.paused" class="rounded bg-amber-500/15 px-3 py-1 text-sm text-amber-500">Pausado</span>
          <span class="text-xs text-muted-foreground">Última comprobación: {{ view.last_checked_at ? new Date(view.last_checked_at).toLocaleString() : 'nunca' }}</span>
          <span class="text-xs text-muted-foreground">Método: {{ view.verification_method }}</span>
        </div>
        <p v-if="view.stage === 'PARTIALLY_CONFIGURED'" class="mt-3 flex items-start gap-2 text-sm text-amber-500">
          <ShieldAlert class="mt-0.5 h-4 w-4" />
          El acceso está confirmado pero el cobro no está verificado — la plataforma no es plenamente compatible hasta resolverlo.
        </p>
        <p v-if="view.stage === 'BLOCKED'" class="mt-3 flex items-start gap-2 text-sm text-red-500">
          <ShieldAlert class="mt-0.5 h-4 w-4" />
          La plataforma reportó acceso restringido. Revisá los requisitos antes de continuar.
        </p>
      </section>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <!-- Left: current step + actions -->
        <div class="space-y-4">
          <section class="rounded-lg border border-border bg-card p-5">
            <h2 class="font-semibold">Paso actual</h2>
            <p class="mt-2 text-sm text-muted-foreground">
              Según el estado registrado, el siguiente paso es:
              <strong>{{ currentStepTitle }}</strong>.
            </p>

            <!-- Stage A: requirements research -->
            <div v-if="view.stage === 'REQUIREMENTS_CHECK'" class="mt-4 space-y-3">
              <div class="rounded-md border border-border p-3 text-sm">
                <p class="text-xs font-medium uppercase text-muted-foreground">Investigación previa (datos del registro de fuentes)</p>
                <dl class="mt-2 grid grid-cols-2 gap-2 text-sm">
                  <div><dt class="text-xs text-muted-foreground">Argentina compatible</dt><dd>{{ checklistStatusLabel[view.research.argentina_compatible.toUpperCase()] || view.research.argentina_compatible }}</dd></div>
                  <div><dt class="text-xs text-muted-foreground">Cuenta requerida</dt><dd>{{ view.research.requires_account }}</dd></div>
                  <div><dt class="text-xs text-muted-foreground">Evaluación técnica</dt><dd>{{ view.research.requires_assessment }}</dd></div>
                  <div><dt class="text-xs text-muted-foreground">Pago documentado</dt><dd>{{ view.research.payment_methods_documented.join(', ') || 'sin dato' }}</dd></div>
                </dl>
                <p v-if="view.research.payment_owner_note" class="mt-2 text-xs text-amber-500">{{ view.research.payment_owner_note }}</p>
              </div>
              <button class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" @click="confirm('registration_status', 'REGISTRATION_SUPPORTED', 'Owner reviewed requirements')">
                Marcar requisitos revisados
              </button>
            </div>

            <!-- Registration guide -->
            <div v-if="view.guide" class="mt-4 rounded-md border border-border p-3">
              <p class="text-xs font-medium uppercase text-muted-foreground">Guía de registro · {{ view.guide.evidence }}</p>
              <p class="mt-1 text-sm">{{ view.guide.name }} — puede quedar desactualizada si la plataforma cambia su UI.</p>
              <ol class="mt-2 list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
                <li v-for="s in view.guide.account_steps.slice(0, 4)" :key="s.title">{{ s.title }}</li>
              </ol>
            </div>

            <!-- Confirmation actions per stage -->
            <div class="mt-4 flex flex-wrap gap-2">
              <button v-if="view.stage === 'REQUIREMENTS_CHECK'" class="rounded-md border border-border px-3 py-2 text-sm" @click="openOfficial" :disabled="!view.guide && !view.research.source_url">
                <span class="inline-flex items-center gap-1">Abrir sitio oficial <ExternalLink class="h-3.5 w-3.5" /></span>
              </button>
              <button v-if="view.stage === 'REGISTRATION_READY' || view.stage === 'REQUIREMENTS_CHECK'" class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" :disabled="busy" @click="confirm('registration_status', 'REGISTRATION_STARTED', 'Owner began registration')">
                Ya empecé el registro
              </button>
              <button v-if="view.stage === 'REGISTRATION_STARTED'" class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" :disabled="busy" @click="confirm('registration_status', 'REGISTRATION_STARTED', 'Account creation confirmed by owner')">
                Ya creé mi cuenta
              </button>
              <button v-if="view.stage === 'ACCOUNT_CREATED' || view.stage === 'REGISTRATION_STARTED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('email_status', 'EMAIL_USER_CONFIRMED', 'Email verification confirmed by owner')">
                Correo verificado
              </button>
              <button v-if="view.stage === 'EMAIL_VERIFICATION' || view.stage === 'ACCOUNT_CREATED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('identity_status', 'KYC_NOT_REQUIRED', 'No KYC required per owner')">
                KYC no requerido
              </button>
              <button v-if="view.stage === 'IDENTITY_VERIFICATION' || view.stage === 'EMAIL_VERIFICATION' || view.stage === 'ACCOUNT_CREATED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('identity_status', 'KYC_USER_CONFIRMED', 'KYC completed by owner')">
                KYC completado
              </button>
              <button v-if="view.stage !== 'FULLY_CONFIGURED' && view.stage !== 'BLOCKED' && view.stage !== 'PARTIALLY_CONFIGURED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('access_status', 'ACCOUNT_ACTIVE', 'Owner confirmed account active')">
                Cuenta activa
              </button>
              <button v-if="view.stage === 'ACCESS_CHECK' || view.stage === 'ACCOUNT_CREATED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('access_status', 'TASK_ACCESS_CONFIRMED', 'Owner confirmed task access')">
                Acceso a tareas confirmado
              </button>
              <button v-if="view.stage === 'PAYOUT_CHECK' || view.stage === 'PARTIALLY_CONFIGURED' || view.stage === 'ACCOUNT_ACCESS_CONFIRMED'" class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" :disabled="busy" @click="confirm('payout_status', 'PAYOUT_COMPATIBLE_AR', 'Owner confirmed payout works from Argentina')">
                Cobro verificado desde Argentina
              </button>
              <button v-if="view.stage === 'PAYOUT_CHECK' || view.stage === 'PARTIALLY_CONFIGURED'" class="rounded-md border border-border px-3 py-2 text-sm" :disabled="busy" @click="confirm('payout_status', 'PAYOUT_UNVERIFIED', 'Payout not yet verified')">
                Cobro sin verificar
              </button>
            </div>
            <p class="mt-3 text-xs text-muted-foreground">
              Las confirmaciones quedan registradas como OWNER_CONFIRMED — no son verificación automática de la plataforma.
              OWNEX nunca solicita contraseñas, códigos MFA ni documentos.
            </p>
          </section>
        </div>

        <!-- Right: checklist + evidence -->
        <div class="space-y-4">
          <section class="rounded-lg border border-border bg-card p-5">
            <h2 class="text-sm font-semibold">Estado de configuración</h2>
            <ul class="mt-3 space-y-2">
              <li v-for="c in view.checklist" :key="c.key" class="flex items-start gap-2 text-sm">
                <CheckCircle2 v-if="c.status === 'YES' || c.status === 'TASK_ACCESS_CONFIRMED' || c.status === 'ACCOUNT_ACTIVE' || c.status === 'FULLY_CONFIGURED' || c.status === 'PAYOUT_COMPATIBLE_AR' || c.status === 'EMAIL_USER_CONFIRMED' || c.status === 'KYC_NOT_REQUIRED'" class="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                <Circle v-else class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/50" />
                <div>
                  <p>{{ c.label }}</p>
                  <p class="text-xs text-muted-foreground">{{ c.status }}<span v-if="c.sub"> · {{ c.sub }}</span> · {{ c.evidence }}</p>
                </div>
              </li>
            </ul>
          </section>

          <section class="rounded-lg border border-border bg-card p-5">
            <button class="text-sm font-semibold" @click="showEvents = !showEvents">
              Historial de eventos {{ showEvents ? '▾' : '▸' }} ({{ view.events.length }})
            </button>
            <ul v-if="showEvents" class="mt-3 max-h-64 space-y-2 overflow-y-auto text-xs">
              <li v-for="e in [...view.events].reverse()" :key="e.id" class="border-l-2 border-border pl-2">
                <p class="font-medium">{{ e.event_type }}</p>
                <p class="text-muted-foreground">{{ e.actor }} · {{ new Date(e.timestamp).toLocaleString() }}<span v-if="e.notes"> — {{ e.notes }}</span></p>
              </li>
              <li v-if="!view.events.length" class="text-muted-foreground">Sin eventos todavía.</li>
            </ul>
          </section>

          <section v-if="view.stage === 'FULLY_CONFIGURED'" class="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-5">
            <h2 class="text-sm font-semibold text-emerald-500">Cuenta lista</h2>
            <p class="mt-1 text-sm text-muted-foreground">Esta plataforma quedó verificada. Todas las oportunidades que la usan ya no aparecerán como bloqueadas por acceso.</p>
            <button class="mt-3 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" @click="router.push('/earning')">Continuar recorrido</button>
          </section>
        </div>
      </div>
    </template>
  </main>
</template>
