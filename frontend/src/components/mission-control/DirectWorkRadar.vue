<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { isTauri } from '@tauri-apps/api/core'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import {
  approveDelivery,
  fetchDeliveryQueue,
  fetchDiscoveredSources,
  discoverSourceCandidates,
  fetchDirectWorkDailyBrief,
  fetchDirectWorkRecommendations,
  fetchDirectWorkWorkBank,
  fetchSourceIntel,
  prepareDelivery,
  probeSourceCandidate,
  runDirectWorkCycle,
  type DailyBrief,
  type DeliverableItem,
  type DeliveryPackage,
  type DirectWorkRanked,
  type SourceIntelResponse,
  type WorkBankState,
  type DiscoveredSourceCandidate,
} from '@/services/ownexData'

const router = useRouter()
const bank = ref<WorkBankState | null>(null)
const sourceCandidates = ref<DiscoveredSourceCandidate[]>([])
const sourceCandidateTotal = ref(0)
const sourceFeedsUnsupported = ref<string[]>([])
const brief = ref<DailyBrief | null>(null)
const ranked = ref<DirectWorkRanked[]>([])
const radar = ref<SourceIntelResponse | null>(null)
const deliveryQueue = ref<DeliverableItem[]>([])
const loading = ref(true)
const running = ref(false)
const discoveringSources = ref(false)
const error = ref('')
const preparing = ref('')
const prepared = ref<Record<string, DeliveryPackage>>({})
const approvedIds = ref<Set<string>>(new Set())
const taskQuery = ref('')
const taskSource = ref('')
const taskStatus = ref('')

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
  if (!window.confirm('¿Confirmás que ya enviaste este trabajo en la plataforma? OWNEX solo registrará el estado; no lo enviará ni confirmará aceptación o pago.')) return
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
const taskSources = computed(() => [...new Set((bank.value?.items ?? []).map((item) => item.platform))].sort())
const filteredWorkItems = computed(() => (bank.value?.items ?? []).filter((item) => {
  const query = taskQuery.value.trim().toLowerCase()
  return (!query || `${item.title} ${item.description ?? ''} ${item.category}`.toLowerCase().includes(query))
    && (!taskSource.value || item.platform === taskSource.value)
    && (!taskStatus.value || item.status === taskStatus.value)
}))

async function openTask(itemId: string) {
  const target = { name: 'work-detail', params: { id: itemId } }
  const url = router.resolve(target).href
  if (!isTauri()) {
    window.open(url, '_blank', 'noopener,noreferrer')
    return
  }

  const label = `work-${itemId.replace(/[^A-Za-z0-9_-]/g, '-').slice(0, 48)}`
  try {
    const existing = await WebviewWindow.getByLabel(label)
    if (existing) {
      await existing.setFocus()
      return
    }
    const detailWindow = new WebviewWindow(label, {
      url,
      title: 'OWNEX · Detalle del trabajo',
      width: 1100,
      height: 800,
      minWidth: 720,
      minHeight: 600,
    })
    void detailWindow.once('tauri://error', () => { void router.push(target) })
  } catch {
    await router.push(target)
  }
}

function isSafeExternalUrl(raw: string): boolean {
  try {
    return ['https:', 'http:'].includes(new URL(raw).protocol)
  } catch {
    return false
  }
}

function sourceLifecycleLabel(lifecycle: string): string {
  const labels: Record<string, string> = {
    DISCOVERED: 'DESCUBIERTA',
    PROBED: 'SONDEADA',
    VERIFIED: 'EVIDENCIA DECLARADA · REVISIÓN PENDIENTE',
    ACTIVE: 'AUTORIZADA · SOLO METADATOS',
    DECAY: 'EN DECAIMIENTO',
    DEACTIVATED: 'DESACTIVADA',
  }
  return labels[lifecycle] ?? lifecycle
}

