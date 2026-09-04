<script setup lang="ts">
interface Props {
  snapshot: any
}

const props = withDefaults(defineProps<Props>(), {
  snapshot: () => ({}),
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
  <div class="tl-capital-dashboard">
    <div class="tl-capital-summary">
      <div class="tl-capital-card tl-total">
        <div class="tl-capital-header">
          <span class="tl-capital-label">TOTAL PORTFOLIO</span>
          <span class="tl-capital-value">{{ formatCurrency(snapshot?.total_usd || 0) }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-bounty">
        <div class="tl-capital-header">
          <span class="tl-capital-label">BOUNTY PAYOUTS</span>
          <span class="tl-capital-value tl-positive">{{ formatCurrency(snapshot?.bounty?.pagado_usd || 0) }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Pendiente</span>
          <span class="tl-detail-value tl-pending">{{ formatCurrency(snapshot?.bounty?.pendiente_usd || 0) }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-work">
        <div class="tl-capital-header">
          <span class="tl-capital-label">WORK INCOME</span>
          <span class="tl-capital-value tl-positive">{{ formatCurrency(snapshot?.work_income?.total_usd || 0) }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Entregado</span>
          <span class="tl-detail-value tl-positive">{{ formatCurrency(snapshot?.work_income?.entregado_usd || 0) }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Pendiente</span>
          <span class="tl-detail-value tl-pending">{{ formatCurrency(snapshot?.work_income?.pendiente_usd || 0) }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-investment">
        <div class="tl-capital-header">
          <span class="tl-capital-label">INVESTMENTS</span>
          <span class="tl-capital-value">{{ formatCurrency(snapshot?.investment?.total_usd || 0) }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Estrategias</span>
          <span class="tl-detail-value">{{ snapshot?.investment?.estrategias?.length || 0 }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-atlas">
        <div class="tl-capital-header">
          <span class="tl-capital-label">ATLAS PORTFOLIO</span>
          <span class="tl-capital-value">{{ formatCurrency(snapshot?.atlas?.total_usd || 0) }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-crypto">
        <div class="tl-capital-header">
          <span class="tl-capital-label">CRYPTO WALLETS</span>
          <span class="tl-capital-value">{{ formatCurrency(snapshot?.crypto?.total_usd || 0) }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-expected">
        <div class="tl-capital-header">
          <span class="tl-capital-label">EXPECTED CASH</span>
          <span class="tl-capital-value tl-pending">{{ formatCurrency(snapshot?.expected_cash?.total || 0) }}</span>
        </div>
        <div class="tl-capital-detail" v-for="rail in snapshot?.expected_cash?.by_rail || []" :key="rail.rail">
          <span class="tl-detail-label">{{ rail.rail }}</span>
          <span class="tl-detail-value tl-pending">{{ formatCurrency(rail.amount_usd) }} ~ {{ rail.date }}</span>
        </div>
      </div>

      <div class="tl-capital-card tl-compat">
        <div class="tl-capital-header">
          <span class="tl-capital-label">PAYMENT COMPAT</span>
          <span class="tl-capital-value">{{ snapshot?.payment_compat?.compatible || 0 }}/{{ snapshot?.payment_compat?.total || 0 }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Compatible</span>
          <span class="tl-detail-value tl-positive">{{ snapshot?.payment_compat?.compatible || 0 }}</span>
        </div>
        <div class="tl-capital-detail">
          <span class="tl-detail-label">Total</span>
          <span class="tl-detail-value">{{ snapshot?.payment_compat?.total || 0 }}</span>
        </div>
      </div>
    </div>

    <div class="tl-capital-breakdown" v-if="snapshot">
      <h3 class="tl-section-title">BREAKDOWN BY STRATEGY</h3>
      <div class="tl-breakdown-table">
        <table>
          <thead>
            <tr>
              <th>STRATEGY</th>
              <th>ALLOCATED</th>
              <th>USED</th>
              <th>P&L</th>
              <th>EXPOSURE</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in snapshot.work_income?.by_strategy || []" :key="item.strategy">
              <td>{{ item.strategy }}</td>
              <td>{{ formatCurrency(item.allocated) }}</td>
              <td>{{ formatCurrency(item.used) }}</td>
              <td :class="item.pnl >= 0 ? 'tl-positive' : 'tl-negative'">{{ item.pnl >= 0 ? '+' : '' }}{{ formatCurrency(item.pnl) }}</td>
              <td>{{ formatCurrency(item.exposure) }}</td>
              <td><span class="tl-badge" :class="item.status === 'active' ? 'badge-live' : 'badge-paper'">{{ item.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
function formatCurrency(val: number | string | null | undefined): string {
  const num = typeof val === 'string' ? parseFloat(val) : (val || 0)
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'USD' }).format(num)
}
</script>

<style scoped>
.tl-capital-dashboard { display: flex; flex-direction: column; gap: 1rem; }
.tl-capital-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
.tl-capital-card {
  background: var(--ownex-surface);
  border: 1px solid var(--ownex-stroke);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.tl-capital-header { display: flex; justify-content: space-between; align-items: baseline; }
.tl-capital-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); font-weight: 600; }
.tl-capital-value { font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.tl-capital-value.tl-positive { color: var(--ownex-green); }
.tl-capital-value.tl-pending { color: var(--ownex-yellow); }
.tl-capital-detail { display: flex; justify-content: space-between; font-size: 0.8rem; padding-top: 0.25rem; border-top: 1px solid var(--ownex-stroke); padding-top: 0.5rem; margin-top: 0.25rem; }
.tl-capital-detail:last-child { border-top: none; padding-top: 0; margin-top: 0; }
.tl-detail-label { color: var(--ownex-muted); font-size: 0.75rem; }
.tl-detail-value { font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.tl-detail-value.tl-positive { color: var(--ownex-green); }
.tl-detail-value.tl-pending { color: var(--ownex-yellow); }
.tl-section-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ownex-muted); margin-bottom: 0.75rem; font-weight: 600; }
.tl-breakdown-table { overflow-x: auto; }
.tl-breakdown-table table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.tl-breakdown-table th, .tl-breakdown-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--ownex-stroke); }
.tl-breakdown-table th { color: var(--ownex-muted); font-weight: 600; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; }
.tl-badge { font-size: 0.6rem; font-weight: 600; text-transform: uppercase; padding: 0.125rem 0.5rem; border-radius: 999px; display: inline-block; }
.badge-live { background: var(--ownex-green); color: var(--ownex-bg); }
.badge-paper { background: var(--ownex-blue); color: var(--ownex-bg); }
</style>