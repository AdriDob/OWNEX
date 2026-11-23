<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/lib/api'

// State de inversión separada por categorías
const loading = ref(true)
const error = ref<string | null>(null)

// CAPITAL / STATE
const totalCapital = ref(0) // Capital total disponible
const deployedCapital = ref(0) // Capital realmente desplegado/asignado
const availableCapital = ref(0) // Capital disponible = total - desplegado - reserva (calculado en loadState)

// PROYECTION vs REALIZED P&L
const projectedReturn = ref(0) // Capital × ROI estimado (no garantizado)
const unrealizedPnL = ref(0) // Ganancia/pérdida de posiciones abiertas
const realizedPnL = ref(0) // Resultado de operaciones cerradas (bruto)
const netRealizedPnL = ref(0) // P&L realizado neto (después de comisiones/costes)

// PAID vs WITHDRAWN
const paidReturn = ref(0) // Beneficios efectivamente acreditados/pagados
const withdrawnCapital = ref(0) // Capital propio retirado del sistema
const withdrawnProfits = ref(0) // Beneficios retirados del exchange/cuenta

// RISK METRICS
const currentDrawdown = ref(0) // Drawdown actual %
const maxDrawdown = ref(0) // Drawdown máximo histórico %
const maxDrawdownPct = ref(0) // Límite de drawdown configurado %
const exposureByStrategy = ref({}) // Exposición por estrategia
const verifiedStrategies = ref(0) // Strategies con historial verificado
const tradesWithEvidence = ref(0) // Trades con evidencia documentada

// PROVENANCE — backend ProvenanceLevel vocabulary; UNKNOWN is the honest
// default when the API does not report a level (never "simulated").
type InvestmentProvenance = 'EXCHANGE' | 'API' | 'IMPORTED' | 'MANUAL' | 'DERIVED' | 'UNKNOWN'
const provenanceLevel = ref<InvestmentProvenance>('UNKNOWN')
const provenanceSource = ref('')
const provenanceCollectedAt = ref('')
const provenanceVerifiedAt = ref('')
const provenanceVerificationMethod = ref('')
const provenanceEvidenceRefs = ref<ProvenanceEvidenceRef[]>([])

type ProvenanceEvidenceRef = 'simulated' | 'user_declared' | 'documented' | 'api_reported' | 'externally_verified'

// Load initial state from backend APIs
async function loadState() {
  try {
    // Fetch capital allocation state
    const statsRes = await api.get('/investment/status')
    if (statsRes && statsRes.success) {
      totalCapital.value = statsRes.total_capital ?? 0
      deployedCapital.value = statsRes.deployed ?? 0
      availableCapital.value = statsRes.available ?? 0
      projectedReturn.value = statsRes.projected_return ?? 0
      // Also fetch provenance data if available
      provenanceLevel.value = (statsRes.provenance_level as InvestmentProvenance | undefined) ?? 'UNKNOWN'
      provenanceSource.value = statsRes.provenance_source ?? ''
      provenanceCollectedAt.value = statsRes.provenance_collected_at ?? ''
      provenanceVerifiedAt.value = statsRes.provenance_verified_at ?? ''
      provenanceVerificationMethod.value = statsRes.provenance_verification_method ?? ''
      provenanceEvidenceRefs.value = statsRes.provenance_evidence_refs ?? []
    }

    // Fetch P&L and trade data
    const pnlRes = await api.get('/investment/metrics')
    if (pnlRes && pnlRes.success) {
      unrealizedPnL.value = pnlRes.unrealized_pnl ?? 0
      realizedPnL.value = pnlRes.realized_pnl ?? 0
      netRealizedPnL.value = pnlRes.net_realized_pnl ?? 0
      paidReturn.value = pnlRes.paid_return ?? 0
      withdrawnCapital.value = pnlRes.withdrawn_capital ?? 0
      withdrawnProfits.value = pnlRes.withdrawn_profits ?? 0
      currentDrawdown.value = pnlRes.current_drawdown ?? 0
      maxDrawdown.value = pnlRes.max_drawdown ?? 0
      maxDrawdownPct.value = pnlRes.max_drawdown_pct ?? 0
      exposureByStrategy.value = pnlRes.exposure_by_strategy ?? {}
      verifiedStrategies.value = pnlRes.verified_strategies ?? 0
      tradesWithEvidence.value = pnlRes.trades_with_evidence ?? 0
    }
  } catch (e: any) {
    error.value = e.message
    // Keep defaults - empty state is valid
  } finally {
    loading.value = false
  }
}

