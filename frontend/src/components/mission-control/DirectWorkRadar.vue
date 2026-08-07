<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  approveDelivery,
  fetchDeliveryQueue,
  fetchDirectWorkDailyBrief,
  fetchDirectWorkRecommendations,
  fetchDirectWorkWorkBank,
  fetchSourceIntel,
  prepareDelivery,
  runDirectWorkCycle,
  type DailyBrief,
  type DeliverableItem,
  type DeliveryPackage,
  type DirectWorkRanked,
  type SourceIntelResponse,
  type WorkBankState,
} from '@/services/ownexData'

const bank = ref<WorkBankState | null>(null)
const brief = ref<DailyBrief | null>(null)
const ranked = ref<DirectWorkRanked[]>([])
const radar = ref<SourceIntelResponse | null>(null)
const deliveryQueue = ref<DeliverableItem[]>([])
const loading = ref(true)
const running = ref(false)
const error = ref('')
const preparing = ref('')
const prepared = ref<Record<string, DeliveryPackage>>({})
const approvedIds = ref<Set<string>>(new Set())

async function loadAll() {
  loading.value = true
  error.value = ''
  const results = await Promise.allSettled([
    fetchDirectWorkWorkBank(),
    fetchDirectWorkDailyBrief(),
    fetchDirectWorkRecommendations(),
    fetchDeliveryQueue(),
    fetchSourceIntel(),
  ])
  loading.value = false

  if (results[0].status === 'fulfilled') bank.value = results[0].value
  if (results[1].status === 'fulfilled') brief.value = results[1].value
  if (results[2].status === 'fulfilled') ranked.value = results[2].value
  if (results[3].status === 'fulfilled') deliveryQueue.value = results[3].value.items
  if (results[4].status === 'fulfilled') radar.value = results[4].value

  if (results.every((r) => r.status === 'rejected')) {
    error.value = 'Direct Work no disponible'
  }
}

async function handlePrepare(itemId: string) {
  preparing.value = itemId
  try {
    prepared.value[itemId] = await prepareDelivery(itemId)
  } catch {
    error.value = 'No se pudo preparar la entrega'
  } finally {
    preparing.value = ''
  }
}

async function handleApprove(itemId: string) {
  try {
    await approveDelivery(itemId)
    approvedIds.value = new Set([...approvedIds.value, itemId])
    await loadAll()
  } catch {
    error.value = 'No se pudo confirmar la entrega'
  }
}

async function runCycle() {
  running.value = true
  bank.value = null
  try {
    bank.value = await runDirectWorkCycle()
  } catch {
    error.value = 'No se pudo ejecutar el ciclo del Work Bank'
  } finally {
    running.value = false
  }
}

function targetsProgress(targets: WorkBankState['targets']) {
  return Object.entries(targets).map(([horizon, t]) => ({
    horizon,
    label: horizon === 'daily' ? 'Día' : horizon === 'weekly' ? 'Semana' : 'Mes',
    achieved: t.achieved,
    target: t.target,
    ready: t.ready_total,
    pct: t.pct,
  }))
}

const briefTop = computed(() => brief.value?.top_opportunity ?? null)

onMounted(loadAll)
</script>

