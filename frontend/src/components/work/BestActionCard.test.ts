import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

/**
 * La acción recomendada tiene que ser **auditable**: ítem, plata,
 * probabilidad, horas y URL real. Una recomendación sin evidencia es una
 * frase motivacional, no una recomendación.
 *
 * Contexto: el motor estaba roto desde 2d74d038 (`build()` sin argumento) y
 * respondía "Sin acción disponible" para siempre. Estos tests fijan que
 * vuelva a responder Y que no invente.
 */
const mockGet = vi.fn()
vi.mock('@/lib/api', () => ({ api: { get: (p: string) => mockGet(p) } }))
vi.mock('@/lib/errors', () => ({ isUnauthenticated: () => false }))

const router = { push: vi.fn() }
vi.mock('vue-router', () => ({ useRouter: () => router }))

import BestActionCard from './BestActionCard.vue'

const REAL = {
  action_type: 'deliver_now',
  title: 'Entregar: [PAID BOUNTY - $660] Enhanced Image Preview',
  description: 'Trabajo completado listo para entregar en github.',
  why_now: 'El trabajo está 100% preparado.',
  platform: 'github',
  work_item_id: 'gh-1',
  expected_value_usd: 660,
  acceptance_probability: 0.95,
  estimated_human_hours: 0.5,
  cash_speed_days: 7,
  url: 'https://github.com/acme/repo/issues/6',
  prerequisites: ['Revisar deliverables'],
}

async function render() {
  const w = mount(BestActionCard)
  await flushPromises()
  return w
}

describe('BestActionCard', () => {
  beforeEach(() => {
    mockGet.mockReset()
    router.push.mockReset()
  })

  it('muestra la acción con su evidencia completa', async () => {
    mockGet.mockResolvedValue(REAL)
    const w = await render()
    const t = w.text()
    expect(t).toContain('$660')
    expect(t).toContain('95%')       // aceptación
    expect(t).toContain('0.5 h')     // tiempo humano
    expect(t).toContain('7 d')       // caja en
    expect(t).toContain('Revisar deliverables')
    expect(t).toContain('gh-1')
  })

  it('abre el work item', async () => {
    mockGet.mockResolvedValue(REAL)
    const w = await render()
    const btn = w.findAll('button').find((b) => b.text().includes('Abrir el trabajo'))
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    expect(router.push).toHaveBeenCalledWith('/operations/work-room/gh-1')
  })

  it('enlaza a la URL real de la plataforma', async () => {
    mockGet.mockResolvedValue(REAL)
    const w = await render()
    const link = w.find('a[href="https://github.com/acme/repo/issues/6"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('rel')).toContain('noopener')
  })

  it('sin acción lo dice, no inventa una', async () => {
    mockGet.mockResolvedValue(null)
    const w = await render()
    expect(w.text()).toContain('Sin acción disponible')
    expect(w.text()).not.toContain('$')
  })

  it('probabilidad ausente se muestra UNKNOWN, no 0%', async () => {
    mockGet.mockResolvedValue({ ...REAL, acceptance_probability: undefined })
    const w = await render()
    // Se mira SOLO el nodo de aceptación: el resto de la tarjeta puede
    // contener "0%" por otro motivo y daría falso positivo.
    expect(w.find('[data-testid="acceptance"]').text()).toBe('UNKNOWN')
  })

  it('valor esperado 0 no se disfraza de dinero ganado', async () => {
    // Con 0 PAID el esperado es 0 REAL: no es UNKNOWN, pero tampoco es ingreso.
    mockGet.mockResolvedValue({ ...REAL, expected_value_usd: 0 })
    const w = await render()
    expect(w.text()).toContain('Valor esperado')
    expect(w.text()).toContain('$0')
    // Y sigue mostrando la probabilidad, que es información distinta.
    expect(w.text()).toContain('95%')
  })
})
