<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDown, HelpCircle, Search, MessageCircle, ExternalLink, Bug, Shield, Cpu, LifeBuoy } from '@lucide/vue'
import Button from '@/components/ui/Button.vue'

interface FaqItem {
  q: string
  a: string
  category: string
  link?: { path: string; label: string }
}

const faqs: FaqItem[] = [
  // ── General ──
  { q: '¿Qué es OWNEX?', a: 'OWNEX es una plataforma de bug bounty automatizada. Escanea programas públicos y privados, ejecuta reconocimiento pasivo y activo, genera hipótesis de vulnerabilidades, valida hallazgos y gestiona el ciclo de vida de reportes.', category: 'General' },
  { q: '¿Cómo activo mi licencia?', a: 'Desde la pantalla de login haz clic en "Activar licencia". Ingresa tu license key y el sistema la validará automáticamente. Si no tienes una, contacta a soporte.', category: 'General', link: { path: '/activation', label: 'Ir a Activación' } },
  { q: '¿Qué modos de operación existen?', a: 'OWNEX soporta tres modos: Manual (tú controlas cada etapa), Automático (el pipeline corre en ciclo completo), y Asistido por IA (el copiloto sugiere acciones y tú apruebas). Se configuran desde Control de Misión.', category: 'General', link: { path: '/mission-control', label: 'Ir a Control de Misión' } },
  { q: '¿Qué navegadores soporta?', a: 'OWNEX funciona en Chrome 90+, Firefox 90+, Edge 90+ y Safari 15+. Requiere Web Crypto API (disponible en todos los navegadores modernos).', category: 'General' },

  // ── Seguridad ──
  { q: '¿Dónde se almacenan mis API keys?', a: 'Las API keys se cifran con AES-256-GCM usando la Web Crypto API del navegador. La clave de cifrado se guarda en localStorage y los datos cifrados en sessionStorage. Al cerrar el navegador, las keys en sessionStorage se borran automáticamente.', category: 'Seguridad' },
  { q: '¿Cómo se protegen las comunicaciones?', a: 'Todas las llamadas a la API usan tokens JWT firmados con HMAC-SHA256. El middleware CSRF de doble cookie protege contra ataques de falsificación. Las rutas de la API requieren autenticación excepto login, health y activation.', category: 'Seguridad' },
  { q: '¿OWNEX registra eventos de seguridad?', a: 'Sí. Todos los eventos de autenticación (login, logout, token almacenado) se registran en un audit log persistente cifrado en ~/.cateye/audit.jsonl con permisos 600.', category: 'Seguridad' },
  { q: '¿Qué pasa si alguien roba mi token de sesión?', a: 'Los tokens tienen expiración de 24 horas. El secret usado para firmarlos persiste en disco con permisos 600. Si necesitas revocar sesiones, puedes reiniciar el servidor o cambiar la variable CATEYE_AUTH_SECRET.', category: 'Seguridad' },

  // ── Operación ──
  { q: '¿Qué tipos de escaneo soporta?', a: 'Escaneo pasivo: subdominios (subfinder, amass), tecnologías (httpx, nuclei), endpoints (katana, gau). Escaneo activo controlado: validación de vulnerabilides solo en targets autorizados dentro del scope.', category: 'Operación' },
  { q: '¿Puedo conectar múltiples plataformas de bug bounty?', a: 'Sí. OWNEX soporta HackerOne, Bugcrowd, Intigriti, Synack y YesWeHack. Conéctalas desde la sección Conexiones en la sidebar.', category: 'Operación', link: { path: '/connections', label: 'Ir a Conexiones' } },
  { q: '¿Cómo funciona el pipeline de validación?', a: 'Discovery → Recon → Hipótesis → Scope Check → Validación → Reporte. Cada etapa corre en su propio intervalo configurable. Puedes monitorear el progreso en Pipeline Monitor.', category: 'Operación', link: { path: '/pipelines', label: 'Ver Pipeline Monitor' } },
  { q: '¿Qué es el cooldown por target?', a: 'Para evitar re-escaneos innecesarios, cada target tiene un cooldown de 1 hora después de ser escaneado. Puedes ver el estado en el detalle del target.', category: 'Operación' },
  { q: '¿Cómo se priorizan los targets?', a: 'El scheduler usa Reward Learning para ajustar prioridades: targets con tipos de vulnerabilidad de alto reward se escanean primero. También se boostean targets con actividad reciente.', category: 'Operación' },

  // ── Copiloto / AI ──
  { q: '¿Cómo funciona el copiloto AI?', a: 'El copiloto analiza el contexto del pipeline, sugiere próximas acciones, genera hipótesis de vulnerabilidades y responde preguntas sobre hallazgos. Se activa con ⌘B o desde el botón en la sidebar.', category: 'Copiloto' },
  { q: '¿Qué modelos AI soporta?', a: 'Ollama (local), OpenAI, Gemini, y OpenRouter. Puedes configurar el proveedor desde Settings → IA. El modelo local recomendado es qwen3:8b.', category: 'Copiloto', link: { path: '/settings', label: 'Configurar IA' } },
  { q: '¿El copiloto accede a mis datos?', a: 'El copiloto solo accede al contexto del pipeline actual: targets, hallazgos, y conversación activa. No envía datos a servidores externos si usas Ollama local.', category: 'Copiloto' },
]

