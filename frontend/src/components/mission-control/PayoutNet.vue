<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getPayoutCatalog, recommendPayout, resolvePayoutProblem,
  type PayoutCatalog, type PayoutMethod, type PayoutResolveResult,
} from '@/services/controlPanel'

const catalog = ref<PayoutCatalog>({})
const loading = ref(true)
const catFilter = ref('')
const sourceFilter = ref('forge')
const resolution = ref<PayoutResolveResult | null>(null)
const resolveForm = ref({ method: '', problem: '' })

const methods = computed(() => {
  let list = catalog.value.methods ?? []
  if (catFilter.value) list = list.filter(m => m.cat === catFilter.value)
  return list
})

const cats = computed(() => Object.keys(catalog.value.categories ?? {}))

async function load() {
  loading.value = true
  try {
    catalog.value = await getPayoutCatalog(catFilter.value)
  } finally {
    loading.value = false
  }
}

async function recFor(src: string) {
  sourceFilter.value = src
  catalog.value = await getPayoutCatalog('')
  catFilter.value = ''
}

async function selectMethod(m: PayoutMethod) {
  resolveForm.value.methodId = m.id
}

async function doResolve() {
  resolution.value = await resolvePayoutProblem(resolveForm.value.methodId, resolveForm.value.problem)
}

onMounted(() => load())
</script>

<template>
  <section class="pn">
    <div class="pn-head">
      <h3 class="pn-title">PAYOUT NET · COBRO SOLO KYC</h3>
      <span class="pn-badge">{{ catalog.total }} métodos</span>
    </div>

    <p v-if="loading" class="pn-muted">Cargando red de cobro...</p>

    <template v-else>
      <div class="pn-tools">
        <select v-model="catFilter" @change="load">
          <option value="">Todas las categorías</option>
          <option v-for="c in cats" :key="c" :value="c">{{ c }}</option>
        </select>
        <div class="pn-sources">
          <button v-for="s in ['forge','pulse','bounty','freelance','web3','prod']" :key="s" class="pn-src" :class="{ active: sourceFilter === s }" @click="recFor(s)">{{ s }}</button>
        </div>
      </div>

      <p v-if="catalog.total === 0" class="pn-muted">Sin métodos cargados.</p>

      <div class="pn-list">
        <div v-for="m in methods" :key="m.id" class="pn-method">
          <div class="pn-mhead">
            <span class="pn-mname">{{ m.name }}</span>
            <span class="pn-mcat">{{ m.cat }}</span>
          </div>
          <div class="pn-mmeta">
            <span>KYC: {{ m.kyc }}</span>
            <span>Cotiz: {{ m.cotiz }}</span>
            <span>{{ m.dias }} día(s)</span>
            <span>Costo: {{ m.costo }}</span>
          </div>
          <div v-if="m.fallbacks.length" class="pn-mfb">
            <span class="pn-fb-label">Fallbacks:</span>
            <span v-for="f in m.fallbacks" :key="f" class="pn-fb">{{ f }}</span>
          </div>
          <button class="pn-btn sm" @click="selectMethod(m)">Reportar problema</button>
        </div>
      </div>

      <!-- Resolución -->
      <div class="pn-resolve">
        <p class="pn-rtitle">REPORTE DE PROBLEMA</p>
        <div class="pn-rrow">
          <select v-model="resolveForm.methodId">
            <option value="">Método…</option>
            <option v-for="m in catalog.methods ?? []" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
          <input v-model="resolveForm.problem" placeholder="Qué falló (KYC, CBU, retiro…)" class="pn-in" />
          <button class="pn-btn" @click="doResolve">Resolver</button>
        </div>
        <div v-if="resolution" class="pn-fix">
          <p class="pn-fixtxt">{{ resolution.fix }}</p>
          <div v-if="resolution.fallbacks?.length" class="pn-fixfb">
            <span class="pn-fb-label">Alternativas:</span>
            <span v-for="f in resolution.fallbacks" :key="f" class="pn-fb">{{ f }}</span>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.pn { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.pn-head { display: flex; align-items: center; gap: 0.7rem; }
.pn-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.pn-badge { margin-left: auto; font-size: 0.65rem; font-weight: 700; color: #34d399; background: rgba(52,211,153,0.12); border: 1px solid rgba(52,211,153,0.3); border-radius: 6px; padding: 0.2rem 0.5rem; }
.pn-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.pn-tools { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.pn-tools select, .pn-rrow select, .pn-row input { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 0.4rem 0.55rem; color: rgba(255,255,255,0.92); font-size: 0.68rem; }
.pn-sources { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.pn-src { border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); border-radius: 6px; padding: 0.25rem 0.5rem; font-size: 0.58rem; color: rgba(255,255,255,0.6); cursor: pointer; text-transform: uppercase; }
.pn-src.active { border-color: rgba(52,211,153,0.5); background: rgba(52,211,153,0.12); color: #6ee7b7; }
.pn-list { display: flex; flex-direction: column; gap: 0.5rem; }
.pn-method { padding: 0.6rem; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); border-radius: 10px; display: flex; flex-direction: column; gap: 0.3rem; }
.pn-mhead { display: flex; align-items: center; gap: 0.5rem; }
.pn-mname { font-size: 0.72rem; font-weight: 600; color: rgba(255,255,255,0.95); }
.pn-mcat { font-size: 0.55rem; text-transform: uppercase; color: #34d399; border: 1px solid rgba(52,211,153,0.3); padding: 0.1rem 0.35rem; border-radius: 4px; }
.pn-mmeta { display: flex; flex-wrap: wrap; gap: 0.6rem; font-size: 0.62rem; color: rgba(255,255,255,0.55); }
.pn-mfb { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; font-size: 0.6rem; }
.pn-fb-label { color: rgba(255,255,255,0.4); }
.pn-fb { color: #93c5fd; border: 1px solid rgba(147,197,253,0.2); background: rgba(147,197,253,0.06); padding: 0.1rem 0.4rem; border-radius: 4px; }
.pn-btn { border: 1px solid rgba(52,211,153,0.4); border-radius: 8px; background: rgba(52,211,153,0.1); color: #6ee7b7; font-size: 0.68rem; font-weight: 600; padding: 0.35rem 0.7rem; cursor: pointer; }
.pn-btn.sm { align-self: flex-start; margin-top: 0.2rem; }
.pn-resolve { display: flex; flex-direction: column; gap: 0.5rem; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 0.6rem; }
.pn-rtitle { margin: 0; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; color: rgba(255,255,255,0.5); }
.pn-rrow { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.pn-in { flex: 1; min-width: 140px; }
.pn-fix { padding: 0.6rem; border: 1px solid rgba(52,211,153,0.2); background: rgba(52,211,153,0.04); border-radius: 10px; display: flex; flex-direction: column; gap: 0.3rem; }
.pn-fixtxt { margin: 0; font-size: 0.72rem; color: rgba(255,255,255,0.9); line-height: 1.5; }
.pn-fixfb { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; font-size: 0.62rem; }
</style>