<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { approveDelivery, fetchWorkBankItem, prepareDelivery, type DeliveryPackage, type WorkBankItem } from '@/services/ownexData'

const route = useRoute()
const item = ref<WorkBankItem | null>(null)
const prepared = ref<DeliveryPackage | null>(null)
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
  } catch (cause: any) {
    error.value = cause?.message || 'No se pudo cargar este trabajo.'
  } finally {
    loading.value = false
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
