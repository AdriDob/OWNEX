import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

/**
 * El invariante: **una bounty sin evidencia de pago no es trabajo accionable.**
 *
 * El banco trae 11 items, 9 de ellos de repos que nunca mergearon un PR
 * (`unpaid_evidence`). Si la UI los mezclara con el trabajo real, el usuario
 * vería $5.810 de "trabajo" que no existe — exactamente el bug que ya se
 * corrigió dos veces en el backend.
 */
const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/lib/api', () => ({
  api: { get: (p: string) => mockGet(p), post: (p: string, b: unknown) => mockPost(p, b) },
}))
vi.mock('@/lib/errors', () => ({ isUnauthenticated: () => false }))

const router = { push: vi.fn() }
vi.mock('vue-router', () => ({ useRouter: () => router }))

import WorkBankList from './WorkBankList.vue'

const BANK = {
  scanned: 1018,
  eligible_zero_barrier: 7,
  ready_to_deliver: 2,
  unpaid_evidence: 9,
  items: [
    { id: 'a', title: 'Fix PoC XSS', platform: 'github', reward: 750, status: 'ready_to_deliver', deliverables: ['a'] },
    { id: 'b', title: 'Write tests', platform: 'github', reward: 660, status: 'ready_to_deliver', deliverables: ['a'] },
    { id: 'c', title: 'Bounty sin merges', platform: 'github', reward: 1250, status: 'unpaid_evidence', deliverables: [] },
    { id: 'd', title: 'Otra sin merges', platform: 'github', reward: 960, status: 'unpaid_evidence', deliverables: [] },
  ],
}

const flush = async () => {
  await new Promise((r) => setTimeout(r, 0))
  await nextTick()
}

describe('WorkBankList', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockPost.mockReset()
    router.push.mockReset()
    mockGet.mockResolvedValue(BANK)
  })

  it('lista sólo el trabajo accionable', async () => {
    const w = mount(WorkBankList)
    await flush()
    expect(w.text()).toContain('Fix PoC XSS')
    expect(w.text()).not.toContain('Bounty sin merges')
  })

  it('informa cuántos ocultó, sin esconderlos', async () => {
    const w = mount(WorkBankList)
    await flush()
    // 4 items, 2 accionables ⇒ 2 ocultos, y el texto lo dice.
    expect(w.text()).toContain('Se ocultan 2')
  })

  it('el resumen distingue listas de sin-evidencia', async () => {
    const w = mount(WorkBankList)
    await flush()
    expect(w.text()).toContain('Listas para entregar')
    expect(w.text()).toContain('Sin evidencia de pago')
  })

  it('abrir un item navega al Work Room', async () => {
    const w = mount(WorkBankList)
    await flush()
    const btn = w.findAll('button').find((b) => b.text() === 'Abrir')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    expect(router.push).toHaveBeenCalledWith('/operations/work-room/a')
  })

  it('correr el ciclo reporta lo que hizo y recarga', async () => {
    mockPost.mockResolvedValue({ scanned: 1018, eligible_zero_barrier: 7, ready_to_deliver: 2 })
    const w = mount(WorkBankList)
    await flush()
    const cycleBtn = w.findAll('button').find((b) => b.text().includes('Correr ciclo'))
    await cycleBtn!.trigger('click')
    await flush()
    expect(mockPost).toHaveBeenCalledWith('/direct-work/workbank/cycle', {})
    expect(w.get('[data-testid="cycle-note"]').text()).toContain('1018')
  })

  it('si el ciclo falla, lo dice y no inventa números', async () => {
    mockPost.mockRejectedValue(new Error('backend caído'))
    const w = mount(WorkBankList)
    await flush()
    const cycleBtn = w.findAll('button').find((b) => b.text().includes('Correr ciclo'))
    await cycleBtn!.trigger('click')
    await flush()
    const note = w.get('[data-testid="cycle-note"]').text()
    expect(note).toContain('falló')
    expect(note).toContain('backend caído')
    expect(note).not.toMatch(/\d+ escaneadas/)
  })

  it('banco vacío invita a correr ciclo, no muestra error', async () => {
    mockGet.mockResolvedValue({ scanned: 0, ready_to_deliver: 0, unpaid_evidence: 0, items: [] })
    const w = mount(WorkBankList)
    await flush()
    expect(w.text()).toContain('No hay trabajo en el banco')
    expect(w.text()).toContain('Corré un ciclo')
  })
})
