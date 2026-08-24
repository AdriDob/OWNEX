<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  openDispute, listDisputes, checkH1Report,
  type DisputeItem,
} from '@/services/controlPanel'

const disputes = ref<DisputeItem[]>([])
const loading = ref(false)
const busy = ref(false)
const showOpen = ref(false)
const form = ref({
  platform: 'hackerone',
  finding_id: '',
  reason: '',
  platform_ref: '',
})
const result = ref<{ success: boolean; message: string } | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await listDisputes()
    disputes.value = res.items || []
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (busy.value || !form.value.finding_id || !form.value.reason) return
  busy.value = true
  try {
    const evidence = {
      finding_id: form.value.finding_id,
      reason: form.value.reason,
      timestamp: new Date().toISOString(),
    }
    const res = await openDispute(form.value.platform, form.value.finding_id, form.value.reason, evidence, form.value.platform_ref || undefined)
    result.value = { success: res.remote.success, message: res.remote.success ? `Disputa abierta: ${res.remote.dispute_id || res.local.dispute_id}` : res.remote.error || 'Error' }
    if (res.remote.success) {
      showOpen.value = false
      form.value = { platform: 'hackerone', finding_id: '', reason: '', platform_ref: '' }
      await load()
    }
  } finally {
    busy.value = false
  }
}

async function checkH1(dispute: DisputeItem) {
  const reportId = dispute.remote?.dispute_id || dispute.local?.finding_id
  if (!reportId) return
  try {
    const res = await checkH1Report(reportId)
    alert(`H1 Status: ${JSON.stringify(res.data, null, 2)}`)
  } catch (e) {
    alert('Error consultando H1: ' + (e as Error).message)
  }
}

onMounted(load)
</script>

<template>
  <section class="dsp">
    <div class="dsp-head">
      <h3 class="dsp-title">⚖️ AUTO-DISPUTE — Reclamos de pago</h3>
    </div>

    <p v-if="loading" class="dsp-muted">Cargando disputas...</p>

    <template v-else>
      <!-- Open new dispute -->
      <div v-if="showOpen" class="dsp-form">
        <h4>Abrir nueva disputa</h4>
        <div class="dsp-field">
          <label>Plataforma</label>
          <select v-model="form.platform" class="dsp-input">
            <option value="hackerone">HackerOne</option>
            <option value="gitcoin">Gitcoin</option>
          </select>
        </div>
        <div class="dsp-field">
          <label>Finding ID / Report ID</label>
          <input v-model="form.finding_id" class="dsp-input" placeholder="ej: 1234567" />
        </div>
        <div class="dsp-field">
          <label>Platform Ref (opcional)</label>
          <input v-model="form.platform_ref" class="dsp-input" placeholder="report_id (H1) o bounty_id (Gitcoin)" />
        </div>
        <div class="dsp-field">
          <label>Razón del reclamo</label>
          <textarea v-model="form.reason" class="dsp-input" rows="3" placeholder="Pago no recibido tras validación..." />
        </div>
        <div class="dsp-form-actions">
          <button class="dsp-btn primary" :disabled="busy" @click="submit">
            {{ busy ? 'Abriendo...' : 'Abrir disputa' }}
          </button>
          <button class="dsp-btn ghost" @click="showOpen = false">Cancelar</button>
        </div>
        <p v-if="result" class="dsp-result" :class="{ success: result.success, fail: !result.success }">{{ result.message }}</p>
      </div>

      <button v-else class="dsp-btn primary" @click="showOpen = true">+ Abrir disputa</button>

      <!-- List -->
      <div v-if="disputes.length" class="dsp-list">
        <h4 class="dsp-sub">Historial ({{ disputes.length }})</h4>
        <div v-for="d in disputes" :key="d.local?.dispute_id || d.remote?.dispute_id" class="dsp-item">
          <div class="dsp-item-main">
            <span class="dsp-platform" :class="d.local?.platform">{{ d.local?.platform || 'unknown' }}</span>
            <span class="dsp-id">{{ d.local?.dispute_id || d.remote?.dispute_id || '—' }}</span>
            <span class="dsp-status" :class="{ ok: d.local?.status === 'opened', err: d.local?.status === 'failed' }">
              {{ d.local?.status || 'unknown' }}
            </span>
          </div>
          <div class="dsp-item-meta">
            <span>Finding: {{ d.local?.finding_id }}</span>
            <span>{{ new Date(d.local?.created_at).toLocaleString() }}</span>
          </div>
          <div class="dsp-item-actions">
            <button class="dsp-btn small" @click="checkH1(d)" v-if="d.local?.platform === 'hackerone'">Check H1</button>
          </div>
        </div>
      </div>

      <p v-else class="dsp-muted">No hay disputas abiertas. Usá "Abrir disputa" si una plataforma no te pagó.</p>

      <!-- Config hint -->
      <div class="dsp-config-hint">
        <strong>Configuración requerida:</strong>
        <code>HACKERONE_API_USER</code>, <code>HACKERONE_API_TOKEN</code>, <code>GITCOIN_API_TOKEN</code> en .env
      </div>
    </template>
  </section>
