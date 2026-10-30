<script setup lang="ts">
/**
 * LocalJobs — trabajo presencial AR (Zona Sur + CABA, junior-friendly).
 * Backend: /api/local-jobs/* (solo lectura; la postulación es MANUAL en el aviso).
 */
import { onMounted, ref } from 'vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import OwnexBadge from '@/components/ui/OwnexBadge.vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import OwnexCard from '@/components/ui/OwnexCard.vue'
import {
  fetchLocalJobBoards,
  fetchLocalJobs,
  type LocalJobResult,
} from '@/services/ownexData'

const loading = ref(true)
const error = ref('')
const results = ref<LocalJobResult[]>([])
const total = ref(0)
const zone = ref('Zona Sur')
const board = ref('all')
const boards = ref<{ board: string; url: string; apply: string }[]>([])

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [s, b] = await Promise.all([
      fetchLocalJobs(zone.value, board.value),
      fetchLocalJobBoards().catch(() => ({ zone: zone.value, boards: [] })),
    ])
    results.value = s.results ?? []
    total.value = s.total
    boards.value = b.boards ?? []
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Error cargando avisos'
  } finally {
    loading.value = false
  }
}

function openUrl(url: string): void {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="p-4 sm:p-6" aria-label="Trabajo local">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-semibold">Trabajo local</h1>
        <p class="text-sm opacity-70">Zona Sur + CABA, junior-friendly. Postulación MANUAL en cada aviso.</p>
      </div>
      <div class="ml-auto flex flex-wrap items-end gap-2">
        <label class="flex flex-col gap-1 text-sm">
          Zona
          <select v-model="zone" class="rounded border border-border bg-background px-2 py-1" @change="load">
            <option>Zona Sur</option>
            <option>CABA</option>
          </select>
        </label>
        <label class="flex flex-col gap-1 text-sm">
          Portal
          <select v-model="board" class="rounded border border-border bg-background px-2 py-1" @change="load">
            <option value="all">Todos</option>
            <option value="zonajobs">ZonaJobs</option>
            <option value="bumeran">Bumeran</option>
            <option value="computrabajo">Computrabajo</option>
          </select>
        </label>
        <OwnexButton variant="secondary" size="sm" @click="load">Actualizar</OwnexButton>
      </div>
    </div>

    <LoadingState v-if="loading" message="Buscando avisos..." />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <OwnexCard class="mb-4">
        <div class="text-xs uppercase opacity-60">Portales (links vivos)</div>
        <div class="mt-2 flex flex-wrap gap-2">
          <OwnexButton
            v-for="b in boards"
            :key="b.board"
            variant="secondary"
            size="sm"
            @click="openUrl(b.url)"
          >
            {{ b.board }} ↗
          </OwnexButton>
        </div>
      </OwnexCard>

      <OwnexCard>
        <div class="mb-2 text-sm opacity-70">{{ total }} avisos · {{ zone }}</div>
        <EmptyState v-if="results.length === 0" title="Sin avisos" description="Revisá los portales directamente." />
        <ul v-else class="flex flex-col gap-2">
          <li
            v-for="r in results"
            :key="`${r.board}:${r.id}`"
            class="flex flex-wrap items-center gap-2 rounded border border-border/60 px-3 py-2"
          >
            <OwnexBadge size="xs" variant="default">{{ r.board }}</OwnexBadge>
            <div class="min-w-52 flex-1">
              <div class="text-sm font-semibold">{{ r.name }}</div>
              <div class="text-xs opacity-60">{{ r.zone }} · {{ r.modality }}</div>
            </div>
            <OwnexBadge size="xs" variant="warning">MANUAL</OwnexBadge>
            <OwnexButton variant="primary" size="xs" @click="openUrl(r.url)">Ver aviso</OwnexButton>
          </li>
        </ul>
      </OwnexCard>
    </template>
  </div>
</template>
