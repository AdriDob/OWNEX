<template>
  <div class="progressive-scaling">
    <div class="header">
      <h1>$3M → $10M Annual Progressive Scaling</h1>
      <p class="subtitle">Risk-minimized path to maximum revenue</p>
    </div>

    <!-- Current Phase Status -->
    <div class="phase-card">
      <div class="phase-header">
        <h2>Current Phase</h2>
        <span :class="['phase-badge', status.phase_class]">{{ status.phase_name }}</span>
      </div>
      <div class="phase-metrics">
        <div class="metric">
          <label>Target Annual</label>
          <span class="value">${{ formatNumber(status.target_annual) }}</span>
        </div>
        <div class="metric">
          <label>Target Monthly</label>
          <span class="value">${{ formatNumber(status.target_monthly) }}</span>
        </div>
        <div class="metric">
          <label>Current Monthly</label>
          <span class="value" :class="{ positive: status.current_monthly_revenue > 0 }">
            ${{ formatNumber(status.current_monthly_revenue) }}
          </span>
        </div>
        <div class="metric">
          <label>Progress</label>
          <span class="value">{{ progressPercentage }}%</span>
        </div>
      </div>
    </div>

    <!-- Progress Timeline -->
    <div class="timeline-section">
      <h2>Progress Timeline</h2>
      <div class="timeline">
        <div
          v-for="phase in phases"
          :key="phase.value"
          :class="['timeline-item', { active: phase.value === status.current_phase, completed: isPhaseCompleted(phase.value) }]"
        >
          <div class="timeline-marker">
            <div class="marker-icon">{{ getPhaseIcon(phase.value) }}</div>
          </div>
          <div class="timeline-content">
            <h3>{{ phase.name }}</h3>
            <p class="phase-details">{{ phase.details }}</p>
            <div class="phase-stats">
              <span class="stat">Annual: ${{ formatNumber(phase.target_annual) }}</span>
              <span class="stat">Risk: {{ phase.risk }}</span>
              <span class="stat">Success: {{ phase.success_prob }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stability Requirements -->
    <div class="stability-section">
      <h2>Stability Requirements</h2>
      <div class="requirements-grid">
        <div class="requirement-item" :class="{ met: requirement.met }">
          <div class="requirement-icon">{{ requirement.met ? '✓' : '○' }}</div>
          <div class="requirement-content">
            <label>{{ requirement.label }}</label>
            <span class="requirement-value">{{ requirement.value }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Risk Monitor -->
    <div class="risk-section">
      <h2>Risk Monitor</h2>
      <div class="risk-level-indicator">
        <div class="risk-bar">
          <div
            class="risk-fill"
            :class="riskLevelClass"
            :style="{ width: riskPercentage + '%' }"
          ></div>
        </div>
        <span :class="['risk-label', riskLevelClass]">{{ riskStatus.current_level }}</span>
      </div>
      <div class="risk-alerts">
        <div v-if="recentAlerts.length === 0" class="no-alerts">
          No recent risk alerts
        </div>
        <div v-else class="alert-list">
          <div
            v-for="alert in recentAlerts"
            :key="alert.timestamp"
            :class="['alert-item', alert.level.toLowerCase()]"
          >
            <span class="alert-icon">{{ getAlertIcon(alert.level) }}</span>
            <span class="alert-message">{{ alert.message }}</span>
            <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto Triggers -->
    <div class="triggers-section">
      <h2>Auto Triggers</h2>
      <div class="triggers-grid">
        <div
          v-for="trigger in triggers"
          :key="trigger.type"
          :class="['trigger-item', { active: trigger.triggered }]"
        >
          <div class="trigger-status">{{ trigger.triggered ? 'ACTIVE' : 'STANDBY' }}</div>
          <div class="trigger-name">{{ formatTriggerType(trigger.type) }}</div>
        </div>
      </div>
      <button @click="checkTriggers" class="check-triggers-btn">Check Triggers</button>
    </div>

    <!-- Adaptive Learning Section -->
    <div class="adaptive-section">
      <h2>Adaptive Learning — Success Rate Improvement</h2>
      <div class="adaptive-grid">
        <div
          v-for="(phase, key) in adaptiveProbabilities"
          :key="key"
          class="adaptive-card"
        >
          <div class="adaptive-header">
            <h3>{{ formatPhaseName(key) }}</h3>
            <span :class="['confidence-badge', getConfidenceClass(phase.confidence)]">
              Confidence: {{ (phase.confidence * 100).toFixed(0) }}%
            </span>
          </div>
          <div class="adaptive-metrics">
            <div class="metric-row">
              <span class="label">Baseline:</span>
              <span class="value baseline">{{ (phase.baseline * 100).toFixed(0) }}%</span>
            </div>
            <div class="metric-row">
              <span class="label">Learned:</span>
              <span class="value learned" :class="{ improved: phase.improvement > 0, perfect: phase.learned >= 0.95 }">
                {{ (phase.learned * 100).toFixed(0) }}%
              </span>
            </div>
            <div class="metric-row">
              <span class="label">Improvement:</span>
              <span class="value" :class="{ positive: phase.improvement > 0, negative: phase.improvement < 0 }">
                {{ phase.improvement > 0 ? '+' : '' }}{{ (phase.improvement * 100).toFixed(1) }}%
              </span>
            </div>
            <div class="metric-row" v-if="phase.learned >= 0.95">
              <span class="label">Status:</span>
              <span class="value perfect-badge">PERFECT 🏆</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Improvement Trajectory -->
    <div class="trajectory-section">
      <h2>Improvement Trajectory</h2>
      <div v-if="trajectory.length === 0" class="no-data">
        No trajectory data yet — record attempts to see improvement over time
      </div>
      <div v-else class="trajectory-chart">
        <div class="trajectory-month" v-for="point in trajectory" :key="point.month">
          <div class="month-label">{{ point.month }}</div>
          <div class="success-rates">
            <div
              v-for="(rate, phase) in point.success_rates"
              :key="phase"
              class="rate-bar"
              :style="{ height: `${rate * 100}%` }"
              :title="`${formatPhaseName(phase)}: ${(rate * 100).toFixed(0)}%`"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Statistics -->
    <div class="statistics-section">
      <h2>Learning Statistics</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <label>Total Attempts</label>
          <span class="value">{{ statistics.total_attempts }}</span>
        </div>
        <div class="stat-card">
          <label>Overall Success Rate</label>
          <span class="value">{{ (statistics.overall_success_rate * 100).toFixed(1) }}%</span>
        </div>
        <div
          v-for="(data, phase) in statistics.phase_breakdown"
          :key="phase"
          class="stat-card"
        >
          <label>{{ formatPhaseName(phase) }}</label>
          <span class="value">{{ (data.rate * 100).toFixed(1) }}%</span>
          <span class="sub">{{ data.attempts }} attempts</span>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="actions-section">
      <h2>Actions</h2>
      <div class="actions-grid">
        <button
          @click="evaluateProgression"
          :disabled="!canEvaluate"
          class="action-btn evaluate"
        >
          Evaluate Progression
        </button>
        <button
          @click="progressPhase"
          :disabled="!canProgress"
          class="action-btn progress"
        >
          Progress to Next Phase
        </button>
        <button
          @click="showMetricsModal = true"
          class="action-btn metrics"
        >
          Update Monthly Metrics
        </button>
      </div>
    </div>

    <!-- Metrics Modal -->
    <div v-if="showMetricsModal" class="modal-overlay" @click="showMetricsModal = false">
      <div class="modal-content" @click.stop>
        <h3>Update Monthly Metrics</h3>
        <form @submit.prevent="updateMetrics">
          <div class="form-group">
            <label>Monthly Revenue ($)</label>
            <input v-model.number="metricsForm.monthly_revenue" type="number" step="0.01" />
          </div>
          <div class="form-group">
            <label>Total Submissions</label>
            <input v-model.number="metricsForm.submissions" type="number" />
          </div>
          <div class="form-group">
            <label>Accepted Submissions</label>
            <input v-model.number="metricsForm.accepted" type="number" />
          </div>
          <div class="form-group">
            <label>Investment Return ($)</label>
            <input v-model.number="metricsForm.investment_return" type="number" step="0.01" />
          </div>
          <div class="form-group">
            <label>Current Capital ($)</label>
            <input v-model.number="metricsForm.current_capital" type="number" step="0.01" />
          </div>
          <div class="form-actions">
            <button type="submit" class="submit-btn">Update</button>
            <button type="button" @click="showMetricsModal = false" class="cancel-btn">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Phase {
  value: string
  name: string
  target_annual: number
  details: string
  risk: string
  success_prob: string
}

interface Status {
  current_phase: string
  phase_name: string
  target_annual: number
  target_monthly: number
  current_monthly_revenue: number
  months_at_phase: number
  required_stability: number
  can_progress: boolean
  current_capital: number
  peak_capital: number
  current_drawdown: number
  max_drawdown: number
  drawdown_limit: number
  acceptance_rate: number
  target_acceptance: number
  risk_of_ruin: number
}

interface RiskStatus {
  current_level: string
  thresholds: Record<string, any>
  recent_alerts: Array<{
    type: string
    level: string
    message: string
    timestamp: string
    action_required: boolean
    action_taken: string | null
  }>
}

interface Trigger {
  type: string
  triggered: boolean
}

const status = ref<Status>({
  current_phase: 'phase_1',
  phase_name: '$3M Annual (Baseline)',
  target_annual: 3000000,
  target_monthly: 250000,
  current_monthly_revenue: 0,
  months_at_phase: 0,
  required_stability: 24,
  can_progress: false,
  current_capital: 0,
  peak_capital: 0,
  current_drawdown: 0,
  max_drawdown: 0,
  drawdown_limit: 0.15,
  acceptance_rate: 0,
  target_acceptance: 0.65,
  risk_of_ruin: 0.05,
})

const riskStatus = ref<RiskStatus>({
  current_level: 'safe',
  thresholds: {},
  recent_alerts: [],
})

const triggers = ref<Trigger[]>([
  { type: 'phase_progression', triggered: false },
  { type: 'phase_downgrade', triggered: false },
  { type: 'risk_warning', triggered: false },
  { type: 'emergency_stop', triggered: false },
])

const adaptiveProbabilities = ref<Record<string, any>>({})
const trajectory = ref<Array<{ month: string; success_rates: Record<string, number>; total_attempts: number }>>([])
const statistics = ref<any>({
  total_attempts: 0,
  overall_success_rate: 0,
  phase_breakdown: {},
})

const showMetricsModal = ref(false)
const metricsForm = ref({
  monthly_revenue: 0,
  submissions: 0,
  accepted: 0,
  investment_return: 0,
  current_capital: 0,
})

const phases: Phase[] = [
  {
    value: 'phase_1',
    name: '$3M Annual (Baseline)',
    target_annual: 3000000,
    details: 'Multi-agent 5x, Work Bank 200 jobs, Freqtrade 5x',
    risk: '<5% ruin',
    success_prob: '80%',
  },
  {
    value: 'phase_2',
    name: '$5M Annual (Moderate)',
    target_annual: 5000000,
    details: 'Multi-agent 8x, Work Bank 400 jobs, Freqtrade 10x',
    risk: '15% ruin',
    success_prob: '60%',
  },
  {
    value: 'phase_3',
    name: '$7M Annual (Aggressive)',
    target_annual: 7000000,
    details: 'Multi-agent 12x, Work Bank 800 jobs, Freqtrade 15x',
    risk: '30% ruin',
    success_prob: '40%',
  },
  {
    value: 'phase_4',
    name: '$10M Annual (Maximum)',
    target_annual: 10000000,
    details: 'Multi-agent 20x, Work Bank 1500 jobs, Freqtrade 25x',
    risk: '50% ruin',
    success_prob: '20%',
  },
]

const progressPercentage = computed(() => {
  if (status.value.target_monthly === 0) return 0
  return Math.min((status.value.current_monthly_revenue / status.value.target_monthly) * 100, 100)
})

const status_phase_class = computed(() => {
  const phase = status.value.current_phase
  return `phase-${phase}`
})

const riskPercentage = computed(() => {
  const levels = { safe: 20, caution: 40, warning: 60, danger: 80, critical: 100 }
  return levels[riskStatus.value.current_level as keyof typeof levels] || 0
})

const riskLevelClass = computed(() => riskStatus.value.current_level)

const recentAlerts = computed(() => riskStatus.value.recent_alerts.slice(-5))

const canEvaluate = computed(() => true)
const canProgress = computed(() => status.value.can_progress)

const requirements = computed(() => [
  {
    label: 'Stability Period',
    value: `${status.value.months_at_phase}/${status.value.required_stability} months`,
    met: status.value.months_at_phase >= status.value.required_stability,
  },
  {
    label: 'Drawdown Limit',
    value: `${(status.value.current_drawdown * 100).toFixed(1)}% ≤ ${(status.value.drawdown_limit * 100).toFixed(1)}%`,
    met: status.value.current_drawdown <= status.value.drawdown_limit,
  },
  {
    label: 'Acceptance Rate',
    value: `${(status.value.acceptance_rate * 100).toFixed(1)}% ≥ ${(status.value.target_acceptance * 100).toFixed(1)}%`,
    met: status.value.acceptance_rate >= status.value.target_acceptance,
  },
])

const formatNumber = (num: number): string => {
  return num.toLocaleString('en-US', { maximumFractionDigits: 0 })
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const formatTriggerType = (type: string): string => {
  return type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

const getPhaseIcon = (phase: string): string => {
  const icons = { phase_1: '🎯', phase_2: '🚀', phase_3: '⚡', phase_4: '🏆' }
  return icons[phase as keyof typeof icons] || '○'
}

const getAlertIcon = (level: string): string => {
  const icons = { safe: '✓', caution: '⚠', warning: '⚠', danger: '🚨', critical: '🛑' }
  return icons[level as keyof typeof icons] || '○'
}

const isPhaseCompleted = (phase: string): boolean => {
  const phaseOrder = ['phase_1', 'phase_2', 'phase_3', 'phase_4']
  const currentIndex = phaseOrder.indexOf(status.value.current_phase)
  const phaseIndex = phaseOrder.indexOf(phase)
  return phaseIndex < currentIndex
}

const formatPhaseName = (phase: string): string => {
  const names = {
    phase_1: 'Phase 1 ($3M)',
    phase_2: 'Phase 2 ($5M)',
    phase_3: 'Phase 3 ($7M)',
    phase_4: 'Phase 4 ($10M)',
  }
  return names[phase as keyof typeof names] || phase
}

const getConfidenceClass = (confidence: number): string => {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

const fetchAdaptiveProbabilities = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/adaptive-probabilities')
    const data = await response.json()
    adaptiveProbabilities.value = data
  } catch (error) {
    console.error('Failed to fetch adaptive probabilities:', error)
  }
}

const fetchTrajectory = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/trajectory')
    const data = await response.json()
    trajectory.value = data
  } catch (error) {
    console.error('Failed to fetch trajectory:', error)
  }
}

const fetchStatistics = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/statistics')
    const data = await response.json()
    statistics.value = data
  } catch (error) {
    console.error('Failed to fetch statistics:', error)
  }
}

