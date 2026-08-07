<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'

const status = ref<any>(null)
const cuil = ref('')
const categoria = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    status.value = await api.get('/api/tax-ar')
  } finally {
    loading.value = false
  }
}

async function setCuil() {
  await api.post('/api/tax-ar/cuil', { cuil: cuil.value })
  await load()
}

async function setCategoria() {
  await api.post('/api/tax-ar/categoria', { categoria: categoria.value })
  await load()
}

onMounted(() => load())
</script>

<template>
  <section class="tax-ar">
    <div class="tax-head">
      <h3 class="tax-title">TAX AR · Monotributo</h3>
    </div>

    <p v-if="loading" class="tax-muted">Cargando estado fiscal...</p>

    <template v-else>
      <div class="tax-form">
        <input v-model="cuil" placeholder="CUIL" class="tax-input" />
        <button class="tax-btn" @click="setCuil">Guardar CUIL</button>
      </div>

      <div class="tax-form">
        <input v-model="categoria" placeholder="Categoría" class="tax-input" />
        <button class="tax-btn" @click="setCategoria">Guardar Categoría</button>
      </div>

      <div v-if="status" class="tax-status">
        <span class="tax-label">Estado: {{ status.status || 'Desconocido' }}</span>
        <span class="tax-label">Ingresos: ${{ status.ingresos_usd || 0 }}</span>
      </div>
    </template>
  </section>
</template>

<style scoped>
.tax-ar {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.tax-head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.tax-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.tax-muted {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}
.tax-form {
  display: flex;
  gap: 0.5rem;
}
.tax-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 0.4rem 0.55rem;
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.68rem;
}
.tax-btn {
  border: 1px solid rgba(52, 211, 153, 0.4);
  border-radius: 8px;
  background: rgba(52, 211, 153, 0.1);
  color: #6ee7b7;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.tax-status {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.tax-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
