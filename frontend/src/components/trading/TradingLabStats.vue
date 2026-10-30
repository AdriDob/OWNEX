<script setup lang="ts">
interface Props {
  totalCapital: number
  todayPnl: number
  drawdown: number
  activeStrategies: number
  systemHealth: number
  systemStatus: string
}

const props = withDefaults(defineProps<Props>(), {
  totalCapital: 0,
  todayPnl: 0,
  drawdown: 0,
  activeStrategies: 0,
  systemHealth: 0,
  systemStatus: 'unknown',
})

function formatCurrency(val: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'USD' }).format(val)
}

function formatPercent(val: number): string {
  return `${val.toFixed(1)}%`
}

function getHealthColor(health: number): string {
  if (health >= 80) return 'var(--ownex-green)'
  if (health >= 50) return 'var(--ownex-yellow)'
  return 'var(--ownex-red)'
}
</script>

<template>
  <div class="tl-stats-grid">
    <div class="tl-stat-card">
      <div class="tl-stat-header">
        <span class="tl-stat-label">TOTAL CAPITAL</span>
        <span class="tl-stat-value">{{ formatCurrency(totalCapital) }}</span>
      </div>
      <div class="tl-stat-bar">
        <div class="tl-stat-bar-fill" :style="{ width: '100%', background: 'var(--ownex-primary)' }"></div>
      </div>
    </div>

    <div class="tl-stat-card">
      <div class="tl-stat-header">
        <span class="tl-stat-label">TODAY P&L</span>
        <span class="tl-stat-value" :class="todayPnl >= 0 ? 'tl-positive' : 'tl-negative'">
          {{ todayPnl >= 0 ? '+' : '' }}{{ todayPnl.toLocaleString('es-AR') }}
        </span>
      </div>
      <div class="tl-stat-bar">
        <div class="tl-stat-bar-fill" :style="{ width: '100%', background: todayPnl >= 0 ? 'var(--ownex-green)' : 'var(--ownex-red)' }"></div>
      </div>
    </div>

    <div class="tl-stat-card">
      <div class="tl-stat-header">
        <span class="tl-stat-label">DRAWDOWN</span>
        <span class="tl-stat-value tl-negative">{{ formatPercent(drawdown) }}</span>
      </div>
      <div class="tl-stat-bar">
        <div class="tl-stat-bar-fill" :style="{ width: Math.min(drawdown * 100, 100) + '%', background: 'var(--ownex-red)' }"></div>
      </div>
    </div>

    <div class="tl-stat-card">
      <div class="tl-stat-header">
        <span class="tl-stat-label">ACTIVE STRATEGIES</span>
        <span class="tl-stat-value">{{ activeStrategies }}</span>
      </div>
      <div class="tl-stat-bar">
        <div class="tl-stat-bar-fill" :style="{ width: '100%', background: 'var(--ownex-green)' }"></div>
      </div>
    </div>

    <div class="tl-stat-card tl-system-health">
      <div class="tl-stat-header">
        <span class="tl-stat-label">SYSTEM HEALTH</span>
        <span class="tl-stat-value" :style="{ color: getHealthColor(systemHealth) }">{{ systemHealth }}%</span>
      </div>
      <div class="tl-stat-bar">
        <div class="tl-stat-bar-fill" :style="{ width: systemHealth + '%', background: getHealthColor(systemHealth) }"></div>
      </div>
      <div class="tl-system-status">{{ systemStatus.toUpperCase() }}</div>
    </div>
  </div>
</template>

<style scoped>
.tl-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
.tl-stat-card {
  background: var(--ownex-surface);
  border: 1px solid var(--ownex-stroke);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 200px;
}
.tl-stat-card.tl-system-health {
  grid-column: 1 / -1;
  max-width: 300px;
}
.tl-stat-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.tl-stat-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ownex-muted);
  font-weight: 600;
}
.tl-stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}
.tl-stat-value.tl-positive { color: var(--ownex-green); }
.tl-stat-value.tl-negative { color: var(--ownex-red); }
.tl-stat-bar {
  height: 6px;
  background: var(--ownex-bg);
  border-radius: 3px;
  overflow: hidden;
}
.tl-stat-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
.tl-system-health .tl-stat-value {
  font-size: 2rem;
}
.tl-system-status {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ownex-muted);
  text-align: center;
  margin-top: 0.25rem;
}
</style>