const fetchStatus = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/status')
    const data = await response.json()
    status.value = data
  } catch (error) {
    console.error('Failed to fetch status:', error)
  }
}

const fetchRiskStatus = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/risk-status')
    const data = await response.json()
    riskStatus.value = data
  } catch (error) {
    console.error('Failed to fetch risk status:', error)
  }
}

const fetchTriggers = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/triggers')
    const data = await response.json()
    triggers.value = data.triggers
  } catch (error) {
    console.error('Failed to fetch triggers:', error)
  }
}

const evaluateProgression = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/evaluate-progression', {
      method: 'POST',
    })
    const data = await response.json()
    alert(`Progression Evaluation:\n${data.reason}\nRecommendation: ${data.recommendation}`)
  } catch (error) {
    console.error('Failed to evaluate progression:', error)
  }
}

const progressPhase = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/progress', {
      method: 'POST',
    })
    const data = await response.json()
    if (data.status === 'progressed') {
      alert(`Progressed to ${data.new_phase}`)
      await fetchStatus()
    } else {
      alert(`Not eligible: ${data.reason}`)
    }
  } catch (error) {
    console.error('Failed to progress:', error)
  }
}

const updateMetrics = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/update-metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metricsForm.value),
    })
    if (response.ok) {
      showMetricsModal.value = false
      await fetchStatus()
      alert('Metrics updated successfully')
    }
  } catch (error) {
    console.error('Failed to update metrics:', error)
  }
}

