<template>
  <div class="settings-panel">
    <div class="settings-header">
      <h3>Configuración del Self-Healer</h3>
      <p class="settings-description">Controla el comportamiento del sistema de auto-reparación</p>
    </div>

    <div class="settings-sections">
      <!-- General -->
      <section class="settings-section">
        <h4>General</h4>
        <div class="setting-row">
          <div class="setting-info">
            <label>Habilitado</label>
            <span class="setting-hint">Activa/desactiva el self-healer completamente</span>
          </div>
          <ToggleSwitch v-model="localConfig.enabled" />
        </div>

        <div class="setting-row">
          <div class="setting-info">
            <label>Intervalo de Escaneo</label>
            <span class="setting-hint">Minutos entre escaneos automáticos</span>
          </div>
          <input
            type="number"
            v-model.number="localConfig.scan_interval_minutes"
            min="1"
            max="1440"
            class="setting-input"
          >
          <span class="setting-unit">minutos</span>
        </div>

        <div class="setting-row">
          <div class="setting-info">
            <label>Máximos Fixes Concurrentes</label>
            <span class="setting-hint">Cuántos fixes procesar en paralelo</span>
          </div>
          <input
            type="number"
            v-model.number="localConfig.max_concurrent_fixes"
            min="1"
            max="10"
            class="setting-input"
          >
        </div>

        <div class="setting-row">
          <div class="setting-info">
            <label>Auto-aprobar Bajo Riesgo</label>
            <span class="setting-hint">Aprobar automáticamente fixes de config_change, restart_service</span>
          </div>
          <ToggleSwitch v-model="localConfig.auto_approve_low_risk" />
        </div>
      </section>

      <!-- Approval -->
      <section class="settings-section">
        <h4>Aprobaciones Requeridas</h4>
        <p class="section-hint">Selecciona qué niveles de riesgo requieren aprobación humana</p>
        <div class="approval-options">
          <label class="approval-option" v-for="level in approvalLevels" :key="level">
            <input
              type="checkbox"
              :value="level"
              v-model="localConfig.require_approval_for"
            >
            <span class="approval-label">{{ formatApprovalLabel(level) }}</span>
            <span class="approval-desc">{{ approvalDescriptions[level] }}</span>
          </label>
        </div>
      </section>

      <!-- Deployment -->
      <section class="settings-section">
        <h4>Despliegue</h4>
        <div class="setting-row">
          <div class="setting-info">
            <label>Duración Canary</label>
            <span class="setting-hint">Minutos monitoreando canary antes de promover</span>
          </div>
          <input
            type="number"
            v-model.number="localConfig.canary_duration_minutes"
            min="1"
            max="120"
            class="setting-input"
          >
          <span class="setting-unit">minutos</span>
        </div>

        <div class="setting-row">
          <div class="setting-info">
            <label>Tiempo Máx. Rollback</label>
            <span class="setting-hint">Minutos máximos para completar rollback automático</span>
          </div>
          <input
            type="number"
            v-model.number="localConfig.max_rollback_time_minutes"
            min="1"
            max="1440"
            class="setting-input"
          >
          <span class="setting-unit">minutos</span>
        </div>
      </section>

      <!-- Excluded Paths -->
      <section class="settings-section">
        <h4>Rutas Excluidas (Protegidas)</h4>
        <p class="section-hint">Estas rutas nunca serán modificadas por el self-healer</p>
        <div class="excluded-paths">
          <div v-for="(path, i) in localConfig.excluded_paths" :key="i" class="excluded-path-row">
            <input
              type="text"
              v-model="localConfig.excluded_paths[i]"
              class="excluded-input"
              placeholder="ej: cores/security/"
            >
            <button @click="removeExcludedPath(i)" class="btn-icon danger" title="Eliminar">🗑️</button>
          </div>
          <button @click="addExcludedPath" class="btn-secondary btn-sm">+ Agregar Ruta</button>
        </div>
      </section>

      <!-- Learning -->
      <section class="settings-section">
        <h4>Aprendizaje</h4>
        <div class="setting-row">
          <div class="setting-info">
            <label>Aprendizaje Habilitado</label>
            <span class="setting-hint">Aprender de despliegues exitosos y fallidos</span>
          </div>
          <ToggleSwitch v-model="localConfig.learning_enabled" />
        </div>
      </section>

      <!-- Actions -->
      <div class="settings-actions">
        <button @click="saveConfig" class="btn-primary" :disabled="saving">
          <span v-if="saving" class="spinner"></span>
          Guardar Cambios
        </button>
        <button @click="resetConfig" class="btn-secondary">
          Restablecer Defaults
        </button>
        <button @click="triggerScan" class="btn-secondary">
          🔍 Escanear Ahora
        </button>
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { onMounted } from 'vue'
import axios from 'axios'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'

