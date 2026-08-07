<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'

const status = ref<any>(null)
const cuit = ref('')
const certPath = ref('')
const keyPath = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    status.value = await api.get('/api/invoicer-ar')
  } finally {
    loading.value = false
  }
}

async function config() {
  await api.post('/api/invoicer-ar/config', {
    cuit: cuit.value,
    cert_path: certPath.value,
    key_path: keyPath.value,
  })
  await load()
}

onMounted(() => load())
</script>

<template>
  <section class="invoicer-ar">
    <div class="invoicer-head">
      <h3 class="invoicer-title">INVOICER AR · Facturación AFIP</h3>
    </div>

    <p v-if="loading" class="invoicer-muted">Cargando estado facturación...</p>

    <template v-else>
      <div class="invoicer-form">
        <input v-model="cuit" placeholder="CUIT" class="invoicer-input" />
        <input v-model="certPath" placeholder="Certificado (.crt)" class="invoicer-input" />
        <input v-model="keyPath" placeholder="Clave (.key)" class="invoicer-input" />
        <button class="invoicer-btn" @click="config">Configurar</button>
      </div>

      <div v-if="status" class="invoicer-status">
        <span class="invoicer-label">Estado: {{ status.status || 'No configurado' }}</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.invoicer-ar {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.invoicer-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.invoicer-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.invoicer-muted {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}
.invoicer-form {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.invoicer-input {
  flex: 1;
  min-width: 140px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 0.4rem 0.55rem;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.68rem;
}
.invoicer-btn {
  border: 1px solid rgba(52, 211, 153, 0.4);
  border-radius: 8px;
  background: rgba(52, 211, 153, 0.1);
  color: #6ee7b7;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.invoicer-status {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.invoicer-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
