<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Copy, Check, RefreshCw, UserRound, Globe, Loader2, Download } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'
import {
  fetchProfileKitStatus,
  saveProfileKit,
  generateProfileKit,
  type ProfileKitProfile,
  type ProfileKitStatus,
  type ProfileKitField,
} from '@/services/ownexData'

const profile = ref<ProfileKitProfile>({
  name: '',
  country: 'Argentina',
  skills: [],
  experience_level: 'none',
  availability_hours: 40,
  github_url: '',
  linkedin_url: '',
  portfolio_url: '',
})

const availablePlatforms = ref<string[]>([])
const skillsInput = ref('')
const lang = ref<'es' | 'en'>('en')
const activePlatform = ref('fiverr')
const kits = ref<Record<string, Record<string, ProfileKitField[]>>>({})
const status = ref<ProfileKitStatus | null>(null)
const saved = ref(false)
const loading = ref(false)
const copying = ref<string | null>(null)
const error = ref('')

const skillList = computed(() =>
  skillsInput.value.split(',').map(s => s.trim()).filter(Boolean),
)

const currentFields = computed<ProfileKitField[]>(() => {
  const platformKit = kits.value[lang.value]?.[activePlatform.value]
  return platformKit ?? []
})

const currentLangLabel = computed(() => (lang.value === 'es' ? 'ES' : 'EN'))

const PLATFORM_LABELS: Record<string, string> = {
  fiverr: 'Fiverr',
  github: 'GitHub',
  hackerone: 'HackerOne',
  bugcrowd: 'Bugcrowd',
  intigriti: 'Intigriti',
  yeswehack: 'YesWeHack',
  opire: 'Opire',
  issuehunt: 'IssueHunt',
  algora: 'Algora',
  outlier: 'Outlier',
  mindrift: 'Mindrift',
  linkedin: 'LinkedIn',
}

function toProfilePayload(): ProfileKitProfile {
  return {
    ...profile.value,
    skills: skillList.value,
  }
}

async function loadStatus() {
  try {
    status.value = await fetchProfileKitStatus()
    availablePlatforms.value = status.value.available_platforms ?? []
    if (status.value.profile) {
      const p = status.value.profile as unknown as ProfileKitProfile
      profile.value = { ...profile.value, ...p }
      if (p.skills) skillsInput.value = (p.skills as string[]).join(', ')
    }
  } catch {
    availablePlatforms.value = []
  }
}

async function runGenerate() {
  loading.value = true
  error.value = ''
  try {
    const resp = await generateProfileKit(toProfilePayload())
    kits.value = resp.kits
    saved.value = true
  } catch {
    error.value = 'No se pudo generar el kit. Verificá que el backend esté corriendo.'
  } finally {
    loading.value = false
  }
}

async function runSave() {
  loading.value = true
  error.value = ''
  try {
    await saveProfileKit(toProfilePayload())
    await runGenerate()
  } catch {
    error.value = 'No se pudo guardar el perfil.'
  } finally {
    loading.value = false
  }
}

async function copyField(key: string, text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  copying.value = key
  setTimeout(() => (copying.value = null), 1500)
}

function copyAll() {
  if (!currentFields.value.length) return
  const block = currentFields.value
    .map(f => `${f.label}: ${f.text}`)
    .join('\n\n')
  copying.value = 'all'
  navigator.clipboard
    ?.writeText(block)
    .catch(() => {
      const ta = document.createElement('textarea')
      ta.value = block
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    })
  setTimeout(() => (copying.value = null), 1500)
}