<template>
  <div class="dw-radar">
    <div class="dw-header">
      <h3>Direct Work · Work Bank</h3>
      <div class="dw-actions">
        <span class="dw-badge">Zero Barrier</span>
        <button class="dw-run" :disabled="running" @click="runCycle">
          {{ running ? 'Ciclando…' : 'Correr ciclo' }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="dw-muted">Analizando oportunidades...</p>
    <p v-if="error" class="dw-muted">{{ error }}</p>

    <template v-if="!loading && !error">
      <!-- Morning Brief top pick -->
      <div v-if="briefTop" class="dw-brief">
        <span class="dw-brief-label">Brief de hoy</span>
        <div class="dw-item">
          <span class="dw-rank">#1</span>
          <div class="dw-main">
            <span class="dw-title">{{ briefTop.opportunity.title }}</span>
            <span class="dw-sub">{{ briefTop.opportunity.platform }} · score {{ Math.round(briefTop.overall_recommendation_score) }}</span>
          </div>
          <div class="dw-meta">
            <span class="dw-ev">${{ Math.round(briefTop.expected_value) }}</span>
          </div>
        </div>
        <span v-if="brief?.learning?.missing_skills?.length" class="dw-gap">
          Skill gap: {{ brief.learning.missing_skills.join(', ') }}
        </span>
        <div v-if="brief?.best_sources?.length" class="dw-sources">
          <span class="dw-sources-label">Donde convierte mejor mi próxima hora</span>
          <ul class="dw-list">
            <li v-for="s in brief.best_sources" :key="s.name" class="dw-item">
              <span class="dw-rank">★</span>
              <div class="dw-main">
                <a :href="s.url" target="_blank" class="dw-title dw-link">{{ s.name }}</a>
                <span class="dw-sub">{{ s.category }}</span>
              </div>
              <div class="dw-meta">
                <span class="dw-score">{{ Math.round(s.trust_score) }}</span>
                <span class="dw-ev">{{ s.earning_potential }}</span>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <!-- Global Radar -->
      <div v-if="radar" class="dw-radar-block">
        <div class="dw-radar-head">
          <span class="dw-deliver-label">Global Radar · {{ radar.analyzed }} fuentes curadas</span>
          <span class="dw-sub">
            {{ radar.stats.argentina_compatible }} compatibles AR · trust avg {{ radar.stats.avg_trust_score }}
          </span>
        </div>
        <ul v-if="radar.sources.length" class="dw-list">
          <li v-for="s in radar.sources.slice(0, 5)" :key="s.name" class="dw-item">
            <span class="dw-rank">{{ s.recommendation === 'DISCOVER' ? '★' : '·' }}</span>
            <div class="dw-main">
              <a :href="s.url" target="_blank" class="dw-title dw-link">{{ s.name }}</a>
              <span class="dw-sub">
                {{ s.category }} · {{ s.entry_barrier }} barrera · {{ s.payment_method }}
              </span>
            </div>
            <div class="dw-meta">
              <span class="dw-score">{{ Math.round(s.trust_score) }}</span>
              <span class="dw-ev">{{ s.earning_potential }}</span>
            </div>
          </li>
        </ul>
      </div>

      <!-- Work Bank targets -->
      <div v-if="bank" class="dw-targets">
        <div v-for="t in targetsProgress(bank.targets)" :key="t.horizon" class="dw-target">
          <div class="dw-target-row">
            <span class="dw-target-label">{{ t.label }}</span>
            <span class="dw-target-count">{{ t.achieved }} / {{ t.target }}</span>
          </div>
          <div class="dw-bar"><span class="dw-bar-fill" :style="{ width: `${t.pct}%` }" /></div>
        </div>
      </div>

      <!-- Delivery queue -->
      <div v-if="deliveryQueue.length" class="dw-deliver">
        <span class="dw-deliver-label">Listos para entregar</span>
        <div v-for="d in deliveryQueue" :key="d.id" class="dw-deliver-item">
          <div class="dw-deliver-main">
            <span class="dw-title">{{ d.title }}</span>
            <span class="dw-sub">{{ d.platform }} · ${{ Math.round(d.reward) }}</span>
            <span v-if="d.payout_method" class="dw-payout">{{ d.payout_method }}</span>
          </div>
          <div class="dw-deliver-actions">
            <button v-if="!prepared[d.id]" class="dw-btn" :disabled="preparing === d.id" @click="handlePrepare(d.id)">
              {{ preparing === d.id ? 'Preparando…' : 'Preparar' }}
            </button>
            <template v-else>
              <span class="dw-sub dw-ok">✓ {{ prepared[d.id].files.length }} archivos en {{ prepared[d.id].package_path }}</span>
              <a v-if="prepared[d.id].guide_url" :href="prepared[d.id].guide_url" target="_blank" class="dw-btn dw-btn-link">Guía</a>
            </template>
            <button
              v-if="!approvedIds.has(d.id)"
              class="dw-btn dw-btn-success"
              @click="handleApprove(d.id)"
            >
              Entregado
            </button>
            <span v-else class="dw-sub dw-ok">✓ Entregado</span>
          </div>
        </div>
      </div>

      <!-- Ranked opportunities -->
      <ul v-if="ranked.length" class="dw-list">
        <li v-for="r in ranked" :key="r.opportunity.id" class="dw-item">
          <span class="dw-rank">{{ r.rank }}</span>
          <div class="dw-main">
            <span class="dw-title">{{ r.opportunity.title }}</span>
            <span class="dw-sub">{{ r.opportunity.platform }} · {{ r.opportunity.category }}</span>
            <span v-if="r.payout_method" class="dw-payout">{{ r.payout_method }}</span>
          </div>
          <div class="dw-meta">
            <span class="dw-score">{{ Math.round(r.overall_recommendation_score) }}</span>
            <span class="dw-ev">${{ Math.round(r.expected_value) }}</span>
          </div>
        </li>
      </ul>

      <p v-if="!bank && ranked.length === 0 && !briefTop" class="dw-muted">
        Sin recomendaciones todavía. Ejecutá un ciclo para preparar trabajos.
      </p>
    </template>
  </div>
</template>

<style scoped>
.dw-radar {
  padding: 1rem;
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.dw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}
.dw-header h3 {
  margin: 0;
  font-size: 1rem;
}
.dw-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.dw-badge {
  font-size: 0.7rem;
  color: #00d5ff;
  border: 1px solid rgba(0, 213, 255, 0.4);
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
}
.dw-run {
  font-size: 0.7rem;
  color: #05060a;
  background: #00d5ff;
  border: none;
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  cursor: pointer;
}
.dw-run:disabled {
  opacity: 0.6;
  cursor: default;
}
.dw-brief {
  border: 1px solid rgba(0, 213, 255, 0.25);
  background: rgba(0, 213, 255, 0.05);
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.dw-brief-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #00d5ff;
}
.dw-radar-block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dw-radar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.dw-link {
  text-decoration: none;
}
.dw-link:hover {
  text-decoration: underline;
  color: #00d5ff;
}
.dw-sources {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.dw-sources-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.5);
}
.dw-gap {
  font-size: 0.7rem;
  color: #ff7a1a;
}
.dw-targets {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dw-target {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.dw-target-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.72rem;
}
.dw-target-label {
  color: #8b8d98;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.dw-target-count {
  font-weight: 600;
  color: #00e39a;
}
.dw-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
}
.dw-bar-fill {
  display: block;
  height: 100%;
  background: #00e39a;
  border-radius: 999px;
}
.dw-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dw-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.dw-rank {
  font-size: 0.85rem;
  font-weight: 700;
  color: #ff7a1a;
  width: 1.25rem;
}
.dw-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.dw-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.85rem;
}
.dw-sub {
  font-size: 0.72rem;
  color: #8b8d98;
}
.dw-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.1rem;
}
.dw-score {
  font-size: 0.9rem;
  font-weight: 600;
  color: #00e39a;
}
.dw-ev {
  font-size: 0.72rem;
  color: #8b8d98;
}
.dw-muted {
  font-size: 0.8rem;
  color: #8b8d98;
}
.dw-deliver {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.dw-deliver-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #00e39a;
}
.dw-deliver-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid rgba(0, 227, 154, 0.2);
  border-radius: 8px;
}
.dw-deliver-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.dw-deliver-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.dw-btn {
  font-size: 0.68rem;
  color: #00d5ff;
  background: transparent;
  border: 1px solid rgba(0, 213, 255, 0.4);
  border-radius: 999px;
  padding: 0.15rem 0.6rem;
  cursor: pointer;
  white-space: nowrap;
}
.dw-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.dw-btn-success {
  color: #00e39a;
  border-color: rgba(0, 227, 154, 0.4);
}
.dw-btn-link {
  text-decoration: none;
}
.dw-ok {
  color: #00e39a;
}
.dw-payout {
  font-size: 0.62rem;
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.2);
  background: rgba(52, 211, 153, 0.08);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  align-self: flex-start;
}
</style>