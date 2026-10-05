import { watch } from 'vue'
import { createI18n } from 'vue-i18n'
import de from '@/locales/de.json'
import en from '@/locales/en.json'
import es from '@/locales/es.json'
import fr from '@/locales/fr.json'
import ja from '@/locales/ja.json'
import zh from '@/locales/zh.json'

const messages = {
  en,
  es,
  fr,
  de,
  ja,
  zh,
}

const SUPPORTED_LOCALES = ['en', 'es', 'fr', 'de', 'ja', 'zh'] as const
type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

const STORAGE_KEY = 'ownex_locale'

/**
 * Idioma por defecto: español (dueño del producto, directive 2026-09-28).
 * Orden de precedencia: elección guardada → español (no el idioma del
 * navegador) → idioma del navegador si está soportado → español.
 * Nunca queda en inglés por defecto: lo que falte cae al fallback 'es'.
 */
export const DEFAULT_LOCALE: SupportedLocale = 'es'

export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  es: 'Español',
  en: 'English',
  fr: 'Français',
  de: 'Deutsch',
  ja: '日本語',
  zh: '中文',
}

function isSupported(value: string | null | undefined): value is SupportedLocale {
  return !!value && (SUPPORTED_LOCALES as readonly string[]).includes(value)
}

function getStoredLocale(): SupportedLocale | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  return isSupported(stored) ? stored : null
}

function getBrowserLocale(): SupportedLocale | null {
  const browserLang = navigator.language?.split('-')[0]
  return isSupported(browserLang) ? browserLang : null
}

export function resolveInitialLocale(): SupportedLocale {
  return getStoredLocale() ?? DEFAULT_LOCALE ?? getBrowserLocale() ?? DEFAULT_LOCALE
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: resolveInitialLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  missingWarn: false,
  fallbackWarn: false,
  messages,
})

export function useI18n() {
  const setLocale = (locale: SupportedLocale) => {
    i18n.global.locale.value = locale
    localStorage.setItem(STORAGE_KEY, locale)
  }

  const currentLocale = i18n.global.locale.value as SupportedLocale

  const t = i18n.global.t

  return {
    setLocale,
    currentLocale,
    t,
    supportedLocales: SUPPORTED_LOCALES,
    localeLabels: LOCALE_LABELS,
    defaultLocale: DEFAULT_LOCALE,
  }
}

export default i18n
