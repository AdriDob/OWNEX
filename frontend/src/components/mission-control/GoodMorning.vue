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
  return status === 'ok' ? '#16a34a' : status === 'degraded' ? '#d97706' : '#e82127'
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
          <span class="gm-sub">{{ Object.keys(state.memory.namespaces).length }} namespaces</span>
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
  border: 1px solid rgba(232, 33, 39, 0.3);
  color: #e82127;
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
  margin-right: 0.35rem;
}
</style>
