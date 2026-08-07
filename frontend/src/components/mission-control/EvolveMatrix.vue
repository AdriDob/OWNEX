<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getWorkLog, registerWorkSession, type WorkLogStatus,
  getPostMortem, registerPostMortem, type PostMortemStatus,
  getAccountHealth, registerHealthAccount, reportHealthEvent, type AccountHealthStatus,
  getPayoutPlanner, configurePayoutPlatform, type PayoutPlannerStatus,
  getBrandWriter, generateBrandDraft, publishBrandDraft, type BrandWriterStatus, type BrandDraftEntry,
  getVaultLock, secureVault, unlockVault, type VaultLockStatus,
  analyzeEmergency, type EmergencyAnalysis,
} from '@/services/controlPanel'

const ws = ref('risk')
const note = ref('')

const work = ref<WorkLogStatus>({})
const pm = ref<PostMortemStatus>({})
const health = ref<AccountHealthStatus>({})
const payouts = ref<PayoutPlannerStatus>({})
const brand = ref<BrandWriterStatus>({})
const vault = ref<VaultLockStatus>({})
const emergency = ref<EmergencyAnalysis | null>(null)

const emColor = ref('#6b7280')

async function load() {
  const [w, p, h, po, b, v] = await Promise.all([
    getWorkLog(), getPostMortem(), getAccountHealth(), getPayoutPlanner(), getBrandWriter(), getVaultLock(),
  ])
  work.value = w; pm.value = p; health.value = h; payouts.value = po; brand.value = b; vault.value = v
}

// ── Work Log ──
const sessionForm = ref({ hours: 2, foco: 'bounty', detail: '', momentum: 5 })
async function addSession() {
  note.value = ''
  const r = await registerWorkSession(sessionForm.value.hours, sessionForm.value.foco, sessionForm.value.detail, sessionForm.value.momentum)
  note.value = r.success ? 'Sesión registrada. Tus proyecciones ahora usan horas reales.' : 'Error al registrar.'
  if (r.success) sessionForm.value.detail = ''
  await load()
}

// ── Post Mortem ──
const pmForm = ref({ title: '', outcome: '', learned: '', repeat: '', avoid: '' })
async function addPostMortem() {
  note.value = ''
  if (!pmForm.value.title || !pmForm.value.outcome) { note.value = 'Completá título y resultado.'; return }
  const r = await registerPostMortem('bounty', pmForm.value.title, pmForm.value.outcome, pmForm.value.learned, pmForm.value.repeat, pmForm.value.avoid)
  note.value = r.success ? 'Episodio guardado — OWNEX aprendió.' : 'Error al guardar.'
  if (r.success) { pmForm.value.title = ''; pmForm.value.learned = ''; pmForm.value.repeat = ''; pmForm.value.avoid = '' }
  await load()
}

// ── Account Health ──
const accForm = ref({ platform: 'outlier' })
async function addHealthAccount() {
  const r = await registerHealthAccount(accForm.value.platform, accForm.value.platform)
  note.value = r.success ? 'Cuenta agregada al monitoreo.' : 'Ya existe o plataforma inválida.'
  await load()
}
async function logHealthEvent(platform: string) {
  await reportHealthEvent(platform, 'qa_fail', 'Simulado desde panel', 20)
  await load()
}

// ── Payout ──
async function togglePayout(id: string) {
  const r = await configurePayoutPlatform(id)
  note.value = r.success ? 'Plataforma marcada como configurada.' : 'Error.'
  await load()
}

// ── Brand ──
const brandForm = ref({ topic: '', detail: '' })
const openDraft = ref<BrandDraftEntry | null>(null)
async function makeDraft() {
  note.value = ''
  if (!brandForm.value.topic) { note.value = 'Escribí un topic.'; return }
  const r = await generateBrandDraft(brandForm.value.topic, brandForm.value.detail)
  if (r.success && r.entry) {
    openDraft.value = r.entry
    brandForm.value.topic = ''
    brandForm.value.detail = ''
  } else note.value = 'Error al generar.'
  await load()
}
async function publishDraft(d: BrandDraftEntry, ch: string) {
  await publishBrandDraft(d.id, ch)
  await load()
}

