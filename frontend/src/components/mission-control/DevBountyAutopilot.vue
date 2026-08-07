<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getDevBountyStatus, activateDevBounty, deactivateDevBounty, runDevBountyCycle,
  getDevBountyQueue, validateDevBounty, setDevBountyBeginnerMode, saveEvidenceClaim,
  type DevBountyStatus, type DevBountyProposal, type EvidenceClaim,
} from '@/services/controlPanel'

const claimStatus = ref<EvidenceClaim | null>(null)

const status = ref<DevBountyStatus | null>(null)
const queue = ref<DevBountyProposal[]>([])
const loading = ref(true)
const running = ref(false)
const busyId = ref('')
const note = ref('')

const isActive = computed(() => status.value?.active)
const count = computed(() => queue.value.length)

async function load() {
  loading.value = true
  const [s, q] = await Promise.all([getDevBountyStatus(), getDevBountyQueue()])
  status.value = s
  queue.value = q.pending || []
  loading.value = false
}

async function run() {
  if (running.value) return
  running.value = true
  note.value = ''
  try {
    const res = await runDevBountyCycle()
    note.value = res.success === false
      ? 'El autopilote no está activo. Activalo primero.'
      : `Descubiertos: ${res.discovered ?? 0} · propuestas listas: ${res.proposals_ready ?? 0}`
  } catch {
    note.value = 'Error al correr el ciclo.'
  } finally {
    running.value = false
    await load()
  }
}

async function act(key: string, fn: () => Promise<DevBountyStatus>) {
  busyId.value = key
  try {
    await fn()
  } finally {
    busyId.value = ''
  }
  await load()
}

async function resolve(id: string, action: string) {
  const proposal = queue.value.find(q => q.id === id)
  await validateDevBounty(id, action)
  if (proposal && action === 'approved') {
    claimStatus.value = await saveEvidenceClaim(id, {
      outcome: 'approved',
      detail: `Bounty "${proposal.title}" validada y lista para submit → ${proposal.repo}`,
      bountyId: proposal.id,
    })
  }
  await load()
}

async function saveProof(q: DevBountyProposal) {
  claimStatus.value = await saveEvidenceClaim(q.id, {
    outcome: 'approved',
    detail: `Bounty "${q.title}" validada y lista para submit → ${q.repo}`,
    bountyId: q.id,
  })
}

async function toggleBeginner(enabled: boolean) {
  await setDevBountyBeginnerMode(enabled)
  await load()
}

onMounted(load)
</script>

<template>
  <section class="db">
    <div class="db-head">
      <h3 class="db-title">DEV BOUNTY AUTOPILOT</h3>
      <span
        v-if="status"
        class="db-badge"
        :style="{ color: isActive ? '#16a34a' : '#6b7280' }"
      >
        {{ isActive ? 'ACTIVO' : 'INACTIVO' }}
      </span>
    </div>

    <p v-if="loading" class="db-muted">Revisando autopilote...</p>

    <template v-else>
      <p class="db-desc">
        Descubre bounts (Opire/Superteam/Algora/Gitcoin), prepara la solución y te deja la
        propuesta lista. <span class="db-em">Vos solo validás y subís.</span>
      </p>

      <!-- Acciones -->
      <div class="db-actions">
        <button v-if="!isActive" class="db-btn ok" :disabled="!!busyId" @click="act('on', activateDevBounty)">
          Activar autopilote
        </button>
        <button v-else class="db-btn off" :disabled="!!busyId" @click="act('off', deactivateDevBounty)">
          Desactivar
        </button>
        <button class="db-btn run" :disabled="!isActive || running || !!busyId" @click="run">
          {{ running ? 'Descubriendo...' : 'Descubrir + proponer' }}
        </button>
      </div>

      <label class="db-toggle">
        <input
          type="checkbox"
          :checked="status?.beginner_mode"
          :disabled="!!busyId"
          @change="toggleBeginner(($event.target as HTMLInputElement).checked)"
        />
        <span>Modo principiante: solo bounts <b>good-first-issue</b> / bugs simples</span>
      </label>

      <p class="db-status" v-if="status">
        Auto-discovery: <b>{{ status.auto_discover ? 'ON' : 'OFF' }}</b> ·
        Auto-proposal: <b>{{ status.auto_proposal ? 'ON' : 'OFF' }}</b> ·
        Validación: <b>Siempre tuya</b>
      </p>

      <p v-if="note" class="db-note">{{ note }}</p>

      <p v-if="claimStatus" class="db-proof">
        📁 Prueba guardada: <code>{{ claimStatus.path.split('/').pop() }}</code>
        · sha256: <code>{{ claimStatus.sha256 }}</code> · {{ claimStatus.timestamp_utc.slice(0,19) }}Z
      </p>

      <!-- Propuestas listas -->
      <div v-if="queue.length" class="db-queue">
        <span class="db-label">Propuestas listas para validar ({{ count }})</span>
        <div v-for="q in queue" :key="q.id" class="db-item">
          <div class="db-item-info">
            <span class="db-item-title">{{ q.title }}</span>
            <span class="db-item-sub">{{ q.platform }} · {{ q.repo }}</span>
          </div>
          <div class="db-item-actions">
            <button class="db-btn ok small" :disabled="!!busyId" @click="resolve(q.id, 'approved')">Validar</button>
            <button class="db-btn off small" :disabled="!!busyId" @click="resolve(q.id, 'rejected')">Rechazar</button>
            <button class="db-btn run small" :disabled="!!busyId" @click="saveProof(q)">Guardar prueba manual</button>
          </div>
        </div>
      </div>

      <p v-else-if="isActive" class="db-muted">
        No hay propuestas pendientes — tocá "Descubrir y proponer" para buscar bounts.
      </p>
    </template>
  </section>
