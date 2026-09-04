<script setup lang="ts">
interface Props {
  engines: Array<any>
  detailed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  engines: () => [],
  detailed: false,
})

function getHealthColor(health: string): string {
  switch (health) {
    case 'online': return 'var(--ownex-green)'
    case 'degraded': return 'var(--ownex-yellow)'
    case 'error': return 'var(--ownex-red)'
    default: return 'var(--ownex-muted)'
  }
}

function getStatusBadge(health: string) {
  const badges: Record<string, { label: string, class: string }> = {
    online: { label: 'ONLINE', class: 'badge-online' },
    degraded: { label: 'DEGRADED', class: 'badge-degraded' },
    error: { label: 'ERROR', class: 'badge-error' },
    not_installed: { label: 'NOT INSTALLED', class: 'badge-not-installed' },
    updating: { label: 'UPDATING', class: 'badge-updating' },
    unsupported: { label: 'UNSUPPORTED', class: 'badge-unsupported' },
  }
  return badges[health] || { label: health.toUpperCase(), class: '' }
}

function formatCapabilities(capabilities: string[]): string {
  return capabilities.slice(0, 3).join(', ') + (capabilities.length > 3 ? ` +${capabilities.length - 3}` : '')
}
</script>

<template>
  <div class="tl-engines-dashboard">
    <div v-if="engines.length === 0" class="tl-empty">
      No engines registered
    </div>

    <div v-else class="tl-engines-grid">
      <div v-for="engine in engines" :key="engine.id" class="tl-engine-card">
        <div class="tl-engine-header">
          <div class="tl-engine-info">
            <h4 class="tl-engine-name">{{ engine.name || engine.id }}</h4>
            <span class="tl-engine-id">{{ engine.id }} v{{ engine.version || '?' }}</span>
          </div>
          <div class="tl-engine-status">
            <span class="tl-status-badge" :class="getStatusBadge(engine.health).class">
              {{ getStatusBadge(engine.health).label }}
            </span>
            <div class="tl-health-indicator" :style="{ backgroundColor: getHealthColor(engine.health) }"></div>
          </div>
        </div>

        <div class="tl-engine-meta" v-if="detailed">
          <div class="tl-meta-row">
            <span class="tl-meta-label">CLASSIFICATION</span>
            <span class="tl-meta-value">{{ engine.classification?.join(', ') || '—' }}</span>
          </div>
          <div class="tl-meta-row">
            <span class="tl-meta-label">CAPABILITIES</span>
            <span class="tl-meta-value">{{ formatCapabilities(engine.capabilities) }}</span>
          </div>
          <div class="tl-meta-row">
            <span class="tl-meta-label">EXCHANGES</span>
            <span class="tl-meta-value">{{ engine.exchanges?.join(', ') || '—' }}</span>
          </div>
          <div class="tl-meta-row">
            <span class="tl-meta-label">MARKETS</span>
            <span class="tl-meta-value">{{ engine.markets?.join(', ') || '—' }}</span>
          </div>
        </div>

        <div class="tl-engine-actions">
          <button class="tl-engine-btn" :disabled="engine.health !== 'online'">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            Start
          </button>
          <button class="tl-engine-btn tl-engine-btn-secondary" :disabled="engine.health !== 'online'">
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Health Check
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
function getHealthColor(health: string): string {
  switch (health) {
    case 'online': return 'var(--ownex-green)'
    case 'degraded': return 'var(--ownex-yellow)'
    case 'error': return 'var(--ownex-red)'
    default: return 'var(--ownex-muted)'
  }
}

function formatCapabilities(caps: string[]): string {
  return caps.slice(0, 3).join(', ') + (caps.length > 3 ? ` +${caps.length - 3}` : '')
}
</script>

<style scoped>
.tl-engines-dashboard { display: flex; flex-direction: column; gap: 1rem; }
.tl-empty { text-align: center; padding: 3rem; color: var(--ownex-muted); }
.tl-engines-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1rem; }
.tl-engine-card {
  background: var(--ownex-surface);
  border: 1px solid var(--ownex-stroke);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.tl-engine-header { display: flex; justify-content: space-between; align-items: flex-start; }
.tl-engine-info { flex: 1; }
.tl-engine-name { margin: 0 0 0.25rem; font-size: 1rem; font-weight: 600; }
.tl-engine-id { font-size: 0.7rem; color: var(--ownex-muted); font-family: monospace; }
.tl-engine-status { display: flex; align-items: center; gap: 0.5rem; }
.tl-engine-meta { border-top: 1px solid var(--ownex-stroke); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.tl-meta-row { display: flex; justify-content: space-between; font-size: 0.8rem; }
.tl-meta-label { color: var(--ownex-muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
.tl-meta-value { font-weight: 600; font-family: monospace; font-size: 0.8rem; }
.tl-engine-actions { display: flex; gap: 0.5rem; padding-top: 0.5rem; border-top: 1px solid var(--ownex-stroke); }
.tl-engine-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--ownex-bg);
  background: var(--ownex-primary);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  flex: 1;
  justify-content: center;
}
.tl-engine-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tl-engine-btn:hover:not(:disabled) { background: var(--ownex-primary-hover); }
.tl-engine-btn-secondary {
  background: transparent;
  color: var(--ownex-fg);
  border: 1px solid var(--ownex-stroke);
}
.tl-engine-btn-secondary:hover:not(:disabled) { background: var(--ownex-accent); }
</style>