<script setup lang="ts">
/**
 * HelpCenter — Ayuda bien desarrollada:
 * 1. Respuestas vivas (calculadas del estado real del sistema)
 * 2. Workflows guiados (loops diarios paso a paso)
 * 3. FAQ completa con búsqueda
 * 4. Acceso directo al Copilot
 */
import {
  Bot,
  ChevronDown,
  Compass,
  ExternalLink,
  HelpCircle,
  Lightbulb,
  Route,
  Search,
  Sparkles,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'

interface QuickAnswer {
  question: string
  answer: string
  action?: { label: string; path: string }
  priority: string
}

interface WorkflowStep {
  n: number
  text: string
  path?: string
}

interface Workflow {
  id: string
  title: string
  when: string
  steps: WorkflowStep[]
}

interface FaqItem {
  q: string
  a: string
  category: string
  link?: { path: string; label: string }
}

const loading = ref(true)
const answers = ref<QuickAnswer[]>([])
const workflows = ref<Workflow[]>([])

async function load(): Promise<void> {
  loading.value = true
  const [qaRes, wfRes] = await Promise.allSettled([
    api.get<{ answers: QuickAnswer[] }>('/help/quick-answers'),
    api.get<{ workflows: Workflow[] }>('/help/workflows'),
  ])
  if (qaRes.status === 'fulfilled') answers.value = qaRes.value.answers ?? []
  if (wfRes.status === 'fulfilled') workflows.value = wfRes.value.workflows ?? []
  loading.value = false
}

onMounted(load)

// ── FAQ (estática, curada) ──
const faqs: FaqItem[] = [
  {
    q: '¿Cómo gano más dinero con OWNEX?',
    a: 'OWNEX maximiza tu $/hora: descubre oportunidades, las rankea por EV (valor esperado = pago × probabilidad), prepara las entregas en el Work Bank y te dice exactamente qué hacer con el Daily Brief. Tu parte: ejecutar la acción #1 cada día y enviar las entregas listas antes de empezar trabajo nuevo.',
    category: 'Dinero',
    link: { path: '/', label: 'Ver Daily Brief' },
  },
  {
    q: '¿Qué es el "EV" y por qué importa?',
    a: 'EV (Expected Value) = pago estimado × probabilidad de éxito. Una tarea de $500 con 20% de probabilidad vale $100 de EV; una de $100 con 90% vale $90. OWNEX prioriza por EV/hora humana para que tu tiempo vaya siempre a la tarea de mayor retorno esperado.',
    category: 'Dinero',
  },
  {
    q: '¿Qué es el Work Bank y "ready_to_deliver"?',
    a: 'El Work Bank guarda trabajos preparados (draft + verificación de términos + match de perfil). "Ready to deliver" = listo para enviar a la plataforma en un click. Cada entrega enviada convierte trabajo preparado en dinero real.',
    category: 'Dinero',
    link: { path: '/operations/work-queue', label: 'Abrir Work Queue' },
  },
  {
    q: '¿Qué hago cada día? (rutina recomendada)',
    a: '1) Abrí el Command Center y leé el Daily Brief. 2) Ejecutá la One Action. 3) Si hay entregas listas, envialas. 4) Marcá lo completado en la cola. 10-15 minutos de gestión + tu tiempo de ejecución. Todo lo demás OWNEX lo hace solo.',
    category: 'Dinero',
    link: { path: '/', label: 'Ir al Command Center' },
  },
  {
    q: '¿Por qué no hay entregas listas?',
    a: 'Puede que falte conectar plataformas (los trabajos quedan "needs_access") o que el discovery siga corriendo. Revisá Integraciones → Cuentas para desbloquear trabajos, y el ranking "¿Dónde trabajo hoy?" para priorizar el onboarding de la plataforma con mejor rate.',
    category: 'Dinero',
    link: { path: '/integrations/accounts', label: 'Integraciones' },
  },
  {
    q: '¿Qué es un item "needs_access"?',
    a: 'Un trabajo que OWNEX preparó pero no puede entregarse hasta que conectes la cuenta de esa plataforma. Conectá las credenciales en Integraciones → Cuentas y el trabajo vuelve a la cola de entregas.',
    category: 'Dinero',
    link: { path: '/integrations/accounts', label: 'Conectar cuentas' },
  },
  {
    q: '¿Qué hago si aparece la alerta "IA no disponible"?',
    a: 'El proveedor de IA activo no responde (por ejemplo Ollama caído). Verificá Settings → IA: cambiá de proveedor o reiniciá el servicio. Mientras tanto el sistema opera en modo degradado: menos análisis, pero no se pierde nada.',
    category: 'Sistema',
    link: { path: '/operations/settings', label: 'Settings → IA' },
  },
  {
    q: '¿Qué significa el % de "salud" del sistema?',
    a: 'Es el resultado del health check: servicios de segundo plano activos (scheduler, discovery, EventBus), bases de datos accesibles y errores recientes. Verde ≥90%: todo funciona. Amarillo: degradado pero operativo. Rojo: revisá el Centro de Alertas.',
    category: 'Sistema',
    link: { path: '/copilot/alerts', label: 'Centro de Alertas' },
  },
  {
    q: '¿OWNEX ejecuta acciones sin mi permiso?',
    a: 'No. Todo lo que gasta dinero o envía datos pasa por un Human Gate: aparece como "Necesita tu aprobación" en la cola o en el Daily Brief. Nada se envía sin que lo apruebes explícitamente.',
    category: 'Sistema',
  },
  {
    q: '¿Dónde veo cuánto gané?',
    a: 'El saldo verificado y pendiente vive en la sidebar (siempre visible) y el detalle en Capital → Ledger. Los pagos se registran desde el payment tracker cuando la plataforma paga.',
    category: 'Dinero',
    link: { path: '/capital', label: 'Ver Capital' },
  },
  {
    q: '¿Cómo sumo una plataforma nueva?',
    a: 'Mirá el ranking "¿Dónde trabajo hoy?" (muestra rate efectivo y readiness por plataforma), abrí la guía de onboarding, completá el registro y guardá credenciales. La plataforma empieza a alimentar tu radar automáticamente.',
    category: 'Sistema',
    link: { path: '/operations/platforms', label: 'Guías de plataforma' },
  },
  {
    q: '¿Qué es el "Setup Checklist"?',
    a: 'La configuración progresiva del sistema, un ítem por día. Cada ítem completado desbloquea plataformas, fuentes u horizontes de ingreso. Al 100% tenés todas las fuentes activas.',
    category: 'Sistema',
    link: { path: '/setup/checklist', label: 'Abrir checklist' },
  },
]

const searchQuery = ref('')
const openFaq = ref<number | null>(null)
const openWf = ref<string | null>(workflows.value[0]?.id ?? null)

const filteredFaqs = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return faqs
  return faqs.filter((f) => f.q.toLowerCase().includes(q) || f.a.toLowerCase().includes(q))
})

