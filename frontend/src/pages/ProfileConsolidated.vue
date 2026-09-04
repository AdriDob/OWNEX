<script setup lang="ts">
/**
 * Profile — Consolidated page with tabs.
 * Combines: ProfileKit + Identity
 */
import { ref, computed, onMounted } from 'vue'
import { User, Shield, Zap, Copy, Check, RefreshCw } from '@lucide/vue'
import Tabs from '@/components/ui/Tabs.vue'

const activeTab = ref('kit')
const loading = ref(true)
const profile = ref<any>(null)
const identity = ref<any>(null)
const copied = ref(false)

async function fetchData() {
  loading.value = true
  try {
    const [pRes, iRes] = await Promise.allSettled([
      fetch('/api/profile-kit').then(r => r.json()),
      fetch('/api/identity').then(r => r.json()),
    ])
    if (pRes.status === 'fulfilled') profile.value = pRes.value
    if (iRes.status === 'fulfilled') identity.value = iRes.value
  } catch { /* silent */ }
  loading.value = false
}

const tabs = computed(() => [
  { id: 'kit', label: 'Profile Kit', icon: User },
  { id: 'identity', label: 'Identity', icon: Shield },
  { id: 'skills', label: 'Skills', icon: Zap },
])

async function copyProfile() {
  if (!profile) return
  const text = JSON.stringify(profile.value, null, 2)
  await navigator.clipboard.writeText(text)
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}

onMounted(fetchData)
</script>

<template>
  <div class="min-h-screen bg-background p-6">
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Profile</h1>
        <p class="text-sm text-muted-foreground">Tu perfil, identidad y habilidades</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="copyProfile"
        >
          <Copy v-if="!copied" class="h-3 w-3" />
          <Check v-else class="h-3 w-3 text-emerald-400" />
          {{ copied ? 'Copied!' : 'Copy Profile' }}
        </button>
        <button
          class="flex items-center gap-1.5 rounded-lg border border-border/30 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="fetchData"
        >
          <RefreshCw class="h-3 w-3" />
        </button>
      </div>
    </div>

    <Tabs v-model="activeTab" :tabs="tabs">
      <!-- Profile Kit -->
      <template #kit>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Profile Information</h3>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Name</p>
                <p class="mt-1 text-sm text-foreground">{{ profile?.name || 'Not set' }}</p>
              </div>
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Email</p>
                <p class="mt-1 text-sm text-foreground">{{ profile?.email || 'Not set' }}</p>
              </div>
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Location</p>
                <p class="mt-1 text-sm text-foreground">{{ profile?.location || 'Not set' }}</p>
              </div>
              <div>
                <p class="text-[10px] font-mono text-muted-foreground">Experience</p>
                <p class="mt-1 text-sm text-foreground">{{ profile?.experience_level || 'beginner' }}</p>
              </div>
            </div>
          </div>

          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Platforms</h3>
            <div v-if="profile?.platforms?.length" class="flex flex-wrap gap-2">
              <span
                v-for="p in profile.platforms"
                :key="p"
                class="rounded-full border border-border/30 px-2 py-0.5 text-[10px] font-mono text-muted-foreground"
              >
                {{ p }}
              </span>
            </div>
            <p v-else class="text-xs text-muted-foreground">No platforms configured</p>
          </div>
        </div>
      </template>

      <!-- Identity -->
      <template #identity>
        <div v-if="loading" class="space-y-4">
          <div v-for="i in 3" :key="i" class="h-20 animate-pulse rounded-lg bg-surface/30" />
        </div>
        <div v-else class="space-y-4">
          <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
            <h3 class="mb-3 text-sm font-semibold text-foreground">Identity Vault</h3>
            <div class="space-y-2">
              <div
                v-for="(value, key) in (identity?.credentials || {})"
                :key="key"
                class="flex items-center justify-between rounded-lg border border-border/20 p-3"
              >
                <span class="font-mono text-xs text-muted-foreground">{{ key }}</span>
                <span class="font-mono text-xs text-foreground">••••••••</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Skills -->
      <template #skills>
        <div class="rounded-xl border border-border/30 bg-surface/50 p-5">
          <h3 class="mb-3 text-sm font-semibold text-foreground">Skills & Experience</h3>
          <div v-if="profile?.skills?.length" class="space-y-2">
            <div
              v-for="skill in profile.skills"
              :key="skill.name"
              class="rounded-lg border border-border/20 p-3"
            >
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-foreground">{{ skill.name }}</span>
                <span class="font-mono text-xs text-muted-foreground">{{ skill.level }}</span>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-8">
            <Zap class="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p class="mt-2 text-sm text-muted-foreground">No skills registered</p>
            <p class="mt-1 text-xs text-muted-foreground/60">Complete tasks to build your profile</p>
          </div>
        </div>
      </template>
    </Tabs>
  </div>
</template>
