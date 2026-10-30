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

function getStoredLocale(): SupportedLocale {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale
  }
  return 'en'
}

function getBrowserLocale(): SupportedLocale {
  const browserLang = navigator.language.split('-')[0]
  if (SUPPORTED_LOCALES.includes(browserLang as SupportedLocale)) {
    return browserLang as SupportedLocale
  }
  return 'en'
}

const initialLocale = getStoredLocale() || getBrowserLocale()

const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
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
  }
}

export default i18n