const checkTriggers = async () => {
  try {
    const response = await fetch('/api/progressive-scaling/check-triggers', {
      method: 'POST',
    })
    const data = await response.json()
    triggers.value = data.results.map((r: any) => ({ type: r.type, triggered: r.triggered }))
    await fetchStatus()
    await fetchRiskStatus()
  } catch (error) {
    console.error('Failed to check triggers:', error)
  }
}

onMounted(() => {
  fetchStatus()
  fetchRiskStatus()
  fetchTriggers()
  fetchAdaptiveProbabilities()
  fetchTrajectory()
  fetchStatistics()
})
</script>

<style scoped>
.progressive-scaling {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 2rem;
}

.header h1 {
  font-size: 2.5rem;
  color: #fbbf24;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #9ca3af;
  font-size: 1.1rem;
}

.phase-card {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
  border: 1px solid #374151;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.phase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.phase-badge {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
}

.phase-badge.phase-phase_1 {
  background: #10b981;
  color: white;
}

.phase-badge.phase-phase_2 {
  background: #3b82f6;
  color: white;
}

.phase-badge.phase-phase_3 {
  background: #f59e0b;
  color: white;
}

.phase-badge.phase-phase_4 {
  background: #ef4444;
  color: white;
}

.phase-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.metric {
  background: rgba(0, 0, 0, 0.3);
  padding: 1rem;
  border-radius: 8px;
}