// Watch for changes - re-fetch when capital state changes
watch([totalCapital, deployedCapital], async () => {
  // Re-fetch detailed metrics when capital changes
  await loadState()
})
</script>

<template>
  <section class="investment-dashboard">
    <div class="id-header">
      <h3 class="id-title">Dashboard de Inversión</h3>
      <p class="id-sub">Capital desplegado vs retornos reales - OWNEX</p>
    </div>

    <div v-if="loading" class="id-loading">Cargando datos de inversión...</div>

    <template v-else>
      <!-- Capital & State Card -->
      <div class="id-card">
        <div class="id-card-head">
          <span class="id-card-label">CAPITAL</span>
          <span class="id-card-value">${{ totalCapital }}</span>
        </div>
        <div class="id-card-body">
          <div class="id-capital-stats">
            <div class="id-capital-item">
              <span class="id-capital-label">Desplegado</span>
              <span class="id-capital-value">${{ deployedCapital }}</span>
            </div>
            <div class="id-capital-item">
              <span class="id-capital-label">Disponible</span>
              <span class="id-capital-value id-capital-ok">${{ availableCapital }}</span>
            </div>
          </div>

          <p class="id-capital-note">
            Capital total vs capital en estrategias activas. No incluye retornos proyectados.
          </p>
        </div>
      </div>

      <!-- Projection vs Realized P&L Card -->
      <div class="id-card">
        <div class="id-card-head">
          <span class="id-card-label">RETORNO: PROYECTADO vs REALIZADO</span>
        </div>
        <div class="id-card-body">
          <div class="id-projection-realized">
            <div class="id-projection-stat">
              <span class="id-projection-label">Proyectado</span>
              <span class="id-projection-value id-projection-projected">${{ projectedReturn }}</span>
              <span class="id-projection-note">Estimación × ROI, no beneficio garantizado</span>
            </div>
            <div class="id-realized-stat">
              <span class="id-realization-label">P&L Realizado (bruto)</span>
              <span class="id-realization-value id-realization-bruto">${{ realizedPnL }}</span>
            </div>
            <div class="id-realization-stat">
              <span class="id-realization-label">P&L Realizado (neto)</span>
              <span class="id-realization-value id-realization-neto">${{ netRealizedPnL }}</span>
              <span class="id-realization-note">Después de comisiones y costes</span>
            </div>
          </div>

          <!-- Risk Badge -->
          <div v-if="maxDrawdownPct > 0" class="id-risk-badge">
            <span class="id-risk-label">Drawdown</span>
            <span class="id-risk-value" :class="{ 'id-risk-warning': currentDrawdown > maxDrawdownPct }">
              {{ currentDrawdown }}% / {{ maxDrawdownPct }}%
            </span>
          </div>
        </div>
      </div>

      <!-- Withdrawn Capital & Profits Card -->
      <div class="id-card">
        <div class="id-card-head">
          <span class="id-card-label">RETIROS Y PAGOS</span>
        </div>
        <div class="id-card-body">
          <div id-withdrawal-stats">
            <div class="id-withdrawal-item">
              <span class="id-withdrawal-label">Beneficios pagados</span>
              <span class="id-withdrawal-value id-withdrawal-paid">${{ paidReturn }}</span>
            </div>
            <div class="id-withdrawal-item">
              <span class="id-withdrawal-label">Capital retirado</span>
              <span class="id-withdrawal-value id-withdrawal-capital">${{ withdrawnCapital }}</span>
              <span class="id-withdrawal-note">Capital propio retornado (no es ganancia)</span>
            </div>
            <div class="id-withdrawal-item">
              <span class="id-withdrawal-label">Beneficios retirados</span>
              <span class="id-withdrawal-value id-withdrawal-profits">${{ withdrawnProfits }}</span>
              <span class="id-withdrawal-note">Ganancias efectivamente retiradas del exchange</span>
            </div>
          </div>

          <p class="id-withdrawal-note">
            ⚠️ Retirar capital propio no es ganar dinero. El ledger separa retorno de devolución del capital.
          </p>
        </div>
      </div>

      <!-- Strategies & Evidence Card -->
      <div class="id-card">
        <div class="id-card-head">
          <span class="id-card-label">ESTRATEGIAS Y EVIDENCIA</span>
        </div>
        <div class="id-card-body">
          <div id-strategy-stats">
            <div class="id-strategy-item">
              <span class="id-strategy-label">Strategies verificadas</span>
              <span class="id-strategy-value id-strategy-ok">{{ verifiedStrategies }}</span>
            </div>
            <div class="id-strategy-item">
              <span class="id-strategy-label">Trades con evidencia</span>
              <span class="id-strategy-value">{{ tradesWithEvidence }}</span>
            </div>
            <div class="id-strategy-item">
              <span class="id-strategy-label">Exposición por estrategia</span>
              <span class="id-strategy-value" :style="{ color: Object.keys(exposureByStrategy).length > 0 ? '#00d5ff' : '#6b7280' }">
                {{ Object.keys(exposureByStrategy).length }} estrategias
              </span>
            </div>
          </div>

          <p class="id-strategy-note">
            Las strategies sin historial verificado no aparecen como lucrativas.
            El P&L no realizado (${{ unrealizedPnL }}) está separado del realizado (${{ realizedPnL }}).
          </p>
        </div>
      </div>

      <!-- Provenance Card -->
      <div class="id-card">
        <div class="id-card-head">
          <span class="id-card-label">PROVEEDORIA DE DATOS</span>
        </div>
        <div class="id-card-body">
          <div class="id-provenance-stats">
            <div class="id-provenance-item">
              <span class="id-provenance-label">Nivel</span>
              <span class="id-provenance-value" :class="{ 'id-provenance-unknown': provenanceLevel === 'UNKNOWN' }">{{ provenanceLevel }}</span>
            </div>
            <div class="id-provenance-item">
              <span class="id-provenance-label">Fuente</span>
              <span class="id-provenance-value">{{ provenanceSource }}</span>
            </div>
            <div class="id-provenance-item">
              <span class="id-provenance-label">Collectd</span>
              <span class="id-provenance-value">{{ provenanceCollectedAt }}</span>
            </div>
            <div class="id-provenance-item">
              <span class="id-provenance-label">Verified</span>
              <span class="id-provenance-value">{{ provenanceVerifiedAt }}</span>
            </div>
            <div class="id-provenance-item">
              <span class="id-provenance-label">Method</span>
              <span class="id-provenance-value">{{ provenanceVerificationMethod }}</span>
            </div>
            <div class="id-provenance-item" v-if="provenanceEvidenceRefs.length > 0">
              <span class="id-provenance-label">Evidencias</span>
              <span class="id-provenance-value">{{ provenanceEvidenceRefs.length }} referencias</span>
            </div>
            <div class="id-provenance-item" v-else>
              <span class="id-provenance-label">Evidencias</span>
              <span class="id-provenance-value">{{ 'Ninguna' }}</span>
            </div>
          </div>
          <p class="id-provenance-note">
            Nivel de procedencia del dato (débil → fuerte): UNKNOWN = sin evidencia suficiente. DERIVED = calculado desde otros datos. MANUAL = ingresado a mano. IMPORTED = importado. API = reportado por API del exchange. EXCHANGE = verificado contra fills del exchange.
          </p>
        </div>
      </div>

      <!-- Summary: Projection vs Earned -->
      <div class="id-summary">
        <div class="id-summary-item">
          <span class="id-summary-label">Capital total</span>
          <span class="id-summary-value">{{ totalCapital }}</span>
        </div>
        <div class="id-summary-item">
          <span class="id-summary-label">Desplegado vs disponible</span>
          <span class="id-summary-value">{{ deployedCapital }} vs {{ availableCapital }}</span>
        </div>
        <div class="id-summary-item">
          <span class="id-summary-label">Proyectado vs Net Realizado</span>
          <span class="id-summary-value">{{ projectedReturn }} vs {{ netRealizedPnL }}</span>
        </div>
        <div v-if="netRealizedPnL > 0" class="id-summary-item id-summary-item-ok">
          <span class="id-summary-label">Meta de retorno</span>
          <span class="id-summary-value ok">✅ Rentabilidad comprobada</span>
        </div>
        <div v-else class="id-summary-item id-summary-item-pending">
          <span class="id-summary-label">Meta de retorno</span>
          <span class="id-summary-value pending">⏳ Proyección pendiente de validación</span>
        </div>
      </div>
    </template>

    <!-- Error state -->
    <div v-if="error" class="id-error">
      <p>Error: {{ error }}</p>
      <button class="id-retry" @click="loadState">Reintentar</button>
    </div>
  </section>

  <style scoped>
  .investment-dashboard {
    border: 1px solid var(--ownex-stroke, #2a2e37);
    border-radius: 12px;
    background: var(--ownex-surface, #111318);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 600px;
  }
  
  .id-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }
  
  .id-title {
    margin: 0;
    font-size: 0.85rem;
    letter-spacing: 0.12em;
    color: #fecaca;
  }
  
  .id-sub {
    font-size: 0.65rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  
  /* Card styles */
  .id-card {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    background: rgba(0, 213, 255, 0.03);
    padding: 0.8rem 1rem;
    margin-bottom: 0.8rem;
  }
  
  .id-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }
  
  .id-card-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(255, 255, 255, 0.4);
  }
  
  .id-card-value {
    font-size: 0.7rem;
    color: #00d5ff;
    font-weight: 600;
  }
  
  .id-card-body {
    margin-top: 0.4rem;
  }
  
  /* Capital stats */
  .id-capital-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .id-capital-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-capital-item:last-child {
    border-bottom: none;
  }
  
  .id-capital-label {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-capital-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-capital-ok {
    color: #16a34a;
  }
  
  .id-capital-note {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 0.2rem;
  }
  
  /* Projection vs Realized */
  .id-projection-realized {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .id-projection-stat {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-projection-stat:last-child {
    border-bottom: none;
  }
  
  .id-projection-label {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-projection-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: #fbbf24; /* amber for projection */
  }
  
  .id-projection-note {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 0.1rem;
  }
  
  .id-realization-stat {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-realization-stat:last-child {
    border-bottom: none;
  }
  
  .id-realization-label {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-realization-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-realization-bruto {
    color: #fbbf24;
  }
  
  .id-realization-neto {
    color: #10b981;
  }
  
  .id-realization-note {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 0.1rem;
  }
  
  /* Risk badge */
  .id-risk-badge {
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 6px;
    padding: 0.4rem 0.6rem;
    margin-top: 0.3rem;
  }
  
  .id-risk-label {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-risk-value {
    font-size: 0.7rem;
    font-weight: 600;
    color: #fbbf24;
  }
  
  .id-risk-warning {
    color: #ef4444;
  }
  
  /* Withdrawal stats */
  .id-withdrawal-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .id-withdrawal-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-withdrawal-item:last-child {
    border-bottom: none;
  }
  
  .id-withdrawal-label {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-withdrawal-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-withdrawal-paid {
    color: #10b981;
  }
  
  .id-withdrawal-capital {
    color: #f59e0b;
  }
  
  .id-withdrawal-profits {
    color: #10b981;
  }
  
  .id-withdrawal-note {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 0.1rem;
  }
  
  /* Strategy stats */
  .id-strategy-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .id-strategy-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-strategy-item:last-child {
    border-bottom: none;
  }
  
  .id-strategy-label {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-strategy-value {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-strategy-ok {
    color: #10b981;
  }
  
  .id-strategy-note {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.3);
    margin-top: 0.2rem;
  }
  
  /* Summary */
  .id-summary {
    margin-top: 0.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.5rem;
  }
  
  .id-summary-item {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-summary-item:last-child {
    border-bottom: none;
  }
  
  .id-summary-label {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-summary-value {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-summary-item-ok {
    color: #10b981;
  }
  
  .id-summary-item-pending {
    color: #f59e0b;
  }
  </style>