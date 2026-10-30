<script setup lang="ts">
/**
 * Content — Content Factory / MPT (TikTok/Reels/Shorts) en una vista.
 * Backend: /api/content-factory/* (solo lectura: salud MPT + schedules).
 * La generación corre en el scheduler propio de la factory.
 */
import { onMounted, ref } from 'vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import {
  fetchContentFactoryJobs,
  fetchContentFactoryStatus,
  type ContentFactoryJob,
  type ContentFactoryStatus,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref('')
const status = ref<ContentFactoryStatus | null>(null)
const jobs = ref<ContentFactoryJob[]>([])

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [s, j] = await Promise.all([
      fetchContentFactoryStatus(),
      fetchContentFactoryJobs().catch(() => ({ total: 0, jobs: [] })),
    ])
    status.value = s
    jobs.value = j.jobs ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando Content Factory'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Contenido">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">Contenido</h1>
        <p class="text-sm opacity-70">MPT → TikTok/Reels/Shorts. La generación corre en schedule propio.</p>
      </div>
      <div class="ml-auto">
        <OwnexButton variant="secondary" size="sm" @click="load">Actualizar</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Cargando factory..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <OwnexCard v-if="status" class="mb-4" variant="highlight">
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <OwnexBadge :variant="status.mpt.healthy ? 'success' : 'default'">
            MPT {{ status.mpt.healthy ? 'saludable' : 'no disponible' }}
          </OwnexBadge>
          <OwnexBadge :variant="status.material_key.configured ? 'success' : 'warning'">
            Materiales {{ status.material_key.configured ? 'OK' : 'falta key Pexels/Coverr' }}
          </OwnexBadge>
        </div>
        <p v-if="!status.material_key.configured" class="mt-2 text-xs opacity-60">
          pexels.com/api (gratis) → pegar en ~/projects/MoneyPrinterTurbo/config.toml → pexels_api_keys.
        </p>
      </OwnexCard>

      <OwnexCard>
        <h2 class="mb-3 text-base font-semibold">Schedules ({{ jobs.length }})</h2>
        <EmptyState v-if="jobs.length === 0" title="Sin schedules" description="La factory no reportó jobs." />
        <ul v-else class="flex flex-col gap-2">
          <li
            v-for="j in jobs"
            :key="j.job_id"
            class="flex flex-wrap items-center gap-2 rounded border border-border/60 px-3 py-2 text-sm"
          >
            <strong>{{ j.name || j.job_id }}</strong>
            <span class="ml-auto font-mono text-xs opacity-60">{{ j.schedule }}</span>
          </li>
        </ul>
      </OwnexCard>
    </template>
  </div>
</template>
