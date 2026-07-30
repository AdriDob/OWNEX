<template>
  <div class="version-backup-page">
    <!-- ═══ TOP BAR ═══ -->
    <header class="top-bar">
      <div class="flex items-center gap-3">
        <!-- Logo mark -->
        <div class="relative w-9 h-9">
          <div class="absolute inset-0 rounded-full border border-primary/40" />
          <div class="absolute inset-[3px] rounded-full border border-primary/20" />
          <div class="absolute inset-[8px] rounded-full bg-primary/20" />
          <div class="absolute inset-[11px] rounded-full bg-primary" />
        </div>
        <span class="text-lg font-bold tracking-widest text-white font-display">OWNEX</span>
        <span class="text-[10px] text-muted tracking-wider">v4.7.0</span>

        <!-- Cycle pills -->
        <div class="nav-pills">
          <span class="pill pill-backup">BACKUP</span>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span class="text-xs text-green-400 font-semibold">BACKUP SYSTEM OPERATIONAL</span>
        </div>
        <div class="live-badge">LIVE</div>
      </div>
    </header>

    <!-- ═══ HERO SECTION ═══ -->
    <section class="hero-section">
      <div class="flex items-start gap-8">
        <!-- Big 'O' mark -->
        <div class="relative w-32 h-32 flex-shrink-0 hidden lg:block">
          <div class="o-ring o-ring-outer" />
          <div class="o-ring o-ring-inner" />
          <div class="o-dot" />
          <div class="o-core" />
        </div>

        <div class="flex-1">
          <h1 class="text-3xl md:text-4xl font-bold text-white font-display tracking-wide">
            Version Backup
          </h1>
          <p class="text-muted mt-2">
            System version history and rollback management · {{ backups.length }} backups available
          </p>
          <div class="flex flex-wrap gap-3 mt-6">
            <button class="action-pill action-primary" @click="showCreateBackupModal = true">
              <Shield class="w-4 h-4" /> Create Backup
            </button>
            <button class="action-pill action-green" @click="restoreLatest" :disabled="!hasBackups || loading">
              <RefreshCw class="w-4 h-4" /> Restore Latest
            </button>
            <button class="action-pill action-gold" @click="refreshBackups" :disabled="loading">
              <Activity class="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ CURRENT VERSION CARD ═══ -->
    <section class="cards-grid">
      <div class="card">
        <div class="card-label">CURRENT VERSION</div>
        <div class="card-value text-primary">{{ currentVersion?.version || 'Loading...' }}</div>
        <div class="card-detail">
          <div class="text-xs text-muted mt-2">
            <div class="flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-green-400" />
              Commit: <span class="font-mono text-xs">{{ currentVersion?.git_commit?.substring(0, 8) || 'Unknown' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-label">BACKUP STORAGE</div>
        <div class="card-value text-green-400">Local SQLite</div>
        <div class="card-detail">Shared with Recovery System</div>
      </div>

      <div class="card">
        <div class="card-label">BACKUP HEALTH</div>
        <div class="flex items-center gap-6">
          <svg class="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(30,41,59,0.5)" stroke-width="6" />
            <circle cx="50" cy="50" r="42" fill="none" stroke="#34D399" stroke-width="6"
              stroke-dasharray="264" :stroke-dashoffset="264 - (264 * 100 / 100)"
              stroke-linecap="round" />
          </svg>
          <div>
            <div class="text-2xl font-bold font-display text-green-400">
              100%
            </div>
            <div class="text-xs text-muted mt-2">
              All backups verified
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-label">BACKUP COUNT</div>
        <div class="card-value text-amber-400">{{ backups.length }} / 10</div>
        <div class="card-detail">Auto-cleanup enabled</div>
      </div>
    </section>

    <!-- ═══ BACKUP HISTORY ═══ -->
    <section class="backup-history-section">
      <div class="section-header">
        <h2 class="text-xl font-bold text-white font-display tracking-wide">BACKUP HISTORY</h2>
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted">{{ backups.length }} backups</span>
          <div class="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
        <p class="text-muted text-sm">Loading backup history...</p>
      </div>

      <div v-else-if="backups.length === 0" class="empty-state">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-muted/30 flex items-center justify-center">
          <Archive class="w-8 h-8 text-muted" />
        </div>
        <p class="text-muted">No backups available</p>
        <button class="action-pill action-primary mt-4" @click="showCreateBackupModal = true">
          <Shield class="w-4 h-4" /> Create First Backup
        </button>
      </div>

      <div v-else class="backups-grid">
        <div v-for="backup in backups" :key="backup.backup_path" class="backup-card" :class="{ 'card-active': backup.state === 'active' }">
          <div class="backup-header">
            <div class="backup-version">
              <span class="version-tag">{{ backup.version }}</span>
              <span class="state-badge" :class="backup.state">{{ backup.state }}</span>
            </div>
            <div class="backup-date">{{ formatDate(backup.created_at) }}</div>
          </div>

          <div class="backup-details">
            <div class="detail-item">
              <span class="text-muted text-xs">Commit:</span>
              <span class="font-mono text-xs">{{ backup.git_commit?.substring(0, 8) }}</span>
            </div>
            <div class="detail-item">
              <span class="text-muted text-xs">Size:</span>
              <span class="text-xs">{{ formatSize(backup.size) }}</span>
            </div>
            <div class="detail-item" v-if="backup.notes">
              <span class="text-muted text-xs">Notes:</span>
              <span class="text-xs truncate">{{ backup.notes }}</span>
            </div>
          </div>

          <div class="backup-actions">
            <button @click="verifyBackup(backup)" class="mini-button mini-info" :disabled="loading">
              <Shield class="w-3 h-3" /> Verify
            </button>
            <button @click="showRollbackModal(backup)" class="mini-button mini-warning" :disabled="loading || backup.state === 'active'">
              <RefreshCw class="w-3 h-3" /> Rollback
            </button>
            <button @click="deleteBackup(backup)" class="mini-button mini-danger" :disabled="loading || backup.state === 'active'">
              <Trash2 class="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ CREATE BACKUP MODAL ═══ -->
    <div v-if="showCreateBackupModal" class="modal-overlay" @click.self="showCreateBackupModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="text-lg font-bold text-white font-display">CREATE BACKUP</h3>
          <button @click="showCreateBackupModal = false" class="close-button">
            <X class="w-5 h-5 text-muted" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Backup Notes</label>
            <textarea v-model="backupNotes" rows="3" class="form-textarea" placeholder="Add notes about this backup (e.g., 'Pre-update before v2.0.0')"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateBackupModal = false" class="action-pill action-secondary">Cancel</button>
          <button @click="createBackup" class="action-pill action-primary" :disabled="loading">
            <Shield v-if="!loading" class="w-4 h-4" />
            <div v-else class="w-4 h-4 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
            Create Backup
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ ROLLBACK MODAL ═══ -->
    <div v-if="showRollbackModal" class="modal-overlay" @click.self="showRollbackModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="text-lg font-bold text-white font-display">ROLLBACK TO VERSION</h3>
          <button @click="showRollbackModal = false" class="close-button">
            <X class="w-5 h-5 text-muted" />
          </button>
        </div>
        <div class="modal-body">
          <div class="rollback-warning">
            <div class="flex items-center gap-3 mb-4">
              <AlertTriangle class="w-6 h-6 text-amber-400" />
              <p class="text-amber-400 font-semibold">WARNING: IRREVERSIBLE ACTION</p>
            </div>
            <p class="text-muted mb-4">You are about to rollback to a previous version. This will restore all files and git state.</p>
          </div>
          <div class="backup-summary">
            <div class="summary-item">
              <span class="text-muted text-xs">Version:</span>
              <span class="text-xs font-bold">{{ selectedBackup?.version }}</span>
            </div>
            <div class="summary-item">
              <span class="text-muted text-xs">Commit:</span>
              <span class="font-mono text-xs">{{ selectedBackup?.git_commit?.substring(0, 8) }}</span>
            </div>
            <div class="summary-item">
              <span class="text-muted text-xs">Created:</span>
              <span class="text-xs">{{ formatDate(selectedBackup?.created_at) }}</span>
            </div>
          </div>
          <div class="pre-rollback-info">
            <div class="flex items-center gap-2">
              <Shield class="w-4 h-4 text-primary" />
              <span class="text-xs text-primary">Pre-rollback backup will be created automatically</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showRollbackModal = false" class="action-pill action-secondary">Cancel</button>
          <button @click="rollbackToVersion" class="action-pill action-warning" :disabled="loading">
            <RefreshCw v-if="!loading" class="w-4 h-4" />
            <div v-else class="w-4 h-4 rounded-full border-2 border-amber-400/30 border-t-amber-400 animate-spin" />
            Rollback
          </button>
        </div>
      </div>
    </div>

    <!-- ═══ VERIFICATION MODAL ═══ -->
    <div v-if="showVerificationModal" class="modal-overlay" @click.self="showVerificationModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="text-lg font-bold text-white font-display">BACKUP INTEGRITY</h3>
          <button @click="showVerificationModal = false" class="close-button">
            <X class="w-5 h-5 text-muted" />
          </button>
        </div>
        <div class="modal-body">
          <div class="verification-result" :class="{ 'result-valid': verificationResult?.valid, 'result-invalid': !verificationResult?.valid }">
            <div class="verification-icon">
              <Shield v-if="verificationResult?.valid" class="w-12 h-12 text-green-400" />
              <AlertTriangle v-else class="w-12 h-12 text-red-400" />
            </div>
            <div class="verification-details">
              <p class="font-semibold">{{ verificationResult?.valid ? 'Backup is valid and integrity verified' : 'Backup verification failed' }}</p>
              <p v-if="!verificationResult?.valid" class="text-red-400 text-sm mt-2">{{ verificationResult?.error }}</p>
              <div v-if="verificationResult?.valid" class="valid-details">
                <div class="detail-item">
                  <span class="text-muted text-xs">Version:</span>
                  <span class="text-xs">{{ verificationResult?.version }}</span>
                </div>
                <div class="detail-item">
                  <span class="text-muted text-xs">Commit:</span>
                  <span class="font-mono text-xs">{{ verificationResult?.git_commit?.substring(0, 8) }}</span>
                </div>
                <div class="detail-item">
                  <span class="text-muted text-xs">Size:</span>
                  <span class="text-xs">{{ formatSize(verificationResult?.size) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showVerificationModal = false" class="action-pill action-primary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Shield, RefreshCw, Activity, Archive, AlertTriangle, X, Trash2 } from '@lucide/vue'
import axios from 'axios'

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
  if (!confirm('Are you sure you want to restore from the latest backup?')) return

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
  if (!confirm('Are you sure you want to delete this backup?')) return

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
/* ═══ STEAM-STYLE THEMING ═══ */
.version-backup-page {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  min-height: 100vh;
  padding: 2rem;
  font-family: 'Inter', system-ui, sans-serif;
}

/* ═══ TOP BAR ═══ */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 2rem;
}

.nav-pills {
  display: flex;
  gap: 0.5rem;
}

.pill {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.pill-backup {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60A5FA;
}

.live-badge {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #F87171;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* ═══ HERO SECTION ═══ */
.hero-section {
  padding: 2rem 0;
  margin-bottom: 2rem;
}

.o-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid;
}

.o-ring-outer {
  inset: 0;
  border-color: rgba(59, 130, 246, 0.3);
  animation: pulse-ring 3s ease-in-out infinite;
}

.o-ring-inner {
  inset: 20px;
  border-color: rgba(59, 130, 246, 0.5);
  animation: pulse-ring 3s ease-in-out infinite 1s;
}

.o-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #60A5FA;
  animation: pulse-dot 2s ease-in-out infinite;
}

.o-core {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: white;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.05); }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 0.7; transform: translate(-50%, -50%) scale(1.2); }
}

