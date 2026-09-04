<script setup lang="ts">
interface Props {
  summary: any
}

const props = withDefaults(defineProps<Props>(), {
  summary: () => ({}),
})

function formatCurrency(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'USD' }).format(num)
}

function formatPercent(val: number): string {
  return `${(val * 100).toFixed(1)}%`
}
</script>

<template>
  <div class="tl-risk-dashboard">
    <div class="tl-risk-overview">
      <div class="tl-risk-card tl-drawdown">
        <div class="tl-risk-header">
          <span class="tl-risk-label">CURRENT DRAWDOWN</span>
          <span class="tl-risk-value tl-negative">{{ formatPercent(summary?.metrics?.current_drawdown || 0) }}</span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill tl-negative" :style="{ width: Math.min((summary?.metrics?.current_drawdown || 0) * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Max: {{ formatPercent(summary?.metrics?.max_drawdown || 0) }}</div>
      </div>

      <div class="tl-risk-card tl-daily-loss">
        <div class="tl-risk-header">
          <span class="tl-risk-label">DAILY P&L</span>
          <span class="tl-risk-value" :class="summary?.metrics?.daily_pnl >= 0 ? 'tl-positive' : 'tl-negative'">
            {{ formatCurrency(summary?.metrics?.daily_pnl || 0) }}
          </span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill" :class="summary?.metrics?.daily_pnl >= 0 ? 'tl-positive' : 'tl-negative'" :style="{ width: Math.min(Math.abs(summary?.metrics?.daily_pnl || 0) / 5000 * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Limit: {{ formatCurrency(summary?.limits?.max_daily_loss || 2000) }}</div>
      </div>

      <div class="tl-risk-card tl-weekly-loss">
        <div class="tl-risk-header">
          <span class="tl-risk-label">WEEKLY P&L</span>
          <span class="tl-risk-value" :class="summary?.metrics?.weekly_pnl >= 0 ? 'tl-positive' : 'tl-negative'">
            {{ formatCurrency(summary?.metrics?.weekly_pnl || 0) }}
          </span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill" :class="summary?.metrics?.weekly_pnl >= 0 ? 'tl-positive' : 'tl-negative'" :style="{ width: Math.min(Math.abs(summary?.metrics?.weekly_pnl || 0) / 5000 * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Limit: {{ formatCurrency(summary?.limits?.max_weekly_loss || 5000) }}</div>
      </div>

      <div class="tl-risk-card tl-leverage">
        <div class="tl-risk-header">
          <span class="tl-risk-label">LEVERAGE</span>
          <span class="tl-risk-value" :class="summary?.metrics?.leverage > 2 ? 'tl-negative' : summary?.metrics?.leverage > 1.5 ? 'tl-warning' : 'tl-positive'">
            {{ (summary?.metrics?.leverage || 0).toFixed(2) }}x
          </span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill" :class="summary?.metrics?.leverage > 3 ? 'tl-negative' : summary?.metrics?.leverage > 2 ? 'tl-warning' : 'tl-positive'" :style="{ width: Math.min((summary?.metrics?.leverage || 0) / 5 * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Max: {{ (summary?.limits?.max_leverage || 3).toFixed(1) }}x</div>
      </div>

      <div class="tl-risk-card tl-liquidity">
        <div class="tl-risk-header">
          <span class="tl-risk-label">LIQUIDITY</span>
          <span class="tl-risk-value tl-positive">{{ formatCurrency(summary?.metrics?.liquidity || 0) }}</span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill tl-positive" :style="{ width: Math.min((summary?.metrics?.liquidity || 0) / 50000 * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Min: {{ formatCurrency(summary?.limits?.min_liquidity || 10000) }}</div>
      </div>

      <div class="tl-risk-card tl-exposure">
        <div class="tl-risk-header">
          <span class="tl-risk-label">TOTAL EXPOSURE</span>
          <span class="tl-risk-value">{{ formatCurrency(summary?.metrics?.total_exposure || 0) }}</span>
        </div>
        <div class="tl-risk-bar">
          <div class="tl-risk-bar-fill" :style="{ width: Math.min((summary?.metrics?.total_exposure || 0) / 100000 * 100, 100) + '%' }"></div>
        </div>
        <div class="tl-risk-detail">Max: {{ formatCurrency(summary?.limits?.max_total_exposure || 100000) }}</div>
      </div>
    </div>

    <div class="tl-risk-limits">
      <h3 class="tl-section-title">RISK LIMITS</h3>
      <div class="tl-limits-table">
        <table>
          <thead>
            <tr>
              <th>LIMIT</th>
              <th>CURRENT</th>
              <th>LIMIT</th>
              <th>USAGE</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="limit in riskLimits" :key="limit.type">
              <td>{{ limit.label }}</td>
              <td>{{ formatCurrency(limit.current) }}</td>
              <td>{{ formatCurrency(limit.value) }}</td>
              <td>
                <div class="tl-usage-bar">
                  <div class="tl-usage-fill" :class="limit.breached ? 'tl-breached' : limit.usage > 80 ? 'tl-warning' : 'tl-ok'" :style="{ width: Math.min(limit.usage, 100) + '%' }"></div>
                </div>
                <span class="tl-usage-pct">{{ limit.usage.toFixed(1) }}%</span>
              </td>
              <td>
                <span class="tl-status-badge" :class="limit.breached ? 'badge-breached' : limit.usage > 80 ? 'badge-warning' : 'badge-ok'">
                  {{ limit.breached ? 'BREACHED' : limit.usage > 80 ? 'WARNING' : 'OK' }}
                </td>
              </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="tl-kill-switches" v-if="summary?.kill_switches">
      <h3 class="tl-section-title">KILL SWITCHES</h3>
      <div class="tl-ks-grid">
        <div class="tl-ks-card" :class="summary.kill_switches.global ? 'tl-active' : ''">
          <div class="tl-ks-header">
            <span class="tl-ks-label">GLOBAL</span>
            <span class="tl-ks-status" :class="summary.kill_switches.global ? 'tl-on' : 'tl-off'">
              {{ summary.kill_switches.global ? 'ACTIVE' : 'INACTIVE' }}
            </span>
          </div>
          <div class="tl-ks-detail">Stops ALL trading</div>
        </div>

        <div class="tl-ks-card" v-for="(active, strategy) in summary.kill_switches.strategies" :key="strategy" :class="active ? 'tl-active' : ''">
          <div class="tl-ks-header">
            <span class="tl-ks-label">{{ strategy }}</span>
            <span class="tl-ks-status" :class="active ? 'tl-on' : 'tl-off'">{{ active ? 'ACTIVE' : 'INACTIVE' }}</span>
          </div>
        </div>

        <div class="tl-ks-card" v-for="(active, exchange) in summary.kill_switches.exchanges" :key="exchange" :class="active ? 'tl-active' : ''">
          <div class="tl-ks-header">
            <span class="tl-ks-label">{{ exchange }}</span>
            <span class="tl-ks-status" :class="active ? 'tl-on' : 'tl-off'">{{ active ? 'ACTIVE' : 'INACTIVE' }}</span>
          </div>
        </div>

        <div class="tl-ks-card" v-for="(active, asset) in summary.kill_switches.assets" :key="asset" :class="active ? 'tl-active' : ''">
          <div class="tl-ks-header">
            <span class="tl-ks-label">{{ asset }}</span>
            <span class="tl-ks-status" :class="active ? 'tl-on' : 'tl-off'">{{ active ? 'ACTIVE' : 'INACTIVE' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
function formatCurrency(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'USD' }).format(num)
}

function formatPercent(val: number): string {
  return `${(val * 100).toFixed(1)}%`
}

const riskLimits = computed(() => [
  { type: 'max_drawdown', label: 'MAX DRAWDOWN', current: summary?.metrics?.current_drawdown || 0, value: summary?.limits?.max_drawdown || 0.15, breached: (summary?.metrics?.current_drawdown || 0) > (summary?.limits?.max_drawdown || 0.15), usage: ((summary?.metrics?.current_drawdown || 0) / (summary?.limits?.max_drawdown || 0.15)) * 100 },
  { type: 'max_daily_loss', label: 'MAX DAILY LOSS', current: Math.abs(summary?.metrics?.daily_pnl || 0), value: summary?.limits?.max_daily_loss || 2000, breached: Math.abs(summary?.metrics?.daily_pnl || 0) > (summary?.limits?.max_daily_loss || 2000), usage: (Math.abs(summary?.metrics?.daily_pnl || 0) / (summary?.limits?.max_daily_loss || 2000)) * 100 },
  { type: 'max_weekly_loss', label: 'MAX WEEKLY LOSS', current: Math.abs(summary?.metrics?.weekly_pnl || 0), value: summary?.limits?.max_weekly_loss || 5000, breached: Math.abs(summary?.metrics?.weekly_pnl || 0) > (summary?.limits?.max_weekly_loss || 5000), usage: (Math.abs(summary?.metrics?.weekly_pnl || 0) / (summary?.limits?.max_weekly_loss || 5000)) * 100 },
  { type: 'max_leverage', label: 'MAX LEVERAGE', current: summary?.metrics?.leverage || 0, value: summary?.limits?.max_leverage || 3, breached: (summary?.metrics?.leverage || 0) > (summary?.limits?.max_leverage || 3), usage: ((summary?.metrics?.leverage || 0) / (summary?.limits?.max_leverage || 3)) * 100 },
  { type: 'max_total_exposure', label: 'MAX EXPOSURE', current: summary?.metrics?.total_exposure || 0, value: summary?.limits?.max_total_exposure || 100000, breached: (summary?.metrics?.total_exposure || 0) > (summary?.limits?.max_total_exposure || 100000), usage: ((summary?.metrics?.total_exposure || 0) / (summary?.limits?.max_total_exposure || 100000)) * 100 },
  { type: 'min_liquidity', label: 'MIN LIQUIDITY', current: summary?.metrics?.liquidity || 0, value: summary?.limits?.min_liquidity || 10000, breached: (summary?.metrics?.liquidity || 0) < (summary?.limits?.min_liquidity || 10000), usage: ((summary?.metrics?.liquidity || 0) / (summary?.limits?.min_liquidity || 10000)) * 100 },
])
</script>

<style scoped>
.tl-risk-dashboard { display: flex; flex-direction: column; gap: 1.5rem; }
.tl-risk-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; }
.tl-risk-card {
  background: var(--ownex-surface);
  border: 1px solid var(--ownex-stroke);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.tl-risk-header { display: flex; justify-content: space-between; align-items: baseline; }
.tl-risk-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); font-weight: 600; }
.tl-risk-value { font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.tl-risk-value.tl-positive { color: var(--ownex-green); }
.tl-risk-value.tl-negative { color: var(--ownex-red); }
.tl-risk-value.tl-warning { color: var(--ownex-yellow); }
.tl-risk-bar { height: 6px; background: var(--ownex-bg); border-radius: 3px; overflow: hidden; }
.tl-risk-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.tl-risk-bar-fill.tl-positive { background: var(--ownex-green); }
.tl-risk-bar-fill.tl-negative { background: var(--ownex-red); }
.tl-risk-bar-fill.tl-warning { background: var(--ownex-yellow); }
.tl-risk-detail { font-size: 0.7rem; color: var(--ownex-muted); text-align: right; }
.tl-risk-limits { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 10px; padding: 1rem; }
.tl-section-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); margin-bottom: 0.75rem; font-weight: 600; }
.tl-limits-table table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.tl-limits-table th, .tl-limits-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--ownex-stroke); }
.tl-limits-table th { color: var(--ownex-muted); font-weight: 600; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; }
.tl-usage-bar { height: 6px; background: var(--ownex-bg); border-radius: 3px; overflow: hidden; width: 100%; max-width: 150px; }
.tl-usage-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.tl-usage-fill.tl-ok { background: var(--ownex-green); }
.tl-usage-fill.tl-warning { background: var(--ownex-yellow); }
.tl-usage-fill.tl-breached { background: var(--ownex-red); }
.tl-usage-pct { font-size: 0.7rem; color: var(--ownex-muted); margin-left: 0.5rem; font-family: monospace; }
.tl-status-badge { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; padding: 0.125rem 0.5rem; border-radius: 999px; display: inline-block; }
.badge-ok { background: var(--ownex-green); color: var(--ownex-bg); }
.badge-warning { background: var(--ownex-yellow); color: var(--ownex-bg); }
.badge-breached { background: var(--ownex-red); color: var(--ownex-bg); }
.tl-kill-switches { margin-top: 1rem; }
.tl-ks-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.tl-ks-card { background: var(--ownex-surface); border: 1px solid var(--ownex-stroke); border-radius: 10px; padding: 1rem; }
.tl-ks-card.tl-active { border-color: var(--ownex-red); background: rgba(248, 113, 113, 0.05); }
.tl-ks-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }
.tl-ks-label { font-size: 0.75rem; font-weight: 600; color: var(--ownex-fg); }
.tl-ks-status { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
.tl-ks-status.tl-on { color: var(--ownex-red); }
.tl-ks-status.tl-off { color: var(--ownex-green); }
.tl-ks-detail { font-size: 0.7rem; color: var(--ownex-muted); }
</style>