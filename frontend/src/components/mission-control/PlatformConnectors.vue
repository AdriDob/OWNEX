<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/lib/api'

const status = ref<any>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    status.value = await api.get('/api/platforms')
  } finally {
    loading.value = false
  }
}

async function syncAll() {
  await api.post('/api/platforms/sync')
  await load()
}

onMounted(() => load())
</script>

<template>
  <section class="platforms">
    <div class="platforms-head">
      <h3 class="platforms-title">PLATFORM CONNECTORS</h3>
      <button class="platforms-btn" @click="syncAll">Sync All</button>
    </div>

    <p v-if="loading" class="platforms-muted">Cargando conectores...</p>

    <template v-else>
      <div v-if="status" class="platforms-list">
        <div v-for="(p, name) in status.platforms || {}" :key="name" class="platforms-item">
          <span class="platforms-name">{{ name }}</span>
          <span class="platforms-status" :class="{ connected: p.connected }">
            {{ p.connected ? '✓ Conectado' : '✗ Desconectado' }}
          </span>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.platforms {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}
.platforms-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
}
.platforms-title {
  margin: 0;
  font-size: 0.85rem;
  letter-spacing: 0.12em;
}
.platforms-btn {
  border: 1px solid rgba(52, 211, 153, 0.4);
  border-radius: 8px;
  background: rgba(52, 211, 153, 0.1);
  color: #6ee7b7;
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.platforms-muted {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}
.platforms-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.platforms-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}
.platforms-name {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.9);
}
.platforms-status {
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.5);
}
.platforms-status.connected {
  color: #00e39a;
}
</style>
