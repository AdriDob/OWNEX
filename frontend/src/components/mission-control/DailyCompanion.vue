<template>
  <section class="daily-companion" v-if="!loading">
    <div class="dc-head">
      <h3 class="dc-title">DAILY COMPANION</h3>
      <span class="dc-time">{{ formatTime(state?.generated_at) }}</span>
    </div>

    <p v-if="!state" class="dc-muted">Daily companion no disponible.</p>

    <template v-else>
      <!-- System Health -->
      <div class="dc-block">
        <span class="dc-label">Sistema</span>
        <span class="dc-value" :style="{ color: systemColor(state.system.status) }">
          {{ state.system.status === 'ok' ? 'Online' : state.system.status }}
        </span>
        <span class="dc-sub">Score: {{ state.system.score }}/100 · Snapshots: {{ state.system.snapshots }}</span>
      </div>

      <!-- Personal State -->
      <div class="dc-block">
        <span class="dc-label">Estado Personal</span>
        <span class="dc-value">{{ state.personal.pending_tasks }} pendientes · {{ state.personal.delivered_today }} entregados hoy</span>
        <ul v-if="state.personal.learning_goals.length" class="dc-list">
          <li v-for="(g, i) in state.personal.learning_goals" :key="i">{{ g }}</li>
        </ul>
      </div>

      <!-- Market Opportunities -->
      <div class="dc-block">
        <span class="dc-label">Mercado</span>
        <span class="dc-value">{{ state.market.opportunities }} fuentes curadas · {{ state.market.new_ecosystems }} nuevos ecosistemas</span>
        <p class="dc-sub" v-if="state.market.recommendation">{{ state.market.recommendation }}</p>
        <div v-if="state.market.top_sources.length" class="dc-sources">
          <template v-for="(src, i) in state.market.top_sources.slice(0, 3)" :key="i">
            <span class="dc-chip">{{ src.name }}</span>
            <span class="dc-chip dc-chip-muted">{{ src.category }}</span>
            <span class="dc-chip dc-chip-trust">Trust {{ src.trust_score }}</span>
            <span class="dc-chip dc-chip-ev">{{ src.earning_potential }}</span>
          </template>
        </div>
      </div>

      <!-- Focus Check -->
      <div class="dc-block">
        <span class="dc-label">Enfoque</span>
        <div class="dc-focus-grid">
          <div class="dc-focus-col">
            <span class="dc-focus-title">Detener</span>
            <ul class="dc-focus-list">
              <li v-for="(s, i) in state.focus.stop.slice(0, 2)" :key="i">{{ s }}</li>
            </ul>
          </div>
          <div class="dc-focus-col">
            <span class="dc-focus-title">Automatizar</span>
            <ul class="dc-focus-list">
              <li v-for="(a, i) in state.focus.automate.slice(0, 2)" :key="i">{{ a }}</li>
            </ul>
          </div>
          <div class="dc-focus-col">
            <span class="dc-focus-title">Delegar</span>
            <ul class="dc-focus-list">
              <li v-for="(d, i) in state.focus.delegate.slice(0, 2)" :key="i">{{ d }}</li>
            </ul>
          </div>
          <div class="dc-focus-col">
            <span class="dc-focus-title">Mejorar</span>
            <ul class="dc-focus-list">
              <li v-for="(i2, i) in state.focus.improve.slice(0, 2)" :key="i">{{ i2 }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Briefing -->
      <div class="dc-block dc-briefing">
        <span class="dc-label">Briefing</span>
        <p class="dc-greeting">{{ state.briefing.greeting }}</p>
        <p class="dc-sub">{{ state.briefing.system_health }}</p>
        <p class="dc-sub">{{ state.briefing.important_tasks }}</p>
        <ul v-if="state.briefing.recommended_actions.length" class="dc-actions">
          <li v-for="(a, i) in state.briefing.recommended_actions.slice(0, 3)" :key="i">→ {{ a }}</li>
        </ul>
        <p v-if="state.briefing.focus_note" class="dc-focus-note">{{ state.briefing.focus_note }}</p>
      </div>

      <!-- Projection -->
      <div class="dc-block" v-if="state.projection.months_to_target !== null">
        <span class="dc-label">Proyección</span>
        <span class="dc-value">Meta en ~{{ state.projection.months_to_target }} meses (cruce mes {{ state.projection.crossing_months }})</span>
        <span class="dc-sub">{{ state.projection.note }}</span>
      </div>
      <div class="dc-block" v-else>
        <span class="dc-label">Proyección</span>
        <span class="dc-sub">{{ state.projection.note }}</span>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchDailyCompanion, type DailyCompanionState } from '@/services/ownexData'

const state = ref<DailyCompanionState | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    state.value = await fetchDailyCompanion()
  } catch {
    state.value = null
  } finally {
    loading.value = false
  }
})

function formatTime(iso: string | undefined) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString()
}

function systemColor(status: string) {
  return status === 'ok' ? '#16a34a' : status === 'degraded' ? '#d97706' : '#00d5ff'
}
</script>

<style scoped>
.daily-companion {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dc-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}

.dc-time {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.4);
}

.dc-muted {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.dc-block {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.dc-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.45);
}

.dc-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.dc-sub {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.dc-list {
  list-style: none;
  margin: 0.25rem 0 0 0.5rem;
  padding: 0;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.7);
}

.dc-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.25rem;
}

.dc-chip {
  font-size: 0.6rem;
  border: 1px solid rgba(0, 227, 154, 0.3);
  color: #00e39a;
  border-radius: 999px;
  padding: 0.08rem 0.5rem;
}

.dc-chip-muted {
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

.dc-chip-trust {
  border-color: rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.dc-chip-ev {
  border-color: rgba(0, 227, 154, 0.3);
  color: #00e39a;
}

.dc-focus-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.dc-focus-col {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.dc-focus-title {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.4);
}

.dc-focus-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.7);
}

.dc-briefing {
  padding: 0.5rem;
  background: rgba(0, 213, 255, 0.05);
  border: 1px solid rgba(0, 213, 255, 0.15);
  border-radius: 8px;
}

.dc-greeting {
  font-weight: 600;
  color: #00d5ff;
  margin: 0 0 0.25rem 0;
}

.dc-actions {
  list-style: none;
  margin: 0.25rem 0 0 0.5rem;
  padding: 0;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.8);
}

.dc-focus-note {
  font-size: 0.7rem;
  color: #00d5ff;
  font-style: italic;
  margin: 0.25rem 0 0 0;
}
</style>