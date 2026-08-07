<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getSkillMethod, setSkillTrack, registerSkillSession,
  type SkillMethodStatus, type SkillTrack,
} from '@/services/controlPanel'

const status = ref<SkillMethodStatus>({})
const loading = ref(true)
const busy = ref(false)
const note = ref('')
const form = ref({ track: 'web', type: 'writeup', title: '', notes: '' })
const showForm = ref(false)

const score = computed(() => status.value.score ?? 0)
const tracks = computed(() => status.value.tracks ?? [])
const currentTrack = computed(() => status.value.current_track ?? 'web')
const sessionTypes = computed(() => status.value.session_types ?? {})
const sessions = computed(() => status.value.sessions ?? [])

const activeTrack = computed(() => tracks.value.find(t => t.id === currentTrack.value))

async function load() {
  loading.value = true
  try {
    status.value = await getSkillMethod()
  } finally {
    loading.value = false
  }
}

async function selectTrack(t: SkillTrack) {
  await setSkillTrack(t.id)
  await load()
}

async function submitSession() {
  busy.value = true
  note.value = ''
  try {
    const res = await registerSkillSession(form.value.track, form.value.type, form.value.title, form.value.notes)
    if (res.success) {
      note.value = `Sesión registrada — skills completadas: ${res.completed}`
      form.value.title = ''
      form.value.notes = ''
      showForm.value = false
      await load()
    } else {
      note.value = 'No se pudo registrar la sesión.'
    }
  } catch {
    note.value = 'Error al registrar.'
  } finally {
    busy.value = false
  }
}

function trackPct(t: SkillTrack) {
  return Math.round((t.done / Math.max(1, t.total)) * 100)
}

onMounted(() => load())
</script>

