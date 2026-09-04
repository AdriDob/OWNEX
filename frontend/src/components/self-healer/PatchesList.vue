<template>
  <div class="patches-list">
    <div class="list-header">
      <h3>Parches Generados</h3>
    </div>

    <div v-if="patches.length === 0" class="empty-state">
      <div class="empty-icon">🔧</div>
      <p>No hay parches generados</p>
      <span class="empty-hint">Los parches se crean al aprobar un plan de fix</span>
    </div>

    <div class="patches-grid">
      <div v-for="patch in patches" :key="patch.id" class="patch-card" :class="{ applied: patch.is_applied }">
        <div class="patch-header">
          <div class="patch-id">{{ patch.id }}</div>
          <span class="status-badge" :class="{ applied: patch.is_applied }">{{ patch.is_applied ? 'Aplicado' : 'Pendiente' }}</span>
        </div>

        <div class="patch-body">
          <div class="patch-field">
            <label>Plan</label>
            <span class="plan-ref">{{ patch.plan_id }}</span>
          </div>

          <div class="patch-field">
            <label>Archivos modificados</label>
            <div class="files-list">
              <span v-for="file in patch.files_changed" :key="file" class="file-tag">{{ file }}</span>
              <span v-if="patch.files_changed.length === 0" class="no-files">Sin archivos</span>
            </div>
          </div>

          <div class="patch-field">
            <label>Tests generados</label>
            <ul v-if="patch.tests_generated.length" class="tests-list">
              <li v-for="test in patch.tests_generated" :key="test" class="test-tag">{{ test }}</li>
            </ul>
            <span v-else class="no-tests">Sin tests</span>
          </div>

          <div class="patch-field">
            <label>Validación</label>
            <pre class="validation-results">{{ JSON.stringify(patch.validation_results, null, 2) }}</pre>
          </div>

          <div class="patch-field">
            <label>Diff</label>
            <pre class="diff-preview">{{ patch.diff || 'Sin diff (acción documentada)' }}</pre>
          </div>
        </div>

        <div class="patch-meta">
          <span class="created-at">Creado: {{ formatTime(patch.created_at) }}</span>
          <span v-if="patch.applied_at" class="applied-at">Aplicado: {{ formatTime(patch.applied_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  patches: any[]
}>()

const searchQuery = ref('')

const filteredPatches = computed(() => {
  if (!searchQuery.value) return props.patches
  const q = searchQuery.value.toLowerCase()
  return props.patches.filter(p =>
    p.id.toLowerCase().includes(q) ||
    p.plan_id.toLowerCase().includes(q) ||
    p.files_changed.some((f: string) => f.toLowerCase().includes(q))
  )
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
.patches-list {
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
  color: var(--ownex-bg-surface);
}

.patches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 16px;
}

.patch-card {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.15s;
}

.patch-card:hover {
  border-color: rgba(0, 213, 255, 0.3);
}

.patch-card.applied {
  border-color: rgba(52, 211, 153, 0.3);
}

.patch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--ownex-bg-base);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.patch-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--ownex-text-secondary);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.applied {
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  color: var(--ownex-green);
}

.status-badge:not(.applied) {
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: var(--ownex-yellow);
}

.patch-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.patch-field label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ownex-text-muted);
  margin-bottom: 6px;
}

.plan-ref {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--ownex-accent);
}

.files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-tag {
  padding: 2px 8px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--ownex-text-secondary);
}

.no-files,
.no-tests {
  font-size: 12px;
  color: var(--ownex-text-muted);
  font-style: italic;
}

.tests-list {
  margin: 0;
  padding-left: 20px;
  color: var(--ownex-text-secondary);
  font-size: 13px;
}

.test-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.validation-results,
.diff-preview {
  margin: 0;
  padding: 12px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--ownex-text-secondary);
  overflow: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-word;
}

.patch-meta {
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background: var(--ownex-bg-base);
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  font-size: 11px;
  color: var(--ownex-text-muted);
}

.created-at {
  font-family: 'JetBrains Mono', monospace;
}

.applied-at {
  font-family: 'JetBrains Mono', monospace;
  color: var(--ownex-green);
}
</style>