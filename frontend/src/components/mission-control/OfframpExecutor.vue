<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'

const status = ref<any>(null)
const defaultProvider = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    status.value = await api.get('/api/offramp')
  } finally {
    loading.value = false
  }
}

async function setDefault() {
  await api.post('/api/offramp/default', { provider: defaultProvider.value })
  await load()
}

onMounted(() => load())
</script>

<template>
  <section class="offramp">
    <div class="offramp-head">
      <h3 class="offramp-title">OFFRAMP · Conversión USD → ARS</h3>
    </div>

    <p v-if="loading" class="offramp-muted">Cargando offramp...</p>

    <template v-else>
      <div class="offramp-form">
        <input v-model="defaultProvider" placeholder="Proveedor (Binance, DolarApp...)" class="offramp-input" />
        <button class="offramp-btn" @click="setDefault">Set Default</button>
      </div>

      <div v-if="status" class="offramp-status">
        <span class="offramp-label">Default: {{ status.default_provider || 'Ninguno' }}</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.offramp {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.offramp-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.offramp-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.offramp-muted {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}
.offramp-form {
  display: flex;
  gap: 0.5rem;
}
.offramp-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 0.4rem 0.55rem;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.68rem;
}
.offramp-btn {
  border: 1px solid rgba(52, 211, 153, 0.4);
  border-radius: 8px;
  background: rgba(52, 211, 153, 0.1);
  color: #6ee7b7;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.offramp-status {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.offramp-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