const groupedFaqs = computed(() => {
  const map: Record<string, FaqItem[]> = {}
  for (const f of filteredFaqs.value) (map[f.category] ??= []).push(f)
  return map
})

function goto(path?: string): void {
  if (path) window.location.hash = path
}

function toggleWf(id: string): void {
  openWf.value = openWf.value === id ? null : id
}

const priorityVariant = (p: string) =>
  p === 'critical' ? 'error' : p === 'high' ? 'warning' : p === 'medium' ? 'info' : 'default'
</script>

<template>
  <div class="space-y-4 p-4 sm:space-y-6 sm:p-6">
    <!-- Header -->
    <div class="animate-in">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Ayuda</p>
      <h1 class="font-display text-xl sm:text-2xl font-bold text-foreground">Centro de Ayuda</h1>
      <p class="mt-0.5 text-sm text-muted-foreground">Respuestas del estado real de tu sistema + guías paso a paso.</p>
    </div>

    <LoadingState v-if="loading" />

    <template v-else>
      <!-- 1. LIVE QUICK ANSWERS -->
      <div class="grid gap-3 sm:grid-cols-2">
        <Card v-for="(ans, i) in answers" :key="i" class="p-4">
          <div class="flex items-start gap-2.5">
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <Lightbulb class="h-4 w-4 text-primary" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold">{{ ans.question }}</p>
                <Badge v-if="ans.priority === 'critical' || ans.priority === 'high'" :variant="priorityVariant(ans.priority)" class="shrink-0 text-[9px] px-1.5 py-0">
                  {{ ans.priority === 'critical' ? 'URGENTE' : 'IMPORTANTE' }}
                </Badge>
              </div>
              <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{{ ans.answer }}</p>
              <button v-if="ans.action" class="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline" @click="goto(ans.action?.path)">
                {{ ans.action.label }} <ExternalLink class="h-3 w-3" />
              </button>
            </div>
          </div>
        </Card>
      </div>

      <!-- 2. GUIDED WORKFLOWS -->
      <Card class="p-0">
        <div class="flex items-center gap-2 border-b border-border/30 px-4 py-3">
          <Route class="h-4 w-4 text-primary" />
          <span class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recorridos guiados</span>
        </div>
        <div class="divide-y divide-border/20">
          <div v-for="wf in workflows" :key="wf.id">
            <button class="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface/20" @click="toggleWf(wf.id)">
              <Compass class="h-4 w-4 shrink-0 text-muted-foreground" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold">{{ wf.title }}</p>
                <p class="truncate text-[11px] text-muted-foreground">{{ wf.when }}</p>
              </div>
              <ChevronDown class="h-4 w-4 shrink-0 text-muted-foreground transition-transform" :class="openWf === wf.id ? 'rotate-180' : ''" />
            </button>
            <div v-if="openWf === wf.id" class="space-y-1 px-4 pb-4 pl-11">
              <div v-for="s in wf.steps" :key="s.n" class="flex items-start gap-2.5 rounded-lg px-2 py-1.5 hover:bg-surface/20">
                <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 font-mono text-[10px] font-bold text-primary">{{ s.n }}</span>
                <p class="flex-1 text-xs leading-relaxed text-foreground/90">{{ s.text }}</p>
                <button v-if="s.path" class="shrink-0 text-[11px] font-medium text-primary hover:underline" @click="goto(s.path)">Ir</button>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <!-- 3. FAQ -->
      <div>
        <div class="relative max-w-md">
          <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar en preguntas frecuentes..."
            class="w-full rounded-lg border border-border/30 bg-surface/50 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition-all focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
        </div>

        <div v-for="(items, cat) in groupedFaqs" :key="cat" class="mt-4 space-y-2">
          <div class="flex items-center gap-2">
            <HelpCircle class="h-4 w-4 text-primary" />
            <h2 class="text-sm font-semibold tracking-tight">{{ cat }}</h2>
            <span class="font-mono text-[10px] text-muted-foreground">({{ items.length }})</span>
          </div>
          <div v-for="(f, i) in items" :key="f.q" class="overflow-hidden rounded-lg border border-border/30 transition-all">
            <button class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium transition-colors hover:bg-surface/20" @click="openFaq = openFaq === `${cat}-${i}` ? null : `${cat}-${i}`">
              <span>{{ f.q }}</span>
              <ChevronDown class="h-4 w-4 shrink-0 text-muted-foreground transition-transform" :class="openFaq === `${cat}-${i}` ? 'rotate-180' : ''" />
            </button>
            <div v-if="openFaq === `${cat}-${i}`" class="border-t border-border/20 px-4 py-3">
              <p class="text-sm leading-relaxed text-muted-foreground">{{ f.a }}</p>
              <router-link v-if="f.link" :to="f.link.path" class="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80">
                {{ f.link.label }} <ExternalLink class="h-3 w-3" />
              </router-link>
            </div>
          </div>
        </div>

        <p v-if="filteredFaqs.length === 0" class="py-8 text-center text-sm text-muted-foreground">Sin resultados para "{{ searchQuery }}".</p>
      </div>

      <!-- 4. Copilot CTA -->
      <Card class="flex flex-col items-center gap-3 border-primary/25 bg-primary/5 p-6 text-center sm:flex-row sm:text-left">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/15">
          <Bot class="h-5 w-5 text-primary" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold">¿Seguís con dudas? Preguntale a OWNEX AI</p>
          <p class="mt-0.5 text-xs text-muted-foreground">Responde con el estado real de tu sistema: oportunidades, pagos, salud y más.</p>
        </div>
        <router-link to="/ai" class="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-background transition-opacity hover:opacity-90">
          <Sparkles class="h-3.5 w-3.5" /> Abrir chat
        </router-link>
      </Card>
    </template>
  </div>
</template>
