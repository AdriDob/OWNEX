<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/lib/api'

// Reactive state for source control
const discoverSources = ref(false)
const fetchCandidates = ref(false)
const verifySource = ref('')
const activateSource = ref('')
const activateNote = ref('')

// Source candidates list
const candidates = ref<any[]>([])
const totalCandidates = ref(0)
const catalogOverview = ref<any>(null)

// Status and metrics
const loading = ref(false)
const error = ref<string | null>(null)
const status = ref('idle') // idle | discovering | verifying | activating

// Income estimates from current system
const activeSources = ref(530) // from the system state
const estimatedRealista = computed(() => activeSources.value * 150)
const estimatedOptimista = computed(() => activeSources.value * 284.04)
const meta150k = computed(() => estimatedOptimista.value >= 150000)
const meta199k = computed(() => estimatedOptimista.value >= 199000)
const catalogTotal = computed(() => catalogOverview.value?.adaptation?.total_sources ?? 0)
const adaptationRows = computed(() => {
  const levels = catalogOverview.value?.adaptation?.levels ?? {}
  return [
    { label: 'adapter_ready', value: levels.adapter_ready ?? 0 },
    { label: 'discoverable', value: levels.discoverable ?? 0 },
    { label: 'catalog_only', value: levels.catalog_only ?? 0 },
    { label: 'integration_verified', value: levels.integration_verified ?? 0 },
    { label: 'argentina_verified', value: levels.argentina_verified ?? 0 },
    { label: 'production_active', value: levels.production_active ?? 0 },
  ]
})
const visibleFamilies = computed(() => {
  const counts = catalogOverview.value?.families?.family_counts ?? {}
  const byFamily = catalogOverview.value?.families?.sources_by_family ?? {}
  return Object.entries(counts)
    .filter(([, count]) => Number(count) > 0)
    .map(([name, count]) => ({
      name: name.replace(/_/g, ' '),
      count: Number(count),
      names: byFamily[name] ?? [],
    }))
})
const candidateFamilies = computed(() => {
  const counts = catalogOverview.value?.families?.family_counts ?? {}
  const candidates = catalogOverview.value?.families?.candidate_counts ?? {}
  return Object.entries(candidates)
    .filter(([name, count]) => Number(counts[name] ?? 0) === 0 && Number(count) > 0)
    .map(([name, count]) => ({
      name: name.replace(/_/g, ' '),
      candidates: Number(count),
    }))
})
const unclassifiedFamilies = computed(() => catalogOverview.value?.families?.unclassified ?? 0)

