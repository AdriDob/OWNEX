<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchGoodMorning, type GoodMorningState } from '@/services/ownexData'

const state = ref<GoodMorningState | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    state.value = await fetchGoodMorning()
  } catch {
    state.value = null
  } finally {
    loading.value = false
  }
})

function statusColor(status: string) {
  return status === 'ok' ? '#16a34a' : status === 'degraded' ? '#d97706' : '#00d5ff'
}
</script>

<template>
  <section class="gm">
    <div class="gm-head">
      <h3 class="gm-title">GOOD MORNING</h3>
      <span v-if="state" class="gm-system" :style="{ color: statusColor(state.system.status) }">
        {{ state.system.status === 'ok' ? 'Ready' : state.system.status }} · score
        {{ Math.round(state.system.score) }}/100
      </span>
      <span v-if="state" class="gm-time">{{ new Date(state.generated_at).toLocaleTimeString() }}</span>
    </div>

    <p v-if="loading" class="gm-muted">Revisando el sistema...</p>
    <p v-else-if="!state" class="gm-muted">Panel mañanero no disponible.</p>

    <template v-else>
      <p class="gm-summary">{{ state.summary }}</p>

      <div class="gm-grid">
        <div class="gm-card">
          <span class="gm-label">Memoria</span>
          <span class="gm-value">{{ state.memory.entries }} entradas</span>
          <span class="gm-sub">{{ state.memory.namespace_count }} namespaces</span>
        </div>
        <div class="gm-card">
          <span class="gm-label">Fuentes escaneadas</span>
          <span class="gm-value">{{ state.opportunities.scanned_sources }}</span>
          <span class="gm-sub">{{ state.opportunities.best_sources.length }} DISCOVER hoy</span>
        </div>
        <div class="gm-card">
          <span class="gm-label">Trabajo pendiente</span>
          <span class="gm-value">{{ state.unfinished_work.ready_to_deliver.length }} listos</span>
          <span class="gm-sub">{{ state.unfinished_work.needs_access.length }} piden acceso</span>
        </div>
        <div class="gm-card">
          <span class="gm-label">Mejoras</span>
          <span class="gm-value">{{ state.improvements_suggested.length }}</span>
          <span class="gm-sub">{{ state.pending_approvals.length }} aprobaciones</span>
        </div>
      </div>

      <div v-if="state.improvements_suggested.length" class="gm-block">
        <span class="gm-label">Sugerencias</span>
        <ul class="gm-list">
          <li v-for="imp in state.improvements_suggested.slice(0, 3)" :key="imp.name">
            <span class="gm-chip">{{ imp.type }}</span>
            {{ imp.name }} — {{ imp.benefit }}
          </li>
        </ul>
      </div>

      <div class="gm-block">
        <div class="gm-setup-head">
          <span class="gm-label">Configuración</span>
          <span class="gm-sub">
            {{ state.setup_progress.complete ? 'Configuración completa' : `${state.setup_progress.complete_pct}% completo` }}
          </span>
        </div>
        <div class="gm-bar" role="progressbar" :aria-valuenow="state.setup_progress.complete_pct" aria-valuemin="0" aria-valuemax="100">
          <div class="gm-bar-fill" :style="{ width: `${state.setup_progress.complete_pct}%` }"></div>
        </div>
        <div v-if="state.setup_progress.next_task" class="gm-task">
          <span class="gm-chip">{{ state.setup_progress.next_task.phase_label }}</span>
          <strong>{{ state.setup_progress.next_task.title }}</strong>
          <span class="gm-task-meta">~{{ state.setup_progress.next_task.est_minutes }} min · {{ state.setup_progress.next_task.why }}</span>
          <code class="gm-how">{{ state.setup_progress.next_task.how_to }}</code>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.gm {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.gm-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.gm-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.gm-system {
  font-size: 0.75rem;
  font-weight: 600;
}
.gm-time {
  margin-left: auto;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.4);
}
.gm-muted {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
}
.gm-summary {
  font-size: 0.78rem;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}
.gm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.5rem;
}
.gm-card {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
  padding: 0.5rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.gm-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.45);
}
.gm-value {
  font-size: 1rem;
  font-weight: 600;
}
.gm-sub {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.5);
}
.gm-block {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.gm-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.75rem;
}
.gm-chip {
  font-size: 0.6rem;
  border: 1px solid rgba(0, 213, 255, 0.3);
  color: #00d5ff;
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
  margin-right: 0.35rem;
}
.gm-setup-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.gm-bar {
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.gm-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: #00d5ff;
  transition: width 0.3s ease;
}
.gm-task {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.78rem;
}
.gm-task-meta {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.55);
}
.gm-how {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.65);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 0.25rem 0.4rem;
  white-space: normal;
  word-break: break-word;
}
</style>
