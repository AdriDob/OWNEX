<template>
  <div class="alert-container">
    <TransitionGroup name="alert" tag="div" class="alert-list">
      <div
        v-for="alert in activeAlerts"
        :key="alert.id"
        :class="['alert', `alert-${alert.type}`, `alert-${alert.priority}`, { 'alert-action': alert.requires_action }]"
      >
        <div class="alert-icon">
          <span v-if="alert.type === 'error'">❌</span>
          <span v-else-if="alert.type === 'warning'">⚠️</span>
          <span v-else-if="alert.type === 'success'">✅</span>
          <span v-else-if="alert.type === 'critical'">🚨</span>
          <span v-else>ℹ️</span>
        </div>
        <div class="alert-content">
          <div class="alert-header">
            <span class="alert-title">{{ alert.title }}</span>
            <span class="alert-category">{{ alert.category }}</span>
          </div>
          <div class="alert-message">{{ alert.message }}</div>
          <div v-if="alert.requires_action && alert.action_steps.length > 0" class="alert-steps">
            <div class="steps-title">Steps to resolve:</div>
            <ol class="steps-list">
              <li v-for="(step, i) in alert.action_steps" :key="i">{{ step }}</li>
            </ol>
          </div>
          <div v-if="alert.ui_path" class="alert-actions">
            <a :href="alert.ui_path" class="action-link">Go to resolve →</a>
          </div>
        </div>
        <button @click="dismissAlert(alert.id)" class="alert-dismiss">
          <span>×</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Alert {
  id: string
  type: string
  category: string
  title: string
  message: string
  timestamp: string
  severity: string
  priority: string
  requires_action: boolean
  action_steps: string[]
  ui_path: string
  auto_dismiss_after: number
  escalated: boolean
  resolved: boolean
  metadata: Record<string, any>
}

const activeAlerts = ref<Alert[]>([])
let pollInterval: number | null = null

const fetchAlerts = async () => {
  try {
    const response = await fetch('/api/alerts/active')
    const data = await response.json()
    activeAlerts.value = data.alerts

    // Auto-dismiss alerts with auto_dismiss_after > 0
    data.alerts.forEach((alert: Alert) => {
      if (alert.auto_dismiss_after > 0) {
        setTimeout(() => {
          dismissAlert(alert.id)
        }, alert.auto_dismiss_after * 1000)
      }
    })
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
  }
}

const dismissAlert = async (alertId: string) => {
  try {
    await fetch(`/api/alerts/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alert_id: alertId }),
    })
    activeAlerts.value = activeAlerts.value.filter(a => a.id !== alertId)
  } catch (error) {
    console.error('Failed to dismiss alert:', error)
  }
}

onMounted(() => {
  fetchAlerts()
  pollInterval = window.setInterval(fetchAlerts, 5000) // Poll every 5 seconds
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style scoped>
.alert-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  max-width: 400px;
  width: 100%;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert {
  background: rgba(0, 0, 0, 0.95);
  border: 1px solid #374151;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  gap: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
}

.alert-enter-active,
.alert-leave-active {
  transition: all 0.3s ease;
}

.alert-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.alert-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.alert-error {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.alert-warning {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.alert-success {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.alert-critical {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.15);
  animation: pulse 2s infinite;
}

.alert-high {
  border-width: 2px;
}

.alert-action {
  border-left: 4px solid #fbbf24;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alert-icon {
  font-size: 24px;
  line-height: 1;
}

.alert-content {
  flex: 1;
  min-width: 0;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.alert-title {
  color: #f3f4f6;
  font-weight: 600;
  font-size: 0.9rem;
}

.alert-category {
  color: #9ca3af;
  font-size: 0.7rem;
  text-transform: uppercase;
  padding: 2px 6px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.alert-message {
  color: #d1d5db;
  font-size: 0.85rem;
  line-height: 1.4;
  margin-bottom: 8px;
  white-space: pre-wrap;
}

.alert-steps {
  margin-top: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.steps-title {
  color: #fbbf24;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 4px;
}

.steps-list {
  color: #d1d5db;
  font-size: 0.8rem;
  margin: 0;
  padding-left: 16px;
}

.steps-list li {
  margin-bottom: 2px;
}

.alert-actions {
  margin-top: 8px;
}

.action-link {
  color: #fbbf24;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
}

.action-link:hover {
  text-decoration: underline;
}

.alert-dismiss {
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.alert-dismiss:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #f3f4f6;
}
</style>
