<template>
  <div class="notification-center">
    <div class="header">
      <h3 class="title">Acciones Requeridas</h3>
      <span v-if="actions.length" class="badge">{{ actions.length }}</span>
    </div>

    <div v-if="loading" class="loading">Cargando...</div>

    <div v-else-if="actions.length" class="actions">
      <div
        v-for="action in actions"
        :key="action.action_id"
        class="action-item"
        :class="action.priority"
      >
        <div class="action-header">
          <span class="action-title">{{ action.title }}</span>
          <span class="action-priority">{{ action.priority }}</span>
        </div>
        <p class="action-reason">{{ action.reason }}</p>
        <p class="action-impact">{{ action.impact }}</p>
        <ol v-if="action.steps.length" class="action-steps">
          <li v-for="(step, i) in action.steps" :key="i">{{ step }}</li>
        </ol>
        <div class="action-footer">
          <span class="action-category">{{ action.category }}</span>
          <button class="btn-resolve" @click="resolve(action.action_id)">Resuelto</button>
        </div>
      </div>
    </div>

    <div v-else class="empty">Sin acciones pendientes</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchPendingActions, resolveAction, type PendingAction } from '@/services/ownexData'

const actions = ref<PendingAction[]>([])
const loading = ref(false)

async function loadActions() {
  loading.value = true
  try {
    const res = await fetchPendingActions()
    actions.value = res.actions || []
  } catch {
    actions.value = []
  } finally {
    loading.value = false
  }
}

async function resolve(actionId: string) {
  try {
    await resolveAction(actionId)
    actions.value = actions.value.filter(a => a.action_id !== actionId)
  } catch {
    // ignore
  }
}

onMounted(loadActions)
</script>

<style scoped>
.notification-center {
  background: #0a0b0f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 16px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0;
}

.badge {
  background: #00d5ff;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-item {
  padding: 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.action-item.high { border-left: 3px solid #00d5ff; }
.action-item.medium { border-left: 3px solid #ff7a1a; }
.action-item.low { border-left: 3px solid #00e39a; }

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.action-priority {
  font-size: 10px;
  text-transform: uppercase;
  color: #888;
}

.action-reason, .action-impact {
  font-size: 11px;
  color: #aaa;
  margin: 4px 0;
}

.action-steps {
  margin: 8px 0;
  padding-left: 16px;
  font-size: 11px;
  color: #888;
}

.action-steps li {
  margin: 2px 0;
}

.action-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.action-category {
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
}

.btn-resolve {
  background: rgba(0, 200, 83, 0.1);
  border: 1px solid rgba(0, 200, 83, 0.3);
  color: #00e39a;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 11px;
}

.btn-resolve:hover {
  background: rgba(0, 200, 83, 0.2);
}

.loading, .empty {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 20px 0;
}
</style>