.metric label {
  display: block;
  color: #9ca3af;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.metric .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f3f4f6;
}

.metric .value.positive {
  color: #10b981;
}

.timeline-section {
  margin-bottom: 2rem;
}

.timeline-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.timeline {
  position: relative;
  padding-left: 2rem;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #374151;
}

.timeline-item {
  position: relative;
  margin-bottom: 2rem;
  padding-left: 1rem;
}

.timeline-marker {
  position: absolute;
  left: -2rem;
  top: 0;
  width: 2rem;
  height: 2rem;
  background: #1f2937;
  border: 2px solid #374151;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.timeline-item.active .timeline-marker {
  border-color: #fbbf24;
  background: #1f2937;
}

.timeline-item.completed .timeline-marker {
  border-color: #10b981;
  background: #10b981;
}

.marker-icon {
  font-size: 1rem;
}

.timeline-content h3 {
  color: #f3f4f6;
  margin-bottom: 0.5rem;
}

.phase-details {
  color: #9ca3af;
  margin-bottom: 0.5rem;
}

.phase-stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stat {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #9ca3af;
}

.stability-section {
  margin-bottom: 2rem;
}

.stability-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.requirements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.requirement-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.requirement-item.met {
  border-color: #10b981;
}

.requirement-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.requirement-item.met .requirement-icon {
  background: #10b981;
}

