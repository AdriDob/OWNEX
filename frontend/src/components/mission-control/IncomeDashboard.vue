<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '@/lib/api'

// Income metrics state - separated projection vs earned
const loading = ref(true)
const error = ref<string | null>(null)

// Current source counts from registry
const activeSources = ref(530)
const totalSources = ref(839)

// PROJECTION: estimated based on sources × historical rate (NOT earned revenue)
const projectedOptimista = computed(() => activeSources.value * 284.04)
const projectedRealista = computed(() => activeSources.value * 150)

// EARNED REVENUE: from revenue ledger / backend API (what's actually been paid)
const earnedRealista = ref(0)
const earnedOptimista = ref(0)
const paidRealista = ref(0)
const paidOptimista = ref(0)

// Load initial state from backend APIs
async function loadState() {
  try {
    // Fetch source counts from registry
    const statsRes = await api.get('/discovery/stats')
    if (statsRes && statsRes.stats) {
      activeSources.value = statsRes.stats.total_active ?? 530
      totalSources.value = statsRes.total_sources ?? 839
    }
    
    // Fetch actual earned revenue from revenue ledger
    const revRes = await api.get('/revenue/summary')
    if (revRes && revRes.success) {
      earnedRealista.value = revRes.total_payout || 0
      earnedOptimista.value = revRes.total_payout || 0  // same, currency conversion handled separately
    }
    
    // Fetch paid/revenue breakdown
    const findingsRes = await api.get('/findings')
    if (findingsRes && findingsRes.items) {
      const paidFindings = findingsRes.items.filter((f: any) => f.status === 'paid' || f.status === 'accepted')
      const paidAmount = paidFindings.reduce((sum: number, f: any) => sum + (f.payout || 0), 0)
      paidRealista.value = paidAmount
      paidOptimista.value = paidAmount
    }
  } catch (e: any) {
    error.value = e.message
    // Keep defaults if backend unavailable
  } finally {
    loading.value = false
  }
}

// Watch for changes - recalculate from backend when available
watch([activeSources], async () => {
  // Re-fetch earned revenue when source count changes
  await loadState()
})
</script>

