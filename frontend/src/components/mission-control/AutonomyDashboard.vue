<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getPaymentTrackerStatus,
  getTrustEngineStatus,
  getClosedLoopStatus,
  type PaymentTrackerStatus,
  type TrustEngineStatus,
  type ClosedLoopStatus,
} from '@/services/controlPanel'

const paymentStatus = ref<PaymentTrackerStatus>({
  total_payments: 0,
  pending_confirmation: 0,
  confirmed: 0,
  total_earnings_30d_usd: 0,
  platforms_with_webhooks: 0,
  platforms_with_polling: 0,
  platforms: [],
})

const trustStatus = ref<TrustEngineStatus>({
  platforms_with_data: 0,
  platforms_with_high_trust: 0,
  high_trust_platforms: [],
  auto_approval_enabled: false,
  auto_approval_threshold_usd: 50,
  min_trust_level: 'high',
  total_opportunities_tracked: 0,
  total_earnings_tracked_usd: 0,
})

const closedLoopStatus = ref<ClosedLoopStatus>({
  config: {
    auto_learn_from_payments: false,
    auto_update_trust: false,
    auto_update_profile: false,
  },
  recommendation_improvement: {
    trust_status: trustStatus.value,
    payment_status: paymentStatus.value,
    learning_active: false,
    profile_updates_enabled: false,
    trust_updates_enabled: false,
  },
})

const loading = ref(true)

const autonomyPercentage = computed(() => {
  if (trustStatus.value.auto_approval_enabled && trustStatus.value.platforms_with_high_trust > 0) {
    return Math.min(100, trustStatus.value.platforms_with_high_trust * 20)
  }
  return 0
})

const autoApprovalLabel = computed(() => {
  if (trustStatus.value.auto_approval_enabled) {
    return `Activo (hasta $${trustStatus.value.auto_approval_threshold_usd})`
  }
  return 'Inactivo'
})

async function load() {
  loading.value = true
  const [p, t, c] = await Promise.all([
    getPaymentTrackerStatus(),
    getTrustEngineStatus(),
    getClosedLoopStatus(),
  ])
  paymentStatus.value = p
  trustStatus.value = t
  closedLoopStatus.value = c
  loading.value = false
}

onMounted(() => load())
</script>

<template>
  <section class="autonomy">
    <div class="autonomy-head">
      <h3 class="autonomy-title">AUTONOMÍA</h3>
      <span class="autonomy-badge">{{ autonomyPercentage }}% auto</span>
    </div>

    <p v-if="loading" class="autonomy-muted">Cargando estado de autonomía...</p>

    <template v-else>
      <!-- Auto-approval status -->
      <div class="autonomy-block">
        <span class="autonomy-label">Auto-aprobación</span>
        <span class="autonomy-value" :class="{ active: trustStatus.auto_approval_enabled }">
          {{ autoApprovalLabel }}
        </span>
      </div>

      <!-- Trust metrics -->
      <div class="autonomy-grid">
        <div class="autonomy-item">
          <span class="autonomy-item-label">Plataformas con datos</span>
          <span class="autonomy-item-value">{{ trustStatus.platforms_with_data }}</span>
        </div>
        <div class="autonomy-item">
          <span class="autonomy-item-label">Plataformas de alta confianza</span>
          <span class="autonomy-item-value">{{ trustStatus.platforms_with_high_trust }}</span>
        </div>
        <div class="autonomy-item">
          <span class="autonomy-item-label">Oportunidades rastreadas</span>
          <span class="autonomy-item-value">{{ trustStatus.total_opportunities_tracked }}</span>
        </div>
        <div class="autonomy-item">
          <span class="autonomy-item-label">Ingresos rastreados</span>
          <span class="autonomy-item-value">${{ Math.round(trustStatus.total_earnings_tracked_usd) }}</span>
        </div>
      </div>

      <!-- Payment tracking -->
      <div class="autonomy-block">
        <span class="autonomy-label">Pagos 30 días</span>
        <span class="autonomy-value">${{ Math.round(paymentStatus.total_earnings_30d_usd) }}</span>
      </div>

      <div class="autonomy-block">
        <span class="autonomy-label">Pagos pendientes</span>
        <span class="autonomy-value" :class="{ warning: paymentStatus.pending_confirmation > 0 }">
          {{ paymentStatus.pending_confirmation }}
        </span>
      </div>

      <!-- Closed loop status -->
      <div class="autonomy-learning">
        <span class="autonomy-learning-label">Closed Loop</span>
        <div class="autonomy-learning-status">
          <span class="autonomy-learning-item">
            {{ closedLoopStatus.config.auto_learn_from_payments ? '✓' : '✗' }} Aprender de pagos
          </span>
          <span class="autonomy-learning-item">
            {{ closedLoopStatus.config.auto_update_trust ? '✓' : '✗' }} Actualizar confianza
          </span>
          <span class="autonomy-learning-item">
            {{ closedLoopStatus.config.auto_update_profile ? '✓' : '✗' }} Actualizar perfil
          </span>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.autonomy {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.autonomy-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.autonomy-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.autonomy-badge {
  margin-left: auto;
  font-size: 0.65rem;
  font-weight: 700;
  color: #00d5ff;
  background: rgba(0, 213, 255, 0.12);
  border: 1px solid rgba(0, 213, 255, 0.3);
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
}
.autonomy-muted {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}
.autonomy-block {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.autonomy-block:last-child {
  border-bottom: none;
}
.autonomy-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.autonomy-value {
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
}
.autonomy-value.active {
  color: #00e39a;
}
.autonomy-value.warning {
  color: #ff7a1a;
}
.autonomy-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  padding: 0.4rem 0;
}
.autonomy-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.autonomy-item-label {
  font-size: 0.62rem;
  color: rgba(255, 255, 255, 0.5);
}
.autonomy-item-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}
.autonomy-learning {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.4rem 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
}
.autonomy-learning-label {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.5);
}
.autonomy-learning-status {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}
.autonomy-learning-item {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.7);
}
</style>
