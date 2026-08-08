<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getSandboxState, submitSandboxBounty, resetSandbox,
  type SandboxBounty, type SandboxProgress,
} from '@/services/controlPanel'

const bounties = ref<SandboxBounty[]>([])
const progress = ref<SandboxProgress | null>(null)
const loading = ref(true)
const activeBounty = ref<SandboxBounty | null>(null)
const solution = ref('')
const solutionFiles = ref<Record<string, string>>({})
const submitting = ref(false)
const result = ref<{ approved: boolean; message: string } | null>(null)

async function load() {
  loading.value = true
  try {
    const state = await getSandboxState()
    bounties.value = state.bounties || []
    progress.value = state.progress || null
  } finally {
    loading.value = false
  }
}

function openBounty(b: SandboxBounty) {
  activeBounty.value = b
  solution.value = b.solution_template || ''
  solutionFiles.value = {}
  b.files_to_edit.forEach(f => { solutionFiles.value[f] = '' })
  result.value = null
}

async function submit() {
  if (!activeBounty.value || submitting.value) return
  submitting.value = true
  try {
    const res = await submitSandboxBounty(activeBounty.value.id, solution.value, solutionFiles.value)
    result.value = { approved: res.approved, message: res.message }
    await load()
  } finally {
    submitting.value = false
  }
}

async function doReset() {
  if (!confirm('¿Reiniciar todo el progreso sandbox?')) return
  await resetSandbox()
  await load()
  activeBounty.value = null
}

function difficultyColor(d: string) {
  return { trivial: '#4ade80', easy: '#93c5fd', medium: '#fbbf24', hard: '#f87171' }[d] || '#6b7280'
}

onMounted(load)
</script>

<template>
  <section class="sbx">
    <div class="sbx-head">
      <h3 class="sbx-title">🧪 SANDBOX MODE</h3>
      <span class="sbx-badge" v-if="progress">Completados: {{ progress.completed }}/{{ progress.total_bounties }} ({{ progress.completion_rate }}%)</span>
    </div>

    <p v-if="loading" class="sbx-muted">Cargando sandbox...</p>

    <template v-else>
      <p class="sbx-desc">
        Modo aprendizaje sin riesgos. Sin API keys, sin GitHub, sin dinero real.
        Resuelve bounties ficticias → aprende el flujo completo → gana confianza.
      </p>

      <!-- Progress -->
      <div class="sbx-progress" v-if="progress">
        <div class="sbx-bar"><div class="sbx-fill" :style="{ width: progress.completion_rate + '%' }"></div></div>
        <div class="sbx-stats">
          <span>💰 Recompensa simulada: <b>${{ progress.total_reward_usd }}</b></span>
          <span>📤 Submissions: {{ progress.submissions }}</span>
        </div>
      </div>

      <!-- Active Bounty Workspace -->
      <div v-if="activeBounty" class="sbx-workspace">
        <div class="sbx-workspace-head">
          <h4>{{ activeBounty.title }}</h4>
          <span class="sbx-diff" :style="{ background: difficultyColor(activeBounty.difficulty) }">{{ activeBounty.difficulty }}</span>
          <button class="sbx-close" @click="activeBounty = null">×</button>
        </div>

        <p class="sbx-task-desc">{{ activeBounty.description }}</p>

        <div class="sbx-files">
          <div v-for="fname in activeBounty.files_to_edit" :key="fname" class="sbx-file">
            <label>{{ fname }}</label>
            <textarea
              v-model="solutionFiles[fname]"
              placeholder="// Tu código aquí..."
              rows="8"
            />
          </div>
          <div class="sbx-file" v-if="!activeBounty.files_to_edit.length">
            <label>Solución (código principal)</label>
            <textarea v-model="solution" placeholder="// Tu solución aquí..." rows="12" />
          </div>
        </div>

        <div class="sbx-hint">
          <strong>Pista:</strong> {{ activeBounty.solution_template }}
        </div>

        <div class="sbx-test-instructions">
          <strong>Cómo testear:</strong> {{ activeBounty.test_instructions }}
        </div>

        <div class="sbx-actions">
          <button class="sbx-btn primary" :disabled="submitting" @click="submit">
            {{ submitting ? 'Validando...' : 'Enviar y Validar' }}
          </button>
        </div>

        <div v-if="result" class="sbx-result" :class="{ success: result.approved, fail: !result.approved }">
          {{ result.message }}
        </div>
      </div>

      <!-- Bounties List -->
      <div v-else class="sbx-list">
        <div v-for="b in bounties" :key="b.id" class="sbx-card" @click="openBounty(b)">
          <div class="sbx-card-main">
            <span class="sbx-card-title">{{ b.title }}</span>
            <span class="sbx-card-reward">${{ b.reward_usd }}</span>
          </div>
          <div class="sbx-card-meta">
            <span class="sbx-diff" :style="{ background: difficultyColor(b.difficulty) }">{{ b.difficulty }}</span>
            <span class="sbx-tags" v-for="t in b.tags" :key="t">{{ t }}</span>
            <span v-if="b.status === 'validated'" class="sbx-done">✅ Validada</span>
            <span v-else-if="b.status === 'submitted'" class="sbx-pending">⏳ Enviada</span>
          </div>
        </div>
      </div>

      <div class="sbx-footer">
        <button class="sbx-btn ghost" @click="doReset">🔄 Reiniciar Sandbox</button>
        <span class="sbx-hint-text">Progreso guardado en ~/.rastro/sandbox/</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.sbx { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.8rem; }
