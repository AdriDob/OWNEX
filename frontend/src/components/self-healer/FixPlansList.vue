<template>
  <div class="fix-plans-list">
    <div class="list-header">
      <h3>Planes de Fix</h3>
      <div class="header-actions">
        <span class="pending-badge" v-if="pendingCount > 0">{{ pendingCount }} pendientes de aprobación</span>
      </div>
    </div>

    <div v-if="plans.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>No hay planes de fix</p>
      <span class="empty-hint">Los planes se generan tras diagnosticar problemas</span>
    </div>

    <div class="plans-list">
      <div v-for="plan in plans" :key="plan.id" class="plan-card" :class="{ pending: plan.awaiting_approval }">
        <div class="plan-header">
          <div class="plan-title-row">
            <h4 class="plan-title">{{ plan.description }}</h4>
            <div class="plan-badges">
              <span class="strategy-badge">{{ plan.strategy }}</span>
              <ApprovalBadge :approval="plan.approval_required" v-if="plan.awaiting_approval" />
              <span class="status-badge completed" v-else-if="!plan.awaiting_approval">Completado</span>
            </div>
          </div>
          <div class="plan-meta">
            <span class="plan-id">{{ plan.id }}</span>
            <span class="effort">⏱️ ~{{ plan.estimated_duration_minutes }}min</span>
          </div>
        </div>

        <div class="plan-body">
          <div class="plan-section">
            <label>Estrategia</label>
            <span class="strategy-badge-large">{{ plan.strategy }}</span>
          </div>

          <div class="plan-section">
            <label>Pasos</label>
            <ol class="steps-list">
              <li v-for="(step, i) in plan.steps" :key="i">{{ step }}</li>
            </ol>
          </div>

          <div class="plan-section">
            <label>Archivos a modificar</label>
            <div class="files-list">
              <span v-for="file in plan.files_to_modify" :key="file" class="file-tag">{{ file }}</span>
              <span v-if="plan.files_to_modify.length === 0" class="no-files">Ninguno especificado</span>
            </div>
          </div>

          <div class="plan-section">
            <label>Cambios de configuración</label>
            <pre v-if="Object.keys(plan.config_changes).length" class="config-changes">{{ JSON.stringify(plan.config_changes, null, 2) }}</pre>
            <span v-else class="no-changes">Sin cambios de configuración</span>
          </div>

          <div class="plan-section">
            <label>Tests a agregar</label>
            <ul v-if="plan.tests_to_add.length" class="tests-list">
              <li v-for="test in plan.tests_to_add" :key="test">{{ test }}</li>
            </ul>
            <span v-else class="no-tests">Sin tests especificados</span>
          </div>

          <div class="plan-section">
            <label>Plan de rollback</label>
            <p class="rollback-plan">{{ plan.rollback_plan }}</p>
          </div>
        </div>

        <div class="plan-actions" v-if="plan.awaiting_approval">
          <button @click="$emit('approve', plan.id)" class="btn-primary">
            ✅ Aprobar y Ejecutar
          </button>
          <button @click="$emit('reject', plan.id)" class="btn-secondary">
            ❌ Rechazar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  plans: any[]
}>()

const emit = defineEmits(['approve', 'reject'])

const pendingCount = computed(() => props.plans.filter(p => p.awaiting_approval).length)
</script>

<style scoped>
.fix-plans-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f5f5f4;
}

.pending-badge {
  padding: 4px 12px;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #fbbf24;
}

.plan-card {
  background: #0e1015;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.15s;
}

.plan-card.pending {
  border-color: rgba(251, 191, 36, 0.3);
  background: rgba(251, 191, 36, 0.02);
}

.plan-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.plan-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.plan-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #f5f5f4;
  flex: 1;
  min-width: 200px;
}

.plan-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.approval-badge {
  padding: 4px 10px;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #fbbf24;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.completed {
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  color: #34d399;
}

.strategy-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(0, 213, 255, 0.15);
  color: #00d5ff;
  text-transform: uppercase;
}

.strategy-badge-large {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(0, 213, 255, 0.15);
  color: #00d5ff;
  text-transform: uppercase;
}

.plan-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #8b8d98;
}

.plan-id {
  font-family: 'JetBrains Mono', monospace;
  color: #5e6272;
}

.effort {
  font-family: 'JetBrains Mono', monospace;
  color: #8b8d98;
}

.plan-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.plan-section label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #5e6272;
}

.steps-list {
  margin: 0;
  padding-left: 20px;
  color: #d9dbdf;
  font-size: 13px;
  line-height: 1.8;
}

.files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-tag {
  padding: 2px 8px;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #d9dbdf;
}

.no-files,
.no-changes,
.no-tests {
  font-size: 12px;
  color: #5e6272;
  font-style: italic;
}

.config-changes {
  margin: 0;
  padding: 12px;
  background: #0a0c11;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #d9dbdf;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}

.tests-list {
  margin: 0;
  padding-left: 20px;
  color: #d9dbdf;
  font-size: 13px;
}

.rollback-plan {
  margin: 0;
  padding: 10px 12px;
  background: rgba(248, 113, 113, 0.05);
  border: 1px solid rgba(248, 113, 113, 0.15);
  border-radius: 8px;
  font-size: 12px;
  color: #fca5a5;
}

.plan-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 8px;
}

.plan-actions .btn-primary,
.plan-actions .btn-secondary {
  flex: 1;
}
</style>