<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Sun, AlertTriangle, ArrowRight, Bot } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import { fetchDirectWorkDailyBrief, type DailyBrief } from '@/services/ownexData'

const router = useRouter()

const brief = ref<DailyBrief | null>(null)
const loading = ref(true)
const error = ref(false)

async function fetchBriefing() {
  loading.value = true
  error.value = false
  try {
    brief.value = await fetchDirectWorkDailyBrief(5)
  } catch { error.value = true }
  finally { loading.value = false }
}

onMounted(fetchBriefing)
</script>

<template>
  <div class="max-w-lg mx-auto space-y-6">
    <template v-if="loading && !brief">
      <Skeleton class="h-32 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error && !brief">
      <div class="animate-in space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Daily</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Today</h1>
        <p class="text-sm text-muted-foreground">System ready</p>
      </div>
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">Could not load briefing</p>
        <button @click="fetchBriefing"
          class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white"
        >Retry</button>
      </Card>
    </template>

    <template v-else>
      <div class="animate-in space-y-1">
        <div class="flex items-center gap-2">
          <p class="text-xs font-bold uppercase tracking-widest text-primary">Daily Brief</p>
          <Bot class="h-5 w-5 text-primary" />
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Today</h1>
        <p class="text-sm text-muted-foreground">{{ brief?.summary || 'System ready' }}</p>
      </div>

      <!-- Best Source -->
      <div v-if="brief?.best_sources && brief.best_sources.length > 0" class="animate-in">
        <Card class="p-4 border-primary/20 cursor-pointer transition-all hover:border-primary/50"
          @click="window.open(brief!.best_sources![0].url, '_blank')"
        >
          <div class="flex items-center gap-2 mb-2">
            <p class="text-[10px] font-bold uppercase tracking-wider text-primary">
              {{ brief.best_sources[0].category }}
            </p>
            <Badge>{{ brief.best_sources[0].trust_score }}/100 trust</Badge>
          </div>
          <p class="text-base font-bold text-foreground mb-1">
            {{ brief.best_sources[0].name }}
          </p>
          <p class="text-sm text-muted-foreground mb-2">
            {{ brief.best_sources[0].average_reward }} avg reward ·
            {{ brief.best_sources[0].earning_potential }} potential
          </p>
          <div class="flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 rounded-md bg-primary/20 px-3 py-1 text-[10px] font-semibold text-white">
              Explore <ArrowRight class="h-3 w-3" />
            </span>
          </div>
        </Card>
      </div>

      <!-- Next Actions -->
      <div v-if="brief?.ranked && brief.ranked.length > 0" class="animate-in space-y-3">
        <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
          Next Actions ({{ brief.scanned }} scanned)
        </p>
        <div v-for="o in brief.ranked.slice(0, 3)" :key="o.platform || o.id">
          <Card class="p-4 flex items-center justify-between transition-all hover:border-primary/30">
            <div>
              <p class="text-sm font-semibold text-foreground">{{ o.platform || o.id }}</p>
              <p class="text-[11px] text-muted-foreground capitalize">{{ o.category }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm font-bold text-success">
                ${{ o.estimated_reward?.toLocaleString() || 0 }}
              </span>
              <span class="text-[10px] text-muted-foreground">
                {{ (o.acceptance_probability * 100).toFixed(0) }}%
              </span>
            </div>
          </Card>
        </div>
      </div>

      <!-- Learning / Skill Gap -->
      <div v-if="brief?.learning?.missing_skills && brief.learning.missing_skills.length > 0" class="animate-in">
        <details class="cursor-pointer">
          <summary class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground py-1 flex items-center gap-2">
            <Sun class="h-3 w-3" />
            Skill Gap Detected
          </summary>
          <ul class="mt-2 space-y-1">
            <li v-for="skill in brief.learning.missing_skills.slice(0, 4)" :key="skill"
              class="text-xs text-muted-foreground flex justify-between">
              <span>{{ skill }}</span>
              <a v-if="brief.learning"
                :href="brief.learning.plan.find(p => p.skill === skill)?.resource || '#'"
                class="text-primary hover:underline">learn</a>
            </li>
          </ul>
        </details>
      </div>
    </template>
  </div>
</template>