async function refreshSources() {
  try {
    const sources = await fetchDiscoveredSources()
    sourceCandidates.value = sources.candidates
    sourceCandidateTotal.value = sources.total
    sourceFeedsUnsupported.value = sources.unsupported_feeds
  } catch {
    // Keep the last known state visible; work data and source discovery degrade independently.
  }
}

async function discoverSourcesNow() {
  discoveringSources.value = true
  error.value = ''
  try {
    await discoverSourceCandidates()
    await refreshSources()
  } catch {
    error.value = 'No se pudo consultar el discovery de fuentes.'
  } finally {
    discoveringSources.value = false
  }
}

async function probeSource(sourceId: string) {
  try {
    const candidate = await probeSourceCandidate(sourceId)
    sourceCandidates.value = sourceCandidates.value.map((item) => item.id === sourceId ? candidate : item)
  } catch {
    error.value = `No se pudo sondear la fuente ${sourceId}.`
  }
}

let refreshTimer: ReturnType<typeof setInterval> | undefined
onMounted(async () => {
  await loadAll()
  await refreshSources()
  refreshTimer = setInterval(() => {
    void loadAll()
    void refreshSources()
  }, 30_000)
})
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
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
                <a v-if="isSafeExternalUrl(s.url)" :href="s.url" target="_blank" rel="noopener noreferrer" class="dw-title dw-link">{{ s.name }}</a>
                <span v-else class="dw-title">{{ s.name }}</span>
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
              <a v-if="isSafeExternalUrl(s.url)" :href="s.url" target="_blank" rel="noopener noreferrer" class="dw-title dw-link">{{ s.name }}</a>
              <span v-else class="dw-title">{{ s.name }}</span>
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

      <section v-if="bank?.items.length" class="dw-deliver">
        <span class="dw-deliver-label">Todos los trabajos · {{ bank.items.length }} registrados</span>
        <div class="flex flex-wrap gap-2">
          <input v-model="taskQuery" aria-label="Buscar trabajos" placeholder="Buscar título o descripción" class="rounded border border-border bg-background px-2 py-1 text-xs" />
          <select v-model="taskSource" aria-label="Filtrar por fuente" class="rounded border border-border bg-background px-2 py-1 text-xs"><option value="">Todas las fuentes</option><option v-for="source in taskSources" :key="source" :value="source">{{ source }}</option></select>
          <select v-model="taskStatus" aria-label="Filtrar por estado" class="rounded border border-border bg-background px-2 py-1 text-xs"><option value="">Todos los estados</option><option v-for="status in [...new Set(bank.items.map((entry) => entry.status))]" :key="status" :value="status">{{ status }}</option></select>
        </div>
        <p v-if="!filteredWorkItems.length" class="dw-sub">No hay trabajos que coincidan con estos filtros.</p>
        <article v-for="item in filteredWorkItems" :key="item.id" class="dw-deliver-item">
          <div class="dw-deliver-main">
            <span class="dw-title">{{ item.title }}</span>
            <span class="dw-sub">{{ item.platform }} · {{ item.category }} · {{ item.reward ? `${item.reward} anunciados (moneda no registrada)` : 'recompensa desconocida' }}</span>
            <span class="dw-sub">{{ item.status }} · acceso: {{ item.access_status }}<template v-if="item.access_requirement"> · {{ item.access_requirement }}</template></span>
          </div>
          <button class="dw-btn" @click="openTask(item.id)">Abrir detalle ↗</button>
        </article>
      </section>

      <section class="dw-radar-block">
        <div class="dw-radar-head">
        <span class="dw-deliver-label">Fuentes descubiertas · {{ sourceCandidateTotal }}</span>
          <div class="dw-actions"><span class="dw-sub">La aprobación habilita solo metadatos; no prueba pagos ni conecta tareas.</span><button class="dw-btn" :disabled="discoveringSources" @click="discoverSourcesNow">{{ discoveringSources ? 'Buscando…' : 'Buscar fuentes' }}</button></div>
        </div>
        <p v-if="sourceFeedsUnsupported.length" class="dw-sub">Feeds no conectados: {{ sourceFeedsUnsupported.join(', ') }}</p>
        <ul v-if="sourceCandidates.length" class="dw-list">
          <li v-for="source in sourceCandidates.slice(0, 10)" :key="source.id" class="dw-item">
            <div class="dw-main">
              <a v-if="isSafeExternalUrl(source.source_url)" :href="source.source_url" target="_blank" rel="noopener noreferrer" class="dw-title dw-link">{{ source.name }}</a>
              <span v-else class="dw-title">{{ source.name }}</span>
              <span class="dw-sub">{{ source.id }} · {{ source.profile?.adapter_type || 'protocolo sin detectar' }}</span>
              <span class="dw-sub">Descubierta: {{ source.discovered_at }} · Sondeo: {{ source.profile?.probed_at || 'sin sondear' }}</span>
              <span v-if="source.last_error" class="dw-sub">Último error: {{ source.last_error }}</span>
              <details v-if="source.profile || source.verification_evidence?.length" class="dw-sub">
                <summary>Ver protocolo y evidencia</summary>
                <span v-if="source.profile?.capabilities?.length">Capacidades declaradas: {{ source.profile.capabilities.join(', ') }}</span>
                <span v-for="evidence in source.profile?.evidence || []" :key="`${evidence.kind}-${evidence.url}`" class="block">{{ evidence.kind || 'Evidencia' }}: {{ evidence.url }}</span>
              <span v-for="evidence in source.verification_evidence" :key="evidence" class="block">Referencia declarada para revisión: {{ evidence }}</span>
              </details>
              <button v-if="!source.profile" class="dw-btn mt-2" @click="probeSource(source.id)">Sondear metadatos</button>
            </div>
            <div class="dw-meta"><span class="dw-sub">{{ sourceLifecycleLabel(source.lifecycle) }}</span></div>
          </li>
        </ul>
        <p v-else class="dw-sub">No hay fuentes candidatas registradas. Estado: vacío o consulta no disponible.</p>
      </section>

      <!-- Delivery queue -->
      <div v-if="deliveryQueue.length" class="dw-deliver">
        <span class="dw-deliver-label">Listos para entregar</span>
        <div v-for="d in deliveryQueue" :key="d.id" class="dw-deliver-item">
          <div class="dw-deliver-main">
            <span class="dw-title">{{ d.title }}</span>
            <span class="dw-sub">{{ d.platform }} · {{ d.reward ? `${d.reward} anunciados (moneda no registrada)` : 'recompensa desconocida' }}</span>
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
              Ya lo envié
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
          </div>
          <div class="dw-meta">
            <span class="dw-score">{{ Math.round(r.overall_recommendation_score) }}</span>
            <span class="dw-ev">${{ Math.round(r.expected_value) }}</span>
            <span
              v-if="r.payment_compat_score < 100 && r.payment_compat_notes.length"
              class="dw-pay-badge"
              :class="{ 'dw-pay-ok': r.payment_compat_score > 50, 'dw-pay-warn': r.payment_compat_score <= 20, 'dw-pay-degraded': r.payment_compat_score > 20 && r.payment_compat_score <= 50 }"
              :title="r.payment_compat_notes[0]"
            >💳 {{ Math.round(r.payment_compat_score) }}</span>
            <span v-else-if="r.payout_method" class="dw-payout">{{ r.payout_method }}</span>
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
.dw-pay-badge {
  font-size: 0.68rem;
  font-weight: 600;
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
  border: 1px solid;
}
.dw-pay-ok {
  color: #00e39a;
  border-color: rgba(0, 227, 154, 0.5);
  background: rgba(0, 227, 154, 0.08);
}
.dw-pay-degraded {
  color: #00d5ff;
  border-color: rgba(0, 213, 255, 0.4);
  background: rgba(0, 213, 255, 0.06);
}
.dw-pay-warn {
  color: #00d5ff;
  border-color: rgba(0, 213, 255, 0.5);
  background: rgba(0, 213, 255, 0.08);
}
</style>
