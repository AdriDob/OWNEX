import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { vi } from 'vitest'

/**
 * El invariante más importante de este panel NO es que se vea lindo: es que
 * **no invente dinero**. Con 0 PAID, `global_net_per_hour` viene `null`
 * (UNKNOWN) y renderizarlo como `$0.00/h` afirma "ganaste cero por hora",
 * que es una afirmación distinta de "no sabemos". Es la clase de mentira que
 * el proyecto ya pagó dos veces (KNOWN_DEBT #34, y el pipeline de $5.810).
 */
const mockGet = vi.fn()

vi.mock('@/lib/api', () => ({ api: { get: (p: string) => mockGet(p) } }))
vi.mock('@/lib/errors', () => ({ isUnauthenticated: () => false }))

import ExecutionPanel from './ExecutionPanel.vue'

const QUEUE = [
  { item_id: 'deliv-1', state: 'ready', payload: { title: 'Fix PoC', platform: 'algora', reward: 960 }, history: [] },
  { item_id: 'deliv-2', state: 'submitted', payload: { title: 'Write tests', platform: 'github', reward: 440 }, history: [{}] },
  { item_id: 'deliv-3', state: 'failed', payload: { title: 'Broken', platform: 'opire', reward: 0 }, history: [{}] },
]

function setup(snapshot: unknown) {
  mockGet.mockImplementation((p: string) => {
    if (p.includes('execution-queue')) return Promise.resolve(QUEUE)
    if (p.includes('economic-feedback')) return Promise.resolve(snapshot)
    return Promise.reject(new Error('no'))
  })
  return mount(ExecutionPanel)
}

describe('ExecutionPanel', () => {
  it('muestra la cola con su estado real', async () => {
    const w = setup({ global_net_per_hour: null })
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    const text = w.text()
    expect(text).toContain('Fix PoC')
    expect(text).toContain('algora')
    expect(text).toContain('submitted')
  })

  it('neto/hora UNKNOWN nunca se renderiza como $0', async () => {
    const w = setup({ global_net_per_hour: null, total_paid: 0 })
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    const text = w.text()
    expect(text).toContain('UNKNOWN')
    expect(text).not.toContain('$0.00/h')
  })

  it('con neto/hora conocido lo muestra como número', async () => {
    const w = setup({ global_net_per_hour: 42.5 })
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    expect(w.text()).toContain('$42.50/h')
  })

  it('cuenta fallidos por su estado', async () => {
    const w = setup({ global_net_per_hour: null })
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    // 1 ready + 1 submitted + 1 failed
    expect(w.text()).toContain('Fallidos')
    const failed = w.text().match(/Fallidos[\s\S]{0,120}/)?.[0] ?? ''
    expect(failed).toContain('1')
  })

  it('sin economic-feedback el panel igual sirve', async () => {
    mockGet.mockImplementation((p: string) => {
      if (p.includes('execution-queue')) return Promise.resolve(QUEUE)
      return Promise.reject(new Error('404'))
    })
    const w = mount(ExecutionPanel)
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    expect(w.text()).toContain('Fix PoC')
    expect(w.text()).toContain('UNKNOWN')
  })

  it('no inventa nada cuando la cola está vacía', async () => {
    mockGet.mockImplementation((p: string) =>
      p.includes('execution-queue') ? Promise.resolve([]) : Promise.resolve({ global_net_per_hour: null }),
    )
    const w = mount(ExecutionPanel)
    await new Promise((r) => setTimeout(r, 0))
    await w.vm.$nextTick()
    expect(w.text()).toContain('vacía')
  })
})