.requirement-content {
  flex: 1;
}

.requirement-content label {
  display: block;
  color: #9ca3af;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}

.requirement-value {
  color: #f3f4f6;
  font-weight: 600;
}

.risk-section {
  margin-bottom: 2rem;
}

.risk-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.risk-level-indicator {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.risk-bar {
  height: 8px;
  background: #374151;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.risk-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.risk-fill.safe {
  background: #10b981;
}

.risk-fill.caution {
  background: #f59e0b;
}

.risk-fill.warning {
  background: #f97316;
}

.risk-fill.danger {
  background: #ef4444;
}

.risk-fill.critical {
  background: #dc2626;
}

.risk-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.risk-label.safe {
  color: #10b981;
}

.risk-label.caution {
  color: #f59e0b;
}

.risk-label.warning {
  color: #f97316;
}

.risk-label.danger {
  color: #ef4444;
}

.risk-label.critical {
  color: #dc2626;
}

.risk-alerts {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
}

.no-alerts {
  color: #10b981;
  text-align: center;
  padding: 1rem;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.2);
}

.alert-item.safe {
  border-left: 3px solid #10b981;
}

.alert-item.caution {
  border-left: 3px solid #f59e0b;
}

.alert-item.warning {
  border-left: 3px solid #f97316;
}

.alert-item.danger {
  border-left: 3px solid #ef4444;
}

.alert-item.critical {
  border-left: 3px solid #dc2626;
}

.alert-icon {
  font-size: 1.2rem;
}

.alert-message {
  flex: 1;
  color: #f3f4f6;
}

.alert-time {
  color: #9ca3af;
  font-size: 0.85rem;
}

.triggers-section {
  margin-bottom: 2rem;
}

.triggers-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.triggers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.trigger-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.trigger-item.active {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.trigger-status {
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #9ca3af;
}

.trigger-item.active .trigger-status {
  color: #ef4444;
}

.trigger-name {
  color: #f3f4f6;
  font-size: 0.9rem;
}

.check-triggers-btn {
  width: 100%;
  padding: 0.75rem;
  background: #374151;
  color: #f3f4f6;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.check-triggers-btn:hover {
  background: #4b5563;
}

.actions-section {
  margin-bottom: 2rem;
}

.actions-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-btn {
  padding: 1rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.evaluate {
  background: #3b82f6;
  color: white;
}

.action-btn.evaluate:hover:not(:disabled) {
  background: #2563eb;
}

.action-btn.progress {
  background: #10b981;
  color: white;
}

.action-btn.progress:hover:not(:disabled) {
  background: #059669;
}

.action-btn.metrics {
  background: #8b5cf6;
  color: white;
}

.action-btn.metrics:hover {
  background: #7c3aed;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
}

.modal-content h3 {
  color: #f3f4f6;
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #9ca3af;
  margin-bottom: 0.5rem;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 6px;
  color: #f3f4f6;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.submit-btn {
  flex: 1;
  padding: 0.75rem;
  background: #10b981;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.cancel-btn {
  flex: 1;
  padding: 0.75rem;
  background: #374151;
  color: #f3f4f6;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.adaptive-section {
  margin-bottom: 2rem;
}

.adaptive-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.adaptive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.adaptive-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
}

.adaptive-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.adaptive-header h3 {
  color: #f3f4f6;
  font-size: 1rem;
  margin: 0;
}

.confidence-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.confidence-badge.high {
  background: #10b981;
  color: white;
}

.confidence-badge.medium {
  background: #f59e0b;
  color: white;
}

.confidence-badge.low {
  background: #6b7280;
  color: white;
}

.adaptive-metrics {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-row .label {
  color: #9ca3af;
  font-size: 0.85rem;
}

.metric-row .value {
  color: #f3f4f6;
  font-weight: 600;
}

.metric-row .value.baseline {
  color: #6b7280;
}

.metric-row .value.learned.improved {
  color: #10b981;
}

.metric-row .value.learned.perfect {
  color: #fbbf24;
  font-weight: 700;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
}

.perfect-badge {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 700;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.metric-row .value.positive {
  color: #10b981;
}

.metric-row .value.negative {
  color: #ef4444;
}

.trajectory-section {
  margin-bottom: 2rem;
}

.trajectory-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.no-data {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  color: #9ca3af;
}

.trajectory-chart {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  gap: 1rem;
  overflow-x: auto;
}

.trajectory-month {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}

.month-label {
  color: #9ca3af;
  font-size: 0.75rem;
  margin-bottom: 0.5rem;
}

.success-rates {
  display: flex;
  gap: 0.25rem;
  align-items: flex-end;
  height: 100px;
}

.rate-bar {
  width: 12px;
  background: linear-gradient(to top, #10b981, #34d399);
  border-radius: 2px;
  transition: height 0.3s ease;
  cursor: pointer;
}

.rate-bar:hover {
  background: linear-gradient(to top, #059669, #10b981);
}

.statistics-section {
  margin-bottom: 2rem;
}

.statistics-section h2 {
  margin-bottom: 1rem;
  color: #f3f4f6;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

.stat-card label {
  display: block;
  color: #9ca3af;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.stat-card .value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f3f4f6;
}

.stat-card .sub {
  display: block;
  color: #6b7280;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}
</style>