</template>

<style scoped>
.dsp { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.dsp-head { display: flex; align-items: center; justify-content: space-between; }
.dsp-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.dsp-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.dsp-form { border: 1px solid rgba(96,165,250,0.3); border-radius: 10px; background: rgba(96,165,250,0.04); padding: 0.8rem; display: flex; flex-direction: column; gap: 0.5rem; }
.dsp-form h4 { margin: 0 0 0.5rem; font-size: 0.75rem; }
.dsp-field { display: flex; flex-direction: column; gap: 0.2rem; }
.dsp-field label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); }
.dsp-input { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e5e7eb; font-size: 0.7rem; padding: 0.4rem 0.6rem; }
.dsp-input:focus { outline: none; border-color: #60a5fa; }
.dsp-form-actions { display: flex; gap: 0.5rem; margin-top: 0.3rem; }
.dsp-btn { border: none; border-radius: 8px; padding: 0.45rem 0.8rem; font-size: 0.68rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.dsp-btn.primary { background: linear-gradient(135deg, #16a34a, #15803d); color: #fff; }
.dsp-btn.primary:hover:not(:disabled) { box-shadow: 0 0 10px 3px rgba(22,132,54,0.3); }
.dsp-btn.ghost { background: transparent; color: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.15); }
.dsp-btn.small { padding: 0.25rem 0.5rem; font-size: 0.6rem; }
.dsp-btn:disabled { opacity: 0.5; cursor: wait; }
.dsp-result { font-size: 0.7rem; padding: 0.5rem; border-radius: 8px; text-align: center; }
.dsp-result.success { background: rgba(22,163,74,0.2); border: 1px solid rgba(22,163,74,0.4); color: #4ade80; }
.dsp-result.fail { background: rgba(0,213,255,0.2); border: 1px solid rgba(0,213,255,0.4); color: #94a3b8; }
.dsp-list { display: flex; flex-direction: column; gap: 0.4rem; }
.dsp-sub { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); margin: 0; }
.dsp-item { border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.6rem; display: flex; flex-direction: column; gap: 0.35rem; }
.dsp-item-main { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.dsp-platform { font-size: 0.55rem; font-weight: 700; padding: 0.1rem 0.35rem; border-radius: 4px; text-transform: uppercase; }
.dsp-platform[hackerone] { background: rgba(255,100,0,0.2); border: 1px solid rgba(255,100,0,0.4); color: #ff8c42; }
.dsp-platform[gitcoin] { background: rgba(0,200,150,0.2); border: 1px solid rgba(0,200,150,0.4); color: #00e6b8; }
.dsp-id { font-family: monospace; font-size: 0.6rem; color: rgba(255,255,255,0.7); }
.dsp-status { font-size: 0.55rem; font-weight: 700; padding: 0.1rem 0.35rem; border-radius: 4px; }
.dsp-status.ok { background: rgba(22,163,74,0.2); color: #4ade80; }
.dsp-status.err { background: rgba(0,213,255,0.2); color: #94a3b8; }
.dsp-item-meta { display: flex; gap: 1rem; font-size: 0.6rem; color: rgba(255,255,255,0.5); }
.dsp-item-actions { display: flex; gap: 0.35rem; margin-top: 0.2rem; }
.dsp-config-hint { margin-top: 0.5rem; padding: 0.5rem; background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.2); border-radius: 8px; font-size: 0.6rem; color: #fbbf24; }
.dsp-config-hint code { background: rgba(0,0,0,0.3); padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.58rem; }
</style>