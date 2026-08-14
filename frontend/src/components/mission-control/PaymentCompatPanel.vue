<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  evaluatePayment,
  fetchPaymentNetwork,
  type PaymentNetworkResponse,
  type PaymentVerdict,
} from '@/services/ownexData'

const network = ref<PaymentNetworkResponse | null>(null)
const verdict = ref<PaymentVerdict | null>(null)
const loading = ref(true)
const evaluating = ref(false)
const error = ref('')

const method = ref('crypto')
const currency = ref('USDC')
const region = ref('global')
const finalCurrency = ref('ARS')
const amount = ref(0)
const useChain = ref(true)

const METHODS = ['ach', 'wire', 'sepa', 'paypal', 'cbu', 'cvu', 'p2p', 'crypto']
const CURRENCIES = ['USDC', 'USDT', 'USD', 'EUR', 'ARS']
const REGIONS = ['global', 'usa', 'argentina', 'eu']

async function loadNetwork() {
  loading.value = true
  error.value = ''
  try {
    network.value = await fetchPaymentNetwork()
  } catch {
    error.value = 'Payment Network no disponible'
  } finally {
    loading.value = false
  }
}

async function runEvaluate() {
  evaluating.value = true
  error.value = ''
  try {
    verdict.value = await evaluatePayment(
      {
        method: method.value,
        currency: currency.value,
        region: region.value,
        amount: amount.value || undefined,
        final_currency: useChain.value ? finalCurrency.value : undefined,
      },
      useChain.value,
    )
  } catch {
    error.value = 'No se pudo evaluar el cobro'
  } finally {
    evaluating.value = false
  }
}

onMounted(loadNetwork)
</script>

<template>
  <section class="pc-panel">
    <div class="pc-head">
      <span class="pc-label">Payment Network · {{ network?.summary.total_accounts ?? '—' }} cuentas</span>
      <span v-if="network" class="pc-sub">
        {{ Object.keys(network.summary.by_layer).length }} capas · {{ Object.keys(network.summary.by_region).length }} regiones
      </span>
    </div>

    <div class="pc-form">
      <div class="pc-fields">
        <label class="pc-field">
          <span class="pc-field-label">Método de pago</span>
          <select v-model="method" class="pc-select">
            <option v-for="m in METHODS" :key="m" :value="m">{{ m.toUpperCase() }}</option>
          </select>
        </label>
        <label class="pc-field">
          <span class="pc-field-label">Moneda</span>
          <select v-model="currency" class="pc-select">
            <option v-for="c in CURRENCIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
        <label class="pc-field">
          <span class="pc-field-label">Región</span>
          <select v-model="region" class="pc-select">
            <option v-for="r in REGIONS" :key="r" :value="r">{{ r }}</option>
          </select>
        </label>
        <label class="pc-field">
          <span class="pc-field-label">Monto USD</span>
          <input v-model.number="amount" type="number" min="0" step="10" class="pc-input" placeholder="0" />
        </label>
      </div>
      <div class="pc-actions">
        <label class="pc-chain">
          <input v-model="useChain" type="checkbox" />
          <span class="pc-chain-label">Off-ramp a {{ finalCurrency }}</span>
        </label>
        <button class="pc-btn" :disabled="evaluating" @click="runEvaluate">
          {{ evaluating ? 'Evaluando…' : '¿Puedo cobrar esto?' }}
        </button>
      </div>
    </div>

    <div v-if="verdict" class="pc-verdict" :class="verdict.compatible ? 'pc-ok' : 'pc-blocked'">
      <div class="pc-verdict-row">
        <span class="pc-verdict-status">
          {{ verdict.compatible ? (verdict.viable ? '✓ Viable' : '✓ Compatible') : '✕ No compatible' }}
        </span>
        <span class="pc-verdict-score">score {{ Math.round(verdict.score) }}</span>
      </div>

      <div v-if="verdict.matches.length" class="pc-block">
        <span class="pc-block-label">Cuentas disponibles</span>
        <ul class="pc-list">
          <li v-for="m in verdict.matches" :key="m.account_id" class="pc-item">
            <div class="pc-main">
              <span class="pc-title">{{ m.account_name }}</span>
              <span class="pc-sub">{{ m.layer }} · {{ m.function }}</span>
            </div>
            <span class="pc-reason">{{ m.reason }}</span>
          </li>
        </ul>
      </div>

      <div v-if="verdict.off_ramp.length" class="pc-block">
        <span class="pc-block-label">Off-ramp</span>
        <ul class="pc-list">
          <li v-for="m in verdict.off_ramp" :key="m.account_id" class="pc-item">
            <div class="pc-main">
              <span class="pc-title">{{ m.account_name }}</span>
              <span class="pc-sub">{{ m.layer }} · {{ m.function }}</span>
            </div>
            <span class="pc-reason">{{ m.reason }}</span>
          </li>
        </ul>
      </div>

      <div v-if="verdict.missing.length" class="pc-block">
        <span class="pc-block-label">Falta</span>
        <span class="pc-missing">{{ verdict.missing.join(' · ') }}</span>
      </div>

      <div v-if="verdict.honest_notes.length" class="pc-block">
        <span v-for="(n, i) in verdict.honest_notes" :key="i" class="pc-note">{{ n }}</span>
      </div>
    </div>

    <div v-if="error" class="pc-error">{{ error }}</div>
  </section>
</template>

<style scoped>
.pc-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.pc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.25rem;
}
.pc-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #00e39a;
}
.pc-sub {
  font-size: 0.68rem;
  color: #8b8d98;
}
.pc-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.pc-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 0.4rem;
}
.pc-field {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.pc-field-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8b8d98;
}
.pc-select,
.pc-input {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: #f0f0f0;
  font-size: 0.72rem;
  padding: 0.3rem 0.4rem;
  outline: none;
}
.pc-select:focus,
.pc-input:focus {
  border-color: #00d5ff;
}
.pc-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.pc-chain {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.68rem;
  color: #8b8d98;
  cursor: pointer;
}
.pc-chain-label {
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pc-btn {
  background: #00d5ff;
  color: #05060a;
  border: none;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.35rem 0.8rem;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pc-btn:hover {
  opacity: 0.9;
}
.pc-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.pc-verdict {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-radius: 8px;
  padding: 0.6rem 0.7rem;
  background: rgba(255, 255, 255, 0.05);
}
.pc-ok {
  border: 1px solid rgba(0, 227, 154, 0.35);
}
.pc-blocked {
  border: 1px solid rgba(255, 122, 26, 0.35);
}
.pc-verdict-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pc-verdict-status {
  font-size: 0.78rem;
  font-weight: 600;
  color: #00e39a;
}
.pc-blocked .pc-verdict-status {
  color: #ff7a1a;
}
.pc-verdict-score {
  font-size: 0.68rem;
  color: #8b8d98;
}
.pc-block {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.pc-block-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8b8d98;
}
.pc-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.pc-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.pc-main {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.pc-title {
  font-size: 0.74rem;
  font-weight: 600;
  color: #f0f0f0;
}
.pc-sub {
  font-size: 0.62rem;
  color: #8b8d98;
}
.pc-reason {
  font-size: 0.62rem;
  color: #8b8d98;
  text-align: right;
  max-width: 55%;
}
.pc-missing {
  font-size: 0.68rem;
  color: #ff7a1a;
}
.pc-note {
  font-size: 0.66rem;
  color: #8b8d98;
  font-style: italic;
}
.pc-error {
  font-size: 0.7rem;
  color: #ff7a1a;
}
</style>
