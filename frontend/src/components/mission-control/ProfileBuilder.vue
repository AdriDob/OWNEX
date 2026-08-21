<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getProfileBuilderStatus, linkProfileBuilder, auditProfileBuilder,
  generateProfileReadme, setProfilePortfolioRepo, setProfileAutoPush,
  type ProfileBuilderStatus, type ProfileBuilderReadme,
} from '@/services/controlPanel'

const status = ref<ProfileBuilderStatus | null>(null)
const loading = ref(true)
const busyId = ref('')
const readmeModal = ref(false)
const readmeContent = ref('')
const readmeCopied = ref(false)
const portfolioRepo = ref('')
const autoPushNote = ref('')
const linkUser = ref('')

const isLinked = computed(() => status.value?.linked)
const score = computed(() => status.value?.score ?? 0)
const username = computed(() => status.value?.username ?? '')
const hasToken = computed(() => status.value?.has_token)
const autoPush = computed(() => status.value?.auto_push)
const recommendations = computed(() => status.value?.recommendations ?? [])
const contributions = computed(() => status.value?.contributions ?? [])

async function load() {
  loading.value = true
  try {
    const s = await getProfileBuilderStatus()
    status.value = s
    portfolioRepo.value = s.portfolio_repo || ''
  } finally {
    loading.value = false
  }
}

async function doLink() {
  busyId.value = 'link'
  try {
    const s = await linkProfileBuilder(linkUser.value)
    status.value = s
  } finally {
    busyId.value = ''
  }
}

async function doAudit() {
  busyId.value = 'audit'
  try {
    const s = await auditProfileBuilder()
    status.value = s
  } finally {
    busyId.value = ''
  }
}

async function savePortfolioRepo() {
  busyId.value = 'repo'
  autoPushNote.value = ''
  try {
    const r = await setProfilePortfolioRepo(portfolioRepo.value)
    autoPushNote.value = r.success === false ? (r.message || 'Repo inválido') : `Repo portfolio guardado: ${portfolioRepo.value}`
    await load()
  } finally {
    busyId.value = ''
  }
}

async function toggleAutoPush(enabled: boolean) {
  busyId.value = 'push'
  try {
    const r = await setProfileAutoPush(enabled)
    autoPushNote.value = r.success === false
      ? 'No se pudo activar.'
      : enabled ? 'Auto-push ACTIVADO: cada bounty validado se sube solo a tu repo portfolio.' : 'Auto-push desactivado.'
    await load()
  } finally {
    busyId.value = ''
  }
}

async function doReadme() {
  busyId.value = 'readme'
  try {
    const r = await generateProfileReadme() as ProfileBuilderReadme
    if (r.success && r.readme) {
      readmeContent.value = r.readme
      readmeModal.value = true
    }
  } finally {
    busyId.value = ''
  }
}

function copyReadme() {
  navigator.clipboard.writeText(readmeContent.value)
  readmeCopied.value = true
  setTimeout(() => { readmeCopied.value = false }, 1500)
}

const scoreColor = computed(() => {
  const s = score.value
  if (s >= 70) return '#16a34a'
  if (s >= 40) return '#eab308'
  return '#e11d48'
})

function getMax(key: string) {
  const map: Record<string, number> = { readme: 25, avatar_bio: 15, pinned_repos: 20, public_repos: 10, contributions: 15, historial: 15 }
  return map[key] ?? 0
}

function priorityStyle(p: string) {
  const map: Record<string, string> = { alta: 'background:#e11d48', media: 'background:#eab308', baja: 'background:#16a34a' }
  return map[p] || ''
}

function formatDate(iso: string) {
  try { return new Date(iso).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) } catch { return iso }
}

onMounted(load)
</script>

