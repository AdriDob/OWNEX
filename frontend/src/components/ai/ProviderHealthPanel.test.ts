import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ProviderHealthPanel from './ProviderHealthPanel.vue'
import { api } from '@/lib/api'

/**
 * ProviderHealthPanel — guards del contrato de honestidad.
 *
 * Este panel renderiza GET /oar/doctor, que hasta esta sesión no tenía
 * NINGÚN consumidor: los datos se descargaban en ownexData.ts:1598 y se
 * descartaban. Los tests fijan las reglas que impiden que el panel mienta,
 * que es la regla que más se rompió en este árbol (UNKNOWN renderizado como
 * $0, "LIVE" sin medir).
 */

const DOCTOR = {
  overall: 'healthy',
  providers: { healthy: ['ollama', 'groq'], degraded: ['fcc'], unhealthy: [], total: 4 },
  health_details: {
    ollama: {
      status: 'healthy',
      latency_ms: 42,
      error_rate: 0,
      success_count: 9,
      error_count: 0,
      last_error: null,
    },
    groq: { status: 'healthy', latency_ms: 310, error_rate: 0, success_count: 3, error_count: 0, last_error: null },
    fcc: { status: 'degraded', latency_ms: 2100, error_rate: 0.12, success_count: 8, error_count: 1, last_error: '429 quota_exceeded' },
    cerebras: {
      status: 'unknown',
      latency_ms: 0,
      error_rate: 0,
      success_count: 0,
      error_count: 0,
      last_error: 'Missing API key or base URL',
    },
  },
  circuit_breakers: { ollama: false, groq: false, fcc: true, cerebras: false },
}

beforeEach(() => {
  vi.restoreAllMocks()
})

function mockDoctor(value: unknown) {
  vi.spyOn(api, 'get').mockResolvedValue(value as never)
}

describe('ProviderHealthPanel', () => {
  it('renderiza una fila por provider con su estado real', async () => {
    mockDoctor(DOCTOR)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    expect(w.findAll('tbody tr')).toHaveLength(4)
    const text = w.text()
    for (const id of ['ollama', 'groq', 'fcc', 'cerebras']) expect(text).toContain(id)
    w.unmount()
  })

  it('UNKNOWN se muestra como desconocido, nunca como ok', async () => {
    mockDoctor(DOCTOR)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    const cerebrasRow = w.findAll('tbody tr').find((tr) => tr.text().includes('cerebras'))!
    expect(cerebrasRow.text()).toContain('desconocido')
    expect(cerebrasRow.text()).not.toContain('ok')
    w.unmount()
  })

  it('un provider sin credencial lo dice y pide la key (no queda mystery)', async () => {
    mockDoctor(DOCTOR)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    const row = w.findAll('tbody tr').find((tr) => tr.text().includes('cerebras'))!
    expect(row.text()).toContain('sin credencial')
    expect(row.text()).toContain('key')
    w.unmount()
  })

  it('latencia 0 se renderiza "sin contactar", no 0ms', async () => {
    mockDoctor(DOCTOR)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    const row = w.findAll('tbody tr').find((tr) => tr.text().includes('cerebras'))!
    expect(row.text()).toContain('sin contactar')
    expect(row.text()).not.toContain('0ms')
    w.unmount()
  })

  it('circuit breaker abierto se muestra aunque el status sea healthy', async () => {
    const withBreaker = {
      ...DOCTOR,
      circuit_breakers: { ...DOCTOR.circuit_breakers, groq: true },
      health_details: {
        ...DOCTOR.health_details,
        groq: { ...DOCTOR.health_details.groq, status: 'healthy' },
      },
    }
    mockDoctor(withBreaker)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    const row = w.findAll('tbody tr').find((tr) => tr.text().includes('groq'))!
    expect(row.text()).toContain('circuit breaker abierto')
    w.unmount()
  })

  it('el contador excluye del "aportan capacidad" a los que tienen breaker abierto', async () => {
    mockDoctor(DOCTOR)
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    // healthy = ollama + groq, pero fcc tiene breaker abierto y cerebras unknown.
    expect(w.text()).toContain('2/4 aportan capacidad')
    w.unmount()
  })

  it('sin providers: empty state honesto, no "todo bien"', async () => {
    mockDoctor({ overall: 'unhealthy', providers: { total: 0 }, health_details: {}, circuit_breakers: {} })
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    expect(w.text()).toContain('no está inicializado')
    expect(w.text()).not.toContain('aportan capacidad')
    w.unmount()
  })

  it('error de red: lo dice y no muestra tabla vacía como si fuera healthy', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('boom'))
    const w = mount(ProviderHealthPanel)
    await flushPromises()

    expect(w.text()).toContain('No se pudo consultar')
    expect(w.text()).toContain('boom')
    w.unmount()
  })
})
