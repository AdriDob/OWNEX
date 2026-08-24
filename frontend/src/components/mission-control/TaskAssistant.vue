<script setup lang="ts">
import { ref } from 'vue'
import { analyzeTask, type TaskAssistantResult } from '@/services/controlPanel'

const task = ref('')
const loading = ref(false)
const result = ref<TaskAssistantResult | null>(null)
const errorMsg = ref('')

const hasInput = ref(false)

async function run() {
  if (!task.value.trim() || loading.value) return
  loading.value = true
  errorMsg.value = ''
  result.value = null
  try {
    result.value = await analyzeTask(task.value)
    if (!result.value.success) {
      errorMsg.value = result.value.error || 'No se pudo analizar.'
    }
  } catch {
    errorMsg.value = 'Error al conectar.'
  } finally {
    loading.value = false
  }
}

function clearAll() {
  task.value = ''
  result.value = null
  errorMsg.value = ''
}

function onInput() {
  hasInput.value = task.value.trim().length > 0
}
</script>

<template>
  <section class="ta">
    <div class="ta-head">
      <h3 class="ta-title">ASISTENTE DE TAREAS</h3>
      <span class="ta-hint">pega el enunciado → borrador técnico para trabajar</span>
    </div>

    <p class="ta-warn">
      Te ayuda a armar material de referencia, NO a copiar la respuesta final (evitá baneos). Reescribí con tu voz.
    </p>

    <textarea
      v-model="task"
      class="ta-input"
      placeholder="Pegá acá el enunciado de la tarea de Outlier/DA..."
      :disabled="loading"
      @input="onInput"
    />

    <div class="ta-actions">
      <button class="ta-btn on" :disabled="!hasInput || loading" @click="run">
        {{ loading ? 'Analizando...' : 'Analizar tarea' }}
      </button>
      <button v-if="result || errorMsg" class="ta-btn ghost" @click="clearAll">Limpiar</button>
    </div>

    <p v-if="errorMsg" class="ta-error">{{ errorMsg }}</p>

    <div v-if="result" class="ta-result">
      <div v-if="result.task_type" class="ta-meta">
        Tipo: {{ result.task_type }} · {{ result.words }} palabras
      </div>
      <div
        v-for="(section, i) in result.sections || []"
        :key="i"
        class="ta-section"
        :class="{ alert: section.title.toLowerCase().includes('pulir') }"
      >
        <div class="ta-section-title">{{ section.title }}</div>
        <pre class="ta-section-body">{{ section.body }}</pre>
      </div>
      <pre v-if="!result.sections?.length && result.response" class="ta-section-body">{{ result.response }}</pre>
    </div>
  </section>
</template>

<style scoped>
.ta {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.ta-head { display: flex; align-items: center; gap: 0.7rem; }
.ta-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.ta-hint { margin-left: auto; font-size: 0.6rem; color: rgba(255, 255, 255, 0.4); }
.ta-warn {
  font-size: 0.68rem; color: #fbbf24; margin: 0; line-height: 1.5;
  border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 8px;
  padding: 0.4rem 0.6rem; background: rgba(251, 191, 36, 0.05);
}
.ta-input {
  width: 100%; min-height: 90px; padding: 0.6rem;
  border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.04); color: #e5e7eb;
  font-size: 0.75rem; font-family: inherit; resize: vertical;
}
.ta-input::placeholder { color: rgba(255, 255, 255, 0.35); }
.ta-input:focus { outline: none; border-color: #4ade80; }
.ta-actions { display: flex; gap: 0.5rem; }
.ta-btn {
  border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px;
  background: rgba(255, 255, 255, 0.04); color: #e5e7eb;
  font-size: 0.72rem; font-weight: 600; padding: 0.4rem 0.8rem; cursor: pointer;
}
.ta-btn.on { border-color: rgba(22, 163, 74, 0.4); color: #4ade80; background: rgba(22, 163, 74, 0.1); }
.ta-btn.ghost { opacity: 0.7; }
.ta-btn:disabled { opacity: 0.4; cursor: default; }
.ta-error { font-size: 0.72rem; color: #94a3b8; margin: 0; }
.ta-result { display: flex; flex-direction: column; gap: 0.5rem; }
.ta-meta { font-size: 0.65rem; color: rgba(255, 255, 255, 0.5); }
.ta-section { border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 10px; overflow: hidden; }
.ta-section.alert { border-color: rgba(251, 191, 36, 0.3); }
.ta-section-title {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 0.4rem 0.6rem; background: rgba(255, 255, 255, 0.04);
}
.ta-section.alert .ta-section-title { color: #fbbf24; }
.ta-section-body {
  margin: 0; padding: 0.6rem; font-size: 0.7rem; line-height: 1.5;
  color: rgba(255, 255, 255, 0.85); white-space: pre-wrap; word-wrap: break-word;
  font-family: inherit;
}
</style>