<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  listObsidianFiles, syncObsidianFile, deleteObsidianFile,
  syncObsidianFull, type ObsidianFile, type ObsidianSyncState,
} from '@/services/controlPanel'

const files = ref<ObsidianFile[]>([])
const loading = ref(true)
const busy = ref(false)
const lastSync = ref('')
const errors = ref<string[]>([])

async function load() {
  loading.value = true
  try {
    const res = await listObsidianFiles()
    files.value = res.files || []
    const state = res.state || {}
    if (state.last_sync) lastSync.value = state.last_sync
    errors.value = state.errors || []
  } catch (e) {
    errors.value.push(String(e))
  } finally {
    loading.value = false
  }
}

async function syncOne(fileId: string) {
  if (busy.value) return
  busy.value = true
  try {
    const res = await syncObsidianFile(fileId)
    if (res.success) {
      await load()
    }
  } catch (e) {
    errors.value.push(String(e))
  } finally {
    busy.value = false
  }
}

async function syncAll() {
  if (busy.value) return
  busy.value = true
  try {
    const res = await syncObsidianFull()
    if (res.success) {
      await load()
    }
  } finally {
    busy.value = false
  }
}

async function deleteOne(fileId: string) {
  if (busy.value) return
  busy.value = true
  try {
    const res = await deleteObsidianFile(fileId)
    if (res.success) {
      await load()
    }
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="obsidian">
    <div class="obsidian-head">
      <h3 class="obsidian-title">📝 Obsidian Sync (Real)</h3>
      <span class="obsidian-badge">{{ lastSync ? new Date(lastSync).toLocaleString() : '—' }}</span>
    </div>

    <p v-if="loading" class="obsidian-muted">Sincronizando...</p>

    <template v-else>
      <div v-if="!files.length" class="obsidian-empty">
        <span class="obsidian-missing-icon">📁</span>
        <p>No hay archivos sincronizados aún.</p>
        <p class="obsidian-hint">Usá `syncObsidianFile` para guardar markdown ↔ JSON.</p>
      </div>

      <template v-else>
        <div class="obsidian-list">
          <div v-for="f in files" :key="f.id" class="obsidian-card">
            <div class="obsidian-card-header">
              <span class="obsidian-file-name">{{ f.title }}</span>
              <span class="obsidian-tags" v-for="t in f.tags" :key="t">{{ t }}</span>
            </div>
            <div class="obsidian-card-meta">
              <span class="obsidian-size">🔤 {{ f.size }} bytes</span>
              <span class="obsidian-sha">sha256: {{ f.sha256 }}</span>
              <span class="obsidian-synced">🕐 {{ f.synced_at }}</span>
            </div>
            <div class="obsidian-card-body">
              <div class="obsidian-code">
                <pre>{{ f.content || '' }}</pre>
              </div>
              <div class="obsidian-actions">
                <button class="obsidian-btn sync" :disabled="busy" @click="syncOne(f.id)">
                  ⚡ Sincronizar
                </button>
                <button class="obsidian-btn del" :disabled="busy" @click="deleteOne(f.id)">
                  🗑️ Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div class="obsidian-actions-row">
        <button class="obsidian-btn" @click="syncAll" :disabled="busy">
          {{ busy ? 'Sincronizando...' : '🔄 Sincronizar todo' }}
        </button>
        <span v-if="errors.length" class="obsidian-errors" :class="{ error: errors.length > 0 }">
          {{ errors.length }} error(s)
        </span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.obsidian { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.obsidian-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.obsidian-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.obsidian-badge { font-size: 0.6rem; font-weight: 700; color: #93c5fd; background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.obsidian-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.obsidian-empty { display: flex; flex-direction: column; align-items: center; padding: 2rem 0; }
.obsidian-missing-icon { font-size: 3rem; opacity: 0.3; }
.obsidian-hint { font-size: 0.65rem; color: rgba(255,255,255,0.5); margin: 0.3rem 0 0; }
.obsidian-list { display: flex; flex-direction: column; gap: 0.6rem; }
.obsidian-card { border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.6rem 0.75rem; display: flex; flex-direction: column; gap: 0.35rem; transition: all 0.15s; }
.obsidian-card:hover { border-color: rgba(96,165,250,0.4); }
.obsidian-card-header { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
.obsidian-file-name { font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.9); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.obsidian-tags { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.obsidian-tag { font-size: 0.55rem; background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.2); color: #93c5fd; border-radius: 3px; padding: 0.1rem 0.3rem; }
.obsidian-card-meta { display: flex; gap: 0.8rem; font-size: 0.58rem; color: rgba(255,255,255,0.5); flex-wrap: wrap; }
.obsidian-code { background: rgba(0,0,0,0.4); border-radius: 8px; padding: 0.5rem; overflow-x: auto; font-size: 0.6rem; }
.obsidian-code pre { margin: 0; white-space: pre-wrap; font-family: monospace; color: #c0caf5; line-height: 1.5; }
.obsidian-actions { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.obsidian-btn { border: none; border-radius: 6px; padding: 0.25rem 0.5rem; font-size: 0.6rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.obsidian-btn.sync { background: rgba(22,163,74,0.15); border: 1px solid rgba(22,163,74,0.3); color: #4ade80; }
.obsidian-btn.sync:hover:not(:disabled) { background: rgba(22,163,74,0.25); }
.obsidian-btn.del { background: rgba(232,33,39,0.15); border: 1px solid rgba(232,33,39,0.3); color: #f87171; }
.obsidian-btn.del:hover:not(:disabled) { background: rgba(232,33,39,0.25); }
.obsidian-btn:disabled { opacity: 0.5; cursor: wait; }
.obsidian-errors { font-size: 0.6rem; color: #f87171; margin-left: 0.5rem; }
.obsidian-actions-row { display: flex; align-items: center; gap: 0.7rem; font-size: 0.6rem; color: rgba(255,255,255,0.4); }
.obsidian-actions-row .obsidian-btn { font-size: 0.58rem; }
</style>