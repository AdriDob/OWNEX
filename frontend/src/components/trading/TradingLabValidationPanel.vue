<script setup lang="ts">
interface Props {
  status: any
}

const props = withDefaults(defineProps<Props>(), {
  status: () => ({}),
})

function getPhaseStatus(phase: string, status: any): { label: string, class: string, passed: boolean } {
  const phases: Record<string, { label: string, key: string }> = {
    phase_1_backtest: { label: 'BACKTEST', key: 'phase_1_backtest' },
    phase_2_out_of_sample: { label: 'OUT-OF-SAMPLE', key: 'phase_2_out_of_sample' },
    phase_3_walk_forward: { label: 'WALK-FORWARD', key: 'phase_3_walk_forward' },
    phase_4_monte_carlo: { label: 'MONTE CARLO', key: 'phase_4_monte_carlo' },
    phase_5_stress_test: { label: 'STRESS TEST', key: 'phase_5_stress_test' },
    phase_6_paper: { label: 'PAPER TRADING', key: 'phase_6_paper' },
    phase_7_canary: { label: 'CANARY', key: 'phase_7_canary' },
    phase_8_production: { label: 'PRODUCTION', key: 'phase_8_production' },
  }

  const phaseInfo = phases[phase] || { label: phase.toUpperCase(), key: phase }
  const phaseStatus = status?.phases?.[phaseInfo.key]
  
  if (!phaseStatus) return { label: phaseInfo.label, class: 'badge-pending', passed: false }
  if (phaseStatus.passed) return { label: phaseInfo.label, class: 'badge-passed', passed: true }
  return { label: phaseInfo.label, class: 'badge-failed', passed: false }
}

function formatTimestamp(ts: string | undefined): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-AR')
}

function formatDuration(start: string | undefined, end: string | undefined): string {
  if (!start || !end) return '—'
  const diff = new Date(end).getTime() - new Date(start).getTime()
  const mins = Math.floor(diff / 60000)
  const secs = Math.floor((diff % 60000) / 1000)
  return `${mins}m ${secs}s`
}
</script>