<template>
  <section class="pb">
    <div class="pb-head">
      <h3 class="pb-title">GITHUB PROFILE BUILDER</h3>
      <span
        v-if="status"
        class="pb-badge"
        :style="{ color: isLinked ? '#16a34a' : '#6b7280' }"
      >
        {{ isLinked ? 'VINCULADO' : 'SIN VINCULAR' }}
      </span>
    </div>

    <p v-if="loading" class="pb-muted">Cargando perfil...</p>

    <template v-else>
      <p class="pb-desc">
        Vinculá tu GitHub a OWNEX. Cada bounty que validés se registra como contribución real,
        y con el auto-push se sube solo a tu repo portfolio. Tu perfil se construye solo.
      </p>

      <!-- No vinculado -->
      <div v-if="!isLinked" class="pb-link">
        <input
          v-model="linkUser"
          placeholder="Tu usuario de GitHub (ej. octocat)"
          class="pb-input"
          :disabled="!!busyId"
        />
        <button class="pb-btn ok" :disabled="!linkUser || !!busyId" @click="doLink">
          Vincular GitHub
        </button>
      </div>

      <!-- Vinculado -->
      <div v-else class="pb-score">
        <div class="pb-score-row">
          <div class="pb-score-ring">
            <span class="pb-score-num" :style="{ color: scoreColor }">{{ score }}</span>
            <span class="pb-score-label">/ 100</span>
          </div>
          <div class="pb-meta">
            <span class="pb-user">@{{ username }}</span>
            <span class="pb-token" :style="{ color: hasToken ? '#16a34a' : '#e11d48' }">
              {{ hasToken ? 'Token OK' : 'Sin GITHUB_TOKEN' }}
            </span>
          </div>
        </div>

        <div class="pb-actions">
          <button class="pb-btn run" :disabled="!!busyId" @click="doAudit">Re-auditar</button>
          <button class="pb-btn run" :disabled="!!busyId" @click="doReadme">Generar README</button>
        </div>

        <!-- Auto-push a repo portfolio -->
        <div class="pb-push">
          <span class="pb-label">AUTO-PUSH A REPO PORTFOLIO</span>
          <div class="pb-push-row">
            <input
              v-model="portfolioRepo"
              placeholder="usuario/repo (ej. adri/bounty-portfolio)"
              class="pb-input"
              :disabled="!!busyId"
            />
            <button class="pb-btn run" :disabled="!!busyId || !portfolioRepo" @click="savePortfolioRepo">
              Guardar repo
            </button>
          </div>
          <label class="pb-toggle">
            <input
              type="checkbox"
              :checked="autoPush"
              :disabled="!!busyId || !status?.portfolio_repo"
              @change="toggleAutoPush(($event.target as HTMLInputElement).checked)"
            />
            <span>
              Auto-subir cada bounty validado a <b>{{ status?.portfolio_repo || '—' }}</b>
            </span>
          </label>
          <p v-if="autoPushNote" class="pb-note">{{ autoPushNote }}</p>
          <p v-if="!hasToken" class="pb-push-warn">⚠️ Para auto-push necesitás GITHUB_TOKEN con scope <b>repo</b> en vault/.env.</p>
        </div>

        <!-- Desglose score -->
        <details class="pb-breakdown" open>
          <summary>Desglose del score</summary>
          <div class="pb-breakdown-grid" v-if="status?.score_detail">
            <div
              v-for="(detail, key) in status.score_detail"
              :key="key"
              class="pb-breakdown-item"
            >
              <span class="pb-breakdown-name">{{ key }}</span>
              <span class="pb-breakdown-pts" :style="{ color: detail.points > 0 ? '#16a34a' : '#e11d48' }">
                {{ detail.points }} / {{ getMax(key) }}
              </span>
              <div class="pb-bar">
                <div
                  class="pb-bar-fill"
                  :style="{
                    width: Math.min(100, (detail.points / getMax(key)) * 100) + '%',
                    background: detail.points > 0 ? '#16a34a' : '#e11d48',
                  }"
                ></div>
              </div>
            </div>
          </div>
        </details>

        <!-- Recomendaciones -->
        <div class="pb-recs">
          <div class="pb-rec" v-for="r in recommendations" :key="r.action">
            <span class="pb-rec-pri" :style="priorityStyle(r.priority)">{{ r.priority.toUpperCase() }}</span>
            <span class="pb-rec-action">{{ r.action }}</span>
            <span class="pb-rec-why">{{ r.why }}</span>
          </div>
        </div>

        <!-- Contribuciones recientes -->
        <details class="pb-contribs" open>
          <summary>Contribuciones registradas ({{ contributions.length }})</summary>
          <div v-if="contributions.length" class="pb-contrib-list">
            <div v-for="c in contributions" :key="c.created_at" class="pb-contrib">
              <span class="pb-contrib-kind">{{ c.kind }}</span>
              <span class="pb-contrib-title">{{ c.title }}</span>
              <span
                v-if="c.push"
                class="pb-contrib-push"
                :style="{ color: c.push.success ? '#4ade80' : '#f87171' }"
              >
                {{ c.push.success ? `push ${c.push.commit}` : c.push.message }}
              </span>
              <span class="pb-contrib-date">{{ formatDate(c.created_at) }}</span>
            </div>
          </div>
          <p v-else class="pb-muted">Sin contribuciones aún — validá tu primer bounty.</p>
        </details>
      </div>
    </template>

    <!-- Modal README -->
    <div v-if="readmeModal" class="pb-modal-backdrop" @click.self="readmeModal = false">
      <div class="pb-modal">
        <div class="pb-modal-head">
          <h4>README.md de tu perfil (listo para copiar)</h4>
          <button class="pb-modal-close" @click="readmeModal = false">✕</button>
        </div>
        <pre class="pb-modal-body">{{ readmeContent }}</pre>
        <div class="pb-modal-foot">
          <button class="pb-btn ok" @click="copyReadme">{{ readmeCopied ? '¡Copiado!' : 'Copiar al portapapeles' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.pb { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.6rem; }
.pb-head { display: flex; align-items: center; gap: 0.7rem; }
.pb-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.pb-badge { margin-left: auto; font-size: 0.6rem; font-weight: 700; }
.pb-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.pb-desc { font-size: 0.72rem; color: rgba(255,255,255,0.75); margin: 0; line-height: 1.5; }
.pb-link { display: flex; gap: 0.5rem; }
.pb-input { flex: 1; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; background: rgba(255,255,255,0.04); color: #e5e7eb; font-size: 0.72rem; padding: 0.4rem 0.7rem; min-width: 0; }
.pb-btn { border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; background: rgba(255,255,255,0.04); color: #e5e7eb; font-size: 0.72rem; font-weight: 600; padding: 0.4rem 0.7rem; cursor: pointer; white-space: nowrap; }
.pb-btn.ok { border-color: rgba(22,163,74,0.4); color: #4ade80; background: rgba(22,163,74,0.1); }
.pb-btn.run { border-color: rgba(96,165,250,0.4); color: #93c5fd; background: rgba(96,165,250,0.1); }
.pb-btn:disabled { opacity: 0.4; cursor: default; }
.pb-score { display: flex; flex-direction: column; gap: 0.5rem; }
.pb-score-row { display: flex; align-items: center; gap: 1rem; }
.pb-score-ring { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 72px; height: 72px; border-radius: 50%; background: conic-gradient(#16a34a calc(var(--score) * 3.6deg), rgba(255,255,255,0.08) 0deg); position: relative; flex-shrink: 0; }
.pb-score-ring::before { content: ''; position: absolute; inset: 4px; border-radius: 50%; background: var(--ownex-surface, #111318); }
.pb-score-num { position: relative; font-size: 1.1rem; font-weight: 700; }
.pb-score-label { position: relative; font-size: 0.6rem; color: rgba(255,255,255,0.4); }
.pb-meta { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.68rem; color: rgba(255,255,255,0.5); }
.pb-user { font-weight: 700; color: #fff; }
.pb-token { font-weight: 500; }
.pb-actions { display: flex; gap: 0.5rem; }
.pb-push { display: flex; flex-direction: column; gap: 0.4rem; border: 1px solid rgba(22,163,74,0.25); border-radius: 10px; padding: 0.6rem; background: rgba(22,163,74,0.04); }
.pb-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); }
.pb-push-row { display: flex; gap: 0.4rem; }
.pb-toggle { display: flex; align-items: center; gap: 0.45rem; font-size: 0.68rem; color: rgba(255,255,255,0.7); cursor: pointer; }
.pb-toggle input { accent-color: #4ade80; cursor: pointer; }
.pb-toggle b { color: #4ade80; }
.pb-note { font-size: 0.68rem; color: #93c5fd; margin: 0; }
.pb-push-warn { font-size: 0.62rem; color: #fbbf24; margin: 0; }
.pb-breakdown summary { cursor: pointer; font-size: 0.7rem; color: rgba(255,255,255,0.6); }
.pb-breakdown-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.4rem; margin-top: 0.4rem; }
.pb-breakdown-item { display: flex; flex-direction: column; gap: 0.15rem; font-size: 0.6rem; }
.pb-breakdown-name { text-transform: capitalize; color: rgba(255,255,255,0.5); }
.pb-breakdown-pts { font-weight: 600; font-size: 0.65rem; }
.pb-bar { height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden; }
.pb-bar-fill { height: 100%; transition: width 0.3s; }
.pb-recs { display: flex; flex-direction: column; gap: 0.35rem; }
.pb-rec { display: flex; gap: 0.5rem; align-items: flex-start; font-size: 0.65rem; padding: 0.4rem 0.5rem; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid #4ade80; }
.pb-rec-pri { font-weight: 700; font-size: 0.55rem; padding: 0.1rem 0.3rem; border-radius: 4px; color: #000; text-transform: uppercase; flex-shrink: 0; margin-top: 0.1rem; }
.pb-rec-action { font-weight: 600; color: #fff; flex: 1; }
.pb-rec-why { color: rgba(255,255,255,0.5); font-size: 0.6rem; }
.pb-contribs summary { cursor: pointer; font-size: 0.7rem; color: rgba(255,255,255,0.6); }
.pb-contrib-list { display: flex; flex-direction: column; gap: 0.3rem; margin-top: 0.3rem; }
.pb-contrib { display: flex; gap: 0.5rem; font-size: 0.6rem; padding: 0.3rem 0.4rem; background: rgba(255,255,255,0.02); border-radius: 6px; align-items: center; }
.pb-contrib-kind { background: rgba(96,165,250,0.2); color: #93c5fd; padding: 0.1rem 0.3rem; border-radius: 4px; font-size: 0.55rem; flex-shrink: 0; }
.pb-contrib-title { flex: 1; color: rgba(255,255,255,0.9); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pb-contrib-push { font-size: 0.55rem; flex-shrink: 0; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pb-contrib-date { color: rgba(255,255,255,0.4); font-size: 0.55rem; white-space: nowrap; }
.pb-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
.pb-modal { background: var(--ownex-surface, #111318); border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; width: 100%; max-width: 640px; max-height: 80vh; display: flex; flex-direction: column; }
.pb-modal-head { display: flex; justify-content: space-between; align-items: center; padding: 0.7rem 1rem; border-bottom: 1px solid var(--ownex-stroke, #2a2e37); }
.pb-modal-head h4 { margin: 0; font-size: 0.8rem; }
.pb-modal-close { background: none; border: none; color: rgba(255,255,255,0.5); font-size: 1.1rem; cursor: pointer; }
.pb-modal-body { padding: 1rem; overflow: auto; font-size: 0.7rem; white-space: pre-wrap; color: #e5e7eb; }
.pb-modal-foot { padding: 0.7rem 1rem; border-top: 1px solid var(--ownex-stroke, #2a2e37); display: flex; justify-content: flex-end; }
</style>