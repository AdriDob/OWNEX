<template>
  <div class="problems-list">
    <div class="list-header">
      <h3>Problemas Detectados</h3>
      <div class="filters">
        <select v-model="severityFilter" class="filter-select">
          <option value="">Todas las severidades</option>
          <option value="critical">Crítico</option>
          <option value="high">Alto</option>
          <option value="medium">Medio</option>
          <option value="low">Bajo</option>
        </select>
        <select v-model="categoryFilter" class="filter-select">
          <option value="">Todas las categorías</option>
          <option value="health_degradation">Salud Degradada</option>
          <option value="error_spike">Pico de Errores</option>
          <option value="performance_regression">Regresión Performance</option>
          <option value="test_failure">Fallos de Tests</option>
          <option value="resource_exhaustion">Agotamiento Recursos</option>
          <option value="dependency_failure">Fallo Dependencia</option>
        </select>
      </div>
    </div>

    <div v-if="filteredProblems.length === 0" class="empty-state">
      <div class="empty-icon">✅</div>
      <p>No hay problemas detectados</p>
      <span class="empty-hint">El sistema está sano</span>
    </div>

    <div class="problems-table">
      <table>
        <thead>
          <tr>
            <th>Severidad</th>
            <th>Categoría</th>
            <th>Título</th>
            <th>Componentes</th>
            <th>Detectado</th>
            <th>Ocurrencias</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="problem in filteredProblems" :key="problem.id" :class="`severity-${problem.severity}`">
            <td>
              <SeverityBadge :severity="problem.severity" />
            </td>
            <td>
              <CategoryBadge :category="problem.category" />
            </td>
            <td class="title-cell">
              <div class="problem-title">{{ problem.title }}</div>
              <div class="problem-desc">{{ problem.description }}</div>
            </td>
            <td>
              <span v-for="comp in problem.affected_components" :key="comp" class="component-tag">{{ comp }}</span>
            </td>
            <td class="time-cell">{{ formatTime(problem.first_seen) }}</td>
            <td class="count-cell">{{ problem.occurrence_count }}</td>
            <td class="actions-cell">
              <button @click="$emit('view-diagnosis', problem.id)" class="action-btn view-btn" title="Ver diagnóstico">
                🔍
              </button>
              <button @click="$emit('approve-fix', problem.id)" class="action-btn fix-btn" title="Aprobar fix">
                🔧
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import SeverityBadge from '@/components/ui/SeverityBadge.vue'
import CategoryBadge from '@/components/ui/CategoryBadge.vue'

const props = defineProps<{
  problems: any[]
}>()

const emit = defineEmits(['view-diagnosis', 'approve-fix'])

const severityFilter = ref('')
const categoryFilter = ref('')

const filteredProblems = computed(() => {
  return props.problems.filter(p => {
    if (severityFilter.value && p.severity !== severityFilter.value) return false
    if (categoryFilter.value && p.category !== categoryFilter.value) return false
    return true
  })
})

function formatTime(isoString: string) {
  const date = new Date(isoString)
  return date.toLocaleString('es-ES', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.problems-list {
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
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ownex-bg-surface);
}

.filters {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 6px 12px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--ownex-bg-surface);
  font-size: 13px;
  cursor: pointer;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state p {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 500;
  color: var(--ownex-green);
}

.empty-hint {
  font-size: 13px;
  color: var(--ownex-text-secondary);
}

.problems-table {
  overflow-x: auto;
}

.problems-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.problems-table th,
.problems-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.problems-table th {
  background: var(--ownex-bg-base);
  color: var(--ownex-text-secondary);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.problems-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.problems-table tr.severity-critical {
  border-left: 3px solid var(--ownex-danger);
}

.problems-table tr.severity-high {
  border-left: 3px solid var(--ownex-yellow);
}

.title-cell {
  max-width: 300px;
}

.problem-title {
  font-weight: 500;
  color: var(--ownex-bg-surface);
  margin-bottom: 2px;
}

.problem-desc {
  font-size: 11px;
  color: var(--ownex-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.time-cell {
  color: var(--ownex-text-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  white-space: nowrap;
}

.count-cell {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: var(--ownex-text-secondary);
}

.actions-cell {
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.action-btn {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.12s;
}

.action-btn:hover {
  border-color: rgba(0, 213, 255, 0.4);
  background: rgba(0, 213, 255, 0.05);
}

.view-btn:hover {
  border-color: rgba(0, 213, 255, 0.4);
}

.fix-btn:hover {
  border-color: rgba(52, 211, 153, 0.4);
}
</style>