<template>
  <div class="tl-validation-panel">
    <div class="tl-validation-header">
      <div class="vl-summary">
        <div class="vl-summary-card">
          <span class="vl-summary-label">OVERALL</span>
          <span class="vl-summary-value" :class="status?.overall_passed ? 'tl-passed' : 'tl-failed'">
            {{ status?.overall_passed ? 'PASSED' : 'FAILED' }}
          </span>
        </div>
        <div class="vl-summary-card">
          <span class="vl-summary-label">CURRENT PHASE</span>
          <span class="vl-summary-value">{{ status?.current_phase || '—' }}</span>
        </div>
        <div class="vl-summary-card">
          <span class="vl-summary-label">STARTED</span>
          <span class="vl-summary-value">{{ formatTimestamp(status?.started_at) }}</span>
        </div>
        <div class="vl-summary-card">
          <span class="vl-summary-label">COMPLETED</span>
          <span class="vl-summary-value">{{ formatTimestamp(status?.completed_at) }}</span>
        </div>
      </div>

      <div class="vl-phases">
        <h3 class="tl-section-title">VALIDATION PHASES</h3>
        <div class="vl-phase-list">
          <div v-for="phase in [
            'phase_1_backtest',
            'phase_2_out_of_sample',
            'phase_3_walk_forward',
            'phase_4_monte_carlo',
            'phase_5_stress_test',
            'phase_6_paper',
            'phase_7_canary',
            'phase_8_production'
          ]" :key="phase" class="vl-phase-item">
            <div class="vl-phase-header" :class="getPhaseStatus(phase, status).class">
              <div class="vl-phase-info">
                <span class="vl-phase-label">{{ getPhaseStatus(phase, status).label }}</span>
                <span class="vl-phase-phase">{{ phase }}</span>
              </div>
              <div class="vl-phase-status">
                <span class="vl-phase-badge" :class="getPhaseStatus(phase, status).class">
                  {{ getPhaseStatus(phase, status).passed ? 'PASSED' : 'FAILED' }}
                </span>
              </div>
            </div>
            <div v-if="status?.phases?.[phase]" class="vl-phase-details">
              <div class="vl-detail-row">
                <span class="vl-detail-label">STATUS</span>
                <span :class="status.phases[phase].passed ? 'tl-passed' : 'tl-failed'">
                  {{ status.phases[phase].passed ? 'PASSED' : 'FAILED' }}
                </span>
              </div>
              <div class="vl-detail-row">
                <span class="vl-detail-label">DURATION</span>
                <span>{{ formatDuration(status.phases[phase].started_at, status.phases[phase].completed_at) }}</span>
              </div>
              <div class="vl-detail-row" v-if="status.phases[phase].details">
                <span class="vl-detail-label">DETAILS</span>
                <span class="vl-detail-value">{{ status.phases[phase].details }}</span>
              </div>
              <div class="vl-detail-row" v-if="status.phases[phase].error">
                <span class="vl-detail-label">ERROR</span>
                <span class="tl-error">{{ status.phases[phase].error }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="vl-overfit" v-if="status?.overfit_report">
        <h3 class="tl-section-title">OVERFITTING ANALYSIS</h3>
        <div class="vl-overfit-summary">
          <div class="vl-overfit-score">
            <span class="vl-overfit-label">OVERFIT SCORE</span>
            <span class="vl-overfit-value" :class="status.overfit_report.risk_level === 'critical' ? 'tl-critical' : status.overfit_report.risk_level === 'high' ? 'tl-high' : status.overfit_report.risk_level === 'medium' ? 'tl-medium' : 'tl-low'">
              {{ status.overfit_report.overall_score }}/100
            </span>
          </div>
          <div class="vl-overfit-risk">
            <span class="vl-overfit-label">RISK LEVEL</span>
            <span :class="status.overfit_report.risk_level === 'critical' ? 'tl-critical' : status.overfit_report.risk_level === 'high' ? 'tl-high' : status.overfit_report.risk_level === 'medium' ? 'tl-medium' : 'tl-low'">
              {{ status.overfit_report.risk_level.toUpperCase() }}
            </span>
          </div>
        </div>

        <div class="vl-checks">
          <h4 class="tl-subtitle">INDIVIDUAL CHECKS</h4>
          <div class="vl-check-list">
            <div v-for="check in status.overfit_report.checks" :key="check.check_name" class="vl-check-item" :class="check.passed ? 'vl-passed' : 'vl-failed'">
              <div class="vl-check-header">
                <span class="vl-check-name">{{ check.check_name.replace(/_/g, ' ').toUpperCase() }}</span>
                <span class="vl-check-badge" :class="check.passed ? 'badge-passed' : check.severity === 'critical' ? 'badge-critical' : check.severity === 'high' ? 'badge-high' : 'badge-medium'">
                  {{ check.passed ? 'PASS' : 'FAIL' }}
                </span>
              </div>
              <div class="vl-check-details">
                <span class="vl-check-severity">Severity: {{ check.severity.toUpperCase() }}</span>
                <span class="vl-check-desc">{{ check.description }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
function formatTimestamp(ts: string | undefined): string {
  if (!ts) return '—'
  return new Date(ts).toLocaleString('es-AR')
}
</script>

<style scoped>
.vl-validation-panel { display: flex; flex-direction: column; gap: 1.5rem; }
.vl-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
.vl-summary-card { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 8px; padding: 1rem; text-align: center; }
.vl-summary-label { display: block; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); margin-bottom: 0.25rem; }
.vl-summary-value { font-size: 1.25rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.vl-summary-value.tl-passed { color: var(--ownex-green); }
.vl-summary-value.tl-failed { color: var(--ownex-red); }
.vl-phase-list { display: flex; flex-direction: column; gap: 0.75rem; }
.vl-phase-item { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 8px; overflow: hidden; }
.vl-phase-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; }
.vl-phase-header.badge-passed { border-left: 4px solid var(--ownex-green); }
.vl-phase-header.badge-failed { border-left: 4px solid var(--ownex-red); }
.vl-phase-header.badge-pending { border-left: 4px solid var(--ownex-yellow); }
.vl-phase-info { display: flex; align-items: center; gap: 0.5rem; }
.vl-phase-label { font-weight: 600; font-size: 0.8rem; }
.vl-phase-phase { font-size: 0.65rem; color: var(--ownex-muted); text-transform: lowercase; }
.vl-phase-status { display: flex; align-items: center; gap: 0.5rem; }
.vl-phase-badge { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; padding: 0.125rem 0.5rem; border-radius: 999px; }
.vl-phase-badge.badge-passed { background: var(--ownex-green); color: var(--ownex-bg); }
.vl-phase-badge.badge-failed { background: var(--ownex-red); color: var(--ownex-bg); }
.vl-phase-badge.badge-pending { background: var(--ownex-yellow); color: var(--ownex-bg); }
.vl-phase-details { padding: 1rem; border-top: 1px solid var(--ownex-stroke); background: var(--ownex-bg); }
.vl-detail-row { display: flex; justify-content: space-between; padding: 0.25rem 0; font-size: 0.8rem; }
.vl-detail-label { color: var(--ownex-muted); }
.vl-detail-value { font-weight: 600; font-family: monospace; }
.vl-overfit { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 8px; padding: 1rem; margin-top: 1rem; }
.vl-overfit-summary { display: flex; gap: 1.5rem; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--ownex-stroke); }
.vl-overfit-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); display: block; margin-bottom: 0.25rem; }
.vl-overfit-value { font-size: 2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.vl-overfit-value.tl-critical { color: var(--ownex-red); }
.vl-overfit-value.tl-high { color: var(--ownex-red); }
.vl-overfit-value.tl-medium { color: var(--ownex-yellow); }
.vl-overfit-value.tl-low { color: var(--ownex-green); }
.vl-overfit-risk { display: flex; justify-content: space-between; align-items: center; }
.vl-overfit-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); }
.vl-overfit-risk span { font-weight: 600; text-transform: uppercase; }
.tl-critical { color: var(--ownex-red); }
.tl-high { color: var(--ownex-red); }
.tl-medium { color: var(--ownex-yellow); }
.tl-low { color: var(--ownex-green); }
.vl-check-list { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.75rem; }
.vl-check-item { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 8px; padding: 1rem; }
.vl-check-item.vl-passed { border-left: 4px solid var(--ownex-green); }
.vl-check-item.vl-failed { border-left: 4px solid var(--ownex-red); }
.vl-check-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.vl-check-name { font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.75rem; }
.vl-check-badge { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; padding: 0.125rem 0.5rem; border-radius: 999px; }
.badge-passed { background: var(--ownex-green); color: var(--ownex-bg); }
.badge-critical { background: var(--ownex-red); color: var(--ownex-bg); }
.badge-high { background: var(--ownex-red); color: var(--ownex-bg); }
.badge-medium { background: var(--ownex-yellow); color: var(--ownex-bg); }
.vl-check-details { font-size: 0.75rem; color: var(--ownex-muted); }
.vl-check-severity { text-transform: uppercase; font-size: 0.65rem; color: var(--ownex-red); margin-right: 1rem; }
.vl-check-desc { font-size: 0.75rem; }
</style>