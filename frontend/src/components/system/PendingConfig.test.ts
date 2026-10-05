import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PendingConfig from './PendingConfig.vue'
import { api } from '@/lib/api'

/**
 * PendingConfig — la superficie que faltaba para la configuración.
 *
 * Pedido del owner: "todo lo que quede pendiente de configuración debe
 * aparecer en la configuración del sistema (front)".
 *
 * Antes esa info estaba en 145 `os.getenv()` dispersos, una tupla de 16 keys
 * en el checklist, y docstrings. Una capacidad gateada por una key invisible
 * es una capacidad que no existe.
 *
 * Los tests fijan las reglas de honestidad, no el markup. La más importante:
 * `bloqueada` ≠ `degradada`. Decir "bloqueada" cuando el sistema funciona
 * igual es la misma clase de mentira que un 0 inventado — y sería más grave
 * porque el owner podría chasear una key que no hace falta.
 */

const SNAP = {
  capabilities: [
    {
      id: 'trading_live',
      label: 'Trading con fondos reales',
      category: 'Trading',
      what: 'Firma y broadcast de transacciones.',
      impact: 'bloqueada',
      configured: false,
      missing_required: ['SOLANA_PRIVATE_KEY'],
      missing_optional: ['TRADING_MODE'],
      requirements: [
        {
          env: 'SOLANA_PRIVATE_KEY',
          present: false,
          optional: false,
          without: 'Sin key NO se puede firmar nada.',
          where: 'Variables de entorno',
        },
        {
          env: 'TRADING_MODE',
          present: false,
          optional: true,
          without: 'Sin esto el default es dry_run.',
          where: 'Variables de entorno',
        },
      ],
    },
    {
      id: 'ai_free_cloud',
      label: 'Providers IA gratis',
      category: 'Inteligencia',
      what: 'Groq, Cerebras, Together, DeepInfra.',
      impact: 'degradada',
      configured: true,
      missing_required: [],
      missing_optional: ['GROQ_API_KEY'],
      requirements: [
        {
          env: 'GROQ_API_KEY',
          present: false,
          optional: true,
          without: 'Sin key Groq no entra al pool.',
          where: 'Variables de entorno',
        },
      ],
    },
    {
      id: 'osint_keyless',
      label: 'OSINT sin key',
      category: 'OSINT',
      what: '16 fuentes keyless.',
      impact: 'ninguno',
      configured: true,
      missing_required: [],
      missing_optional: [],
      requirements: [],
    },
  ],
  totals: {
    capabilities: 3,
    configured: 2,
    pending_blocking: 1,
    envs_referenced: 19,
    envs_set: 4,
  },
  note: 'sólo presencia de variables, nunca valores',
}

beforeEach(() => {
  vi.restoreAllMocks()
})

function mock(value: unknown) {
  vi.spyOn(api, 'get').mockResolvedValue(value as never)
}

describe('PendingConfig', () => {
  it('distingue bloqueada de degradada', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('1 bloqueada(s)')
    expect(text).toContain('1 degradada(s)')
    expect(text).toContain('no arranca sin esto')
    expect(text).toContain('funciona, pero con menos alcance')
    w.unmount()
  })

  it('una key opcional NO se presenta como requerida', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    const groq = w.findAll('li').find((li) => li.text().includes('GROQ_API_KEY'))!
    expect(groq.text()).toContain('opcional')
    expect(groq.text()).not.toContain('requerida')
    w.unmount()
  })

  it('explica qué se pierde con cada key faltante', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    const priv = w.findAll('li').find((li) => li.text().includes('SOLANA_PRIVATE_KEY'))!
    expect(priv.text()).toContain('Sin key NO se puede firmar nada')
    w.unmount()
  })

  it('una capacidad keyless se muestra como completa, no como faltante', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('sin configuración pendiente')
    expect(text).toContain('OSINT sin key')
    w.unmount()
  })

  it('nada de esto cuando no falta nada', async () => {
    mock({
      capabilities: [{ ...SNAP.capabilities[2] }],
      totals: { ...SNAP.totals, capabilities: 1, pending_blocking: 0, envs_set: 19 },
      note: SNAP.note,
    })
    const w = mount(PendingConfig)
    await flushPromises()

    expect(w.text()).toContain('Ninguna capacidad requiere configuración')
    w.unmount()
  })

  it('declara que nunca muestra valores', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    expect(w.text()).toContain('nunca valores')
    w.unmount()
  })

  it('error de red se dice, no muestra "todo completo"', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('boom'))
    const w = mount(PendingConfig)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('No se pudo consultar')
    expect(text).not.toContain('Ninguna capacidad requiere configuración')
    w.unmount()
  })

  it('agrupa por categoría', async () => {
    mock(SNAP)
    const w = mount(PendingConfig)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('Trading')
    expect(text).toContain('Inteligencia')
    expect(text).toContain('OSINT')
    w.unmount()
  })
})
