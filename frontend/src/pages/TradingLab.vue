<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchTradingLabDashboard,
  fetchStrategyRankings,
  fetchCapitalSnapshot,
  fetchRiskSummary,
  fetchEngineRegistry,
  fetchValidationStatus,
  fetchStrategyDetail,
  type TradingLabDashboard,
  type StrategyScore,
  type CapitalSnapshot,
  type RiskSummary,
  type EngineHealthStatus,
} from '@/services/ownexData'
import {
  TradingLabStats,
  TradingLabStrategyTable,
  TradingLabCapitalWidget,
  TradingLabRiskWidget,
  TradingLabEngineStatus,
  TradingLabValidationPanel,
} from '@/components/trading'
import { OwnexButton } from '@/components/ui/OwnexButton'
import { OwnexCard } from '@/components/ui/OwnexCard'

const router = useRouter()

// ── State ──────────────────────────────────────────────────────────────
const loading = ref(true)
const error = ref<string | null>(null)

const dashboard = ref<TradingLabDashboard | null>(null)
const strategyScores = ref<Array<any>>([])
const capitalSnapshot = ref<any>(null)
const riskSummary = ref<any>(null)
const engineRegistry = ref<Array<any>>([])
const validationStatus = ref<any>(null)

const activeTab = ref<'overview' | 'strategies' | 'capital' | 'risk' | 'engines' | 'validation'>('overview')
const selectedStrategy = ref<any>(null)
const showStrategyDetail = ref(false)

const autoRefresh = ref(true)
const refreshInterval = ref<ReturnType<typeof setInterval> | null>(null)

// ── Computed ───────────────────────────────────────────────────────────
const totalCapital = computed(() => capitalSnapshot.value?.total_usd || 0)
const todayPnL = computed(() => capitalSnapshot.value?.bounty?.pendiente_usd || 0)
const currentDrawdown = computed(() => riskSummary.value?.metrics?.current_drawdown || 0)
const activeStrategies = computed(() => strategyScores.value.filter(s => s.composite_score > 0).length)

// ── Methods ────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [
      dashboardRes,
      rankingsRes,
      capitalRes,
      riskRes,
      enginesRes,
      validationRes,
    ] = await Promise.allSettled([
      fetchTradingLabDashboard(),
      fetchStrategyRankings(),
      fetchCapitalSnapshot(),
      fetchRiskSummary(),
      fetchEngineRegistry(),
      fetchValidationStatus(),
    ])

    if (dashboardRes.status === 'fulfilled') dashboard.value = dashboardRes.value
    if (rankingsRes.status === 'fulfilled') strategyScores.value = rankingsRes.value
    if (capitalRes.status === 'fulfilled') capitalSnapshot.value = capitalRes.value
    if (riskRes.status === 'fulfilled') riskSummary.value = riskRes.value
    if (enginesRes.status === 'fulfilled') engineRegistry.value = enginesRes.value?.engines || []
    if (validationRes.status === 'fulfilled') validationStatus.value = validationRes.value

    if ([dashboardRes, rankingsRes, capitalRes, riskRes, enginesRes, validationRes].every(r => r.status === 'rejected')) {
      error.value = 'No se pudo cargar el Trading Lab'
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Error al cargar datos'
  } finally {
    loading.value = false
  }
}

function handleRefresh() {
  loadAll()
}

function startAutoRefresh() {
  if (refreshInterval.value) clearInterval(refreshInterval.value)
  if (autoRefresh.value) {
    refreshInterval.value = setInterval(() => loadAll(), 30000)
  }
}

function stopAutoRefresh() {
  if (refreshInterval.value) clearInterval(refreshInterval.value)
  refreshInterval.value = null
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) startAutoRefresh()
  else stopAutoRefresh()
}

function openStrategyDetail(strategy: any) {
  selectedStrategy.value = strategy
  showStrategyDetail.value = true
}

function closeStrategyDetail() {
  showStrategyDetail.value = false
  selectedStrategy.value = null
}

