<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { api } from '@/lib/api'

interface GuideStep {
  id: string
  title: string
  action: string
  status: string
  done: boolean
}

interface GuideCategory {
  id: string
  title: string
  desc: string
  steps: GuideStep[]
}

interface GuideData {
  success: boolean
  categories: GuideCategory[]
  total_steps: number
  done_steps: number
  progress: number
}

const guide = ref<GuideData | null>(null)
const loading = ref(true)
const open = ref<Record<string, boolean>>({})

const progress = computed(() => guide.value?.progress ?? 0)
const doneSteps = computed(() => guide.value?.done_steps ?? 0)
const totalSteps = computed(() => guide.value?.total_steps ?? 0)

async function load() {
  loading.value = true
  try {
    guide.value = await api.get<GuideData>('/api/guide/master')
  } catch {
    guide.value = null
  } finally {
    loading.value = false
  }
}

function toggle(id: string) {
  open.value[id] = !open.value[id]
}

function stepClass(s: GuideStep) {
  return s.done ? 'mg-step done' : 'mg-step'
}

onMounted(load)
</script>

<template>
  <section class="mg">
    <div class="mg-head">
      <h3 class="mg-title">GUÍA MAESTRA · EMPEZÁ A GANAR</h3>
      <span v-if="guide" class="mg-progress">{{ guide.progress }}%</span>
    </div>

    <p v-if="loading" class="mg-muted">Revisando qué te falta...</p>
    <p v-else-if="!guide" class="mg-muted">Guía no disponible.</p>

    <template v-else>
      <!-- Barra de progreso -->
      <div class="mg-bar">
        <div class="mg-bar-fill" :style="{ width: progress + '%' }" />
      </div>
      <p class="mg-muted">{{ doneSteps }} de {{ totalSteps }} pasos completados</p>

      <!-- Categorías -->
      <div
        v-for="cat in guide.categories"
        :key="cat.id"
        class="mg-cat"
        :class="{ open: open[cat.id] }"
      >
        <button class="mg-cat-head" @click="toggle(cat.id)">
          <div class="mg-cat-titles">
            <span class="mg-cat-title">{{ cat.title }}</span>
            <span class="mg-cat-desc">{{ cat.desc }}</span>
          </div>
          <span class="mg-cat-count">
            {{ cat.steps.filter((s) => s.done).length }}/{{ cat.steps.length }}
          </span>
        </button>

        <div v-if="open[cat.id]" class="mg-cat-body">
          <div
            v-for="s in cat.steps"
            :key="s.id"
            :class="stepClass(s)"
          >
            <input
              type="checkbox"
              :checked="s.done"
              disabled
              class="mg-check"
            />
            <div class="mg-step-info">
              <span class="mg-step-title">{{ s.title }}</span>
              <span class="mg-step-action">{{ s.action }}</span>
            </div>
            <span class="mg-step-badge">{{ s.done ? 'HECHO' : 'PENDIENTE' }}</span>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.mg {
  border: 1px solid var(--ownex-stroke, #2a2e37);
  border-radius: 12px;
  background: var(--ownex-surface, #111318);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.mg-head { display: flex; align-items: center; gap: 0.75rem; }
.mg-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.mg-progress { margin-left: auto; font-size: 0.8rem; font-weight: 700; color: #4ade80; }
.mg-muted { font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); margin: 0; }
.mg-bar {
  height: 6px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); overflow: hidden;
}
.mg-bar-fill { height: 100%; background: linear-gradient(90deg, #16a34a, #4ade80); transition: width 0.4s ease; }
.mg-cat {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  overflow: hidden;
}
.mg-cat-head {
  width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 0.6rem;
  background: transparent; border: none; padding: 0.6rem 0.7rem; cursor: pointer;
  color: inherit; font: inherit;
}
.mg-cat-head:hover { background: rgba(255, 255, 255, 0.03); }
.mg-cat-titles { display: flex; flex-direction: column; gap: 0.1rem; text-align: left; }
.mg-cat-title { font-size: 0.75rem; font-weight: 700; color: rgba(255, 255, 255, 0.9); }
.mg-cat-desc { font-size: 0.62rem; color: rgba(255, 255, 255, 0.45); }
.mg-cat-count { font-size: 0.65rem; font-weight: 700; color: #4ade80; flex-shrink: 0; }
.mg-cat-body { padding: 0.1rem 0.5rem 0.5rem; display: flex; flex-direction: column; gap: 0.3rem; }
.mg-step {
  display: flex; align-items: center; gap: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 0.4rem 0.5rem;
}
.mg-step.done { opacity: 0.7; border-color: rgba(22, 163, 74, 0.3); }
.mg-check { accent-color: #16a34a; }
.mg-step-info { display: flex; flex-direction: column; gap: 0.05rem; flex: 1; }
.mg-step-title { font-size: 0.72rem; font-weight: 600; color: rgba(255, 255, 255, 0.9); }
.mg-step-action { font-size: 0.62rem; color: rgba(255, 255, 255, 0.5); line-height: 1.4; }
.mg-step.done .mg-step-action { text-decoration: line-through; }
.mg-step-badge {
  font-size: 0.55rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 999px;
  color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); flex-shrink: 0;
}
.mg-step.done .mg-step-badge { color: #4ade80; border-color: rgba(74, 222, 128, 0.3); }
</style>