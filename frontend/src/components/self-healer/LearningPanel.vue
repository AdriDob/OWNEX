<template>
  <div class="learning-panel">
    <!-- Stats Overview -->
    <div class="stats-row">
      <StatCard title="Total Entradas" :value="stats.total_entries" icon="📚" color="info" />
      <StatCard title="Éxitos" :value="stats.successful_deployments" icon="✅" color="success" />
      <StatCard title="Fallos" :value="stats.failed_deployments" icon="❌" color="danger" />
      <StatCard title="Tasa Éxito" :value="Math.round(stats.success_rate * 100) + '%'" icon="📈" color="primary" />
    </div>

    <!-- Tabs -->
    <div class="learning-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="learning-tab"
        :class="{ active: activeTab === tab.id }"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Successful Patterns -->
    <div v-if="activeTab === 'successful'" class="tab-panel">
      <div class="patterns-header">
        <h4>Patrones Exitosos</h4>
        <div class="patterns-actions">
          <button @click="pruneLearning" class="btn-secondary btn-sm">Limpiar Antiguos</button>
        </div>
      </div>

      <div v-if="successfulPatterns.length === 0" class="empty-state">
        <p>No hay patrones exitosos aún</p>
        <span class="empty-hint">Los patrones se registran tras despliegues exitosos</span>
      </div>

      <div class="patterns-list">
        <div v-for="pattern in successfulPatterns" :key="pattern.learning_id || pattern.patch_id" class="pattern-card success">
          <div class="pattern-header">
            <span class="pattern-type">✅ Éxito</span>
            <span class="pattern-id">{{ pattern.learning_id || pattern.patch_id }}</span>
          </div>
          <div class="pattern-details">
            <div class="detail-row">
              <label>Despliegue</label>
              <span>{{ pattern.deployment_id }}</span>
            </div>
            <div class="detail-row">
              <label>Parche</label>
              <span>{{ pattern.patch_id }}</span>
            </div>
            <div class="detail-row">
              <label>Métricas</label>
              <pre>{{ JSON.stringify(pattern.metrics || {}, null, 2) }}</pre>
            </div>
            <div class="detail-row">
              <label>Health Checks</label>
              <pre>{{ JSON.stringify(pattern.health_checks || {}, null, 2) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Failed Patterns -->
    <div v-if="activeTab === 'failed'" class="tab-panel">
      <div class="patterns-header">
        <h4>Patrones Fallidos (evitar)</h4>
      </div>

      <div v-if="failedPatterns.length === 0" class="empty-state">
        <p>No hay patrones fallidos</p>
        <span class="empty-hint">¡Buena señal!</span>
      </div>

      <div class="patterns-list">
        <div v-for="pattern in failedPatterns" :key="pattern.learning_id || pattern.patch_id" class="pattern-card failure">
          <div class="pattern-header">
            <span class="pattern-type">❌ Fallo</span>
            <span class="pattern-id">{{ pattern.learning_id || pattern.patch_id }}</span>
          </div>
          <div class="pattern-details">
            <div class="detail-row">
              <label>Error</label>
              <span class="error-text">{{ pattern.error || 'Desconocido' }}</span>
            </div>
            <div class="detail-row">
              <label>Despliegue</label>
              <span>{{ pattern.deployment_id }}</span>
            </div>
            <div class="detail-row">
              <label>Parche</label>
              <span>{{ pattern.patch_id }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import StatCard from '@/components/ui/StatCard.vue'

const props = defineProps<{
  stats: any
  successfulPatterns: any[]
  failedPatterns: any[]
}>()

const activeTab = ref('successful')

const tabs = [
  { id: 'successful', label: '✅ Éxitos' },
  { id: 'failed', label: '❌ Fallos' },
]
</script>

<style scoped>
.learning-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.learning-tabs {
  display: flex;
  gap: 8px;
  background: #0a0c11;
  padding: 4px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.learning-tab {
  flex: 1;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #8b8d98;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.learning-tab:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #d9dbdf;
}

.learning-tab.active {
  background: #0e1015;
  color: #f5f5f4;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.tab-panel {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.patterns-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.patterns-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #f5f5f4;
}

.patterns-actions {
  display: flex;
  gap: 8px;
}

.patterns-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pattern-card {
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 16px;
  transition: border-color 0.15s;
}

.pattern-card.success:hover {
  border-color: rgba(52, 211, 153, 0.3);
}

.pattern-card.failure:hover {
  border-color: rgba(248, 113, 113, 0.3);
}

.pattern-card.failure {
  border-left: 3px solid rgba(248, 113, 113, 0.3);
}

.pattern-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.pattern-type {
  font-size: 14px;
}

.pattern-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #5e6272;
}

.pattern-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-row label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #5e6272;
}

.detail-row span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #d9dbdf;
}

.detail-row pre {
  margin: 0;
  padding: 8px;
  background: #05060a;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #8b8d98;
  overflow: auto;
  max-height: 150px;
}

.error-text {
  color: #f87171;
  font-weight: 500;
}
</style>