function formatCurrency(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'USD' }).format(num)
}

function formatPercent(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return `${(num * 100).toFixed(1)}%`
}

function formatNumber(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return new Intl.NumberFormat('es-AR').format(num)
}

function getHealthColor(health: string): string {
  switch (health) {
    case 'online': return 'var(--ownex-green)'
    case 'degraded': return 'var(--ownex-yellow)'
    case 'error': return 'var(--ownex-red)'
    default: return 'var(--ownex-muted)'
  }
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}

// ── Lifecycle ──────────────────────────────────────────────────────────
onMounted(async () => {
  await loadAll()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

function stopAutoRefresh() {
  if (refreshInterval.value) clearInterval(refreshInterval.value)
}
</script>

<template>
  <div class="trading-lab">
    <div class="tl-header">
      <div class="tl-title-section">
        <h1 class="tl-title">TRADING LAB</h1>
        <span class="tl-subtitle">Multi-Engine Trading Orchestrator</span>
      </div>
      <div class="tl-actions">
        <div class="tl-status" :style="{ backgroundColor: dashboard?.system?.health >= 80 ? 'var(--ownex-green)' : dashboard?.system?.health >= 50 ? 'var(--ownex-yellow)' : 'var(--ownex-red)' }">
          <span class="tl-status-dot"></span>
          <span>{{ dashboard?.system?.status?.toUpperCase() || 'LOADING' }}</span>
        </div>
        <div class="tl-auto-refresh">
          <label class="tl-toggle">
            <input type="checkbox" v-model="autoRefresh" @change="toggleAutoRefresh ? startAutoRefresh() : stopAutoRefresh()" />
            <span class="tl-toggle-label">Auto (30s)</span>
          </label>
          <OwnexButton variant="ghost" size="sm" @click="handleRefresh" :disabled="loading">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Refresh
          </OwnexButton>
        </div>
      </div>
    </div>

    <p v-if="loading" class="tl-loading">Cargando Trading Lab...</p>
    <p v-if="error" class="tl-error">{{ error }}</p>

    <template v-if="!loading && !error">
      <!-- Tab Navigation -->
      <div class="tl-tabs" role="tablist">
        <button
          v-for="tab in ['overview', 'strategies', 'capital', 'risk', 'engines', 'validation']"
          :key="tab"
          :class="['tl-tab', { active: activeTab === tab }]"
          @click="activeTab = tab"
          :aria-selected="activeTab === tab"
          role="tab"
        >
          {{ tab.toUpperCase() }}
        </button>
      </div>

      <!-- OVERVIEW TAB -->
      <div v-if="activeTab === 'overview'" class="tl-tab-panel">
        <TradingLabStats
          :total-capital="totalCapital"
          :today-pnl="todayPnL"
          :drawdown="currentDrawdown"
          :active-strategies="activeStrategies"
          :system-health="dashboard?.system?.health || 0"
          :system-status="dashboard?.system?.status || 'unknown'"
        />

        <div class="tl-grid-2">
          <OwnexCard title="TOP STRATEGIES" class="tl-card-full">
            <TradingLabStrategyTable :strategies="strategyScores.slice(0, 5)" @open-detail="openStrategyDetail" />
          </OwnexCard>

          <OwnexCard title="ENGINE STATUS" class="tl-card-full">
            <TradingLabEngineStatus :engines="engineRegistry" />
          </OwnexCard>
        </div>
      </div>

      <!-- STRATEGIES TAB -->
      <div v-if="activeTab === 'strategies'" class="tl-tab-panel">
        <div class="tl-toolbar">
          <h2>STRATEGY RANKINGS</h2>
          <div class="tl-filters">
            <select v-model="strategyFilter.ranking" class="tl-select">
              <option value="composite">COMPOSITE SCORE</option>
              <option value="return">RETURN</option>
              <option value="sharpe">SHARPE</option>
              <option value="drawdown">DRAWDOWN</option>
            </select>
          </div>
        </div>
        <TradingLabStrategyTable :strategies="filteredStrategies" @open-detail="openStrategyDetail" />
      </div>

      <!-- CAPITAL TAB -->
      <div v-if="activeTab === 'capital'" class="tl-tab-panel">
        <TradingLabCapitalWidget :snapshot="capitalSnapshot" />
      </div>

      <!-- RISK TAB -->
      <div v-if="activeTab === 'risk'" class="tl-tab-panel">
        <TradingLabRiskWidget :summary="riskSummary" />
      </div>

      <!-- ENGINES TAB -->
      <div v-if="activeTab === 'engines'" class="tl-tab-panel">
        <TradingLabEngineStatus :engines="engineRegistry" :detailed="true" />
      </div>

      <!-- VALIDATION TAB -->
      <div v-if="activeTab === 'validation'" class="tl-tab-panel">
        <TradingLabValidationPanel :status="validationStatus" />
      </div>
    </template>

    <!-- Strategy Detail Modal -->
    <div v-if="showStrategyDetail" class="tl-modal-overlay" @click.self="closeStrategyDetail">
      <div class="tl-modal">
        <div class="tl-modal-header">
          <h3>{{ selectedStrategy?.name || 'STRATEGY DETAIL' }}</h3>
          <button class="tl-modal-close" @click="closeStrategyDetail">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div class="tl-modal-body">
          <div v-if="selectedStrategy" class="tl-detail-grid">
            <div class="tl-detail-section">
              <h4>SCORES</h4>
              <div class="tl-score-bars">
                <div v-for="item in [
                  { label: 'COMPOSITE', value: selectedStrategy.composite_score, max: 100 },
                  { label: 'RETURN', value: selectedStrategy.return_score, max: 100 },
                  { label: 'RISK ADJ', value: selectedStrategy.risk_adjusted_score, max: 100 },
                  { label: 'CONSISTENCY', value: selectedStrategy.consistency_score, max: 100 },
                  { label: 'LIQUIDITY', value: selectedStrategy.liquidity_score, max: 100 },
                  { label: 'EXECUTION', value: selectedStrategy.execution_quality_score, max: 100 },
                  { label: 'ROBUSTNESS', value: selectedStrategy.robustness_score, max: 100 },
                ]" :key="item.label">
                  <div class="tl-score-row">
                    <span class="tl-score-label">{{ item.label }}</span>
                    <span class="tl-score-value">{{ Math.round(item.value) }}</span>
                  </div>
                  <div class="tl-progress-bar">
                    <div class="tl-progress-fill" :style="{ width: item.value + '%', backgroundColor: getScoreColor(item.value) }"></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="tl-detail-section">
              <h4>PENALTIES</h4>
              <div class="tl-penalty-list">
                <div v-for="item in [
                  { label: 'DRAWDOWN', value: selectedStrategy.drawdown_penalty },
                  { label: 'OVERFIT', value: selectedStrategy.overfit_penalty },
                  { label: 'CORRELATION', value: selectedStrategy.correlation_penalty },
                  { label: 'FEES', value: selectedStrategy.fee_penalty },
                  { label: 'SLIPPAGE', value: selectedStrategy.slippage_penalty },
                  { label: 'DATA QUALITY', value: selectedStrategy.data_quality_penalty },
                ]" :key="item.label">
                  <span class="tl-penalty-label">{{ item.label }}</span>
                  <span class="tl-penalty-value" :class="item.value > 0 ? 'tl-penalty-warn' : ''">{{ item.value }}</span>
                </div>
              </div>
            </div>

            <div class="tl-detail-section">
              <h4>REGIME PERFORMANCE</h4>
              <div class="tl-regime-table">
                <table>
                  <thead><tr><th>REGIME</th><th>SCORE</th></tr></thead>
                  <tbody>
                    <tr v-for="(value, regime) in selectedStrategy.regime_scores" :key="regime">
                      <td>{{ regime }}</td>
                      <td :style="{ color: getScoreColor(value) }">{{ Math.round(value) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="tl-detail-section">
              <h4>METADATA</h4>
              <dl class="tl-meta-list">
                <div v-for="item in [
                  { label: 'STRATEGY ID', value: selectedStrategy.strategy_id },
                  { label: 'ENGINE', value: selectedStrategy.engine_id },
                  { label: 'RANK', value: selectedStrategy.rank },
                  { label: 'COMPUTED', value: selectedStrategy.computed_at },
                ]" :key="item.label">
                  <dt>{{ item.label }}</dt>
                  <dd>{{ item.value }}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.trading-lab {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.tl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--ownex-stroke);
}
.tl-title { margin: 0; font-size: 1.5rem; font-weight: 700; }
.tl-subtitle { font-size: 0.75rem; color: var(--ownex-muted); text-transform: uppercase; letter-spacing: 0.1em; }
.tl-status { display: flex; align-items: center; gap: 0.5rem; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.tl-status-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.tl-auto-refresh { display: flex; align-items: center; gap: 1rem; }
.tl-toggle { display: flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; color: var(--ownex-muted); cursor: pointer; }
.tl-loading, .tl-error { text-align: center; padding: 3rem; font-size: 1.1rem; }
.tl-error { color: var(--ownex-red); }
.tl-tabs { display: flex; gap: 0.25rem; overflow-x: auto; padding-bottom: 0.5rem; border-bottom: 1px solid var(--ownex-stroke); }
.tl-tab { padding: 0.5rem 1rem; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: var(--ownex-muted); background: transparent; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.2s; }
.tl-tab:hover { color: var(--ownex-fg); }
.tl-tab.active { color: var(--ownex-primary); border-bottom-color: var(--ownex-primary); }
.tl-tab-panel { animation: fadeIn 0.2s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
.tl-grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
@media (max-width: 1024px) { .tl-grid-2 { grid-template-columns: 1fr; } }
.tl-card-full { height: 100%; }
.tl-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 1rem; }
.tl-filters { display: flex; gap: 0.5rem; }
.tl-select { padding: 0.35rem 0.75rem; font-size: 0.75rem; background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 6px; color: var(--ownex-fg); }
.tl-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 1rem; }
.tl-modal { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 12px; max-width: 800px; width: 100%; max-height: 90vh; overflow-y: auto; }
.tl-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem 1.5rem; border-bottom: 1px solid var(--ownex-stroke); }
.tl-modal-close { background: none; border: none; color: var(--ownex-muted); cursor: pointer; padding: 0.25rem; }
.tl-modal-body { padding: 1.5rem; }
.tl-detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
.tl-detail-section { background: var(--ownex-bg); border: 1px solid var(--ownex-stroke); border-radius: 8px; padding: 1rem; }
.tl-detail-section h4 { margin: 0 0 1rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ownex-muted); }
.tl-score-bars { display: flex; flex-direction: column; gap: 1rem; }
.tl-score-row { display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.25rem; }
.tl-score-label { color: var(--ownex-muted); text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.7rem; }
.tl-score-value { font-weight: 700; font-size: 1rem; }
.tl-progress-bar { height: 6px; background: var(--ownex-bg); border-radius: 3px; overflow: hidden; }
.tl-progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.tl-penalty-list { display: flex; flex-direction: column; gap: 0.5rem; }
.tl-penalty-row { display: flex; justify-content: space-between; font-size: 0.85rem; }
.tl-penalty-warn { color: var(--ownex-red); }
.tl-regime-table table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.tl-regime-table th, .tl-regime-table td { padding: 0.5rem; text-align: left; border-bottom: 1px solid var(--ownex-stroke); }
.tl-regime-table th { color: var(--ownex-muted); font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
.tl-meta-list { display: flex; flex-direction: column; gap: 0.75rem; }
.tl-meta-list dt { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ownex-muted); }
.tl-meta-list dd { margin: 0; font-family: monospace; font-size: 0.85rem; color: var(--ownex-fg); }
.tl-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
@media (max-width: 1024px) { .tl-grid-3 { grid-template-columns: 1fr; } }
</style>