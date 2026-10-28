import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'

/**
 * El invariante: **un envío que no ocurrió no se reporta como enviado.**
 *
 * Medido el 2026-10-05: `POST /direct-work/workbank/{id}/submit` responde
 * **HTTP 200 con `success: false`** cuando el envío cae en DLQ (en vivo:
 * `last_error: "GITHUB_TOKEN no configurada"`, `attempts: 3`). La UI
 * informaba "Enviado a la plataforma" igual, porque miraba el status HTTP.
 *
 * `auto-submit` tiene la forma espejo: `success: false` + `reason` (sin
 * `message`), y hoy NO envía nada —el executor tiene un TODO y devuelve
 * `requires_manual_action: true`. El botón no puede prometer lo que no hace.
 */
const mockPost = vi.fn()
const mockGet = vi.fn()

vi.mock('@/lib/api', () => ({
  api: { get: (p: string) => mockGet(p), post: (p: string) => mockPost(p) },
}))
vi.mock('@/lib/errors', () => ({ isUnauthenticated: () => false }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: 'it-1' } }), useRouter: () => ({ push: vi.fn() }) }))

const notifications = {
  success: vi.fn(),
  error: vi.fn(),
}
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => notifications }))

import WorkRoom from './WorkRoom.vue'

const ITEM = {
  id: 'it-1',
  title: 'Fix PoC',
  platform: 'github',
  category: 'dev_bounty',
  reward: 960,
  barrier_score: 90,
  employment_type: 'bounty',
  status: 'ready_to_deliver',
  access_status: 'public',
  access_requirement: '',
  deliverables: ['work.md'],
  created_at: '2026-10-05',
  ready_to_deliver: true,
  description: '',
  url: '',
  payout_method: '',
  payout_method_rationale: '',
  started_at: null,
  delivered_at: null,
  human_minutes_actual: null,
}

async function render() {
  const w = mount(WorkRoom)
  await flushPromises()
  // Las acciones viven en la pestaña «Entrega»; «Visión general» es la activa.
  await w.findAll('button').find((b) => b.text().trim() === 'Entrega')!.trigger('click')
  await flushPromises()
  return w
}

async function clickByText(w: ReturnType<typeof mount>, label: string) {
  const btn = w.findAll('button').find((b) => b.text().includes(label))
  expect(btn, `botón "${label}" no encontrado`).toBeTruthy()
  await btn!.trigger('click')
  await flushPromises()
}

describe('WorkRoom — el envío no se inventa', () => {
  beforeEach(() => {
    mockPost.mockReset()
    mockGet.mockReset()
    notifications.success.mockReset()
    notifications.error.mockReset()
    // El componente busca `res.items.find(i => i.id === workId)`.
    mockGet.mockResolvedValue({ items: [ITEM] })
  })

  it('submit en DLQ (HTTP 200, success:false) NO dice "Enviado"', async () => {
    mockPost.mockResolvedValue({
      success: false,
      status: 'dlq',
      attempts: 3,
      last_error: 'GITHUB_TOKEN no configurada',
      message: 'Failed: GITHUB_TOKEN no configurada',
    })
    const w = await render()
    await clickByText(w, 'Enviar a plataforma')

    expect(notifications.success).not.toHaveBeenCalled()
    expect(notifications.error).toHaveBeenCalled()
    const msg = String(notifications.error.mock.calls[0]?.[0] ?? '')
    expect(msg).toContain('GITHUB_TOKEN')
  })

  it('submit exitoso sí confirma', async () => {
    mockPost.mockResolvedValue({ success: true, status: 'submitted', external_id: 'pr-9' })
    const w = await render()
    await clickByText(w, 'Enviar a plataforma')
    expect(notifications.success).toHaveBeenCalled()
    expect(notifications.error).not.toHaveBeenCalled()
  })

  it('auto-submit rechazado muestra el motivo del trust engine', async () => {
    // Forma espejo: `reason`, sin `message`.
    mockPost.mockResolvedValue({
      success: false,
      status: 'requires_manual_approval',
      reason: 'Auto-approval disabled globally',
    })
    const w = await render()
    await clickByText(w, 'Auto (trust engine)')

    const note = w.find('[data-testid="trust-note"]')
    expect(note.exists()).toBe(true)
    expect(note.text()).toContain('Auto-approval disabled globally')
  })

  it('auto-submit aprobado NO promete que se envió', async () => {
    mockPost.mockResolvedValue({ success: true, status: 'auto_submitted', reason: 'ok' })
    const w = await render()
    await clickByText(w, 'Auto (trust engine)')
    const note = w.find('[data-testid="trust-note"]')
    // Hoy el executor NO envía: el botón tiene que decirlo.
    expect(note.text()).toMatch(/lo hacés vos|no envía|manual/i)
  })

  it('approve fallido no dice "entregado"', async () => {
    mockPost.mockResolvedValue({ success: false, status: 'not_ready', message: 'Item no está listo' })
    const w = await render()
    await clickByText(w, 'Marcar entregado')
    expect(notifications.success).not.toHaveBeenCalled()
    expect(notifications.error).toHaveBeenCalledWith('Item no está listo')
  })
})
