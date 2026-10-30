<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-xl font-bold text-foreground sm:text-2xl">Setup Checklist</h1>
        <p class="mt-1 text-xs text-muted-foreground sm:text-sm">
          Configura tu sistema paso a paso. Cada ítem te dice exactamente qué necesitás y cómo conseguirlo.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right">
          <div class="text-2xl font-bold text-foreground sm:text-3xl">{{ status.complete_pct }}%</div>
          <div class="text-[10px] text-muted-foreground sm:text-xs">{{ status.done_items }}/{{ status.total_items }} completados</div>
        </div>
        <div class="h-12 w-12 rounded-full border-4 border-muted flex items-center justify-center sm:h-16 sm:w-16">
          <svg class="h-12 w-12 -rotate-90" viewBox="0 0 36 36">
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              class="text-muted"
              stroke-width="3"
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="currentColor"
              class="text-primary"
              stroke-width="3"
              :stroke-dasharray="`${status.complete_pct}, 100`"
            />
          </svg>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
      {{ error }}
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Next Task Banner -->
      <div
        v-if="status.next_task"
        class="rounded-lg border border-primary/30 bg-primary/5 p-4"
      >
        <div class="flex items-start gap-3">
          <span class="mt-0.5 text-lg">🎯</span>
          <div>
            <div class="font-semibold text-foreground">Tarea de hoy</div>
            <div class="text-sm text-muted-foreground">{{ status.next_task.title }}</div>
            <div class="mt-1 text-xs text-muted-foreground">{{ status.next_task.how_to }}</div>
          </div>
        </div>
      </div>

      <!-- Phases -->
      <div v-for="phase in phases" :key="phase.id" class="space-y-3">
        <div class="flex items-center gap-2">
          <h2 class="text-lg font-semibold text-foreground">{{ phase.label }}</h2>
          <span class="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {{ phase.done }}/{{ phase.total }}
          </span>
        </div>

        <div class="space-y-2">
          <div
            v-for="item in phase.items"
            :key="item.id"
            class="rounded-lg border border-border/50 bg-surface/30 p-4 transition-colors hover:border-border"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1">
                <div class="flex items-center gap-2">
                  <span v-if="item.done" class="text-green-500">✅</span>
                  <span v-else class="text-muted-foreground">⏳</span>
                  <h3 class="font-medium text-foreground" :class="{ 'text-muted-foreground line-through': item.done }">
                    {{ item.title }}
                  </h3>
                  <span
                    v-if="item.auto"
                    class="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary"
                  >
                    AUTO
                  </span>
                  <span
                    v-else
                    class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  >
                    MANUAL
                  </span>
                </div>
                <p class="mt-1 text-sm text-muted-foreground">{{ item.why }}</p>
                <div
                  v-if="!item.done"
                  class="mt-2 rounded-md bg-muted/50 p-3 text-sm"
                >
                  <div class="mb-1 text-xs font-medium text-foreground/80 sm:text-sm">Cómo hacerlo:</div>
                  <div class="text-xs text-muted-foreground sm:text-sm">{{ item.how_to }}</div>
                  <div class="mt-1 text-[10px] text-muted-foreground/70 sm:text-xs">
                    ⏱ ~{{ item.est_minutes }} minutos
                  </div>
                </div>
              </div>
              <div class="flex-shrink-0">
                <button
                  v-if="!item.done && item.manual"
                  class="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
                  :aria-label="`Marcar como completado: ${item.title}`"
                  @click="markDone(item.id)"
                >
                  Marcar listo
                </button>
                <button
                  v-else-if="item.done && item.manual"
                  class="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted"
                  :aria-label="`Deshacer: ${item.title}`"
                  @click="markUndone(item.id)"
                >
                  Deshacer
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- All done -->
      <div
        v-if="status.complete"
        class="rounded-lg border border-green-500/30 bg-green-500/5 p-6 text-center"
      >
        <div class="text-4xl">🎉</div>
        <div class="mt-2 text-lg font-semibold text-foreground">¡Configuración completa!</div>
        <div class="mt-1 text-sm text-muted-foreground">Tu sistema está listo para operar.</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/lib/api'

interface ChecklistItem {
  id: string
  phase: string
  priority: number
  title: string
  why: string
  est_minutes: number
  how_to: string
  auto: boolean
}

interface ChecklistStatus {
  complete_pct: number
  total_items: number
  done_items: number
  done: string[]
  pending: ChecklistItem[]
  next_task: ChecklistItem | null
  phases: Record<string, { total: number; done: number }>
  complete: boolean
}

const loading = ref(true)
const error = ref('')
const status = ref<ChecklistStatus>({
  complete_pct: 0,
  total_items: 0,
  done_items: 0,
  done: [],
  pending: [],
  next_task: null,
  phases: {},
  complete: false,
})

const phaseLabels: Record<string, string> = {
  essentials: 'Esencial para ingreso',
  platforms: 'Onboarding de plataformas',
  optional: 'Opcional',
}

interface PhaseGroup {
  id: string
  label: string
  total: number
  done: number
  items: (ChecklistItem & { done: boolean })[]
}

const phases = computed<PhaseGroup[]>(() => {
  const doneSet = new Set(status.value.done)
  const allItems: (ChecklistItem & { done: boolean })[] = [
    ...status.value.done.map((id) => ({
      id,
      phase: 'essentials',
      priority: 0,
      title: id,
      why: '',
      est_minutes: 0,
      how_to: '',
      auto: true,
      done: true,
    })),
    ...status.value.pending.map((item) => ({ ...item, done: false })),
  ]

  const grouped: Record<string, PhaseGroup> = {}
  for (const item of allItems) {
    const phaseId = item.phase
    if (!grouped[phaseId]) {
      grouped[phaseId] = {
        id: phaseId,
        label: phaseLabels[phaseId] || phaseId,
        total: 0,
        done: 0,
        items: [],
      }
    }
    grouped[phaseId].total++
    if (item.done) grouped[phaseId].done++
    grouped[phaseId].items.push(item)
  }

  return Object.values(grouped).sort((a, b) => {
    const order = ['essentials', 'platforms', 'optional']
    return order.indexOf(a.id) - order.indexOf(b.id)
  })
})

async function fetchStatus() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.get<ChecklistStatus>('/setup/checklist/status')
    status.value = data
  } catch (e: any) {
    error.value = e?.message || 'Failed to load checklist'
  } finally {
    loading.value = false
  }
}

async function markDone(itemId: string) {
  try {
    await api.post(`/setup/checklist/${itemId}/done`)
    await fetchStatus()
  } catch (e: any) {
    error.value = e?.message || 'Failed to mark item'
  }
}

async function markUndone(itemId: string) {
  try {
    await api.post(`/setup/checklist/${itemId}/undone`)
    await fetchStatus()
  } catch (e: any) {
    error.value = e?.message || 'Failed to undo item'
  }
}

onMounted(fetchStatus)
</script>