.sbx-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.sbx-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.sbx-badge { font-size: 0.6rem; font-weight: 700; color: #93c5fd; background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.sbx-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.sbx-desc { font-size: 0.72rem; color: rgba(255,255,255,0.75); margin: 0; line-height: 1.5; }
.sbx-progress { display: flex; flex-direction: column; gap: 0.4rem; }
.sbx-bar { height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.sbx-fill { height: 100%; background: linear-gradient(90deg, #16a34a, #4ade80); border-radius: 3px; transition: width 0.3s; }
.sbx-stats { display: flex; gap: 1rem; font-size: 0.65rem; color: rgba(255,255,255,0.6); }
.sbx-stats b { color: #4ade80; }

.sbx-workspace { border: 1px solid rgba(96,165,250,0.3); border-radius: 10px; background: rgba(96,165,250,0.04); padding: 0.8rem; display: flex; flex-direction: column; gap: 0.6rem; }
.sbx-workspace-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
.sbx-workspace-head h4 { margin: 0; font-size: 0.8rem; }
.sbx-diff { font-size: 0.55rem; font-weight: 700; color: #000; padding: 0.1rem 0.35rem; border-radius: 4px; text-transform: uppercase; }
.sbx-close { background: none; border: none; color: rgba(255,255,255,0.5); font-size: 1.2rem; cursor: pointer; padding: 0; line-height: 1; }
.sbx-close:hover { color: #fff; }
.sbx-task-desc { font-size: 0.7rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }
.sbx-files { display: flex; flex-direction: column; gap: 0.5rem; }
.sbx-file { display: flex; flex-direction: column; gap: 0.2rem; }
.sbx-file label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); }
.sbx-file textarea { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e5e7eb; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; padding: 0.5rem; resize: vertical; }
.sbx-file textarea:focus { outline: none; border-color: #60a5fa; }
.sbx-hint { font-size: 0.62rem; color: #fbbf24; background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.2); border-radius: 8px; padding: 0.5rem; white-space: pre-wrap; font-family: monospace; }
.sbx-test-instructions { font-size: 0.62rem; color: rgba(255,255,255,0.6); background: rgba(255,255,255,0.02); border-radius: 8px; padding: 0.5rem; }
.sbx-actions { display: flex; gap: 0.5rem; }
.sbx-btn { border: none; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.7rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.sbx-btn.primary { background: linear-gradient(135deg, #16a34a, #15803d); color: #fff; }
.sbx-btn.primary:hover:not(:disabled) { box-shadow: 0 0 12px 5px rgba(22,132,54,0.55); }
.sbx-btn.ghost { background: transparent; color: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.15); }
.sbx-btn.ghost:hover { color: #fff; border-color: rgba(255,255,255,0.3); }
.sbx-btn:disabled { opacity: 0.5; cursor: wait; }
.sbx-result { font-size: 0.7rem; padding: 0.5rem; border-radius: 8px; text-align: center; }
.sbx-result.success { background: rgba(22,163,74,0.2); border: 1px solid rgba(22,163,74,0.4); color: #4ade80; }
.sbx-result.fail { background: rgba(232,33,39,0.2); border: 1px solid rgba(232,33,39,0.4); color: #f87171; }

.sbx-list { display: flex; flex-direction: column; gap: 0.4rem; }
.sbx-card { border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 0.7rem; cursor: pointer; transition: all 0.15s; }
.sbx-card:hover { border-color: rgba(96,165,250,0.5); background: rgba(96,165,250,0.04); }
.sbx-card-main { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
.sbx-card-title { font-size: 0.72rem; font-weight: 600; color: rgba(255,255,255,0.9); }
.sbx-card-reward { font-size: 0.7rem; font-weight: 700; color: #4ade80; }
.sbx-card-meta { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.sbx-tags { font-size: 0.55rem; color: rgba(255,255,255,0.5); background: rgba(255,255,255,0.04); padding: 0.1rem 0.3rem; border-radius: 4px; }
.sbx-done { font-size: 0.55rem; color: #4ade80; }
.sbx-pending { font-size: 0.55rem; color: #fbbf24; }

.sbx-footer { display: flex; align-items: center; justify-content: space-between; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.06); }
.sbx-hint-text { font-size: 0.6rem; color: rgba(255,255,255,0.4); }
</style>