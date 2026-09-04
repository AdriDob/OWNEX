<template>
  <div class="deployments-list">
    <div class="list-header">
      <h3>Despliegues</h3>
      <StatusBadge :status="activeDeployment?.status === 'staging' || activeDeployment?.status === 'canary' ? 'running' : activeDeployment?.status === 'completed' ? 'running' : 'stopped'" :label="activeDeployment ? getStatusLabel(activeDeployment.status) : 'Sin despliegue activo'" />
    </div>

    <div v-if="deployments.length === 0 && !activeDeployment" class="empty-state">
      <div class="empty-icon">🚀</div>
      <p>No hay despliegues</p>
      <span class="empty-hint">Los despliegues ocurren al aprobar un parche</span>
    </div>

    <!-- Active Deployment -->
    <div v-if="activeDeployment" class="active-deployment-card">
      <div class="active-header">
        <h4>🔄 Despliegue Activo</h4>
        <StatusBadge :status="getStatusKey(activeDeployment.status)" :label="getStatusLabel(activeDeployment.status)" />
      </div>

      <div class="deployment-progress">
        <ProgressStep label="Staging" :completed="isCompleted('staging')" :current="isCurrent('staging')" :healthy="activeDeployment.health_checks?.staging" />
        <ProgressStep label="Canary" :completed="isCompleted('canary')" :current="isCurrent('canary')" :healthy="activeDeployment.health_checks?.canary" />
        <ProgressStep label="Producción" :completed="isCompleted('production')" :current="isCurrent('production')" :healthy="activeDeployment.health_checks?.production" />
      </div>

      <div class="deployment-meta">
        <span>{{ activeDeployment.id }}</span>
        <span>{{ activeDeployment.patch_id }}</span>
        <span>Iniciado: {{ formatTime(activeDeployment.started_at) }}</span>
      </div>

      <div class="active-actions" v-if="activeDeployment.status !== 'completed' && activeDeployment.status !== 'rolled_back'">
        <button @click="confirmRollback(activeDeployment.id)" class="btn-danger">
          🔄 Rollback Manual
        </button>
      </div>
    </div>

    <!-- History -->
    <div v-if="deployments.length > 0" class="history-section">
      <h4>Historial</h4>
      <div class="deployments-table">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Parche</th>
              <th>Estado</th>
              <th>Entorno</th>
              <th>Iniciado</th>
              <th>Completado</th>
              <th>Rollback</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="deploy in deployments" :key="deploy.id">
              <td><span class="deploy-id">{{ deploy.id }}</span></td>
              <td><span class="patch-ref">{{ deploy.patch_id }}</span></td>
              <td><StatusBadge :status="getStatusKey(deploy.status)" :label="getStatusLabel(deploy.status)" /></td>
              <td>{{ deploy.environment }}</td>
              <td class="time-cell">{{ formatTime(deploy.started_at) }}</td>
              <td class="time-cell">{{ deploy.completed_at ? formatTime(deploy.completed_at) : '—' }}</td>
              <td>
                <span v-if="deploy.rollback_triggered" class="rollback-badge">↩️ Rollback</span>
                <span v-else>—</span>
              </td>
              <td class="actions-cell">
                <button v-if="deploy.status !== 'completed' && deploy.status !== 'rolled_back'" @click="confirmRollback(deploy.id)" class="action-btn rollback-btn" title="Rollback">🔄</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ProgressStep from '@/components/self-healer/ProgressStep.vue'

const props = defineProps<{
  deployments: any[]
}>()

const emit = defineEmits(['rollback'])

const activeDeployment = ref<any>(null)

const activeDeploy = computed(() => {
  return props.deployments.find(d =>
    d.status === 'staging' || d.status === 'canary' || d.status === 'production'
  )
})

function getStatusKey(status: string) {
  const map: Record<string, string> = {
    pending: 'pending',
    staging: 'running',
    canary: 'running',
    production: 'running',
    completed: 'running',
    rolled_back: 'stopped',
    failed: 'stopped',
  }
  return map[status] || 'pending'
}

function getStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: 'Pendiente',
    staging: 'Staging',
    canary: 'Canary',
    production: 'Producción',
    completed: 'Completado',
    rolled_back: 'Rollback',
    failed: 'Fallido',
  }
  return labels[status] || status
}

function isCompleted(stage: string) {
  if (!activeDeployment.value) return false
  const stages = ['staging', 'canary', 'production']
  const currentIndex = stages.indexOf(activeDeployment.value.status)
  const stageIndex = stages.indexOf(stage)
  return stageIndex < currentIndex || activeDeployment.value.status === 'completed'
}

function isCurrent(stage: string) {
  if (!activeDeployment.value) return false
  return activeDeployment.value.status === stage
}


function formatTime(isoString: string) {
  const date = new Date(isoString)
  return date.toLocaleString('es-ES', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function confirmRollback(deploymentId: string) {
  if (!confirm('¿Confirmar rollback de este despliegue?')) return
  emit('rollback', deploymentId)
}
</script>

<style scoped>
.deployments-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f5f5f4;
}

.active-deployment-card {
  background: #0e1015;
  border: 1px solid rgba(0, 213, 255, 0.2);
  border-radius: 12px;
  padding: 20px;
}

.active-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.active-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #f5f5f4;
}

.deployment-progress {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #0a0c11;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}

.progress-step.current {
  border-left-color: #00d5ff;
  background: rgba(0, 213, 255, 0.05);
}

.progress-step.completed {
  border-left-color: #34d399;
}

.progress-step.failed {
  border-left-color: #f87171;
}

.step-icon {
  font-size: 16px;
}

.step-label {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #d9dbdf;
}

.step-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.step-healthy {
  color: #34d399;
}

.step-unhealthy {
  color: #f87171;
}

.step-pending {
  color: #fbbf24;
}

.deployment-meta {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: #5e6272;
  font-family: 'JetBrains Mono', monospace;
  padding: 12px;
  background: #0a0c11;
  border-radius: 8px;
}

.active-actions {
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.history-section h4 {
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  color: #8b8d98;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.deployments-table {
  overflow-x: auto;
}

.deployments-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.deployments-table th,
.deployments-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.deployments-table th {
  background: #0a0c11;
  color: #8b8d98;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.deployments-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.deploy-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #8b8d98;
}

.patch-ref {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #00d5ff;
}

.time-cell {
  color: #8b8d98;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  white-space: nowrap;
}

.rollback-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: 999px;
  font-size: 11px;
  color: #f87171;
}

.actions-cell {
  white-space: nowrap;
}

.rollback-btn {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.12s;
}

.rollback-btn:hover {
  background: rgba(248, 113, 113, 0.1);
  border-color: #f87171;
}
</style>