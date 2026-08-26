<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  AlertTriangle, Archive, Check, Database, FileText, FolderOpen,
  GitBranch, RefreshCw, Search, Shield, X,
} from '@lucide/vue'
import {
  connectVault, disconnectVault, scanVault, initializeVault, searchKnowledge,
  fetchKnowledgeHealth, fetchKnowledgeStatus, runKnowledgeSync, fetchGitStatus,
  commitVault, fetchSecurityScan, fetchSnapshots, createSnapshot,
  type KnowledgeHealth, type KnowledgeStatus, type KnowledgeSearchResult,
} from '@/services/knowledge'

const status = ref<KnowledgeStatus | null>(null)
const health = ref<KnowledgeHealth | null>(null)
const vaultPath = ref('')
const searchQuery = ref('')
const results = ref<KnowledgeSearchResult[]>([])
const searching = ref(false)
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const notice = ref('')
const selectedNote = ref<{ path: string; content: string } | null>(null)

const commitMessage = ref('')
const pendingDiff = ref<string[] | null>(null)
const snapshots = ref<string[]>([])

const isConnected = computed(() => !!status.value?.connected)

const indexStats = computed(() => health.value?.index ?? null)
const healthIssues = computed(() => health.value?.health ?? null)
const gitInfo = computed(() => health.value?.git ?? null)
const security = computed(() => health.value?.security ?? null)
const backupInfo = computed(() => health.value?.backups ?? null)

onMounted(loadAll)

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    status.value = await fetchKnowledgeStatus()
    if (status.value?.connected) {
      await Promise.all([loadHealth(), loadSnapshots()])
    }
  } catch {
    error.value = 'No se pudo conectar con el backend.'
  } finally {
    loading.value = false
  }
}

async function loadHealth() {
  health.value = await fetchKnowledgeHealth()
  if (health.value?.git) gitInfo.value = health.value.git
}

async function loadSnapshots() {
  const res = await fetchSnapshots()
  snapshots.value = res.snapshots ?? []
}

function showError(e: unknown) {
  const detail = (e as { detail?: string })?.detail
  error.value = typeof detail === 'string' ? detail : 'Operación fallida.'
}

