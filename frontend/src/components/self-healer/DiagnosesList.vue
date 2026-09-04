<template>
  <div class="diagnoses-list">
    <div class="list-header">
      <h3>Diagnósticos</h3>
    </div>

    <div v-if="diagnoses.length === 0" class="empty-state">
      <div class="empty-icon">🔍</div>
      <p>No hay diagnósticos aún</p>
      <span class="empty-hint">Ejecutar un escaneo para generar diagnósticos</span>
    </div>

    <div class="diagnoses-grid">
      <div v-for="diagnosis in diagnoses" :key="diagnosis.id" class="diagnosis-card">
        <div class="diagnosis-header">
          <div class="diagnosis-meta">
            <span class="confidence-badge" :class="`confidence-${diagnosis.confidence}`">{{ diagnosis.confidence }}</span>
            <span class="risk-badge" :class="`risk-${diagnosis.risk_level}`">{{ diagnosis.risk_level }}</span>
          </div>
          <span class="strategy-badge">{{ diagnosis.suggested_strategy }}</span>
        </div>

        <div class="diagnosis-body">
          <div class="diagnosis-field">
            <label>Causa Raíz</label>
            <p>{{ diagnosis.root_cause }}</p>
          </div>

          <div class="diagnosis-field">
            <label>Factores Contribuyentes</label>
            <ul>
              <li v-for="factor in diagnosis.contributing_factors" :key="factor">{{ factor }}</li>
            </ul>
          </div>

          <div class="diagnosis-field">
            <label>Evidencia</label>
            <ul>
              <li v-for="ev in diagnosis.evidence" :key="ev">{{ ev }}</li>
            </ul>
          </div>

          <div class="diagnosis-field">
            <label>Razonamiento</label>
            <p>{{ diagnosis.reasoning }}</p>
          </div>

          <div class="diagnosis-footer">
            <span class="effort">⏱️ ~{{ diagnosis.estimated_effort_hours }}h</span>
            <span class="diagnosis-id">{{ diagnosis.id }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  diagnoses: any[]
}>()

const searchQuery = ref('')

const filteredDiagnoses = computed(() => {
  if (!searchQuery.value) return props.diagnoses
  const q = searchQuery.value.toLowerCase()
  return props.diagnoses.filter(d =>
    d.root_cause.toLowerCase().includes(q) ||
    d.reasoning.toLowerCase().includes(q)
  )
})
</script>

<style scoped>
.diagnoses-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f5f5f4;
}

.search-box {
  padding: 8px 12px;
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #f5f5f4;
  font-size: 13px;
  width: 300px;
}

.diagnoses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 16px;
}

.diagnosis-card {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.15s;
}

.diagnosis-card:hover {
  border-color: rgba(0, 213, 255, 0.3);
}

.diagnosis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.diagnosis-meta {
  display: flex;
  gap: 8px;
}

.confidence-badge,
.risk-badge,
.strategy-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.confidence-high { background: rgba(52, 211, 153, 0.2); color: #34d399; }
.confidence-very_high { background: rgba(52, 211, 153, 0.3); color: #34d399; }
.confidence-medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
.confidence-low { background: rgba(248, 113, 113, 0.2); color: #f87171; }

.risk-low { background: rgba(52, 211, 153, 0.2); color: #34d399; }
.risk-medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
.risk-high { background: rgba(248, 113, 113, 0.2); color: #f87171; }
.risk-critical { background: rgba(248, 113, 113, 0.3); color: #f87171; }

.strategy-badge {
  background: rgba(0, 213, 255, 0.15);
  color: #00d5ff;
}

.diagnosis-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diagnosis-field label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #5e6272;
  margin-bottom: 6px;
}

.diagnosis-field p {
  margin: 0;
  color: #d9dbdf;
  line-height: 1.6;
  font-size: 13px;
}

.diagnosis-field ul {
  margin: 0;
  padding-left: 18px;
  color: #d9dbdf;
  font-size: 13px;
}

.diagnosis-field li {
  margin: 4px 0;
}

.diagnosis-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.effort {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #8b8d98;
}

.diagnosis-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #5e6272;
}
</style>