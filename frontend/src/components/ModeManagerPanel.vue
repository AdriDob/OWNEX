<template>
  <div class="mode-manager-panel">
    <div class="panel-header">
      <h2>Mode Manager</h2>
      <div class="header-actions">
        <button @click="refreshModes" class="refresh-btn">🔄 Refresh</button>
        <button @click="showHistory = true" class="history-btn">📜 History</button>
      </div>
    </div>

    <!-- Active Modes Summary -->
    <div class="active-summary">
      <div class="summary-card">
        <span class="summary-label">Active Modes:</span>
        <span class="summary-value">{{ activeCount }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Conflicts:</span>
        <span class="summary-value" :class="{ 'has-conflicts': hasConflicts }">{{ conflictCount }}</span>
      </div>
    </div>

    <!-- Mode Categories -->
    <div class="mode-categories">
      <div v-for="(modes, category) in modesByCategory" :key="category" class="category-section">
        <h3>{{ category }}</h3>
        <div class="mode-list">
          <div
            v-for="mode in modes"
            :key="mode.mode_key"
            :class="['mode-item', { active: mode.active, conflict: hasConflict(mode) }]"
          >
            <div class="mode-info">
              <div class="mode-header">
                <span class="mode-name">{{ mode.name }}</span>
                <span :class="['mode-status', mode.active ? 'active' : 'inactive']">
                  {{ mode.active ? '✓ Active' : '○ Inactive' }}
                </span>
              </div>
              <div class="mode-description">{{ mode.description }}</div>
              <div v-if="hasConflict(mode)" class="conflict-warning">
                ⚠️ Conflict detected
              </div>
            </div>
            <div class="mode-actions">
              <button
                @click="toggleMode(mode)"
                :class="['toggle-btn', mode.active ? 'deactivate' : 'activate']"
                :disabled="hasConflict(mode) && !mode.active"
              >
                {{ mode.active ? 'Deactivate' : 'Activate' }}
              </button>
              <button @click="showDetails(mode)" class="details-btn">ℹ️</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Conflict Modal -->
    <div v-if="showConflictModal" class="modal-overlay" @click="showConflictModal = false">
      <div class="modal-content" @click.stop>
        <h3>⚠️ Mode Conflict Detected</h3>
        <div class="conflict-details">
          <p>Cannot activate <strong>{{ conflictModalMode?.name }}</strong> due to conflicts:</p>
          <ul>
            <li v-for="conflict in conflictModalConflicts" :key="conflict">
              {{ conflict }}
            </li>
          </ul>
        </div>
        <div class="conflict-resolution">
          <h4>Suggested Resolution:</h4>
          <ul>
            <li v-for="suggestion in conflictModalSuggestions" :key="suggestion.conflict">
              <strong>Deactivate {{ suggestion.conflict_name }}</strong>: {{ suggestion.reason }}
            </li>
          </ul>
        </div>
        <div class="modal-actions">
          <button @click="forceActivate" class="force-btn">Force Activate (Auto-Resolve)</button>
          <button @click="showConflictModal = false" class="cancel-btn">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Details Modal -->
    <div v-if="showDetailsModal" class="modal-overlay" @click="showDetailsModal = false">
      <div class="modal-content details-modal" @click.stop>
        <h3>{{ detailsMode?.name }}</h3>
        <div class="details-content">
          <div class="detail-row">
            <span class="detail-label">Description:</span>
            <span class="detail-value">{{ detailsMode?.description }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Category:</span>
            <span class="detail-value">{{ detailsMode?.category }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Type:</span>
            <span class="detail-value">{{ detailsMode?.mode_type }}</span>
          </div>
          <div v-if="detailsMode?.mutually_exclusive_with?.length" class="detail-row">
            <span class="detail-label">Mutually Exclusive With:</span>
            <span class="detail-value">{{ detailsMode.mutually_exclusive_with.join(', ') }}</span>
          </div>
          <div v-if="detailsMode?.compatible_with?.length" class="detail-row">
            <span class="detail-label">Compatible With:</span>
            <span class="detail-value">{{ detailsMode.compatible_with.join(', ') }}</span>
          </div>
          <div v-if="detailsMode?.requires?.length" class="detail-row">
            <span class="detail-label">Requires:</span>
            <span class="detail-value">{{ detailsMode.requires.join(', ') }}</span>
          </div>
          <div v-if="detailsMode?.excludes?.length" class="detail-row">
            <span class="detail-label">Excludes:</span>
            <span class="detail-value">{{ detailsMode.excludes.join(', ') }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="showDetailsModal = false" class="close-btn">Close</button>
        </div>
      </div>
    </div>

    <!-- History Modal -->
    <div v-if="showHistory" class="modal-overlay" @click="showHistory = false">
      <div class="modal-content history-modal" @click.stop>
        <h3>Mode Change History</h3>
        <div class="history-list">
          <div v-for="change in history" :key="change.id" class="history-item">
            <div class="history-header">
              <span class="history-mode">{{ change.mode_key }}</span>
              <span class="history-time">{{ formatTime(change.timestamp) }}</span>
            </div>
            <div class="history-change">
              <span v-if="change.old_value" class="old-value">{{ change.old_value }}</span>
              <span class="arrow">→</span>
              <span class="new-value">{{ change.new_value }}</span>
            </div>
            <div v-if="change.auto_resolved?.length" class="auto-resolved">
              Auto-resolved: {{ change.auto_resolved.join(', ') }}
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="showHistory = false" class="close-btn">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

interface Mode {
  mode_key: string
  name: string
  description: string
  category: string
  mode_type: string
  mode_value: string
  active: boolean
  mutually_exclusive_with: string[]
  compatible_with: string[]
  requires: string[]
  excludes: string[]
}

interface ModeHistory {
  id: string
  mode_key: string
  old_value: string | null
  new_value: string
  timestamp: string
  auto_resolved: string[]
  conflicts_detected: string[]
}

const availableModes = ref<Record<string, Mode>>({})
const activeModes = ref<Record<string, string>>({})
const history = ref<ModeHistory[]>([])
const showConflictModal = ref(false)
const showDetailsModal = ref(false)
const showHistory = ref(false)
const conflictModalMode = ref<Mode | null>(null)
const conflictModalConflicts = ref<string[]>([])
const conflictModalSuggestions = ref<any[]>([])
const detailsMode = ref<Mode | null>(null)

const activeCount = computed(() => Object.keys(activeModes.value).length)
const conflictCount = computed(() => {
  let count = 0
  Object.values(availableModes.value).forEach((mode) => {
    if (hasConflict(mode)) count++
  })
  return count
})
const hasConflicts = computed(() => conflictCount.value > 0)

const modesByCategory = computed(() => {
  const grouped: Record<string, Mode[]> = {}
  Object.values(availableModes.value).forEach((mode) => {
    if (!grouped[mode.category]) {
      grouped[mode.category] = []
    }
    grouped[mode.category].push(mode)
  })
  return grouped
})

function hasConflict(mode: Mode): boolean {
  // Check if mode is mutually exclusive with any active mode
  for (const exclusiveKey of mode.mutually_exclusive_with) {
    if (exclusiveKey in availableModes.value) {
      const exclusiveMode = availableModes.value[exclusiveKey]
      if (exclusiveMode.active) {
        return true
      }
    }
  }
  // Check if any active mode excludes this mode
  for (const [key, activeValue] of Object.entries(activeModes.value)) {
    for (const modeData of Object.values(availableModes.value)) {
      if (modeData.mode_type === key && modeData.mode_value === activeValue) {
        if (modeData.excludes.includes(mode.mode_key)) {
          return true
        }
      }
    }
  }
  return false
}

async function refreshModes() {
  try {
    const [availableRes, activeRes, historyRes] = await Promise.all([
      fetch('/api/modes/available'),
      fetch('/api/modes/active'),
      fetch('/api/modes/history'),
    ])
    availableModes.value = await availableRes.json()
    activeModes.value = (await activeRes.json()).active_modes
    history.value = (await historyRes.json()).history
  } catch (error) {
    console.error('Failed to refresh modes:', error)
  }
}

async function toggleMode(mode: Mode) {
  if (mode.active) {
    // Deactivate
    try {
      await fetch(`/api/modes/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode_key: mode.mode_key, force: true }),
      })
      await refreshModes()
    } catch (error) {
      console.error('Failed to deactivate mode:', error)
    }
  } else {
    // Activate - check for conflicts first
    const conflicts = []
    for (const exclusiveKey of mode.mutually_exclusive_with) {
      if (exclusiveKey in availableModes.value) {
        const exclusiveMode = availableModes.value[exclusiveKey]
        if (exclusiveMode.active) {
          conflicts.push(exclusiveKey)
        }
      }
    }

    if (conflicts.length > 0) {
      conflictModalMode.value = mode
      conflictModalConflicts.value = conflicts
      conflictModalSuggestions.value = conflicts.map((key) => ({
        conflict: key,
        conflict_name: availableModes.value[key].name,
        action: 'deactivate',
        reason: `${mode.name} is mutually exclusive with ${availableModes.value[key].name}`,
      }))
      showConflictModal.value = true
    } else {
      await activateMode(mode.mode_key)
    }
  }
}

async function activateMode(modeKey: string) {
  try {
    const response = await fetch('/api/modes/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode_key, force: false }),
    })
    const result = await response.json()

    if (result.status === 'conflict') {
      conflictModalMode.value = availableModes.value[modeKey]
      conflictModalConflicts.value = result.conflicts
      conflictModalSuggestions.value = result.suggested_resolution.suggestions
      showConflictModal.value = true
    } else {
      await refreshModes()
    }
  } catch (error) {
    console.error('Failed to activate mode:', error)
  }
}

async function forceActivate() {
  if (!conflictModalMode.value) return

  try {
    await fetch('/api/modes/set-force', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode_key: conflictModalMode.value.mode_key, force: true }),
    })
    showConflictModal.value = false
    await refreshModes()
  } catch (error) {
    console.error('Failed to force activate mode:', error)
  }
}

function showDetails(mode: Mode) {
  detailsMode.value = mode
  showDetailsModal.value = true
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleString()
}

onMounted(() => {
  refreshModes()
})
</script>

<style scoped>
.mode-manager-panel {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.panel-header h2 {
  color: var(--ownex-bg-surface);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.refresh-btn,
.history-btn {
  padding: 0.5rem 1rem;
  background: var(--ownex-text-muted);
  color: var(--ownex-bg-surface);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover,
.history-btn:hover {
  background: var(--ownex-text-muted);
}

.active-summary {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 8px;
  padding: 1rem;
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-label {
  color: var(--ownex-text-secondary);
  font-size: 0.85rem;
}

.summary-value {
  color: var(--ownex-bg-surface);
  font-weight: 700;
  font-size: 1.1rem;
}

.summary-value.has-conflicts {
  color: var(--ownex-yellow);
}

.mode-categories {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.category-section h3 {
  color: var(--ownex-yellow);
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
}

.mode-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.mode-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
}

.mode-item.active {
  border-color: var(--ownex-green);
  background: rgba(16, 185, 129, 0.1);
}

.mode-item.conflict {
  border-color: var(--ownex-yellow);
  background: rgba(245, 158, 11, 0.1);
}

.mode-info {
  flex: 1;
}

.mode-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.mode-name {
  color: var(--ownex-bg-surface);
  font-weight: 600;
  font-size: 0.95rem;
}

.mode-status {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.mode-status.active {
  background: rgba(16, 185, 129, 0.2);
  color: var(--ownex-green);
}

.mode-status.inactive {
  background: rgba(107, 114, 128, 0.2);
  color: var(--ownex-text-muted);
}

.mode-description {
  color: var(--ownex-text-secondary);
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.conflict-warning {
  color: var(--ownex-yellow);
  font-size: 0.8rem;
  font-weight: 600;
}

.mode-actions {
  display: flex;
  gap: 0.5rem;
}

.toggle-btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.toggle-btn.activate {
  background: var(--ownex-green);
  color: white;
  border-color: var(--ownex-green);
}

.toggle-btn.activate:hover {
  background: var(--ownex-green);
}

.toggle-btn.deactivate {
  background: var(--ownex-text-muted);
  color: var(--ownex-bg-surface);
  border-color: var(--ownex-text-muted);
}

.toggle-btn.deactivate:hover {
  background: var(--ownex-text-muted);
}

.toggle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.details-btn {
  padding: 0.5rem;
  background: var(--ownex-text-muted);
  color: var(--ownex-bg-surface);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s ease;
}

.details-btn:hover {
  background: var(--ownex-text-muted);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-content {
  background: var(--ownex-bg-elevated);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.details-modal,
.history-modal {
  max-width: 700px;
}

.modal-content h3 {
  color: var(--ownex-bg-surface);
  margin: 0 0 1rem 0;
}

.conflict-details,
.conflict-resolution,
.details-content {
  color: var(--ownex-text-secondary);
  margin-bottom: 1rem;
}

.conflict-details ul,
.conflict-resolution ul {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}

.conflict-details li,
.conflict-resolution li {
  margin-bottom: 0.25rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--ownex-text-muted);
}

.detail-label {
  color: var(--ownex-text-secondary);
  font-weight: 600;
}

.detail-value {
  color: var(--ownex-bg-surface);
  text-align: right;
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.force-btn {
  padding: 0.75rem 1.5rem;
  background: var(--ownex-yellow);
  color: white;
  border: 1px solid var(--ownex-yellow);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.force-btn:hover {
  background: var(--ownex-yellow);
}

.cancel-btn,
.close-btn {
  padding: 0.75rem 1.5rem;
  background: var(--ownex-text-muted);
  color: var(--ownex-bg-surface);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.cancel-btn:hover,
.close-btn:hover {
  background: var(--ownex-text-muted);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ownex-text-muted);
  border-radius: 6px;
  padding: 0.75rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}

.history-mode {
  color: var(--ownex-yellow);
  font-weight: 600;
  font-size: 0.9rem;
}

.history-time {
  color: var(--ownex-text-secondary);
  font-size: 0.8rem;
}

.history-change {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--ownex-text-secondary);
  font-size: 0.85rem;
}

.old-value {
  color: var(--ownex-text-muted);
  text-decoration: line-through;
}

.new-value {
  color: var(--ownex-green);
  font-weight: 600;
}

.arrow {
  color: var(--ownex-text-secondary);
}

.auto-resolved {
  color: var(--ownex-yellow);
  font-size: 0.8rem;
  margin-top: 0.25rem;
}
</style>