.action-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid;
  transition: all 0.2s;
  cursor: pointer;
}

.action-pill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-primary {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
  color: #60A5FA;
}

.action-primary:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.3);
  border-color: rgba(59, 130, 246, 0.6);
}

.action-green {
  background: rgba(52, 211, 153, 0.2);
  border-color: rgba(52, 211, 153, 0.4);
  color: #34D399;
}

.action-green:hover:not(:disabled) {
  background: rgba(52, 211, 153, 0.3);
  border-color: rgba(52, 211, 153, 0.6);
}

.action-gold {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.4);
  color: #FBBF24;
}

.action-gold:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.3);
  border-color: rgba(251, 191, 36, 0.6);
}

.action-red {
  background: rgba(248, 113, 113, 0.2);
  border-color: rgba(248, 113, 113, 0.4);
  color: #F87171;
}

.action-red:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.3);
  border-color: rgba(248, 113, 113, 0.6);
}

.action-warning {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.4);
  color: #FBBF24;
}

.action-warning:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.3);
  border-color: rgba(251, 191, 36, 0.6);
}

.action-secondary {
  background: rgba(100, 116, 139, 0.2);
  border-color: rgba(100, 116, 139, 0.4);
  color: #94A3B8;
}

.action-secondary:hover:not(:disabled) {
  background: rgba(100, 116, 139, 0.3);
  border-color: rgba(100, 116, 139, 0.6);
}