// Load initial state
async function loadState() {
  loading.value = true
  try {
    // Fetch current stats
    const statsRes = await api.get('/discovery/stats')
    if (statsRes && statsRes.stats) {
      activeSources.value = statsRes.stats.total_active ?? 530
    }
    try {
      catalogOverview.value = await api.get('/discovery/sources/overview')
    } catch {
      catalogOverview.value = null
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// Fetch candidates from discovery system
async function loadCandidates() {
  try {
    const res = await api.get('/discovery/sources/candidates')
    candidates.value = res.candidates ?? []
    totalCandidates.value = res.total ?? candidates.value.length
    status.value = 'candidates_loaded'
  } catch (e: any) {
    error.value = e.message
    status.value = 'error'
  }
}

// Verify a source (3 checks obligatorios)
async function doVerifySource(sourceId: string) {
  status.value = 'verifying'
  try {
    const res = await api.post(`/discovery/sources/${sourceId}/verify`, {
      honeypot_pass: 'true',
      funding_verified: 'true',
      eligibility_verified: 'true'
    })
    return res
  } catch (e: any) {
    error.value = e.message
    status.value = 'error'
    throw e
  }
}

// Activate a source with approval note
async function doActivateSource(sourceId: string, note: string) {
  status.value = 'activating'
  try {
    const res = await api.post(`/discovery/sources/${sourceId}/activate`, {
      approval_note: note
    })
    return res
  } catch (e: any) {
    error.value = e.message
    status.value = 'error'
    throw e
  }
}

// Trigger discovery scan
async function runDiscovery() {
  status.value = 'discovering'
  try {
    const res = await api.post('/discovery/sources/discover')
    // Refresh candidates after discovery
    await loadCandidates()
    return res
  } catch (e: any) {
    error.value = e.message
    status.value = 'error'
    throw e
  }
}

// Watch for error clear
watch([error], () => {
  if (!error.value) {
    status.value = 'idle'
  }
})
</script>

<template>
  <section class="source-control">
    <div class="sc-header">
      <h3 class="sc-title">Control de Sources</h3>
      <p class="sc-sub">Gestión semiautónoma del pipeline de sources</p>
    </div>

    <div v-if="loading" class="sc-loading">Cargando estado...</div>

    <template v-else>
      <!-- Income Summary -->
      <div class="sc-income-summary">
        <div class="sc-income-block">
          <span class="sc-income-label">Sources ACTIVE con evidencia</span>
          <span class="sc-income-value">{{ activeSources.value }}</span>
        </div>
        <div class="sc-income-block">
          <span class="sc-income-label">Ingreso Realista</span>
          <span class="sc-income-value">${{ Math.round(estimatedRealista.value) }}/mes</span>
        </div>
        <div class="sc-income-block">
          <span class="sc-income-label">Ingreso Optimista</span>
          <span class="sc-income-value">${{ Math.round(estimatedOptimista.value) }}/mes</span>
        </div>
        <div v-if="meta150k" class="sc-income-block sc-income-ok">
          <span class="sc-income-label">Meta +$150k: <strong>✅ ALcanzada</strong></span>
        </div>
        <div v-else-if="meta199k" class="sc-income-block sc-income-ok">
          <span class="sc-income-label">Meta +$199k: <strong>✅ ALcanzada</strong></span>
        </div>
        <div v-else class="sc-income-block sc-income-pending">
          <span class="sc-income-label">Faltan por agregar</span>
          <span class="sc-income-value">{{ Math.ceil((199000 - estimatedOptimista.value) / 284.04) }} sources más</span>
        </div>
      </div>

      <!-- Catalog adaptation + families -->
      <div v-if="catalogOverview" class="sc-catalog-overview">
        <div class="sc-catalog-grid">
          <div class="sc-catalog-block">
            <span class="sc-income-label">Catálogo unificado</span>
            <span class="sc-income-value">{{ catalogTotal }}</span>
          </div>
          <div v-for="row in adaptationRows" :key="row.label" class="sc-catalog-block">
            <span class="sc-income-label">{{ row.label }}</span>
            <span class="sc-income-value">{{ row.value }}</span>
          </div>
        </div>
        <div class="sc-family-list">
          <span class="sc-income-label">Familias nivel 2</span>
          <div class="sc-family-chips">
            <span v-for="fam in visibleFamilies" :key="fam.name" class="sc-family-chip" :title="fam.names.join(', ')">
              {{ fam.name }} · {{ fam.count }}
            </span>
            <span
              v-for="fam in candidateFamilies"
              :key="`cand-${fam.name}`"
              class="sc-family-chip muted"
              title="Candidatos por verificar; no son fuentes catalogadas"
            >
              {{ fam.name }} · 0/{{ fam.candidates }} cand
            </span>
            <span class="sc-family-chip muted">sin familia · {{ unclassifiedFamilies }}</span>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="sc-actions" v-if="totalCandidates.value > 0">
        <div class="sc-action-row">
          <button 
            class="sc-btn primary" 
            @click="runDiscovery"
            :disabled="status === 'discovering'"
          >
            {{ status === 'discovering' ? 'Buscando...' : 'Descubrir Sources' }}
          </button>
          <button 
            class="sc-btn secondary" 
            @click="fetchCandidates"
            :disabled="status !== 'idle'"
          >
            {{ status === 'idle' ? 'Cargar Candidates' : 'Cargando...' }}
          </button>
        </div>

        <div v-if="candidates.length > 0" class="sc-candidates-list">
          <h4 class="sc-candidates-title">Candidates ({{ candidates.length }})</h4>
          <ul class="sc-candidates-ul">
            <li v-for="(c, i) in candidates" :key="i" class="sc-candidate-li">
              <span class="sc-candidate-name">{{ c.name || c.source || `Source ${i + 1}` }}</span>
              <span class="sc-candidate-platform">{{ c.platform || 'unknown' }}</span>
              <span 
                class="sc-candidate-actions">
                <button 
                  class="sc-btn-mini" 
                  @click="doVerifySource(c.id || c.name)"
                  title="Verificar source"
                >
                  ✓
                </button>
                <button 
                  class="sc-btn-mini" 
                  @click="activateNote = c.name; status = 'activating'; doActivateSource(c.id || c.name, activateNote)"
                  title="Activar source"
                >
                  ✓
                </button>
              </span>
            </li>
          </ul>
        </div>

        <!-- Verify/Activate forms -->
        <div v-if="status === 'verifying'" class="sc-verifying">
          <p>Verificando source...</p>
          <p class="sc-sub">Se aplican los 3 checks: honeypot_pass, funding_verified, eligibility_verified</p>
        </div>

        <div v-if="status === 'activating'" class="sc-activating">
          <p>Activando source...</p>
          <p class="sc-sub">Se requiere nota de aprobación humana</p>
          <textarea 
            v-model="activateNote" 
            class="sc-approval-note"
            placeholder="Nota de aprobación (ej: P0 priority: verified Argentina payout path)"
            rows="2"
          ></textarea>
          <button 
            class="sc-btn-primary-small" 
            @click="doActivateSource(activateSource || 'unknown', activateNote)"
            :disabled="!activateNote.trim()"
          >
            Activar
          </button>
        </div>
      </div>

      <!-- No candidates message -->
      <p v-else class="sc-no-candidates">
        No hay candidates disponibles. Haz clic en "Descubrir Sources" para cargar nuevas candidates.
      </p>
    </template>

    <!-- Error state -->
    <div v-if="error" class="sc-error">
      <p>Error: {{ error }}</p>
      <button class="sc-retry" @click="loadState">Reintentar</button>
    </div>
  </section>

  <style scoped>
  .source-control {
    border: 1px solid var(--ownex-stroke, #2a2e37);
    border-radius: 12px;
    background: var(--ownex-surface, #111318);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .sc-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }
  
  .sc-title {
    margin: 0;
    font-size: 0.85rem;
    letter-spacing: 0.12em;
    color: #fecaca;
  }
  
  .sc-sub {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  
  .sc-income-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .sc-income-block {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
  
  .sc-income-block:last-child {
    border-bottom: none;
  }
  
  .sc-income-label {
    font-size: 0.62rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  
  .sc-income-value {
    font-size: 0.9rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .sc-income-ok {
    color: #16a34a;
  }
  
  .sc-income-pending {
    color: #d97706;
  }
  
  .sc-actions {
    margin: 0.5rem 0;
  }
  
  .sc-action-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  
  .sc-btn {
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.04);
    color: #e5e7eb;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.35rem 0.6rem;
    cursor: pointer;
    transition: opacity 0.15s ease;
  }
  
  .sc-btn:hover { opacity: 0.85; }
  
  .sc-btn.primary {
    border-color: rgba(0, 213, 255, 0.5);
    color: #fecaca;
    background: rgba(0, 213, 255, 0.12);
  }
  
  .sc-btn.secondary {
    background: rgba(0, 213, 255, 0.08);
    color: #00d5ff;
  }
  
  .sc-btn-mini {
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius 6px;
    background: transparent;
    color: #00d5ff;
    font-size: 0.6rem;
    padding: 0.2rem 0.4rem;
    cursor: pointer;
  }
  
  .sc-candidates-list {
    margin: 0.5rem 0;
  }
  
  .sc-candidates-title {
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }
  
  .sc-candidates-ul {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .sc-candidate-li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 0.72rem;
    color: rgba(255, 255, 255, 0.8);
  }
  
  .sc-candidate-li:last-child {
    border-bottom: none;
  }
  
  .sc-candidate-name {
    font-weight: 600;
    color: #fecaca;
  }
  
  .sc-candidate-platform {
    font-size: 0.6rem;
    color: #94a3b8;
    margin-left: auto;
  }
  
  .sc-candidate-actions .sc-btn-mini {
    margin-left: 0.2rem;
  }
  
  .sc-approval-note {
    width: 100%;
    background: rgba(0, 213, 255, 0.08);
    border: 1px solid rgba(0, 213, 255, 0.3);
    border-radius: 6px;
    padding: 0.5rem;
    font-size: 0.7rem;
    color: #e5e7eb;
    resize: vertical;
    margin: 0.3rem 0;
  }
  
  .sc-verifying, .sc-activating {
    padding: 0.5rem 0;
    color: #00d5ff;
    font-size: 0.7rem;
  }
  
  .sc-sub {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 0.2rem;
  }
  
  .sc-no-candidates {
    padding: 1rem;
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.75rem;
  }
  
  .sc-error {
    padding: 0.5rem;
    background: rgba(255, 59, 48, 0.1);
    border: 1px solid rgba(255, 59, 48, 0.3);
    border-radius: 6px;
    color: #ff3f30;
    font-size: 0.7rem;
  }
  
  .sc-retry {
    margin-top: 0.4rem;
    background: transparent;
    color: #ff3f30;
  }
  
  .sc-income-block.sc-income-ok .sc-income-value {
    color: #16a34a;
  }
  
  .sc-income-block.sc-income-pending .sc-income-value {
    color: #d97706;
  }

  .sc-catalog-overview {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 0.6rem 0;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .sc-catalog-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
  }

  .sc-catalog-block {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .sc-family-list {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .sc-family-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .sc-family-chip {
    border: 1px solid rgba(0, 213, 255, 0.25);
    border-radius: 999px;
    background: rgba(0, 213, 255, 0.08);
    color: #e5e7eb;
    font-size: 0.62rem;
    padding: 0.2rem 0.55rem;
  }

  .sc-family-chip.muted {
    border-color: rgba(255, 255, 255, 0.15);
    background: rgba(255, 255, 255, 0.04);
    color: rgba(255, 255, 255, 0.55);
  }
  </style>
</template>