</template>

<style scoped>
.db {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.db-head { display: flex; align-items: center; gap: 0.7rem; }
.db-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.db-badge { margin-left: auto; font-size: 0.6rem; font-weight: 700; }
.db-muted { font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); margin: 0; }
.db-desc { font-size: 0.72rem; color: rgba(255, 255, 255, 0.75); margin: 0; line-height: 1.5; }
.db-em { color: #4ade80; font-weight: 600; }
.db-actions { display: flex; gap: 0.5rem; }
.db-toggle { display: flex; align-items: center; gap: 0.45rem; font-size: 0.68rem; color: rgba(255, 255, 255, 0.7); cursor: pointer; }
.db-toggle input { accent-color: #4ade80; cursor: pointer; }
.db-toggle b { color: #4ade80; }
.db-btn {
  border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px;
  background: rgba(255, 255, 255, 0.04); color: #e5e7eb;
  font-size: 0.72rem; font-weight: 600; padding: 0.4rem 0.7rem; cursor: pointer;
}
.db-btn.ok { border-color: rgba(22, 163, 74, 0.4); color: #4ade80; background: rgba(22, 163, 74, 0.1); }
.db-btn.off { border-color: rgba(232, 33, 39, 0.4); color: #f87171; background: rgba(232, 33, 39, 0.08); }
.db-btn.run { border-color: rgba(96, 165, 250, 0.4); color: #93c5fd; background: rgba(96, 165, 250, 0.1); }
.db-btn.small { padding: 0.25rem 0.5rem; font-size: 0.65rem; }
.db-btn:disabled { opacity: 0.4; cursor: default; }
.db-info { font-size: 0.68rem; color: rgba(255, 255, 255, 0.6); margin: 0; }
.db-info b { color: #4ade80; }
.db-note { font-size: 0.72rem; color: #93c5fd; margin: 0; }
.db-proof { font-size: 0.64rem; color: #4ade80; margin: 0; word-break: break-all; }
.db-proof code { background: rgba(74,222,128,0.12); border: 1px solid rgba(74,222,128,0.25); border-radius: 4px; padding: 0.1rem 0.3rem; font-size: 0.6rem; }
.db-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255, 255, 255, 0.45); }
.db-queue { display: flex; flex-direction: column; gap: 0.4rem; }
.db-item {
  display: flex; align-items: center; justify-content: space-between; gap: 0.6rem;
  border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 0.5rem 0.6rem;
}
.db-item-info { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.db-item-title { font-size: 0.72rem; font-weight: 600; color: rgba(255, 255, 255, 0.9); }
.db-item-sub { font-size: 0.62rem; color: rgba(255, 255, 255, 0.45); }
.db-item-actions { display: flex; gap: 0.35rem; flex-shrink: 0; }
</style>