const props = defineProps<{
  config: any
}>()

const emit = defineEmits(['update'])

const localConfig = ref<any>({})
const saving = ref(false)

const approvalLevels = [
  'none',
  'low_risk',
  'high_risk',
  'critical',
] as const

const approvalDescriptions: Record<string, string> = {
  none: 'Sin aprobación (solo cambios triviales)',
  low_risk: 'Config changes, reinicios de servicio',
  high_risk: 'Cambios de código, actualizaciones de dependencias',
  critical: 'Deploy a producción, rollbacks, cambios de seguridad',
}

function formatApprovalLabel(level: string) {
  const labels: Record<string, string> = {
    none: 'Ninguna',
    low_risk: 'Bajo Riesgo',
    high_risk: 'Alto Riesgo',
    critical: 'Crítico',
  }
  return labels[level] || level
}

onMounted(() => {
  localConfig.value = { ...props.config }
})

watch(() => props.config, (newConfig) => {
  localConfig.value = { ...newConfig }
}, { deep: true })

async function saveConfig() {
  saving.value = true
  try {
    await axios.put('/api/self-healer/config', localConfig.value)
    emit('update', localConfig.value)
  } catch (e) {
    console.error('Failed to save config:', e)
  } finally {
    saving.value = false
  }
}

function resetConfig() {
  if (confirm('¿Restablecer configuración a valores por defecto?')) {
    localConfig.value = {
      enabled: true,
      scan_interval_minutes: 15,
      max_concurrent_fixes: 2,
      auto_approve_low_risk: true,
      require_approval_for: ['high_risk', 'critical'],
      excluded_paths: [
        'core/',
        'cores/security/',
        'cores/license/',
        'cores/identity_vault.py',
        'cores/vault_crypto.py',
        'cores/auth/',
      ],
      protected_branches: ['main', 'master', 'release/*'],
      max_rollback_time_minutes: 30,
      canary_duration_minutes: 10,
      learning_enabled: true,
      max_learning_entries: 10000,
    }
  }
}

function addExcludedPath() {
  localConfig.value.excluded_paths.push('')
}

function removeExcludedPath(index: number) {
  localConfig.value.excluded_paths.splice(index, 1)
}

async function triggerScan() {
  try {
    await axios.post('/api/self-healer/scan', { force: true })
    emit('update', localConfig.value)
  } catch (e) {
    console.error('Scan failed:', e)
  }
}
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.settings-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--ownex-bg-surface);
}

.settings-description {
  margin: 0;
  font-size: 13px;
  color: var(--ownex-text-secondary);
}

.settings-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.settings-section h4 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ownex-bg-surface);
}

.section-hint {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--ownex-text-secondary);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  flex-wrap: wrap;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 200px;
}

.setting-info label {
  font-size: 13px;
  font-weight: 500;
  color: var(--ownex-bg-surface);
}

.setting-hint {
  font-size: 11px;
  color: var(--ownex-text-muted);
}

.setting-input {
  width: 100px;
  padding: 6px 10px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--ownex-bg-surface);
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
}

.setting-input:focus {
  outline: none;
  border-color: rgba(0, 213, 255, 0.4);
}

.setting-unit {
  font-size: 12px;
  color: var(--ownex-text-secondary);
  font-family: 'JetBrains Mono', monospace;
}

.approval-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.approval-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.12s;
}

.approval-option:hover {
  border-color: rgba(0, 213, 255, 0.3);
  background: rgba(0, 213, 255, 0.02);
}

.approval-option input[type='checkbox'] {
  margin-top: 2px;
  width: 16px;
  height: 16px;
  accent-color: var(--ownex-accent);
}

.approval-label {
  font-weight: 500;
  color: var(--ownex-bg-surface);
  min-width: 100px;
}

.approval-desc {
  font-size: 12px;
  color: var(--ownex-text-secondary);
  flex: 1;
}

.excluded-paths {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.excluded-path-row {
  display: flex;
  gap: 8px;
}

.excluded-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--ownex-bg-base);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--ownex-bg-surface);
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
}

.btn-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--ownex-text-secondary);
  cursor: pointer;
  transition: all 0.12s;
}

.btn-icon:hover {
  background: rgba(255, 255, 255, 0.04);
}

.btn-icon.danger:hover {
  background: rgba(248, 113, 113, 0.1);
  color: var(--ownex-danger);
}

.settings-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .setting-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .setting-input {
    width: 100%;
  }
}
</style>