<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { approveDelivery, completeGuideStep, fetchExecutionGuide, fetchWorkBankItem, prepareDelivery, type DeliveryPackage, type GuidedGuide, type WorkBankItem } from '@/services/ownexData'

const route = useRoute()
const item = ref<WorkBankItem | null>(null)
const prepared = ref<DeliveryPackage | null>(null)
const guide = ref<GuidedGuide | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const updatedAt = ref('')
const sourceUrl = computed(() => {
  try {
    const url = new URL(item.value?.url || '')
    return ['http:', 'https:'].includes(url.protocol) ? url.href : ''
  } catch {
    return ''
  }
})
let refreshTimer: ReturnType<typeof setInterval> | undefined

const statusLabel = computed(() => ({
  ready_to_deliver: 'Listo para preparar/entregar',
  needs_access: 'Requiere configuración humana',
  delivered: 'Entrega confirmada por el usuario',
  preparing: 'Preparando',
}[item.value?.status ?? ''] ?? item.value?.status ?? 'Desconocido'))

async function loadItem() {
  try {
    item.value = await fetchWorkBankItem(String(route.params.id))
    updatedAt.value = new Date().toLocaleTimeString()
    error.value = ''
    void loadGuide()
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo cargar este trabajo.'
  } finally {
    loading.value = false
  }
}

const actorBadge: Record<string, string> = {
  HUMAN_REQUIRED: 'bg-amber-500/15 text-amber-500',
  OWNEX_AUTOMATED: 'bg-sky-500/15 text-sky-500',
  OWNEX_ASSISTED: 'bg-violet-500/15 text-violet-500',
  EXTERNAL_WAITING: 'bg-zinc-500/15 text-zinc-400',
  BLOCKED: 'bg-red-500/15 text-red-500',
  VERIFIED_COMPLETED: 'bg-emerald-500/15 text-emerald-500',
}
const evidenceLabel: Record<string, string> = {
  VERIFIED_OFFICIAL: 'Oficial verificado',
  VERIFIED_BY_API: 'Verificado por API',
  VERIFIED_BY_OWNEX: 'Verificado por OWNEX',
  OWNER_CONFIRMED: 'Confirmado por vos',
  AI_GENERATED_GUIDANCE: 'Guía generada (no oficial)',
  ESTIMATED: 'Estimado',
  UNKNOWN: 'Desconocido',
  EXPIRED: 'Expirado',
}

async function loadGuide() {
  if (!item.value) return
  try {
    guide.value = await fetchExecutionGuide(item.value.id)
  } catch {
    guide.value = null
  }
}

async function handleCompleteStep(stepId: string) {
  if (!item.value) return
  busy.value = true
  error.value = ''
  try {
    await completeGuideStep(item.value.id, stepId)
    await loadGuide()
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo registrar el paso.'
  } finally {
    busy.value = false
  }
}

async function handlePrepare() {
  if (!item.value) return
  busy.value = true
  error.value = ''
  try {
    prepared.value = await prepareDelivery(item.value.id)
    await loadItem()
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo preparar la entrega.'
  } finally {
    busy.value = false
  }
}

