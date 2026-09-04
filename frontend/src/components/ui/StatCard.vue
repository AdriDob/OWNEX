<template>
  <div class="stat-card" :class="color">
    <div class="stat-icon">{{ icon }}</div>
    <div class="stat-content">
      <p class="stat-title">{{ title }}</p>
      <p class="stat-value">{{ value }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  icon: string
  color?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'muted'
}>()
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  transition: border-color 0.15s;
}

.stat-card:hover {
  border-color: rgba(255, 255, 255, 0.12);
}

.stat-icon {
  font-size: 24px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-title {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8b8d98;
}

.stat-value {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #f5f5f4;
  line-height: 1.2;
}

.stat-card.primary {
  border-color: rgba(0, 213, 255, 0.3);
}

.stat-card.primary .stat-icon {
  background: rgba(0, 213, 255, 0.1);
  border-color: rgba(0, 213, 255, 0.2);
  color: #00d5ff;
}

.stat-card.success {
  border-color: rgba(52, 211, 153, 0.3);
}

.stat-card.success .stat-icon {
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.2);
  color: #34d399;
}

.stat-card.warning {
  border-color: rgba(251, 191, 36, 0.3);
}

.stat-card.warning .stat-icon {
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.stat-card.danger {
  border-color: rgba(248, 113, 113, 0.3);
}

.stat-card.danger .stat-icon {
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.stat-card.info {
  border-color: rgba(0, 213, 255, 0.3);
}

.stat-card.info .stat-icon {
  background: rgba(0, 213, 255, 0.1);
  border-color: rgba(0, 213, 255, 0.2);
  color: #00d5ff;
}

.stat-card.muted {
  border-color: rgba(139, 141, 152, 0.3);
}

.stat-card.muted .stat-icon {
  background: rgba(139, 141, 152, 0.1);
  border-color: rgba(139, 141, 152, 0.2);
  color: #8b8d98;
}
</style>