<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getDailyTasks, setDailyTaskStatus, advanceDailyTaskDay, type DailyTasksResult } from '@/services/controlPanel'

const board = ref<DailyTasksResult>({})
const loading = ref(true)
const busy = ref(false)
const note = ref('')

const day = computed(() => board.value.day ?? 1)
const tasks = computed(() => board.value.tasks ?? [])
const done = computed(() => board.value.done ?? 0)
const total = computed(() => board.value.total ?? 0)
const progress = computed(() => Math.round((done.value / Math.max(total.value, 1)) * 100))
const pct = computed(() => `${progress.value}%`)

async function load(force = false) {
  loading.value = true
  try {
    board.value = await getDailyTasks(force)
  } finally {
    loading.value = false
  }
}

async function toggle(t: { id: string; status?: string }) {
  const next = t.status === 'done' ? 'pending' : 'done'
  await setDailyTaskStatus(t.id, next)
  await load()
}

async function advance() {
  busy.value = true
  note.value = ''
  try {
    board.value = await advanceDailyTaskDay()
    note.value = `Avanzaste al día ${board.value.day}.`
  } catch {
    note.value = 'Error al avanzar de día.'
  } finally {
    busy.value = false
  }
}

function catColor(cat: string) {
  const map: Record<string, string> = { alta: '#e11d48', media: '#eab308', baja: '#16a34a' }
  return map[cat] || '#6b7280'
}

onMounted(() => load())
</script>

<template>
  <section class="dt">
    <div class="dt-head">
      <h3 class="dt-title">TAREAS DE HOY · DÍA {{ day }}</h3>
      <span class="dt-day-badge">Día {{ day }}</span>
    </div>

    <p v-if="loading" class="dt-muted">Armando tus tareas de hoy...</p>

    <template v-else>
      <p class="dt-msg">{{ board.message }}</p>

      <div class="dt-progress">
        <div class="dt-bar"><div class="dt-fill" :style="{ width: pct }"></div></div>
        <span class="dt-pct">{{ done }}/{{ total }} · {{ pct }}</span>
      </div>

      <div class="dt-list">
        <div
          v-for="t in tasks"
          :key="t.id"
          class="dt-task"
          :class="{ done: t.status === 'done' }"
        >
          <input
            type="checkbox"
            :checked="t.status === 'done'"
            @change="toggle(t)"
          />
          <div class="dt-body">
            <span class="dt-title" :title="t.detail">{{ t.title }}</span>
            <span v-if="t.detail" class="dt-detail">{{ t.detail }}</span>
          </div>
          <span v-if="t.cat" class="dt-cat" :style="{ background: catColor(t.cat) }">{{ t.cat }}</span>
        </div>
      </div>

      <p v-if="note" class="dt-note">{{ note }}</p>

      <button class="dt-advance" :disabled="busy" @click="advance">Avanzar al próximo día</button>
    </template>
  </section>
</template>

<style scoped>
.dt { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.6rem; }
.dt-head { display: flex; align-items: center; gap: 0.7rem; }
.dt-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.dt-day-badge { margin-left: auto; font-size: 0.65rem; font-weight: 700; color: #93c5fd; background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.dt-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.dt-msg { font-size: 0.72rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }
.dt-progress { display: flex; align-items: center; gap: 0.6rem; }
.dt-bar { flex: 1; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.dt-fill { height: 100%; background: linear-gradient(90deg, #16a34a, #4ade80); border-radius: 3px; transition: width 0.3s; }
.dt-pct { font-size: 0.65rem; color: rgba(255,255,255,0.6); white-space: nowrap; }
.dt-list { display: flex; flex-direction: column; gap: 0.35rem; }
.dt-task { display: flex; align-items: flex-start; gap: 0.55rem; padding: 0.5rem 0.6rem; background: rgba(255,255,255,0.02); border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); }
.dt-task.done { opacity: 0.55; }
.dt-task.done .dt-title { text-decoration: line-through; }
.dt-task input { accent-color: #4ade80; margin-top: 0.15rem; cursor: pointer; flex-shrink: 0; }
.dt-body { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; flex: 1; }
.dt-title { font-size: 0.72rem; color: rgba(255,255,255,0.9); font-weight: 600; line-height: 1.4; }
.dt-detail { font-size: 0.62rem; color: rgba(255,255,255,0.45); line-height: 1.4; }
.dt-cat { font-size: 0.55rem; font-weight: 700; color: #000; padding: 0.1rem 0.35rem; border-radius: 4px; text-transform: uppercase; flex-shrink: 0; margin-top: 0.1rem; }
.dt-note { font-size: 0.68rem; color: #93c5fd; margin: 0; }
.dt-advance { align-self: flex-end; border: 1px solid rgba(96,165,250,0.4); border-radius: 8px; background: rgba(96,165,250,0.1); color: #93c5fd; font-size: 0.68rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer; }
.dt-advance:disabled { opacity: 0.4; cursor: default; }
</style>