<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Crosshair, Zap, ListOrdered, ArrowLeft } from '@lucide/vue'
import { api } from '@/lib/api'

const router = useRouter()
const url = ref('')
const title = ref('')
const notes = ref('')
const severity = ref('medium')
const category = ref('bug_bounty')
const capturing = ref(false)
const saved = ref<{ id: string; enrichment: Record<string, any> } | null>(null)
const error = ref('')

async function capture() {
  if (!url.value.trim()) return
  capturing.value = true
  error.value = ''
  try {
    const res = await api.post('/quick-capture', {
      url: url.value.trim(),
      title: title.value || undefined,
      category: category.value,
      severity: severity.value,
      notes: notes.value,
      source: 'manual',
    })
    saved.value = res
    url.value = ''
    title.value = ''
    notes.value = ''
  } catch (e: any) {
    error.value = e?.message || 'Capture failed'
  } finally {
    capturing.value = false
  }
}

async function queue(id: string) {
  try {
    await api.post(`/quick-capture/${id}/queue`)
  } catch (e: any) {
    error.value = e?.message || 'Queue failed'
  }
}

onMounted(() => {
  // Prefill URL from clipboard if present.
  navigator.clipboard
    ?.readText()
    .then((t) => {
      if (t && /^https?:\/\//.test(t)) url.value = t
    })
    .catch(() => {})
})
</script>

<template>
  <div class="qc-shell">
    <div class="qc-header">
      <button class="qc-back" @click="router.push('/')"><ArrowLeft :size="16" /> Atrás</button>
      <h1 class="qc-title"><Crosshair :size="18" /> QUICK CAPTURE</h1>
      <span class="qc-hint">Ctrl+Shift+O lo abre desde cualquier página · Ctrl+Shift+P muestra la próxima acción</span>
    </div>

    <form class="qc-form" @submit.prevent="capture">
      <label>
        <span class="qc-label">URL / Endpoint</span>
        <input v-model="url" required placeholder="https://target.com/api/users?id=1" autofocus />
      </label>
      <div class="qc-row">
        <label>
          <span class="qc-label">Título (opcional)</span>
          <input v-model="title" placeholder="IDOR en /api/users" />
        </label>
        <label>
          <span class="qc-label">Severidad</span>
          <select v-model="severity">
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </label>
        <label>
          <span class="qc-label">Categoría</span>
          <select v-model="category">
            <option value="bug_bounty">Bug Bounty</option>
            <option value="dev_bounty">Dev Bounty</option>
            <option value="security_research">Security Research</option>
            <option value="ai_evaluation">AI Evaluation</option>
          </select>
        </label>
      </div>
      <label>
        <span class="qc-label">Notas</span>
        <textarea v-model="notes" rows="3" placeholder="Parámetro numérico, respuesta con datos de otro usuario, etc."></textarea>
      </label>
      <p v-if="error" class="qc-error">{{ error }}</p>
      <button class="qc-submit" :disabled="capturing || !url.trim()">
        <Crosshair :size="16" /> {{ capturing ? 'Capturando…' : 'Capturar y enriquecer' }}
      </button>
    </form>

    <div v-if="saved" class="qc-result">
      <h2><Zap :size="16" /> Capturado</h2>
      <dl>
        <dt>Dominio</dt><dd>{{ saved.enrichment.domain }}</dd>
        <dt>Path</dt><dd>{{ saved.enrichment.path }}</dd>
        <dt>Platforma</dt><dd>{{ saved.enrichment.platform || 'desconocida' }}</dd>
        <dt>Requiere foco</dt><dd>{{ saved.enrichment.requires_focus ? 'sí' : 'no' }}</dd>
      </dl>
      <button class="qc-submit" @click="queue(saved.id)"><ListOrdered :size="16" /> Enviar al Work Bank</button>
    </div>
  </div>
</template>

<style scoped>
.qc-shell { max-width: 640px; margin: 2rem auto; padding: 0 1rem; font-family: 'JetBrains Mono', monospace; }
.qc-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; }
.qc-back { display: flex; align-items: center; gap: 0.35rem; background: transparent; border: 1px solid var(--ownex-stroke, #2a2e37); color: var(--ownex-text, #fff); padding: 0.4rem 0.7rem; border-radius: 8px; cursor: pointer; }
.qc-title { display: flex; align-items: center; gap: 0.5rem; font-size: 1.1rem; margin: 0; }
.qc-hint { font-size: 0.65rem; color: rgba(255,255,255,0.5); }
.qc-form { display: flex; flex-direction: column; gap: 1rem; background: rgba(255,255,255,0.03); border: 1px solid var(--ownex-stroke, #2a2e37); padding: 1.25rem; border-radius: 12px; }
.qc-label { display: block; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); margin-bottom: 0.3rem; }
input, select, textarea { width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--ownex-stroke, #2a2e37); color: #fff; border-radius: 8px; padding: 0.55rem 0.7rem; font-size: 0.85rem; }
.qc-row { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 0.75rem; }
.qc-submit { display: flex; align-items: center; justify-content: center; gap: 0.5rem; background: #00d5ff; color: #05060a; border: none; border-radius: 8px; padding: 0.65rem 1rem; font-weight: 600; cursor: pointer; }
.qc-submit:disabled { opacity: 0.5; cursor: default; }
.qc-error { color: #e82127; font-size: 0.75rem; }
.qc-result { margin-top: 1.5rem; background: rgba(0,213,255,0.05); border: 1px solid rgba(0,213,255,0.25); border-radius: 12px; padding: 1rem; }
.qc-result h2 { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; }
.qc-result dl { display: grid; grid-template-columns: 130px 1fr; gap: 0.3rem 0.75rem; font-size: 0.8rem; }
.qc-result dt { color: rgba(255,255,255,0.5); }
.qc-result dd { margin: 0; }
</style>