import { beforeEach, describe, expect, it } from 'vitest'

/**
 * Idioma por defecto = español (directive owner 2026-09-28).
 * Precedencia: elección guardada → español → navegador → español.
 */
describe('resolveInitialLocale', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('default es español sin elección guardada', async () => {
    const { DEFAULT_LOCALE, resolveInitialLocale } = await import('../useI18n')
    expect(DEFAULT_LOCALE).toBe('es')
    expect(resolveInitialLocale()).toBe('es')
  })

  it('respeta la elección guardada aunque no sea español', async () => {
    localStorage.setItem('ownex_locale', 'en')
    const { resolveInitialLocale } = await import('../useI18n')
    expect(resolveInitialLocale()).toBe('en')
  })

  it('ignora valores guardados inválidos', async () => {
    localStorage.setItem('ownex_locale', 'klingon')
    const { resolveInitialLocale } = await import('../useI18n')
    expect(resolveInitialLocale()).toBe('es')
  })

  it('expone etiquetas de los 6 idiomas soportados', async () => {
    const mod = await import('../useI18n')
    const { localeLabels, supportedLocales } = mod.useI18n()
    expect(supportedLocales).toHaveLength(6)
    expect(localeLabels.es).toBe('Español')
    for (const code of supportedLocales) {
      expect(localeLabels[code]).toBeTruthy()
    }
  })

  it('el fallback es español (nunca inglés por defecto)', async () => {
    const { DEFAULT_LOCALE } = await import('../useI18n')
    expect(DEFAULT_LOCALE).toBe('es')
  })
})
