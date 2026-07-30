<template>
  <div class="version-backup-page">
    <div class="page-header">
      <h1>{{ t('version_backup.title') }}</h1>
      <p>{{ t('version_backup.subtitle') }}</p>
    </div>

    <!-- Current Version Info -->
    <div class="current-version-card">
      <div class="card-header">
        <h2>{{ t('version_backup.current_version') }}</h2>
        <div class="card-actions">
          <button @click="refreshCurrentVersion" class="btn btn-secondary" :disabled="loading">
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          </button>
        </div>
      </div>
      <div class="version-info" v-if="currentVersion">
        <div class="info-item">
          <label>{{ t('version') }}:</label>
          <span>{{ currentVersion.version }}</span>
        </div>
        <div class="info-item">
          <label>{{ t('git_commit') }}:</label>
          <span class="commit-hash">{{ currentVersion.git_commit }}</span>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <button @click="showCreateBackupModal = true" class="btn btn-primary">
        <i class="fas fa-plus"></i>
        {{ t('version_backup.create_backup') }}
      </button>
      <button @click="restoreLatest" class="btn btn-warning" :disabled="!hasBackups || loading">
        <i class="fas fa-undo"></i>
        {{ t('version_backup.restore_latest') }}
      </button>
      <button @click="refreshBackups" class="btn btn-secondary" :disabled="loading">
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
        {{ t('refresh') }}
      </button>
    </div>

    <!-- Backups List -->
    <div class="backups-section">
      <div class="section-header">
        <h2>{{ t('version_backup.version_history') }}</h2>
        <div class="backup-count">{{ backups.length }} {{ t('backups') }}</div>
      </div>

      <div v-if="loading" class="loading">
        <i class="fas fa-spinner fa-spin"></i>
        {{ t('loading') }}...
      </div>

      <div v-else-if="backups.length === 0" class="empty-state">
        <i class="fas fa-archive"></i>
        <p>{{ t('version_backup.no_backups') }}</p>
      </div>

      <div v-else class="backups-list">
        <div v-for="backup in backups" :key="backup.backup_path" class="backup-card" :class="{ 'active': backup.state === 'active' }">
          <div class="backup-header">
            <div class="backup-version">
              <span class="version-tag">{{ backup.version }}</span>
              <span class="state-badge" :class="backup.state">{{ backup.state }}</span>
            </div>
            <div class="backup-date">{{ formatDate(backup.created_at) }}</div>
          </div>

          <div class="backup-details">
            <div class="detail-item">
              <i class="fas fa-code-branch"></i>
              <span class="commit-hash">{{ backup.git_commit }}</span>
            </div>
            <div class="detail-item">
              <i class="fas fa-database"></i>
              <span>{{ formatSize(backup.size) }}</span>
            </div>
            <div class="detail-item" v-if="backup.notes">
              <i class="fas fa-sticky-note"></i>
              <span>{{ backup.notes }}</span>
            </div>
          </div>

          <div class="backup-actions">
            <button @click="verifyBackup(backup)" class="btn btn-sm btn-info" :disabled="loading">
              <i class="fas fa-check-circle"></i>
              {{ t('version_backup.verify') }}
            </button>
            <button @click="showRollbackModal(backup)" class="btn btn-sm btn-warning" :disabled="loading || backup.state === 'active'">
              <i class="fas fa-undo"></i>
              {{ t('version_backup.rollback') }}
            </button>
            <button @click="deleteBackup(backup)" class="btn btn-sm btn-danger" :disabled="loading || backup.state === 'active'">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Backup Modal -->
    <div v-if="showCreateBackupModal" class="modal-overlay" @click.self="showCreateBackupModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ t('version_backup.create_backup') }}</h3>
          <button @click="showCreateBackupModal = false" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>{{ t('version_backup.backup_notes') }}</label>
            <textarea v-model="backupNotes" rows="3" :placeholder="t('version_backup.backup_notes_placeholder')"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateBackupModal = false" class="btn btn-secondary">{{ t('cancel') }}</button>
          <button @click="createBackup" class="btn btn-primary" :disabled="loading">
            <i class="fas fa-save" v-if="!loading"></i>
            <i class="fas fa-spinner fa-spin" v-else></i>
            {{ t('version_backup.create_backup') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Rollback Modal -->
    <div v-if="showRollbackModal" class="modal-overlay" @click.self="showRollbackModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ t('version_backup.rollback_to_version') }}</h3>
          <button @click="showRollbackModal = false" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="rollback-info">
            <p>{{ t('version_backup.rollback_warning') }}</p>
            <div class="backup-summary">
              <div class="summary-item">
                <label>{{ t('version') }}:</label>
                <span>{{ selectedBackup?.version }}</span>
              </div>
              <div class="summary-item">
                <label>{{ t('git_commit') }}:</label>
                <span class="commit-hash">{{ selectedBackup?.git_commit }}</span>
              </div>
              <div class="summary-item">
                <label>{{ t('created_at') }}:</label>
                <span>{{ formatDate(selectedBackup?.created_at) }}</span>
              </div>
            </div>
            <p class="pre-rollback-info">
              <i class="fas fa-info-circle"></i>
              {{ t('version_backup.pre_rollback') }} {{ t('version_backup.will_be_created') }}
            </p>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showRollbackModal = false" class="btn btn-secondary">{{ t('cancel') }}</button>
          <button @click="rollbackToVersion" class="btn btn-warning" :disabled="loading">
            <i class="fas fa-undo" v-if="!loading"></i>
            <i class="fas fa-spinner fa-spin" v-else></i>
            {{ t('version_backup.rollback') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Verification Result Modal -->
    <div v-if="showVerificationModal" class="modal-overlay" @click.self="showVerificationModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ t('version_backup.integrity') }}</h3>
          <button @click="showVerificationModal = false" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="verification-result" :class="{ 'valid': verificationResult?.valid, 'invalid': !verificationResult?.valid }">
            <i class="fas" :class="verificationResult?.valid ? 'fa-check-circle' : 'fa-exclamation-circle'"></i>
            <div class="result-details">
              <p>{{ verificationResult?.valid ? t('version_backup.backup_valid') : t('version_backup.backup_invalid') }}</p>
              <p v-if="!verificationResult?.valid" class="error-message">{{ verificationResult?.error }}</p>
              <div v-if="verificationResult?.valid" class="valid-details">
                <div class="detail-item">
                  <label>{{ t('version') }}:</label>
                  <span>{{ verificationResult?.version }}</span>
                </div>
                <div class="detail-item">
                  <label>{{ t('git_commit') }}:</label>
                  <span class="commit-hash">{{ verificationResult?.git_commit }}</span>
                </div>
                <div class="detail-item">
                  <label>{{ t('size') }}:</label>
                  <span>{{ formatSize(verificationResult?.size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showVerificationModal = false" class="btn btn-primary">{{ t('close') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const { t } = useI18n()

const loading = ref(false)
const backups = ref<any[]>([])
const currentVersion = ref<any>(null)
const showCreateBackupModal = ref(false)
const showRollbackModal = ref(false)
const showVerificationModal = ref(false)
const backupNotes = ref('')
const selectedBackup = ref<any>(null)
const verificationResult = ref<any>(null)

const hasBackups = computed(() => backups.value.length > 0)

const refreshCurrentVersion = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/version-backup/current-version')
    currentVersion.value = response.data
  } catch (error) {
    console.error('Failed to fetch current version:', error)
  } finally {
    loading.value = false
  }
}

const refreshBackups = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/version-backup/backups')
    backups.value = response.data.backups || []
  } catch (error) {
    console.error('Failed to fetch backups:', error)
  } finally {
    loading.value = false
  }
}

const createBackup = async () => {
  loading.value = true
  try {
    const response = await axios.post('/api/version-backup/backup', {
      notes: backupNotes.value
    })

    if (response.data.success) {
      showCreateBackupModal.value = false
      backupNotes.value = ''
      await refreshBackups()
    }
  } catch (error) {
    console.error('Failed to create backup:', error)
  } finally {
    loading.value = false
  }
}

const verifyBackup = async (backup: any) => {
  loading.value = true
  try {
    const response = await axios.get(`/api/version-backup/backup/${encodeURIComponent(backup.backup_path)}/verify`)
    verificationResult.value = response.data
    showVerificationModal.value = true
  } catch (error) {
    console.error('Failed to verify backup:', error)
    verificationResult.value = { valid: false, error: 'Verification failed' }
    showVerificationModal.value = true
  } finally {
    loading.value = false
  }
}

const showRollbackModal = (backup: any) => {
  selectedBackup.value = backup
  showRollbackModal.value = true
}

const rollbackToVersion = async () => {
  loading.value = true
  try {
    const response = await axios.post('/api/version-backup/rollback', {
      version: selectedBackup.value?.version,
      git_commit: selectedBackup.value?.git_commit
    })

    if (response.data.success) {
      showRollbackModal.value = false
      await refreshBackups()
      await refreshCurrentVersion()
    }
  } catch (error) {
    console.error('Failed to rollback:', error)
  } finally {
    loading.value = false
  }
}

const restoreLatest = async () => {
  if (!confirm(t('version_backup.restore_latest_confirm'))) return

  loading.value = true
  try {
    const response = await axios.post('/api/version-backup/restore-latest')

    if (response.data.success) {
      await refreshBackups()
      await refreshCurrentVersion()
    }
  } catch (error) {
    console.error('Failed to restore latest:', error)
  } finally {
    loading.value = false
  }
}

const deleteBackup = async (backup: any) => {
  if (!confirm(t('version_backup.delete_backup_confirm'))) return

  loading.value = true
  try {
    // TODO: Implement delete endpoint
    await refreshBackups()
  } catch (error) {
    console.error('Failed to delete backup:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

onMounted(() => {
  refreshCurrentVersion()
  refreshBackups()
})
</script>

<style scoped>
.version-backup-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: #666;
}

.current-version-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-header h2 {
  font-size: 1.25rem;
  margin: 0;
}

.version-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  gap: 0.5rem;
}

.info-item label {
  font-weight: 600;
  color: #666;
}

.commit-hash {
  font-family: monospace;
  background: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

.quick-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.quick-actions button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.backups-section {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 1.25rem;
  margin: 0;
}

.backup-count {
  color: #666;
  font-size: 0.875rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #999;
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.backups-list {
  display: grid;
  gap: 1rem;
}

.backup-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.backup-card:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.backup-card.active {
  border-color: #52c41a;
  background: #f6ffed;
}

.backup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.backup-version {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.version-tag {
  font-weight: 600;
  font-size: 1.125rem;
}

.state-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.state-badge.active {
  background: #52c41a;
  color: white;
}

.state-badge.backup {
  background: #1890ff;
  color: white;
}

.state-badge.rollback {
  background: #faad14;
  color: white;
}

.backup-date {
  color: #666;
  font-size: 0.875rem;
}

.backup-details {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #666;
  font-size: 0.875rem;
}

.backup-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-warning {
  background: #faad14;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #ffc53d;
}

.btn-danger {
  background: #ff4d4f;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #ff7875;
}

.btn-info {
  background: #13c2c2;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #36cfc9;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

.rollback-info p {
  margin-bottom: 1rem;
}

.backup-summary {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.summary-item {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.summary-item label {
  font-weight: 600;
  color: #666;
}

.pre-rollback-info {
  color: #1890ff;
  font-size: 0.875rem;
}

.verification-result {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.verification-result.valid {
  color: #52c41a;
}

.verification-result.invalid {
  color: #ff4d4f;
}

.verification-result i {
  font-size: 2rem;
}

.result-details {
  flex: 1;
}

.error-message {
  color: #ff4d4f;
  margin-top: 0.5rem;
}

.valid-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e0e0e0;
}
</style>