function exportMarkdown() {
  const langKit = kits.value[lang.value]
  if (!langKit) return
  const md = [
    `# OWNEX Profile Kit — ${currentLangLabel}`,
    '',
    `> Generado ${new Date().toISOString()} · Perfil de ${profile.value.name || 'Desarrollador'} (${profile.value.country})`,
    '',
    ...availablePlatforms.value.flatMap(platform => {
      const fields = langKit[platform] ?? []
      if (!fields.length) return []
      return [
        `## ${PLATFORM_LABELS[platform] ?? platform}`,
        '',
        ...fields.flatMap(f => ['### ' + f.label, '', f.text, '']),
      ]
    }),
  ].join('\n')
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ownex-profile-kit-${lang.value}.md`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadStatus()
  if (availablePlatforms.value.length) {
    activePlatform.value = availablePlatforms.value[0]
  }
  await runGenerate()
})
</script>

<template>
  <div class="mx-auto max-w-6xl px-6 py-8">
    <!-- Header -->
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="font-display text-2xl font-bold tracking-tight text-foreground">Profile Kit</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Textos listos para copiar en cada plataforma, generados desde tu perfil. Bilingüe EN + ES.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex items-center rounded-lg border border-border/40 bg-surface/40 p-0.5">
          <button
            v-for="l in (['en', 'es'] as const)"
            :key="l"
            :class="[
              'rounded-md px-3 py-1.5 font-mono text-xs font-semibold uppercase transition-all',
              lang === l ? 'bg-white text-black' : 'text-muted-foreground hover:text-foreground',
            ]"
            @click="lang = l"
          >
            {{ l }}
          </button>
        </div>
        <Button :disabled="loading" @click="runSave">
          <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
          <RefreshCw v-else class="h-4 w-4" />
          {{ saved ? 'Guardar y regenerar' : 'Guardar perfil' }}
        </Button>
      </div>
    </div>

    <p v-if="error" class="mb-4 rounded-lg border border-error/30 bg-error/10 px-4 py-2 text-sm text-error">
      {{ error }}
    </p>

    <div class="grid gap-6 lg:grid-cols-[320px_1fr]">
      <!-- Perfil -->
      <div class="rounded-xl border border-border/40 bg-background/60 p-5">
        <div class="mb-4 flex items-center gap-2">
          <UserRound class="h-4 w-4 text-primary" />
          <h2 class="font-display text-sm font-bold uppercase tracking-[0.15em] text-foreground">Tu perfil</h2>
        </div>

        <div class="space-y-4">
          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Nombre</label>
            <input
              v-model="profile.name"
              type="text"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="Adriel"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">País</label>
            <input
              v-model="profile.country"
              type="text"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Skills (separadas por coma)
            </label>
            <input
              v-model="skillsInput"
              type="text"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="Python, Go, TypeScript"
            />
            <div v-if="skillList.length" class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="s in skillList"
                :key="s"
                class="rounded-full border border-border/40 bg-surface/40 px-2 py-0.5 font-mono text-[10px] text-foreground"
              >
                {{ s }}
              </span>
            </div>
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Experiencia (años)
            </label>
            <input
              v-model="profile.experience_level"
              type="text"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="none"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Disponibilidad (hs/semana)
            </label>
            <input
              v-model.number="profile.availability_hours"
              type="number"
              min="0"
              max="168"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">GitHub</label>
            <input
              v-model="profile.github_url"
              type="url"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="https://github.com/usuario"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">LinkedIn</label>
            <input
              v-model="profile.linkedin_url"
              type="url"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="https://linkedin.com/in/usuario"
            />
          </div>

          <div>
            <label class="mb-1 block font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Portfolio</label>
            <input
              v-model="profile.portfolio_url"
              type="url"
              class="w-full rounded-lg border border-border/40 bg-surface/40 px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="https://tusitio.com"
            />
          </div>
        </div>
      </div>

      <!-- Kit -->
      <div class="rounded-xl border border-border/40 bg-background/60 p-5">
        <div class="mb-4 flex items-center gap-2">
          <Globe class="h-4 w-4 text-primary" />
          <h2 class="font-display text-sm font-bold uppercase tracking-[0.15em] text-foreground">Kit generado</h2>
          <span class="ml-auto rounded-full border border-border/40 px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
            {{ currentLangLabel }} · {{ PLATFORM_LABELS[activePlatform] ?? activePlatform }}
          </span>
        </div>

        <!-- Platform tabs -->
        <div class="mb-4 flex flex-wrap items-center gap-1.5">
          <button
            v-for="p in availablePlatforms"
            :key="p"
            :class="[
              'rounded-lg border px-3 py-1.5 font-mono text-[11px] font-medium transition-all',
              activePlatform === p
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border/40 text-muted-foreground hover:border-border hover:text-foreground',
            ]"
            @click="activePlatform = p"
          >
            {{ PLATFORM_LABELS[p] ?? p }}
          </button>
          <button
            class="ml-auto flex items-center gap-1 rounded-md border border-border/40 px-2.5 py-1.5 font-mono text-[10px] text-muted-foreground transition-all hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!currentFields.length"
            @click="copyAll"
          >
            <Check v-if="copying === 'all'" class="h-3 w-3 text-success" />
            <Copy v-else class="h-3 w-3" />
            {{ copying === 'all' ? 'Todo copiado' : 'Copiar todo' }}
          </button>
          <button
            class="flex items-center gap-1.5 rounded-md border border-border/40 px-2.5 py-1.5 font-mono text-[10px] text-muted-foreground transition-all hover:border-primary hover:text-primary"
            :disabled="!Object.keys(kits[lang] ?? {}).length"
            @click="exportMarkdown"
          >
            <Download class="h-3 w-3" />
            Exportar .md
          </button>
        </div>

        <!-- Fields -->
        <div class="space-y-3">
          <div
            v-for="field in currentFields"
            :key="field.key"
            class="group rounded-lg border border-border/30 bg-surface/30 p-3 transition-colors hover:border-border/60"
          >
            <div class="mb-1.5 flex items-center justify-between">
              <span class="font-mono text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {{ field.label }}
              </span>
              <span class="font-mono text-[10px] text-muted-foreground/50">{{ field.key }}</span>
              <button
                class="flex items-center gap-1 rounded-md border border-border/40 px-2 py-1 font-mono text-[10px] text-muted-foreground transition-all hover:border-primary hover:text-primary"
                @click="copyField(field.key, field.text)"
              >
                <Check v-if="copying === field.key" class="h-3 w-3 text-success" />
                <Copy v-else class="h-3 w-3" />
                {{ copying === field.key ? 'Copiado' : 'Copiar' }}
              </button>
            </div>
            <pre class="whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground">{{ field.text }}</pre>
          </div>

          <p v-if="!currentFields.length" class="py-8 text-center text-sm text-muted-foreground">
            Sin campos generados todavía. Completá tu perfil y guardá.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
