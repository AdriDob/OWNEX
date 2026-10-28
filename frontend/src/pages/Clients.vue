<script setup lang="ts">
/**
 * Clients — funnel Adriel Webs (lead → propuesta → proyecto → MRR).
 * Backend: /api/client-acquisition/* (captura, propuestas, proyectos, contratos).
 * Tier gratis como prueba de valor; el ingreso está en mantenimiento recurrente.
 */
import { onMounted, ref } from 'vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import {
  captureAcquisitionLead,
  fetchAcquisitionLeads,
  fetchAcquisitionStatus,
  type AcquisitionLead,
  type AcquisitionStatus,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref('')
const status = ref<AcquisitionStatus | null>(null)
const leads = ref<AcquisitionLead[]>([])

const nameInput = ref('')
const contactInput = ref('')
const busyCapture = ref(false)

const usd = (n: number | null | undefined): string => (n != null ? `$${Number(n).toLocaleString('es-AR')}` : '—')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [s, l] = await Promise.all([
      fetchAcquisitionStatus(),
      fetchAcquisitionLeads().catch(() => ({ total: 0, leads: [] })),
    ])
    status.value = s
    leads.value = l.leads ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando clientes'
  } finally {
    loading.value = false
  }
}

async function doCapture(): Promise<void> {
  if (!nameInput.value.trim()) return
  busyCapture.value = true
  try {
    await captureAcquisitionLead({ name: nameInput.value.trim(), contact: contactInput.value.trim(), source: 'instagram' })
    nameInput.value = ''
    contactInput.value = ''
    await load()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'No se pudo capturar'
  } finally {
    busyCapture.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Clientes">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">Adriel Webs</h1>
        <p class="text-sm opacity-70">Leads → propuestas → proyectos → mantenimiento recurrente.</p>
      </div>
      <div class="ml-auto">
        <OwnexButton variant="secondary" size="sm" @click="load">Actualizar</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando funnel..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <OwnexCard v-if="status" class="mb-4" variant="highlight">
        <div class="flex flex-wrap items-center gap-4 text-sm">
          <div><span class="opacity-60">Leads:</span> <strong>{{ status.leads }}</strong></div>
          <div><span class="opacity-60">Propuestas:</span> <strong>{{ status.proposals }}</strong></div>
          <div><span class="opacity-60">Proyectos:</span> <strong>{{ status.projects }}</strong></div>
          <div><span class="opacity-60">MRR:</span> <strong>{{ usd(status.mrr_usd) }}</strong></div>
        </div>
      </OwnexCard>

      <div class="mb-4 grid gap-4 md:grid-cols-2">
        <OwnexCard>
          <h2 class="mb-2 text-base font-semibold">Capturar lead</h2>
          <div class="flex flex-wrap items-end gap-2">
            <label class="flex flex-col gap-1 text-sm">
              Negocio
              <input v-model="nameInput" type="text" placeholder="Panadería Sur" class="rounded border border-border bg-background px-2 py-1" />
            </label>
            <label class="flex flex-col gap-1 text-sm">
              Contacto
              <input v-model="contactInput" type="text" placeholder="@instagram / tel" class="rounded border border-border bg-background px-2 py-1" />
            </label>
            <OwnexButton variant="primary" size="sm" :loading="busyCapture" @click="doCapture">Capturar</OwnexButton>
          </div>
        </OwnexCard>

        <OwnexCard>
          <h2 class="mb-2 text-base font-semibold">Funnel</h2>
          <div v-if="status" class="flex flex-wrap gap-1">
            <OwnexBadge v-for="(count, stage) in status.funnel" :key="stage" size="xs" variant="default">
              {{ stage }} ×{{ count }}
            </OwnexBadge>
          </div>
        </OwnexCard>
      </div>

      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Leads</h2>
        <EmptyState v-if="leads.length === 0" title="Sin leads" description="Capturá el primero desde IG/FB/WA." />
        <ul v-else class="flex flex-col gap-2">
          <li
            v-for="l in leads.slice(0, 20)"
            :key="l.id"
            class="flex flex-wrap items-center gap-2 rounded border border-border/60 px-3 py-2 text-sm"
          >
            <strong>{{ l.name }}</strong>
            <span class="text-xs opacity-60">{{ l.business_type || l.source }}</span>
            <OwnexBadge size="xs" variant="default" class="ml-auto">{{ l.stage }}</OwnexBadge>
          </li>
        </ul>
      </OwnexCard>
    </template>
  </div>
</template>
