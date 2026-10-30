<template>
  <div v-if="goodMorning" class="space-y-4">
    <!-- Setup Progress Card -->
    <div
      v-if="goodMorning.setup_progress && !goodMorning.setup_progress.complete"
      class="rounded-lg border border-primary/30 bg-primary/5 p-4"
    >
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-lg">🎯</span>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <div class="font-semibold text-foreground">Setup incompleto</div>
            <div class="rounded bg-primary/10 px-2 py-0.5 text-xs text-primary font-medium">
              {{ goodMorning.setup_progress.complete_pct }}%
            </div>
          </div>
          <div v-if="goodMorning.setup_progress.next_task" class="mt-2 space-y-1">
            <div class="text-sm text-foreground font-medium">
              Tarea de hoy: {{ goodMorning.setup_progress.next_task.title }}
            </div>
            <div class="text-xs text-muted-foreground">
              {{ goodMorning.setup_progress.next_task.how_to }}
            </div>
            <div class="flex items-center gap-2 mt-1">
              <span class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                ⏱ ~{{ goodMorning.setup_progress.next_task.est_minutes }} min
              </span>
              <span class="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {{ goodMorning.setup_progress.next_task.phase_label }}
              </span>
            </div>
          </div>
          <div class="mt-3">
            <a
              href="/setup/checklist"
              class="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Ver checklist completo →
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Complete badge -->
    <div
      v-else-if="goodMorning.setup_progress && goodMorning.setup_progress.complete"
      class="rounded-lg border border-green-500/30 bg-green-500/5 p-4"
    >
      <div class="flex items-center gap-3">
        <span class="text-lg">🎉</span>
        <div>
          <div class="font-semibold text-foreground">Configuración completa</div>
          <div class="text-sm text-muted-foreground">Tu sistema está listo para operar al 100%</div>
        </div>
      </div>
    </div>

    <!-- Daily Summary -->
    <div class="rounded-lg border border-border/50 bg-surface/30 p-4 space-y-2">
      <div class="text-sm font-medium text-foreground">Resumen del día</div>
      <div class="text-xs text-muted-foreground whitespace-pre-line">{{ goodMorning.summary }}</div>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
      <a
        v-if="goodMorning.important_tasks.length > 0"
        href="/operations/work-queue"
        class="rounded-lg border border-border/50 bg-surface/30 p-3 text-center hover:border-primary/50 transition-colors"
      >
        <div class="text-2xl font-bold text-primary">{{ goodMorning.important_tasks.length }}</div>
        <div class="text-xs text-muted-foreground">Listos para entregar</div>
      </a>
      <a
        v-if="goodMorning.unfinished_work.needs_access.length > 0"
        href="/setup/checklist"
        class="rounded-lg border border-border/50 bg-surface/30 p-3 text-center hover:border-primary/50 transition-colors"
      >
        <div class="text-2xl font-bold text-warning">{{ goodMorning.unfinished_work.needs_access.length }}</div>
        <div class="text-xs text-muted-foreground">Necesitan acceso</div>
      </a>
      <a
        href="/integrations/connections"
        class="rounded-lg border border-border/50 bg-surface/30 p-3 text-center hover:border-primary/50 transition-colors"
      >
        <div class="text-2xl font-bold" :class="goodMorning.system.status === 'ok' ? 'text-success' : 'text-destructive'">
          {{ goodMorning.system.status === 'ok' ? '✓' : '✗' }}
        </div>
        <div class="text-xs text-muted-foreground">Sistema: {{ goodMorning.system.status }}</div>
      </a>
      <a
        href="/setup/checklist"
        class="rounded-lg border border-border/50 bg-surface/30 p-3 text-center hover:border-primary/50 transition-colors"
      >
        <div class="text-2xl font-bold text-primary">{{ goodMorning.setup_progress.complete_pct }}%</div>
        <div class="text-xs text-muted-foreground">Setup completado</div>
      </a>
    </div>
  </div>

  <div v-else class="rounded-lg border border-border/50 bg-surface/30 p-8 text-center">
    <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto" />
    <div class="mt-2 text-sm text-muted-foreground">Cargando panel diario...</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchGoodMorning, type GoodMorningState } from '@/services/ownexData'

const goodMorning = ref<GoodMorningState | null>(null)
const loading = ref(true)

async function loadGoodMorning() {
  try {
    goodMorning.value = await fetchGoodMorning()
  } catch (e) {
    console.warn('[GoodMorning] Failed to load:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadGoodMorning)
</script>