const searchQuery = ref('')
const openIndex = ref<number | null>(null)

const categories = [...new Set(faqs.map(f => f.category))]

const filtered = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return faqs
  return faqs.filter(f =>
    f.q.toLowerCase().includes(q) || f.a.toLowerCase().includes(q) || f.category.toLowerCase().includes(q),
  )
})

const grouped = computed(() => {
  const map: Record<string, FaqItem[]> = {}
  for (const f of filtered.value) {
    if (!map[f.category]) map[f.category] = []
    map[f.category].push(f)
  }
  return map
})

function toggle(i: number) {
  openIndex.value = openIndex.value === i ? null : i
}

const categoryIcons: Record<string, any> = {
  General: HelpCircle,
  Seguridad: Shield,
  Operación: Cpu,
  Copiloto: MessageCircle,
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Preguntas Frecuentes</h1>
      <p class="mt-1 text-sm text-muted-foreground">Respuestas rápidas a las dudas más comunes sobre OWNEX.</p>
    </div>

    <!-- Search -->
    <div class="relative max-w-md">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Buscar preguntas..."
        class="w-full rounded-lg border border-border/30 bg-surface/50 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground/50 outline-none transition-all focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
      />
    </div>

    <!-- Results count -->
    <p v-if="searchQuery" class="text-xs text-muted-foreground">
      {{ filtered.length }} {{ filtered.length === 1 ? 'resultado' : 'resultados' }}
    </p>

    <!-- FAQ accordion by category -->
    <div v-for="cat in categories" :key="cat" class="space-y-3">
      <div v-if="grouped[cat]?.length" class="flex items-center gap-2">
        <component :is="categoryIcons[cat] || HelpCircle" class="h-4 w-4 text-primary" />
        <h2 class="text-sm font-semibold tracking-tight">{{ cat }}</h2>
      </div>

      <div class="space-y-2">
        <div
          v-for="(faq, i) in grouped[cat]"
          :key="faq.q"
          class="overflow-hidden rounded-lg border border-border/30 transition-all"
        >
          <button
            @click="toggle(i)"
            class="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-medium transition-colors hover:bg-surface/20"
          >
            <span>{{ faq.q }}</span>
            <ChevronDown
              class="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200"
              :class="openIndex === i ? 'rotate-180' : ''"
            />
          </button>
          <div
            :class="[
              'grid transition-all duration-200 ease-in-out',
              openIndex === i ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0',
            ]"
          >
            <div class="overflow-hidden">
              <div class="border-t border-border/20 px-5 py-4">
                <p class="text-sm leading-relaxed text-muted-foreground">{{ faq.a }}</p>
                <router-link
                  v-if="faq.link"
                  :to="faq.link.path"
                  class="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-primary transition-colors hover:text-primary/80"
                >
                  {{ faq.link.label }}
                  <ExternalLink class="h-3 w-3" />
                </router-link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- No results -->
    <div
      v-if="filtered.length === 0"
      class="flex flex-col items-center gap-3 py-16 text-center"
    >
      <Search class="h-8 w-8 text-muted-foreground/40" />
      <p class="text-sm text-muted-foreground">No se encontraron preguntas para "{{ searchQuery }}"</p>
      <button
        @click="searchQuery = ''"
        class="text-xs text-primary transition-colors hover:text-primary/80"
      >
        Limpiar búsqueda
      </button>
    </div>

    <!-- Contact support -->
    <div class="rounded-lg border border-border/30 bg-surface/20 p-6 text-center">
      <LifeBuoy class="mx-auto h-6 w-6 text-muted-foreground" />
      <h3 class="mt-3 text-sm font-semibold">¿No encontraste lo que buscabas?</h3>
      <p class="mt-1 text-xs text-muted-foreground">Nuestro equipo de soporte está listo para ayudarte.</p>
      <div class="mt-4 flex items-center justify-center gap-3">
        <Button variant="outline" size="sm" @click="$emit('openCopilot')">
          <MessageCircle class="h-3.5 w-3.5" />
          Preguntar al Copiloto
        </Button>
      </div>
    </div>
  </div>
</template>
