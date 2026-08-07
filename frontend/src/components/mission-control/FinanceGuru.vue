<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  askFinanceGuru, resolveFinanceAccount, getFinanceAccounts,
  type FinanceAccount, type FinanceAskResult, type FinanceResolveResult,
} from '@/services/controlPanel'

const query = ref('')
const answer = ref<FinanceAskResult | null>(null)
const accounts = ref<FinanceAccount[]>([])
const resolveForm = ref({ account_id: '', problem: '' })
const resolution = ref<FinanceResolveResult | null>(null)
const loading = ref(true)

async function load() {
  const res = await getFinanceAccounts()
  accounts.value = res.accounts ?? []
  loading.value = false
}

async function ask() {
  if (!query.value.trim()) return
  answer.value = await askFinanceGuru(query.value)
}

async function doResolve() {
  if (!resolveForm.value.account_id || !resolveForm.value.problem) return
  resolution.value = await resolveFinanceAccount(resolveForm.value.account_id, resolveForm.value.problem)
}

onMounted(() => load())
</script>

<template>
  <section class="fg">
    <div class="fg-head">
      <h3 class="fg-title">FINANCE GURU · COBRO Y CUENTAS USA/INTL DESDE AR</h3>
    </div>

    <!-- Pregunta libre -->
    <div class="fg-ask">
      <textarea v-model="query" rows="2" placeholder="Ej: cómo abro cuenta en USA desde Argentina solo con KYC / me retuvieron un pago en Payoneer / mejor forma de cobrar bounty en ARS..." />
      <button class="fg-btn" @click="ask">PREGUNTAR A OWNEX</button>
    </div>

    <div v-if="answer" class="fg-answer">
      <p class="fg-intent">Intent: {{ answer.intent }}</p>
      <p class="fg-text">{{ answer.answer }}</p>
      <div v-if="answer.recommended?.length" class="fg-recs">
        <span class="fg-rec-title">Recomendadas:</span>
        <button v-for="r in answer.recommended" :key="r.id" class="fg-rec" @click="resolveForm.account_id = r.id">{{ r.name }} ({{ r.dias }})</button>
      </div>
    </div>

    <!-- Resolución de problema concreto -->
    <div class="fg-resolve">
      <p class="fg-rtitle">RESOLVER PROBLEMA CON UNA CUENTA</p>
      <div class="fg-rrow">
        <select v-model="resolveForm.account_id">
          <option value="">Cuenta…</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
        </select>
        <input v-model="resolveForm.problem" placeholder="Qué falló (ej: me retuvieron el pago, KYC rechazado, tarjeta bloqueada...)" class="fg-in" />
        <button class="fg-btn" @click="doResolve">Resolver</button>
      </div>
      <div v-if="resolution" class="fg-fix">
        <p class="fg-fixtext">{{ resolution.fix }}</p>
        <div v-if="resolution.fallbacks?.length" class="fg-fbf">
          <span class="fg-fblabel">Fallbacks:</span>
          <span v-for="f in resolution.fallbacks" :key="f" class="fg-fb">{{ f }}</span>
        </div>
      </div>
    </div>

    <!-- Catálogo -->
    <div class="fg-catalog">
      <p class="fg-ctitle">CATÁLOGO DE CUENTAS ({{ accounts.length }} opciones)</p>
      <div class="fg-grid">
        <div v-for="a in accounts" :key="a.id" class="fg-card">
          <div class="fg-cname">{{ a.name }}</div>
          <div class="fg-cm">Región: {{ a.region }} · KYC: {{ a.kyc }}</div>
          <div class="fg-cm">{{ a.llc_needed ? '⚠️ Requiere LLC' : '✅ Solo KYC' }}</div>
          <div class="fg-cm">Para: {{ a.para.slice(0, 3).join(', ') }}</div>
          <button class="fg-btn-sm" @click="resolveForm.account_id = a.id">Ver pasos</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.fg { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.8rem; }
.fg-head { display: flex; align-items: center; gap: 0.6rem; }
.fg-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.fg-ask { display: flex; flex-direction: column; gap: 0.5rem; }
.fg-ask textarea { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.6rem; color: rgba(255,255,255,0.95); font-size: 0.72rem; resize: vertical; min-height: 70px; }
.fg-btn { border: 1px solid rgba(96,165,250,0.4); border-radius: 8px; background: rgba(96,165,250,0.1); color: #93c5fd; font-size: 0.68rem; font-weight: 600; padding: 0.4rem 0.8rem; cursor: pointer; align-self: flex-start; }
.fg-btn.sm { align-self: flex-start; margin-top: 0.2rem; }
.fg-answer { padding: 0.7rem; border: 1px solid rgba(96,165,250,0.2); background: rgba(96,165,250,0.05); border-radius: 10px; display: flex; flex-direction: column; gap: 0.4rem; }
.fg-intent { margin: 0; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.1em; color: #93c5fd; }
.fg-text { margin: 0; font-size: 0.75rem; color: rgba(255,255,255,0.9); line-height: 1.5; white-space: pre-wrap; }
.fg-recs { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
.fg-rec-title { font-size: 0.62rem; font-weight: 700; color: rgba(255,255,255,0.5); }
.fg-rec { border: 1px solid rgba(96,165,250,0.2); background: rgba(96,165,250,0.05); border-radius: 6px; padding: 0.2rem 0.45rem; font-size: 0.6rem; color: #93c5fd; cursor: pointer; }
.fg-resolve { display: flex; flex-direction: column; gap: 0.5rem; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 0.6rem; }
.fg-rtitle { margin: 0; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); }
.fg-rrow { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.fg-rrow select { min-width: 180px; }
.fg-rrow input { flex: 1; min-width: 180px; }
.fg-in { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.4rem 0.55rem; color: rgba(255,255,255,0.92); font-size: 0.68rem; }
.fg-fix { padding: 0.6rem; border: 1px solid rgba(34,211,128,0.2); background: rgba(34,211,128,0.04); border-radius: 10px; display: flex; flex-direction: column; gap: 0.3rem; }
.fg-fixtext { margin: 0; font-size: 0.72rem; color: rgba(255,255,255,0.9); line-height: 1.5; }
.fg-fbf { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; font-size: 0.62rem; }
.fg-fblabel { color: rgba(255,255,255,0.4); }
.fg-fb { color: #6ee7b7; border: 1px solid rgba(110,231,183,0.2); background: rgba(110,231,183,0.06); padding: 0.1rem 0.4rem; border-radius: 4px; }
.fg-catalog { display: flex; flex-direction: column; gap: 0.5rem; }
.fg-ctitle { margin: 0; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); }
.fg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.5rem; }
.fg-card { padding: 0.6rem; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); border-radius: 10px; display: flex; flex-direction: column; gap: 0.25rem; }
.fg-cname { font-size: 0.72rem; font-weight: 600; color: rgba(255,255,255,0.95); }
.fg-cm { font-size: 0.6rem; color: rgba(255,255,255,0.55); }
.fg-btn-sm { align-self: flex-start; margin-top: 0.3rem; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.7); font-size: 0.6rem; padding: 0.2rem 0.4rem; border-radius: 6px; cursor: pointer; }
</style>