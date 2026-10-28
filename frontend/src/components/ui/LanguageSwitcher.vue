<script setup lang="ts">
/**
 * LanguageSwitcher — botón de traducción siempre visible (directive owner
 * 2026-09-28: español por defecto, cambio a 1 clic desde cualquier pantalla).
 *
 * Compacto por diseño: cabe en el toolbar sin competir con el contenido.
 */
import { computed, ref } from 'vue'
import { Check, Globe } from '@lucide/vue'
import { useI18n, type SupportedLocale } from '@/composables/useI18n'

const { setLocale, currentLocale, localeLabels, supportedLocales } = useI18n()
const open = ref(false)

const active = computed(() => currentLocale)
const shortLabel = computed(() => (active.value === 'es' ? 'ES' : active.value.toUpperCase()))

function pick(code: SupportedLocale) {
  setLocale(code)
  open.value = false
}
</script>

<template>
  <div class="relative">
    <button
      class="flex h-6 items-center gap-1 rounded border border-orion-border/30 px-1.5 font-mono text-[10px] uppercase text-muted-foreground/70 transition-colors hover:bg-orion-bg-elevated hover:text-foreground"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :aria-label="`Idioma: ${localeLabels[active]}`"
      title="Cambiar idioma / Change language"
      data-testid="language-switcher"
      @click="open = !open"
    >
      <Globe class="h-3 w-3" />
      <span>{{ shortLabel }}</span>
    </button>

    <div
      v-if="open"
      class="absolute right-0 z-50 mt-1 min-w-[9rem] overflow-hidden rounded-lg border border-orion-border/30 bg-orion-bg-elevated py-1 shadow-xl"
      role="listbox"
    >
      <button
        v-for="code in supportedLocales"
        :key="code"
        class="flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-[11px] transition-colors hover:bg-orion-surface/40"
        :class="code === active ? 'text-foreground' : 'text-muted-foreground'"
        role="option"
        :aria-selected="code === active"
        @click="pick(code)"
      >
        <span>{{ localeLabels[code] }}</span>
        <Check v-if="code === active" class="h-3 w-3" />
      </button>
    </div>
  </div>
</template>