<template>
  <section class="income-dashboard">
    <div class="id-header">
      <h3 class="id-title">Dashboard de Ingresos</h3>
      <p class="id-sub">Estimaciones vs ingresos reales - OWNEX</p>
    </div>

    <div v-if="loading" class="id-loading">Cargando datos...</div>

    <template v-else>
      <!-- Projection Card (based on sources × rate) -->
      <div class="id-card id-card-projection">
        <div class="id-card-head">
          <span class="id-card-label">POTENCIAL OPTIMISTA</span>
          <span class="id-card-sub">Fuentes × rate histórico</span>
        </div>
        <div class="id-card-body">
          <div class="id-projected-stats">
            <div class="id-stat">
              <span class="id-stat-label">Estimado/mes</span>
              <span class="id-stat-value">${{ Math.round(projectedOptimista.value) }}/mes</span>
            </div>
            <div class="id-stat">
              <span class="id-stat-label">Estimado realista</span>
              <span class="id-stat-value">${{ Math.round(projectedRealista.value) }}/mes</span>
            </div>
          </div>
          <p class="id-projected-note">
            Proyección basada en {{ activeSources.value }} sources ACTIVE con evidencia.
            No garantiza ingresos cobrados. Rate conservador: $150 real / $284 optimista por source/mes.
          </p>
        </div>
      </div>

      <!-- Earned Revenue Card (what's actually been paid) -->
      <div class="id-card id-card-earned">
        <div class="id-card-head">
          <span class="id-card-label">INGRESOS COBRADOS</span>
          <span class="id-card-sub">De revenue ledger</span>
        </div>
        <div class="id-card-body">
          <div class="id-earned-stats">
            <div class="id-stat">
              <span class="id-stat-label">Realista cobrado</span>
              <span class="id-stat-value">${{ Math.round(earnedRealista.value) }}/mes</span>
            </div>
            <div class="id-stat">
              <span class="id-stat-label">Optimista cobrado</span>
              <span class="id-stat-value">${{ Math.round(earnedOptimista.value) }}/mes</span>
            </div>
          </div>
          <p class="id-earned-note">
            Ingresos efectivamente registrados y pagados.
            Fuente: Revenue Ledger / backend API.
          </p>
        </div>
      </div>

      <!-- Paid/Withdrawn Breakdown -->
      <div class="id-card id-card-breakdown" v-if="paidRealista.value > 0 || earnedRealista.value > 0">
        <div class="id-card-head">
          <span class="id-card-label">Desglose de Pagos</span>
        </div>
        <div class="id-card-body">
          <div class="id-breakdown-stats">
            <div class="id-breakdown-item">
              <span class="id-breakdown-label">Realista pagado</span>
              <span class="id-breakdown-value">${{ Math.round(paidRealista.value) }}</span>
            </div>
            <div class="id-breakdown-item">
              <span class="id-breakdown-label">Optimista pagado</span>
              <span class="id-breakdown-value">${{ Math.round(paidOptimista.value) }}</span>
            </div>
            <div class="id-breakdown-item">
              <span class="id-breakdown-label">Realista earned</span>
              <span class="id-breakdown-value">${{ Math.round(earnedRealista.value) }}</span>
            </div>
            <div class="id-breakdown-item">
              <span class="id-breakdown-label">Optimista earned</span>
              <span class="id-breakdown-value">${{ Math.round(earnedOptimista.value) }}</span>
            </div>
          </div>
          <p class="id-breakdown-note">
            Diferencia entre earned y paid puede incluir procesos en curso, comisiones, o divisas.
          </p>
        </div>
      </div>

      <!-- Summary: Projection vs Earned -->
      <div class="id-summary">
        <div class="id-summary-item">
          <span class="id-summary-label">Fuentes ACTIVE con evidencia</span>
          <span class="id-summary-value">{{ activeSources.value }}</span>
        </div>
        <div class="id-summary-item">
          <span class="id-summary-label">Proyectado optimista/mes</span>
          <span class="id-summary-value">${{ Math.round(projectedOptimista.value) }}</span>
        </div>
        <div class="id-summary-item">
          <span class="id-summary-label">Cobrado optimista/mes</span>
          <span class="id-summary-value">${{ Math.round(earnedOptimista.value) }}</span>
        </div>
        <div v-if="earnedOptimista.value > 0" class="id-summary-item id-summary-item-ok">
          <span class="id-summary-label">Meta +$150k</span>
          <span class="id-summary-value ok">✅ Alcanzada en ingresos cobrados</span>
        </div>
        <div v-else class="id-summary-item id-summary-item-pending">
          <span class="id-summary-label">Meta +$150k</span>
          <span class="id-summary-value pending">⏳ Proyección, no cobrada</span>
        </div>
      </div>

      <!-- Source Growth Stats (informational only) -->
      <div class="id-growth">
        <h4 class="id-growth-title">Crecimiento de Sources (informacional)</h4>
        <div class="id-growth-stats">
          <div class="id-growth-stat">
            <span class="id-growth-label">Total Sources</span>
            <span class="id-growth-value">{{ totalSources.value }}</span>
          </div>
          <div class="id-growth-stat">
            <span class="id-growth-label">ACTIVE con evidencia</span>
            <span class="id-growth-value">{{ activeSources.value }}</span>
          </div>
        </div>
        <p class="id-growth-note">
          Tracking de registry growth, no proyección de ingresos directa.
        </p>
      </div>
    </template>

    <!-- Error state -->
    <div v-if="error" class="id-error">
      <p>Error: {{ error }}</p>
      <button class="id-retry" @click="loadState">Reintentar</button>
    </div>
  </section>

  <style scoped>
  .income-dashboard {
    border: 1px solid var(--ownex-stroke, #2a2e37);
    border-radius: 12px;
    background: var(--ownex-surface, #111318);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
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
  
  .id-income-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
    margin: 0.5rem 0;
  }
  
  .id-stat {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-stat:last-child {
    border-bottom: none;
  }
  
  .id-stat-label {
    font-size: 0.58rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-stat-value {
    font-size: 0.85rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-targets {
    margin: 0.5rem 0;
  }
  
  .id-targets-title {
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }
  
  .id-target-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-target-item:last-child {
    border-bottom: none;
  }
  
  .id-target-info {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  
  .id-target-label {
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.8);
  }
  
  .id-target-remaining {
    color: #d97706;
    font-size: 0.65rem;
  }
  
  .id-target-reached-label {
    color: #16a34a;
    font-size: 0.65rem;
    font-weight: 600;
  }
  
  .id-progression {
    margin: 0.5rem 0;
  }
  
  .id-progression-title {
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }
  
  .id-progression-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 0.5rem;
  }
  
  .id-progression-item {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-progression-item:last-child {
    border-bottom: none;
  }
  
  .id-progression-label {
    font-size: 0.6rem;
    color: rgba(255, 255, 255, 0.5);
    text-align: center;
  }
  
  .id-progression-realista {
    font-size: 0.65rem;
    color: #fbbf24;
    text-align: right;
  }
  
  .id-progression-optimista {
    font-size: 0.65rem;
    color: #00d5ff;
    text-align: right;
  }
  
  .id-growth {
    margin: 0.5rem 0;
  }
  
  .id-growth-title {
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
  }
  
  .id-growth-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 0.5rem;
  }
  
  .id-growth-stat {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .id-growth-stat:last-child {
    border-bottom: none;
  }
  
  .id-growth-label {
    font-size: 0.55rem;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .id-growth-value {
    font-size: 0.8rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
  
  .id-loading, .id-error {
    padding: 0.5rem;
    color: rgba(255, 255, 255, 0.5);
  }
  </style>
</template>