<template>
  <section class="sm">
    <div class="sm-head">
      <h3 class="sm-title">SKILL METHOD · RUTA DEL 0,1%</h3>
      <span class="sm-badge">{{ status.done_skills }}/{{ status.total_skills }} skills</span>
    </div>

    <p v-if="loading" class="sm-muted">Cargando ruta de estudio...</p>

    <template v-else>
      <p class="sm-msg">{{ status.message }}</p>

      <div class="sm-score">
        <div class="sm-bar"><div class="sm-fill" :style="{ width: score + '%' }"></div></div>
        <span class="sm-pct">{{ score }}%</span>
      </div>

      <div class="sm-tracks">
        <button
          v-for="t in tracks"
          :key="t.id"
          class="sm-track"
          :class="{ active: t.id === currentTrack }"
          @click="selectTrack(t)"
        >
          <span class="sm-t-icon">{{ t.icon }}</span>
          <span class="sm-t-name">{{ t.name }}</span>
          <span class="sm-t-prog">{{ trackPct(t) }}%</span>
        </button>
      </div>

      <div v-if="activeTrack" class="sm-levels">
        <div v-for="lvl in activeTrack.levels" :key="lvl.id" class="sm-level">
          <div class="sm-l-head">
            <span class="sm-l-name">{{ lvl.name }}</span>
            <span class="sm-l-prog">{{ lvl.progress }}/{{ lvl.total }}</span>
          </div>
          <div class="sm-l-bar"><div class="sm-l-fill" :style="{ width: (lvl.progress / Math.max(1, lvl.total)) * 100 + '%' }"></div></div>
          <div class="sm-skills">
            <span
              v-for="s in lvl.skills"
              :key="s"
              class="sm-skill"
              :class="{ done: lvl.progress > lvl.total - 1 }"
            >{{ s }}</span>
          </div>
        </div>
      </div>

      <button class="sm-btn" @click="showForm = !showForm">
        {{ showForm ? 'Cerrar' : '+ Registrar sesión de evidencia' }}
      </button>

      <form v-if="showForm" class="sm-form" @submit.prevent="submitSession">
        <select v-model="form.track">
          <option v-for="t in tracks" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <select v-model="form.type">
          <option v-for="(desc, key) in sessionTypes" :key="key" :value="key">{{ key }} — {{ desc }}</option>
        </select>
        <input v-model="form.title" placeholder="Título (ej: Write-up IDOR en app de test)" required />
        <input v-model="form.notes" placeholder="Notas / link al write-up o lab" />
        <button class="sm-btn" :disabled="busy">Guardar sesión</button>
      </form>

      <p v-if="note" class="sm-note">{{ note }}</p>

      <div v-if="sessions.length" class="sm-sessions">
        <div v-for="s in sessions.slice().reverse()" :key="s.id" class="sm-session">
          <span class="sm-s-type">{{ s.type }}</span>
          <div class="sm-s-body">
            <span class="sm-s-title">{{ s.title }}</span>
            <span class="sm-s-meta">{{ s.track_name }} · {{ new Date(s.created_at).toLocaleDateString() }}</span>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.sm { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.sm-head { display: flex; align-items: center; gap: 0.7rem; }
.sm-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.sm-badge { margin-left: auto; font-size: 0.65rem; font-weight: 700; color: #a78bfa; background: rgba(167,139,250,0.12); border: 1px solid rgba(167,139,250,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.sm-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.sm-msg { font-size: 0.72rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }
.sm-score { display: flex; align-items: center; gap: 0.6rem; }
.sm-bar { flex: 1; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; }
.sm-fill { height: 100%; background: linear-gradient(90deg, #8b5cf6, #a78bfa); border-radius: 4px; transition: width 0.3s; }
.sm-pct { font-size: 0.7rem; font-weight: 700; color: #a78bfa; white-space: nowrap; }
.sm-tracks { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.sm-track { display: flex; align-items: center; gap: 0.4rem; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); border-radius: 8px; padding: 0.3rem 0.6rem; font-size: 0.65rem; color: rgba(255,255,255,0.7); cursor: pointer; }
.sm-track.active { border-color: rgba(167,139,250,0.5); background: rgba(167,139,250,0.12); color: #c4b5fd; }
.sm-t-icon { font-size: 0.8rem; }
.sm-t-prog { font-weight: 700; }
.sm-levels { display: flex; flex-direction: column; gap: 0.5rem; }
.sm-level { padding: 0.6rem; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; background: rgba(255,255,255,0.02); display: flex; flex-direction: column; gap: 0.35rem; }
.sm-l-head { display: flex; justify-content: space-between; font-size: 0.7rem; }
.sm-l-name { font-weight: 600; color: rgba(255,255,255,0.9); }
.sm-l-prog { color: rgba(255,255,255,0.5); }
.sm-l-bar { height: 5px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden; }
.sm-l-fill { height: 100%; background: linear-gradient(90deg, #f59e0b, #fbbf24); border-radius: 3px; }
.sm-skills { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.sm-skill { font-size: 0.6rem; color: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.08); padding: 0.15rem 0.4rem; border-radius: 4px; }
.sm-skill.done { color: #4ade80; border-color: rgba(74,222,128,0.3); }
.sm-btn { align-self: flex-start; border: 1px solid rgba(167,139,250,0.4); border-radius: 8px; background: rgba(167,139,250,0.1); color: #c4b5fd; font-size: 0.68rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer; }
.sm-btn:disabled { opacity: 0.4; cursor: default; }
.sm-form { display: flex; flex-direction: column; gap: 0.4rem; }
.sm-form select, .sm-form input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.45rem 0.6rem; color: rgba(255,255,255,0.9); font-size: 0.7rem; }
.sm-note { font-size: 0.68rem; color: #a78bfa; margin: 0; }
.sm-sessions { display: flex; flex-direction: column; gap: 0.35rem; }
.sm-session { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.6rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); }
.sm-s-type { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); padding: 0.1rem 0.35rem; border-radius: 4px; flex-shrink: 0; }
.sm-s-body { display: flex; flex-direction: column; min-width: 0; }
.sm-s-title { font-size: 0.68rem; color: rgba(255,255,255,0.9); font-weight: 600; }
.sm-s-meta { font-size: 0.6rem; color: rgba(255,255,255,0.45); }
</style>
