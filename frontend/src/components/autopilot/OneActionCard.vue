<script setup lang="ts">
/**
 * OneActionCard — tarjeta de una acción automática.
 * Cada acción tiene: id, label, description, enabled, disabled, action, result.
 */
defineProps<{
  autoRefresh: boolean
  refreshInterval: number
  action: string
  description: string
  status: 'pending' | 'running' | 'done' | 'error'
}>()

const statusLabel = ref<string>('pending')
</script>

<template>
  <div class="card">
    <header class="card-header">
      <h3>Acción: {{ action }}</h3>
      <p class="card-description">{{ description }}</p>
    </header>
    <footer class="card-footer">
      <span class="badge" :class="status">{{ statusLabel }}</span>
    </footer>
  </div>
</template>

<style scoped>
.card {
  border: 1px solid var(--ownex-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--ownex-bg-surface);
}
.card-header {
  margin-bottom: 8px;
}
.card-header h3 {
  margin: 0 0 4px;
  color: var(--ownex-text-primary);
}
.card-description {
  margin: 0 0 8px;
  color: var(--ownex-text-secondary);
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  text-transform: uppercase;
}
.badge.pending { background: var(--ownex-bg-glass); color: var(--ownex-text-secondary); }
.badge.running { background: var(--ownex-yellow); color: #fff; }
.badge.done { background: var(--ownex-green); color: #fff; }
.badge.error { background: var(--ownex-danger); color: #fff; }
</style>