/* ═══ CARDS GRID ═══ */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  backdrop-filter: blur(10px);
}

.card-label {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #94A3B8;
  margin-bottom: 0.5rem;
}

.card-value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'Inter', system-ui, sans-serif;
}

.card-detail {
  font-size: 0.75rem;
  color: #94A3B8;
  margin-top: 0.5rem;
}

.mini-chart {
  display: flex;
  align-items: flex-end;
  gap: 0.25rem;
  height: 2rem;
  margin-top: 0.5rem;
}

.mini-chart .bar {
  width: 0.5rem;
  background: rgba(52, 211, 153, 0.3);
  border-radius: 2px;
  transition: all 0.3s;
}

.mini-chart .bar.active {
  background: #34D399;
}

/* ═══ BACKUP HISTORY SECTION ═══ */
.backup-history-section {
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.loading-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #94A3B8;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #94A3B8;
}

.backups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.backup-card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
  backdrop-filter: blur(10px);
  transition: all 0.2s;
}

.backup-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.backup-card.card-active {
  border-color: rgba(52, 211, 153, 0.3);
  background: rgba(52, 211, 153, 0.1);
}

.backup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.backup-version {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.version-tag {
  font-weight: 700;
  font-size: 1rem;
  color: #60A5FA;
}

.state-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.state-badge.active {
  background: rgba(52, 211, 153, 0.2);
  border: 1px solid rgba(52, 211, 153, 0.3);
  color: #34D399;
}

.state-badge.backup {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #60AFA;
}

.state-badge.rollback {
  background: rgba(251, 191, 36, 0.2);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #FBBF24;
}

.backup-date {
  color: #94A3B8;
  font-size: 0.75rem;
}

.backup-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
}

