<template>
  <div class="daily-income-plan">
    <div class="header">
      <h3 class="title">Daily Income Plan</h3>
      <button class="btn-refresh" @click="loadPlan" :disabled="loading">
        <span v-if="!loading">↻</span>
        <span v-else class="spin">↻</span>
      </button>
    </div>

    <div v-if="loading" class="loading">Cargando...</div>

    <div v-else-if="plan" class="content">
      <div class="ceilings">
        <div class="ceiling optimistic">
          <span class="ceiling-label">Optimistic</span>
          <span class="ceiling-value">${{ plan.optimistic_max_usd }}</span>
        </div>
        <div class="ceiling realistic">
          <span class="ceiling-label">Realistic</span>
          <span class="ceiling-value">${{ plan.realistic_max_usd }}</span>
        </div>
        <div class="ceiling conservative">
          <span class="ceiling-label">Conservative</span>
          <span class="ceiling-value">${{ plan.conservative_max_usd }}</span>
        </div>
      </div>

      <div v-if="plan.daily_target_usd > 0" class="target">
        <span>Meta: ${{ plan.daily_target_usd }}</span>
        <span v-if="plan.gap_usd > 0" class="gap warning">Gap: ${{ plan.gap_usd }}</span>
        <span v-else class="gap success">Meta alcanzable</span>
      </div>

      <div v-if="plan.optimism_arguments.length" class="arguments">
        <span class="arg-title">Argumentos:</span>
        <ul>
          <li v-for="(arg, i) in plan.optimism_arguments.slice(0, 3)" :key="i">{{ arg }}</li>
        </ul>
      </div>

      <div v-if="plan.items.length" class="top-items">
        <span class="items-title">Top oportunidades:</span>
        <div class="item" v-for="(item, i) in plan.items.slice(0, 3)" :key="i">
          <span class="item-title">{{ item.title.slice(0, 40) }}</span>
          <span class="item-ev">${{ item.expected_value_usd }} EV</span>
        </div>
      </div>
    </div>

    <div v-else class="empty">Sin datos. Cargá la meta diaria para ver el plan.</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchMaxDailyIncome, type MaxDailyIncomePlan } from '@/services/ownexData'

const plan = ref<MaxDailyIncomePlan | null>(null)
const loading = ref(false)

async function loadPlan() {
  loading.value = true
  try {
    plan.value = await fetchMaxDailyIncome(100)
  } catch {
    plan.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadPlan)
</script>

<style scoped>
.daily-income-plan {
  background: #0a0b0f;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 16px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0;
}

.btn-refresh {
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #888;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
}

.btn-refresh:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}

.ceilings {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.ceiling {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.02);
}

.ceiling.optimistic { border: 1px solid rgba(0, 200, 83, 0.3); }
.ceiling.realistic { border: 1px solid rgba(33, 150, 243, 0.3); }
.ceiling.conservative { border: 1px solid rgba(255, 152, 0, 0.3); }

.ceiling-label {
  font-size: 10px;
  color: #888;
  text-transform: uppercase;
}

.ceiling-value {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.target {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #aaa;
  padding: 8px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.gap.warning { color: #ff7a1a; }
.gap.success { color: #00e39a; }

.arguments, .top-items {
  margin-top: 8px;
  font-size: 11px;
  color: #888;
}

.arg-title, .items-title {
  font-weight: 600;
  color: #aaa;
}

.arguments ul {
  margin: 4px 0 0 16px;
  padding: 0;
}

.arguments li {
  margin: 2px 0;
}

.item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}

.item-ev {
  color: #00e39a;
  font-weight: 600;
}

.loading, .empty {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 20px 0;
}

.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