async function confirmDelivered() {
  if (!item.value || !window.confirm('¿Confirmás que enviaste esta entrega en la plataforma? OWNEX solo la marcará como entregada; no enviará nada por vos.')) return
  busy.value = true
  error.value = ''
  try {
    await approveDelivery(item.value.id)
    await loadItem()
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo registrar la confirmación.'
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  void loadItem()
  refreshTimer = setInterval(() => void loadItem(), 30_000)
})
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 p-5 md:p-8">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-xs uppercase tracking-widest text-muted-foreground">Trabajo · {{ item?.platform || 'Work Bank' }}</p>
        <h1 class="mt-2 text-2xl font-semibold text-foreground">{{ item?.title || 'Detalle del trabajo' }}</h1>
        <p class="mt-2 text-sm text-muted-foreground">Estado: {{ statusLabel }} · Actualizado {{ updatedAt || '—' }}</p>
      </div>
      <button class="rounded-md border border-border px-3 py-2 text-sm" @click="loadItem">Actualizar</button>
    </header>

    <p v-if="error" role="alert" class="rounded-lg border border-destructive/30 p-4 text-sm text-destructive">{{ error }}</p>
    <p v-if="loading" class="text-sm text-muted-foreground">Cargando estado y evidencia...</p>

    <template v-if="item">
      <section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <article class="rounded-lg border border-border p-4"><p class="text-xs text-muted-foreground">Recompensa anunciada</p><p class="mt-1 text-lg font-semibold">{{ item.reward ? `${item.reward} (moneda no registrada)` : 'Sin monto registrado' }}</p><p class="text-xs text-muted-foreground">No implica financiación ni pago confirmado</p></article>
        <article class="rounded-lg border border-border p-4"><p class="text-xs text-muted-foreground">Categoría</p><p class="mt-1 font-medium">{{ item.category || 'Desconocida' }}</p></article>
        <article class="rounded-lg border border-border p-4"><p class="text-xs text-muted-foreground">Acceso</p><p class="mt-1 font-medium">{{ item.access_status || 'Desconocido' }}</p><p v-if="item.access_requirement" class="mt-1 text-xs text-muted-foreground">{{ item.access_requirement }}</p></article>
        <article class="rounded-lg border border-border p-4"><p class="text-xs text-muted-foreground">Ajuste de barrera</p><p class="mt-1 font-medium">{{ item.barrier_score }}/100</p></article>
      </section>

      <section class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]">
        <article class="space-y-4 rounded-lg border border-border p-5">
          <div><h2 class="font-semibold">Descripción y contexto</h2><p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">{{ item.description || 'La fuente no proporcionó una descripción.' }}</p></div>
          <div><h2 class="font-semibold">Entregables identificados</h2><ul class="mt-2 list-inside list-disc space-y-1 text-sm text-muted-foreground"><li v-for="deliverable in item.deliverables" :key="deliverable">{{ deliverable }}</li><li v-if="!item.deliverables?.length">No hay entregables registrados.</li></ul></div>
          <div class="flex flex-wrap gap-4 text-xs text-muted-foreground"><span>Creado: {{ item.created_at || 'Desconocido' }}</span><span>Tipo: {{ item.employment_type || 'Desconocido' }}</span></div>
        </article>

        <aside class="space-y-4 rounded-lg border border-border p-5">
          <h2 class="font-semibold">Fuente y evidencia</h2>
          <p class="text-sm text-muted-foreground">La oportunidad está registrada en el Work Bank. El estado de financiación, elegibilidad geográfica y condiciones de pago no se infieren si la fuente no los proporciona.</p>
          <a v-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener noreferrer" class="inline-flex text-sm underline">Abrir publicación original ↗</a>
          <p v-else class="text-sm text-muted-foreground">No hay URL original registrada.</p>
          <dl class="space-y-2 border-t border-border pt-3 text-sm"><div><dt class="text-xs text-muted-foreground">Método de cobro sugerido</dt><dd>{{ item.payout_method || 'Sin verificar' }}</dd></div><div v-if="item.payout_method_rationale"><dt class="text-xs text-muted-foreground">Motivo</dt><dd>{{ item.payout_method_rationale }}</dd></div></dl>
        </aside>
      </section>

      <section v-if="guide" class="rounded-lg border border-border p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="font-semibold">Guía de ejecución</h2>
            <p class="mt-1 text-sm text-muted-foreground">Qué hacer, dónde ir y quién actúa en cada paso. Los enlaces solo usan URLs verificadas.</p>
          </div>
          <div class="text-right text-sm">
            <p class="font-medium">{{ guide.progress.completed }}/{{ guide.progress.total }} pasos</p>
            <div class="mt-1 h-1.5 w-40 rounded bg-muted"><div class="h-1.5 rounded bg-primary" :style="{ width: `${guide.progress.pct}%` }" /></div>
          </div>
        </div>

        <div v-if="guide.where_to_go.platform_url || guide.where_to_go.opportunity_url" class="mt-4 flex flex-wrap gap-3 text-sm">
          <a v-if="guide.where_to_go.opportunity_url" :href="guide.where_to_go.opportunity_url" target="_blank" rel="noopener noreferrer" class="rounded-md border border-border px-3 py-1.5 underline">Publicación original ↗</a>
          <a v-if="guide.where_to_go.platform_url" :href="guide.where_to_go.platform_url" target="_blank" rel="noopener noreferrer" class="rounded-md border border-border px-3 py-1.5 underline">{{ guide.where_to_go.platform_name }} ↗</a>
        </div>

        <ol class="mt-4 space-y-3">
          <li v-for="(step, idx) in guide.steps" :key="step.id" class="rounded-md border border-border p-4" :class="{ 'opacity-60': step.status === 'blocked' }">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs font-medium text-muted-foreground">{{ idx + 1 }}.</span>
              <span class="text-sm font-medium">{{ step.title }}</span>
              <span class="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase" :class="actorBadge[step.actor] || 'bg-zinc-500/15 text-zinc-400'">{{ step.actor_label }}</span>
              <span class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">{{ evidenceLabel[step.evidence] || step.evidence }}</span>
              <span v-if="step.status === 'completed'" class="text-[10px] font-medium uppercase text-emerald-500">completado</span>
              <span v-else-if="step.status === 'blocked'" class="text-[10px] font-medium uppercase text-red-500">bloqueado</span>
            </div>
            <p class="mt-2 text-sm text-muted-foreground">{{ step.instruction }}</p>
            <p v-if="step.detail" class="mt-1 text-xs text-muted-foreground">{{ step.detail }}</p>
            <div class="mt-2 flex flex-wrap items-center gap-3">
              <a v-if="step.url" :href="step.url" target="_blank" rel="noopener noreferrer" class="text-xs underline">Abrir enlace ↗</a>
              <button
                v-if="step.status !== 'completed' && step.actor !== 'EXTERNAL_WAITING' && step.status !== 'blocked'"
                class="rounded border border-border px-2 py-1 text-xs disabled:opacity-50"
                :disabled="busy"
                @click="handleCompleteStep(step.id)"
              >Marcar completado</button>
            </div>
          </li>
        </ol>

        <div class="mt-4 grid gap-3 border-t border-border pt-4 text-sm sm:grid-cols-2">
          <div>
            <h3 class="text-xs font-medium uppercase text-muted-foreground">Entrega</h3>
            <p class="mt-1 text-muted-foreground">{{ (guide.submission_guide as any)?.channel || 'platform_ui' }} — revisá el formato antes de enviar. Guardá la confirmación como evidencia.</p>
          </div>
          <div>
            <h3 class="text-xs font-medium uppercase text-muted-foreground">Pago</h3>
            <p class="mt-1 text-muted-foreground">{{ (guide.payment_guide as any)?.reward_caveat || 'Verificá el pago solo cuando esté efectivamente recibido.' }}</p>
            <p v-if="(guide.payment_guide as any)?.payout_method_suggested" class="mt-1 text-xs">Método sugerido: {{ (guide.payment_guide as any).payout_method_suggested }}</p>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-border p-5">
        <h2 class="font-semibold">Progreso y acciones humanas</h2>
        <p class="mt-2 text-sm text-muted-foreground">Este registro no contiene eventos de claim, revisión, aceptación o pago. No se mostrarán como completados hasta que exista evidencia conectada.</p>
        <div class="mt-4 flex flex-wrap gap-2">
          <button v-if="item.status !== 'delivered'" class="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50" :disabled="busy" @click="handlePrepare">{{ busy ? 'Procesando…' : 'Preparar paquete local' }}</button>
          <button v-if="item.status !== 'delivered'" class="rounded-md border border-border px-4 py-2 text-sm disabled:opacity-50" :disabled="busy" @click="confirmDelivered">Confirmar que ya lo envié</button>
        </div>
        <div v-if="prepared" class="mt-4 rounded-md border border-border p-3 text-sm">
          <p class="font-medium">Paquete preparado localmente · no enviado</p>
          <p class="mt-1 text-muted-foreground">{{ prepared.files.length }} archivos · {{ prepared.package_path }}</p>
          <a v-if="prepared.guide_url" :href="prepared.guide_url" target="_blank" rel="noopener noreferrer" class="mt-2 inline-flex underline">Ver guía de entrega ↗</a>
        </div>
      </section>
    </template>
  </main>
</template>