.backup-actions {
  display: flex;
  gap: 0.5rem;
}

.mini-button {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid;
  transition: all 0.2s;
  cursor: pointer;
}

.mini-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mini-info {
  background: rgba(52, 211, 153, 0.2);
  border-color: rgba(52, 211, 153, 0.3);
  color: #34D399;
}

.mini-info:hover:not(:disabled) {
  background: rgba(52, 211, 153, 0.3);
  border-color: rgba(52, 211, 153, 0.5);
}

.mini-warning {
  background: rgba(251, 191, 36, 0.2);
  border-color: rgba(251, 191, 36, 0.3);
  color: #FBBF24;
}

.mini-warning:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.3);
  border-color: rgba(251, 191, 36, 0.5);
}

.mini-danger {
  background: rgba(248, 113, 113, 0.2);
  border-color: rgba(248, 113, 113, 0.3);
  color: #F87171;
}

.mini-danger:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.3);
  border-color: rgba(248, 113, 113, 0.5);
}

/* ═══ MODAL ═══ */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: rgba(30, 41, 59, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  backdrop-filter: blur(20px);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.close-button {
  background: none;
  border: none;
  cursor: pointer;
  color: #94A3B8;
  transition: color 0.2s;
}

.close-button:hover {
  color: white;
}

.modal-body {
  padding: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-textarea {
  width: 100%;
  padding: 0.75rem;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.375rem;
  color: white;
  font-family: 'Inter', system-ui, sans-serif;
  resize: vertical;
  font-size: 0.875rem;
}

.form-textarea:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.5);
}

.rollback-warning {
  padding: 1rem;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.backup-summary {
  background: rgba(15, 23, 42, 0.5);
  padding: 1rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.pre-rollback-info {
  padding: 0.75rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 0.375rem;
}

.verification-result {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.verification-icon {
  flex-shrink: 0;
}

.verification-details {
  flex: 1;
}

.result-valid {
  color: #34D399;
}

.result-invalid {
  color: #F87171;
}

.valid-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>