<script setup lang="ts">
interface Props {
  strategies: Array<any>
}

const props = withDefaults(defineProps<Props>(), {
  strategies: () => [],
})

const emit = defineEmits<{ (e: 'open-detail', strategy: any): void }>()

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

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}

function getStatusBadge(status: string): { label: string, class: string } {
  const badges: Record<string, { label: string, class: string }> = {
    live: { label: 'LIVE', class: 'badge-live' },
    paper: { label: 'PAPER', class: 'badge-paper' },
    canary: { label: 'CANARY', class: 'badge-canary' },
    validated: { label: 'VALIDATED', class: 'badge-validated' },
    paper: { label: 'PAPER', class: 'badge-paper' },
    backtesting: { label: 'BACKTEST', class: 'badge-backtest' },
    discovered: { label: 'DISCOVERED', class: 'badge-discovered' },
  }
  return badges[status] || { label: status.toUpperCase(), class: '' }
}
</script>

<template>
  <div class="tl-strategy-table">
    <div class="tl-table-wrapper">
      <table class="tl-strategy-table-inner">
        <thead>
          <tr>
            <th>#</th>
            <th>STRATEGY</th>
            <th>ENGINE</th>
            <th>STATUS</th>
            <th>COMPOSITE</th>
            <th>RETURN</th>
            <th>SHARPE</th>
            <th>DRAWDOWN</th>
            <th>WIN%</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(strategy, index) in strategies" :key="strategy.strategy_id" class="tl-strategy-row" @click="openDetail(strategy)">
            <td class="tl-rank">{{ strategy.rank || index + 1 }}</td>
            <td>
              <div class="tl-strategy-name">
                <span class="tl-name">{{ strategy.name || strategy.strategy_id }}</span>
                <span class="tl-id">{{ strategy.strategy_id }}</span>
              </div>
            </td>
            <td>
              <span class="tl-engine">{{ strategy.engine_id || strategy.engine }}</span>
            </td>
            <td>
              <span class="tl-badge" :class="getStatusBadge(strategy.status).class">
                {{ getStatusBadge(strategy.status).label }}
              </span>
            </td>
            <td>
              <div class="tl-score-cell">
                <span :style="{ color: getScoreColor(strategy.composite_score || 0) }">{{ Math.round(strategy.composite_score || 0) }}</span>
                <div class="tl-mini-bar">
                  <div class="tl-mini-bar-fill" :style="{ width: (strategy.composite_score || 0) + '%', background: getScoreColor(strategy.composite_score || 0) }"></div>
                </div>
              </div>
            </td>
            <td class="tl-positive" v-if="(strategy.expected_value || strategy.expected_value_usd || 0) >= 0" :class="{ 'tl-negative': (strategy.expected_value || strategy.expected_value_usd || 0) < 0 }">
              {{ formatCurrency(strategy.expected_value || strategy.expected_value_usd || 0) }}
            </td>
            <td>{{ (strategy.sharpe || 0).toFixed(2) }}</td>
            <td class="tl-negative">{{ formatPercent(strategy.max_drawdown || strategy.max_drawdown || 0) }}</td>
            <td>{{ formatPercent(strategy.win_rate || strategy.win_rate || 0) }}</td>
            <td>
              <button class="tl-action-btn" @click.stop="openDetail($event, strategy)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="strategies.length === 0" class="tl-empty">No strategies found</p>
  </div>
</template>

<script>
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

function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--ownex-green)'
  if (score >= 60) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}
</script>

<style scoped>
.tl-strategy-table { overflow: hidden; }
.tl-table-wrapper { overflow-x: auto; }
.tl-strategy-table-inner { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.tl-strategy-table-inner th,
.tl-strategy-table-inner td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--ownex-stroke); }
.tl-strategy-table-inner th { color: var(--ownex-muted); font-weight: 600; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap; }
.tl-strategy-table-inner td { white-space: nowrap; font-size: 0.8rem; }
.tl-strategy-row { cursor: pointer; transition: background 0.15s; }
.tl-strategy-row:hover { background: var(--ownex-bg); }
.tl-rank { font-weight: 700; color: var(--ownex-primary); width: 40px; }
.tl-strategy-name { display: flex; flex-direction: column; gap: 0.125rem; }
.tl-name { font-weight: 600; font-size: 0.85rem; }
.tl-id { font-size: 0.65rem; color: var(--ownex-muted); font-family: monospace; }
.tl-engine { font-size: 0.7rem; color: var(--ownex-muted); font-family: monospace; text-transform: uppercase; }
.tl-badge { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; padding: 0.125rem 0.5rem; border-radius: 999px; display: inline-block; }
.badge-live { background: var(--ownex-green); color: var(--ownex-bg); }
.badge-paper { background: var(--ownex-blue); color: var(--ownex-bg); }
.badge-canary { background: var(--ownex-yellow); color: var(--ownex-bg); }
.badge-validated { background: var(--ownex-primary); color: var(--ownex-bg); }
.badge-backtest { background: var(--ownex-muted); color: var(--ownex-bg); }
.badge-discovered { background: transparent; color: var(--ownex-muted); border: 1px solid var(--ownex-stroke); }
.tl-score-cell { display: flex; flex-direction: column; gap: 0.25rem; }
.tl-mini-bar { height: 4px; background: var(--ownex-bg); border-radius: 2px; overflow: hidden; }
.tl-mini-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
.tl-positive { color: var(--ownex-green); }
.tl-negative { color: var(--ownex-red); }
.tl-action-btn { background: none; border: none; color: var(--ownex-muted); cursor: pointer; padding: 0.25rem; border-radius: 4px; opacity: 0.5; transition: all 0.2s; }
.tl-action-btn:hover { color: var(--ownex-primary); opacity: 1; }
.tl-empty { text-align: center; padding: 3rem; color: var(--ownex-muted); }
</style>