async function runConnect() {
  if (!vaultPath.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    status.value = await connectVault(vaultPath.value.trim())
    await loadAll()
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}

async function runDisconnect() {
  busy.value = true
  try {
    status.value = await disconnectVault()
    health.value = null
    results.value = []
    snapshots.value = []
  } finally {
    busy.value = false
  }
}

async function runScan(full: boolean) {
  busy.value = true
  error.value = ''
  try {
    await scanVault(full)
    await loadHealth()
    notice.value = full ? 'Reindexado completo terminado.' : 'Escaneo incremental terminado.'
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}

async function runSync() {
  busy.value = true
  error.value = ''
  try {
    const res = await runKnowledgeSync()
    notice.value = res.ok ? 'Sincronización diaria ejecutada.' : res.reason ?? 'Sync fallido.'
    await loadHealth()
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q) return
  searching.value = true
  error.value = ''
  try {
    const res = await searchKnowledge(q)
    results.value = res.results ?? []
  } catch (e) {
    showError(e)
  } finally {
    searching.value = false
  }
}

async function openNote(path: string) {
  try {
    const { fetchNote } = await import('@/services/knowledge')
    const note = await fetchNote(path)
    selectedNote.value = { path: note.path, content: note.content }
  } catch {
    error.value = 'No se pudo abrir la nota.'
  }
}

async function runSecurityScan() {
  busy.value = true
  error.value = ''
  try {
    const res = await fetchSecurityScan()
    health.value = { ...(health.value ?? {}), security: res }
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}

async function previewCommit() {
  if (!commitMessage.value.trim()) return
  busy.value = true
  pendingDiff.value = null
  try {
    await commitVault(commitMessage.value.trim(), false)
  } catch (e) {
    const detail = (e as { detail?: { authorization_required?: boolean; pending?: string[] } })?.detail
    if (detail?.authorization_required) {
      pendingDiff.value = detail.pending ?? []
    } else {
      showError(e)
    }
  } finally {
    busy.value = false
  }
}

async function confirmCommit() {
  busy.value = true
  error.value = ''
  try {
    await commitVault(commitMessage.value.trim(), true)
    notice.value = 'Commit realizado.'
    pendingDiff.value = null
    commitMessage.value = ''
    await loadHealth()
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}

async function confirmSnapshot() {
  busy.value = true
  error.value = ''
  try {
    await createSnapshot(true)
    notice.value = 'Snapshot creado.'
    await loadSnapshots()
  } catch (e) {
    showError(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="kv">
    <header class="kv-head">
      <div>
        <h1 class="kv-title">KNOWLEDGE VAULT</h1>
        <p class="kv-sub">El vault de Obsidian como fuente de verdad. OWNEX lo indexa, busca y protege.</p>
      </div>
      <span class="kv-badge" :class="isConnected ? 'kv-badge-ok' : 'kv-badge-off'">
        {{ isConnected ? 'CONECTADO' : 'DESCONECTADO' }}
      </span>
    </header>

    <p v-if="loading" class="kv-muted">Cargando estado del vault...</p>

    <div v-if="error" class="kv-error">
      <AlertTriangle :size="14" /> {{ error }}
    </div>
    <div v-if="notice" class="kv-notice">
      <Check :size="14" /> {{ notice }}
    </div>

    <!-- Disconnected: connect card -->
    <section v-if="!loading && !isConnected" class="kv-card kv-connect">
      <h3 class="kv-card-title"><FolderOpen :size="15" /> Conectar vault</h3>
      <p class="kv-muted">Ruta local del vault de Obsidian, por ejemplo <code>~/Documents/Obsidian/Mi Vault</code></p>
      <div class="kv-row">
        <input
          v-model="vaultPath"
          class="kv-input"
          placeholder="/home/usuario/Obsidian/Vault"
          @keyup.enter="runConnect"
        />
        <button class="kv-btn kv-btn-primary" :disabled="busy || !vaultPath.trim()" @click="runConnect">
          {{ busy ? 'Conectando...' : 'Conectar' }}
        </button>
      </div>
    </section>

    <template v-else-if="isConnected">
      <!-- Vault info + actions -->
      <section class="kv-card">
        <div class="kv-card-head">
          <h3 class="kv-card-title"><Database :size="15" /> Vault</h3>
          <div class="kv-row">
            <button class="kv-btn" :disabled="busy" @click="runScan(false)">Scan incremental</button>
            <button class="kv-btn" :disabled="busy" @click="runScan(true)">Reindexar</button>
            <button class="kv-btn" :disabled="busy" @click="runSync">Sync diario</button>
            <button class="kv-btn kv-btn-danger" :disabled="busy" @click="runDisconnect">Desconectar</button>
          </div>
        </div>
        <div class="kv-grid kv-grid-4">
          <div class="kv-stat">
            <span class="kv-stat-label">Archivos</span>
            <span class="kv-stat-value">{{ health?.vault?.files ?? 0 }}</span>
          </div>
          <div class="kv-stat">
            <span class="kv-stat-label">Markdown</span>
            <span class="kv-stat-value">{{ health?.vault?.markdown ?? 0 }}</span>
          </div>
          <div class="kv-stat">
            <span class="kv-stat-label">Adjuntos</span>
            <span class="kv-stat-value">{{ health?.vault?.attachments ?? 0 }}</span>
          </div>
          <div class="kv-stat">
            <span class="kv-stat-label">Índice</span>
            <span class="kv-stat-value" :class="health?.vault?.index_healthy ? 'kv-ok' : 'kv-warn'">
              {{ health?.vault?.index_healthy ? 'sano' : 'incompleto' }}
            </span>
          </div>
        </div>
        <p class="kv-muted kv-path">{{ health?.vault?.path ?? status?.vault_path }}</p>
        <p v-if="health?.vault?.last_scan" class="kv-muted">
          Último escaneo: {{ new Date(health.vault.last_scan).toLocaleString() }}
        </p>
      </section>

      <!-- Search -->
      <section class="kv-card">
        <h3 class="kv-card-title"><Search :size="15" /> Búsqueda híbrida</h3>
        <div class="kv-row">
          <input
            v-model="searchQuery"
            class="kv-input"
            placeholder="Buscar en el vault (títulos, tags, links, texto, semántica)..."
            @keyup.enter="runSearch"
          />
          <button class="kv-btn kv-btn-primary" :disabled="searching || !searchQuery.trim()" @click="runSearch">
            {{ searching ? 'Buscando...' : 'Buscar' }}
          </button>
        </div>
        <ul v-if="results.length" class="kv-list">
          <li v-for="r in results" :key="r.path" class="kv-result" @click="openNote(r.path)">
            <div class="kv-result-head">
              <FileText :size="13" />
              <span class="kv-result-title">{{ r.title || r.path }}</span>
              <span class="kv-result-score">{{ Math.round(r.relevance * 100) }}%</span>
            </div>
            <p class="kv-result-snippet">{{ r.snippet }}</p>
            <div class="kv-result-meta">
              <span v-for="t in r.tags" :key="t" class="kv-tag">#{{ t }}</span>
              <span class="kv-muted">{{ r.path }}</span>
            </div>
          </li>
        </ul>
        <p v-else-if="searchQuery && !searching" class="kv-muted">Sin resultados para "{{ searchQuery }}".</p>
      </section>

      <!-- Note modal -->
      <div v-if="selectedNote" class="kv-modal" @click.self="selectedNote = null">
        <div class="kv-modal-card">
          <div class="kv-modal-head">
            <span class="kv-result-title">{{ selectedNote.path }}</span>
            <button class="kv-btn kv-btn-ghost" @click="selectedNote = null"><X :size="14" /></button>
          </div>
          <pre class="kv-note">{{ selectedNote.content }}</pre>
        </div>
      </div>

      <!-- Health -->
      <section class="kv-card">
        <h3 class="kv-card-title"><Shield :size="15" /> Salud del conocimiento</h3>
        <div class="kv-grid kv-grid-3">
          <div class="kv-box">
            <span class="kv-stat-label">Notas indexadas</span>
            <span class="kv-stat-value">{{ indexStats?.notes ?? 0 }}</span>
            <span class="kv-stat-label">Tags · {{ indexStats?.distinct_tags ?? 0 }} · Links · {{ indexStats?.links ?? 0 }}</span>
          </div>
          <div class="kv-box">
            <span class="kv-stat-label">Broken links</span>
            <span class="kv-stat-value" :class="(healthIssues?.broken_links ?? 0) ? 'kv-warn' : 'kv-ok'">
              {{ healthIssues?.broken_links ?? 0 }}
            </span>
            <ul v-if="healthIssues?.broken_link_items?.length" class="kv-mini-list">
              <li v-for="(b, i) in healthIssues.broken_link_items" :key="i">{{ b.from }} → {{ b.to }}</li>
            </ul>
          </div>
          <div class="kv-box">
            <span class="kv-stat-label">Duplicados / adjuntos faltantes</span>
            <span class="kv-stat-value">
              <span class="kv-warn">{{ healthIssues?.duplicate_notes ?? 0 }}</span>
              / <span class="kv-warn">{{ healthIssues?.missing_attachments ?? 0 }}</span>
            </span>
            <ul v-if="healthIssues?.duplicate_items?.length" class="kv-mini-list">
              <li v-for="(d, i) in healthIssues.duplicate_items" :key="i">{{ (d.paths ?? []).join(' = ') }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Git + Security + Backups -->
      <section class="kv-card">
        <h3 class="kv-card-title"><GitBranch :size="15" /> Git, seguridad y backups</h3>
        <div class="kv-grid kv-grid-3">
          <div class="kv-box">
            <div class="kv-box-head">
              <span class="kv-stat-label">Git</span>
              <span class="kv-muted">{{ gitInfo?.is_repo ? gitInfo.branch : 'sin repo' }}</span>
            </div>
            <p class="kv-stat-value">{{ gitInfo?.dirty_files ?? 0 }} archivos sin commit</p>
            <p v-if="gitInfo?.last_commit" class="kv-muted">{{ gitInfo.last_commit }}</p>
            <div v-if="gitInfo?.is_repo" class="kv-box-actions">
              <input v-model="commitMessage" class="kv-input" placeholder="Mensaje de commit" />
              <button class="kv-btn kv-btn-primary" :disabled="busy || !commitMessage.trim()" @click="previewCommit">
                Commit
              </button>
            </div>
            <div v-if="pendingDiff" class="kv-box">
              <p class="kv-stat-label">Archivos pendientes (requiere confirmación)</p>
              <ul class="kv-mini-list">
                <li v-for="(f, i) in pendingDiff" :key="i">{{ f }}</li>
              </ul>
              <button class="kv-btn kv-btn-danger" :disabled="busy" @click="confirmCommit">Confirmar commit</button>
            </div>
          </div>

          <div class="kv-box">
            <div class="kv-box-head">
              <span class="kv-stat-label">Secretos</span>
              <button class="kv-btn kv-btn-ghost" :disabled="busy" @click="runSecurityScan">Escanear</button>
            </div>
            <p class="kv-stat-value" :class="security?.clean ? 'kv-ok' : 'kv-warn'">
              {{ security?.clean ? 'Limpio' : `${security?.findings?.length ?? 0} hallazgos` }}
            </p>
            <ul v-if="security?.findings?.length" class="kv-mini-list">
              <li v-for="(f, i) in security.findings" :key="i">
                {{ f.kind }} · {{ f.file }}:{{ f.line }}
              </li>
            </ul>
          </div>

          <div class="kv-box">
            <div class="kv-box-head">
              <span class="kv-stat-label">Backups (keep 10)</span>
              <button class="kv-btn kv-btn-ghost" :disabled="busy" @click="confirmSnapshot">Crear snapshot</button>
            </div>
            <p class="kv-stat-value">{{ backupInfo?.count ?? 0 }} snapshots</p>
            <p v-if="backupInfo?.last" class="kv-muted">{{ backupInfo.last.name }}</p>
            <ul v-if="snapshots.length" class="kv-mini-list">
              <li v-for="s in snapshots.slice(0, 10)" :key="s"><Archive :size="12" /> {{ s }}</li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.kv {
  padding: 24px;
  color: #f5f5f5;
  font-family: 'Inter', system-ui, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
}

.kv-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

.kv-title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.04em;
  margin: 0;
}

.kv-sub {
  color: #8a8a8a;
  font-size: 13px;
  margin: 6px 0 0;
}

.kv-badge {
  font-size: 11px;
  letter-spacing: 0.12em;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #2e2e2e;
  white-space: nowrap;
}

.kv-badge-ok {
  color: #16a34a;
  border-color: rgba(22, 163, 74, 0.4);
}

.kv-badge-off {
  color: #8a8a8a;
}

.kv-card {
  background: #0a0a0a;
  border: 1px solid #1f1f1f;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.kv-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.kv-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  margin: 0 0 14px;
  color: #f5f5f5;
}

.kv-connect {
  max-width: 560px;
}

.kv-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.kv-input {
  flex: 1;
  min-width: 220px;
  background: #050505;
  border: 1px solid #2e2e2e;
  border-radius: 8px;
  color: #f5f5f5;
  padding: 9px 12px;
  font-size: 13px;
  outline: none;
}

.kv-input:focus {
  border-color: #f5f5f5;
}

.kv-btn {
  background: transparent;
  color: #f5f5f5;
  border: 1px solid #2e2e2e;
  border-radius: 8px;
  padding: 9px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: background 120ms;
  white-space: nowrap;
}

.kv-btn:hover:not(:disabled) {
  background: #141414;
}

.kv-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.kv-btn-primary {
  background: #ffffff;
  color: #000000;
  border-color: #ffffff;
}

.kv-btn-primary:hover:not(:disabled) {
  background: #e5e5e5;
}

.kv-btn-danger {
  border-color: rgba(0, 213, 255, 0.5);
  color: #00d5ff;
}

.kv-btn-ghost {
  border: none;
  padding: 2px 8px;
  font-size: 12px;
  color: #8a8a8a;
}

.kv-grid {
  display: grid;
  gap: 14px;
}

.kv-grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.kv-grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

.kv-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kv-stat-label {
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #6b6b6b;
  text-transform: uppercase;
}

.kv-stat-value {
  font-size: 22px;
  font-weight: 500;
  margin: 2px 0;
}

.kv-ok {
  color: #16a34a;
}

.kv-warn {
  color: #d97706;
}

.kv-muted {
  color: #6b6b6b;
  font-size: 12px;
  margin: 4px 0;
}

.kv-path {
  margin-top: 12px;
  font-family: 'JetBrains Mono', monospace;
}

.kv-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #00d5ff;
  background: rgba(0, 213, 255, 0.08);
  border: 1px solid rgba(0, 213, 255, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  margin-bottom: 14px;
}

.kv-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
  border: 1px solid rgba(22, 163, 74, 0.3);
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  margin-bottom: 14px;
}

.kv-list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kv-result {
  border: 1px solid #1f1f1f;
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background 120ms;
}

.kv-result:hover {
  background: #141414;
}

.kv-result-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kv-result-title {
  font-size: 14px;
  font-weight: 500;
}

.kv-result-score {
  margin-left: auto;
  font-size: 12px;
  color: #8a8a8a;
}

.kv-result-snippet {
  color: #8a8a8a;
  font-size: 12px;
  margin: 6px 0;
  line-height: 1.5;
}

.kv-result-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.kv-tag {
  color: #d4d4d8;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 8px;
  border-radius: 999px;
}

.kv-box {
  border: 1px solid #1f1f1f;
  border-radius: 10px;
  padding: 14px;
}

.kv-box-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.kv-box-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.kv-mini-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  font-size: 12px;
  color: #8a8a8a;
  max-height: 160px;
  overflow-y: auto;
}

.kv-mini-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.kv-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 50;
}

.kv-modal-card {
  background: #0a0a0a;
  border: 1px solid #2e2e2e;
  border-radius: 12px;
  max-width: 760px;
  width: 100%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kv-modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #1f1f1f;
}

.kv-note {
  margin: 0;
  padding: 18px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d8;
  white-space: pre-wrap;
  font-family: 'JetBrains Mono', monospace;
}

code {
  color: #f5f5f5;
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .kv-grid-3,
  .kv-grid-4 {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 560px) {
  .kv-grid-3,
  .kv-grid-4 {
    grid-template-columns: 1fr;
  }
}
</style>