// ── Vault ──
const passphrase = ref('')
const passErr = ref('')
async function lockVault() {
  passErr.value = ''
  const r = await secureVault(passphrase.value)
  if (r.success) { note.value = 'Vault asegurado.'; passphrase.value = '' } else passErr.value = r.message || 'Passphrase muy corta (min 8).'
  await load()
}
async function unlockVaultPass() {
  passErr.value = ''
  const r = await unlockVault(passphrase.value)
  if (!r.success) passErr.value = r.message || 'Passphrase incorrecta.'
  await load()
}

// ── Emergency ──
async function riskCheck(target = 5000) {
  emergency.value = await analyzeEmergency(target, 'monthly')
  const lvl = emergency.value?.level ?? 'info'
  emColor.value = { info: '#6b7280', normal: '#4ade80', warning: '#fbbf24', critical: '#e11d48' }[lvl] ?? '#6b7280'
}

function fmt(n: number | undefined) {
  return `${n ?? 0}h`
}

onMounted(() => { load(); riskCheck() })
</script>

<template>
  <section class="ev">
    <div class="ev-head">
      <h3 class="ev-title">CRECIMIENTO · MÓDULOS DEL 0,1%</h3>
      <span class="ev-tabs">
        <button v-for="t in [['risk','EMERGENCIA'],['work','WORK'],['pm','POST-MORTEM'],['health','ACCOUNTS'],['payout','COBRO'],['brand','BRAND'],['vault','VAULT']]" :key="t[0]" class="ev-tab" :class="{ active: ws === t[0] }" @click="ws = t[0]">{{ t[1] }}</button>
      </span>
    </div>

    <p v-if="note" class="ev-note">{{ note }}</p>

    <!-- ── EMERGENCIA ── -->
    <template v-if="ws === 'risk'">
      <div class="ev-card" :style="{ borderColor: emColor + '66', background: emColor + '14' }">
        <span class="ev-status" :style="{ color: emColor }">NIVEL: {{ emergency?.level ?? 'info' }}</span>
        <p class="ev-verdict">{{ emergency?.verdict }}</p>
        <div class="ev-signals">
          <div class="ev-cell"><span>Proyección mes</span><b>${{ ((emergency?.projection) ?? 0).toLocaleString() }}</b></div>
          <div class="ev-cell"><span>Bounts listos</span><b>{{ emergency?.signals?.bount_pending ?? 0 }}</b></div>
          <div class="ev-cell"><span>Horas (7d)</span><b>{{ fmt(emergency?.signals?.hours_7d) }}</b></div>
          <div class="ev-cell"><span>VPN</span><b>{{ emergency?.signals?.vpn_ready ? 'Sí' : 'No' }}</b></div>
        </div>
        <div v-if="emergency?.plan?.length" class="ev-plan">
          <div v-for="a in emergency.plan" :key="a.title" class="ev-plan-item">
            <span class="ev-p-impact">{{ a.impact }}</span>
            <div class="ev-p-body">
              <span class="ev-p-title">{{ a.title }}</span>
              <span class="ev-p-why">{{ a.why }}<template v-if="a.detail"> — {{ a.detail }}</template></span>
            </div>
          </div>
        </div>
        <button class="ev-btn" @click="riskCheck()">Re-analizar meta $5.000</button>
      </div>
    </template>

    <!-- ── WORK ── -->
    <template v-else-if="ws === 'work'">
      <div class="ev-signals">
        <div class="ev-cell"><span>7 días</span><b>{{ fmt(work.hours_7d) }}</b></div>
        <div class="ev-cell"><span>30 días</span><b>{{ fmt(work.hours_30d) }}</b></div>
        <div class="ev-cell"><span>Sesiones</span><b>{{ work.total_sessions }}</b></div>
        <div class="ev-cell"><span>Momentum</span><b>{{ work.avg_momentum }}</b></div>
      </div>
      <p class="ev-msg">{{ work.message }}</p>
      <div class="ev-form-row wrap">
        <input v-model.number="sessionForm.hours" type="number" min="0.5" max="16" step="0.5" />
        <select v-model="sessionForm.foco">
          <option v-for="f in work.foco_options" :key="f" :value="f">{{ f }}</option>
        </select>
        <input v-model="sessionForm.detail" placeholder="¿En qué trabajaste?" class="grow" />
        <select v-model="sessionForm.momentum">
          <option :value="i" v-for="i in 10" :key="i">{{ i }}</option>
        </select>
        <button class="ev-btn" @click="addSession">Registrar</button>
      </div>
      <div v-if="work.sessions?.length" class="ev-list">
        <div v-for="s in work.sessions" :key="s.id" class="ev-item">
          <span class="ev-it-tag">{{ s.foco }}</span>
          <div class="ev-it-body">
            <span class="ev-it-title">{{ s.detail || s.foco }}</span>
            <span class="ev-it-meta">{{ s.hours }}h · {{ new Date(s.created_at).toLocaleDateString() }}</span>
          </div>
          <b class="ev-amt">{{ s.hours }}h</b>
        </div>
      </div>
    </template>

    <!-- ── POST MORTEM ── -->
    <template v-else-if="ws === 'pm'">
      <div class="ev-form-row wrap">
        <input v-model="pmForm.title" placeholder="Título (ej: bounty X)" class="grow" />
        <select v-model="pmForm.outcome">
          <option value="">Resultado…</option>
          <option value="approved">Aprobado</option>
          <option value="rejected">Rechazado</option>
          <option value="closed">Cerrado</option>
        </select>
      </div>
      <div class="ev-form-row wrap">
        <input v-model="pmForm.learned" placeholder="Qué aprendí" class="grow" />
        <input v-model="pmForm.repeat" placeholder="Qué repetir" class="grow" />
        <input v-model="pmForm.avoid" placeholder="Qué evitar" class="grow" />
        <button class="ev-btn" @click="addPostMortem()">Guardar episodio</button>
      </div>
      <div class="ev-stats">Aprobado {{ pm.approved ?? 0 }} · Rechazado {{ pm.rejected ?? 0 }} · Cerrado {{ pm.closed ?? 0 }}</div>
      <div v-if="pm.learnings?.length" class="ev-learn">
        <span class="ev-learn-title">LEARNINGS ACTIVOS</span>
        <div v-for="l in pm.learnings" :key="l" class="ev-learn-item">{{ l }}</div>
      </div>
      <div v-if="pm.episodes?.length" class="ev-list">
        <div v-for="e in pm.episodes" :key="e.id" class="ev-item">
          <span class="ev-it-tag" :class="e.outcome">{{ e.outcome }}</span>
          <div class="ev-it-body">
            <span class="ev-it-title">{{ e.item_title }}</span>
            <span class="ev-it-meta">{{ e.item_type }} · {{ new Date(e.created_at).toLocaleDateString() }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- ── ACCOUNTS ── -->
    <template v-else-if="ws === 'health'">
      <div v-if="health.alerts?.length" class="ev-alerts">
        <div v-for="a in health.alerts" :key="a.platform + a.level" class="ev-alert"><b>{{ a.platform }}</b> · {{ a.level }} — {{ a.why }}</div>
      </div>
      <p v-else class="ev-msg">Sin alertas. Agregá cuentas para monitorear riesgo de ban.</p>
      <div class="ev-form-row wrap">
        <input v-model="accForm.platform" placeholder="Plataforma (outlier, da, mindrift…)" class="grow" />
        <button class="ev-btn" @click="addHealthAccount()">+ cuenta</button>
      </div>
      <div v-if="health.accounts?.length" class="ev-list">
        <div v-for="a in health.accounts" :key="a.platform" class="ev-item">
          <span class="ev-dot" :style="{ background: a.health_score >= 80 ? '#4ade80' : a.health_score >= 50 ? '#fbbf24' : '#e11d48' }"></span>
          <div class="ev-it-body">
            <span class="ev-it-title">{{ a.name }}</span>
            <span class="ev-it-meta">{{ a.events?.length ?? 0 }} eventos</span>
          </div>
          <b class="ev-amt">{{ a.health_score }}%</b>
          <button class="ev-btn-small" @click="logHealthEvent(a.platform)">QA fail</button>
        </div>
      </div>
    </template>

    <!-- ── COBRO ── -->
    <template v-else-if="ws === 'payout'">
      <p class="ev-msg">{{ payouts.message }}</p>
      <div class="ev-list">
        <div v-for="p in payouts.platforms" :key="p.id" class="ev-item">
          <div class="ev-it-body">
            <span class="ev-it-title">{{ p.name }}</span>
            <span class="ev-it-meta">{{ p.method }} · {{ p.arrival_days }} días · {{ p.note }}</span>
          </div>
          <button v-if="!p.configured" class="ev-btn-small" @click="togglePayout(p.id)">Configurar</button>
          <span v-else class="ev-ok">✓ configurado</span>
        </div>
      </div>
    </template>

    <!-- ── BRAND ── -->
    <template v-else-if="ws === 'brand'">
      <div class="ev-form-row wrap">
        <input v-model="brandForm.topic" placeholder="Topic (ej: Writeup SSRF a interno)" class="grow" />
        <input v-model="brandForm.detail" placeholder="Detalle / evidencia" class="grow" />
        <button class="ev-btn" @click="makeDraft">Generar borrador</button>
      </div>
      <div v-if="brand.drafts?.length" class="ev-list">
        <div v-for="d in brand.drafts" :key="d.id" class="ev-item column">
          <div class="ev-draft-head">
            <span class="ev-it-title">{{ d.topic }}</span>
            <span v-if="d.published" class="ev-ok">publicado</span>
            <button class="ev-btn-small" @click="openDraft = openDraft?.id === d.id ? null : d">ver</button>
          </div>
          <template v-if="openDraft?.id === d.id">
            <div v-for="dr in d.drafts" :key="dr.channel" class="ev-draft-block">
              <div class="ev-draft-head">
                <b class="ev-draft-channel">{{ dr.channel }}</b>
                <button class="ev-btn-small" @click="publishDraft(d, dr.channel)">{{ dr.published ? 'hecho' : 'marcar publicado' }}</button>
              </div>
              <pre class="ev-draft-text">{{ dr.text }}</pre>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- ── VAULT ── -->
    <template v-else-if="ws === 'vault'">
      <p class="ev-msg">{{ vault.message }}</p>
      <div class="ev-val-inline"><span>Modo</span><b :style="{ color: vault.mode === 'locked' ? '#4ade80' : '#fbbf24' }">{{ vault.mode }}</b></div>
      <div class="ev-form-row wrap">
        <input v-model="passphrase" type="password" placeholder="Passphrase (min 8)" class="grow" />
        <button class="ev-btn" @click="lockVault">Asegurar</button>
        <button class="ev-btn-small" @click="unlockVaultPass">Desbloquear</button>
      </div>
      <p v-if="passErr" class="ev-note err">{{ passErr }}</p>
      <div v-if="vault.protected?.length" class="ev-list">
        <div v-for="p in vault.protected" :key="p" class="ev-item"><span class="ev-it-title">{{ p }}</span></div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.ev { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.ev-head { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; }
.ev-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.ev-tabs { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.ev-tab { border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); border-radius: 6px; padding: 0.25rem 0.5rem; font-size: 0.58rem; color: rgba(255,255,255,0.6); cursor: pointer; }
.ev-tab.active { border-color: rgba(96,165,250,0.5); background: rgba(96,165,250,0.12); color: #93c5fd; }
.ev-note { font-size: 0.68rem; color: #93c5fd; margin: 0; }
.ev-note.err { color: #e11d48; }
.ev-msg { font-size: 0.7rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }
.ev-card { border: 1px solid; border-radius: 10px; padding: 0.7rem; display: flex; flex-direction: column; gap: 0.5rem; }
.ev-status { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em; }
.ev-verdict { margin: 0; font-size: 0.78rem; color: rgba(255,255,255,0.92); }
.ev-signals { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.4rem; }
.ev-cell { display: flex; flex-direction: column; gap: 0.1rem; padding: 0.4rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); }
.ev-cell span { font-size: 0.6rem; color: rgba(255,255,255,0.45); }
.ev-cell b { font-size: 0.8rem; color: rgba(255,255,255,0.92); }
.ev-plan { display: flex; flex-direction: column; gap: 0.3rem; }
.ev-plan-item { display: flex; gap: 0.5rem; padding: 0.45rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; }
.ev-p-impact { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); padding: 0.1rem 0.35rem; border-radius: 4px; height: fit-content; }
.ev-p-body { display: flex; flex-direction: column; gap: 0.1rem; }
.ev-p-title { font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.92); }
.ev-p-why { font-size: 0.62rem; color: rgba(255,255,255,0.55); }
.ev-btn { border: 1px solid rgba(96,165,250,0.4); border-radius: 8px; background: rgba(96,165,250,0.1); color: #93c5fd; font-size: 0.68rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer; white-space: nowrap; }
.ev-btn-small { border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.7); font-size: 0.6rem; padding: 0.25rem 0.5rem; cursor: pointer; white-space: nowrap; }
.ev-form-row { display: flex; gap: 0.35rem; }
.ev-form-row select, .ev-form-row input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.4rem 0.55rem; color: rgba(255,255,255,0.92); font-size: 0.68rem; }
.grow { flex: 1; min-width: 120px; }
.wrap { flex-wrap: wrap; }
.ev-list { display: flex; flex-direction: column; gap: 0.3rem; }
.ev-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.55rem; background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); }
.ev-item.column { flex-direction: column; align-items: stretch; }
.ev-it-tag { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); padding: 0.1rem 0.35rem; border-radius: 4px; flex-shrink: 0; }
.ev-it-tag.approved { color: #4ade80; border-color: rgba(74,222,128,0.3); }
.ev-it-tag.rejected { color: #e11d48; border-color: rgba(225,29,72,0.3); }
.ev-it-body { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.ev-it-title { font-size: 0.7rem; font-weight: 600; color: rgba(255,255,255,0.92); }
.ev-it-meta { font-size: 0.6rem; color: rgba(255,255,255,0.45); }
.ev-amt { font-size: 0.7rem; color: #93c5fd; }
.ev-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.ev-draft-head { display: flex; align-items: center; gap: 0.5rem; justify-content: space-between; }
.ev-draft-channel { font-size: 0.65rem; color: #93c5fd; text-transform: uppercase; }
.ev-draft-block { display: flex; flex-direction: column; gap: 0.3rem; }
.ev-draft-text { font-size: 0.65rem; color: rgba(255,255,255,0.85); white-space: pre-wrap; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 0.5rem; background: rgba(255,255,255,0.03); margin: 0; }
.ev-ok { color: #4ade80; font-weight: 700; font-size: 0.7rem; }
.ev-alerts { display: flex; flex-direction: column; gap: 0.3rem; }
.ev-alert { padding: 0.45rem 0.55rem; border-radius: 8px; border: 1px solid rgba(225,29,72,0.3); background: rgba(225,29,72,0.05); font-size: 0.68rem; color: #fda4af; }
.ev-stats { font-size: 0.68rem; color: rgba(255,255,255,0.75); }
.ev-learn { display: flex; flex-direction: column; gap: 0.2rem; }
.ev-learn-title { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); }
.ev-learn-item { font-size: 0.65rem; color: rgba(255,255,255,0.8); padding: 0.3rem 0.5rem; background: rgba(96,165,250,0.06); border-radius: 6px; }
.ev-val-inline { display: flex; align-items: center; gap: 0.4rem; }
.ev-val-inline span { font-size: 0.68rem; color: rgba(255,255,255,0.6); }
.ev-val-inline b { font-size: 0.8rem; }
</style>