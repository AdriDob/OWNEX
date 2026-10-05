import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TradingRadars from './TradingRadars.vue'
import { api } from '@/lib/api'

/**
 * TradingRadars — pump.fun / dip / spread desde el panel.
 *
 * Estos tres radares YA existían en el backend con APIs keyless reales
 * (DexScreener, RugCheck, Binance, Jupiter) y jobs de scheduler. Lo que no
 * existía era el consumidor: 9 endpoints de trading con 0 renders.
 *
 * Además, al construir el panel encontré que `/pump/radar` y `/dip/radar`
 * eran **500 garantizados** (`__dict__` sobre dataclasses con `slots=True`).
 * Eso se arregló aparte; este archivo fija las reglas de honestidad del
 * panel, que es lo que evita que un radar vuelva a mentirse.
 */

const PUMP_OK = {
  success: true,
  count: 1,
  scanned_at: Math.floor(Date.now() / 1000) - 60,
  candidates: [
    {
      mint: 'So11111111111111111111111111111111111111112',
      symbol: 'PUMP',
      name: 'Pump Token',
      price_usd: 0.00123,
      price_change_h24: 88.5,
      volume_h24: 120000,
      liquidity_usd: 30000,
      dex: 'pumpswap',
      url: 'https://dexscreener.com/solana/xyz',
      pump_score: 91,
      reasons: [],
      warnings: [],
      passed_filters: true,
      rug: {},
    },
  ],
}

const PUMP_FILTERED = {
  success: true,
  count: 1,
  scanned_at: Math.floor(Date.now() / 1000),
  candidates: [
    {
      mint: 'So11111111111111111111111111111111111111113',
      symbol: 'RUGGED',
      name: 'Rug Token',
      price_usd: 0.0001,
      price_change_h24: 400,
      volume_h24: 5000,
      liquidity_usd: 900,
      dex: 'raydium',
      url: 'https://dexscreener.com/solana/abc',
      pump_score: 95,
      reasons: ['liquidez 900 < 10000', 'volumen 5000 < 10000'],
      warnings: ['rug score 95: peligro'],
      passed_filters: false,
      rug: {},
    },
  ],
}

beforeEach(() => {
  vi.restoreAllMocks()
})

function mockRadar(value: unknown) {
  vi.spyOn(api, 'get').mockResolvedValue(value as never)
}

describe('TradingRadars', () => {
  it('renderiza un candidato con sus datos', async () => {
    mockRadar(PUMP_OK)
    const w = mount(TradingRadars)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('PUMP')
    expect(text).toContain('Pump Token')
    expect(text).toContain('+88.5%')
    w.unmount()
  })

  it('un candidato que NO pasó los filtros se marca explícito', async () => {
    mockRadar(PUMP_FILTERED)
    const w = mount(TradingRadars)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('no apto')
    expect(text).toContain('liquidez 900 < 10000')
    expect(text).toContain('rug score 95')
    // Y el header dice que ninguno pasó
    expect(text).toContain('ninguno pasó los filtros duros')
    w.unmount()
  })

  it('cuenta separados los que pasaron filtros', async () => {
    mockRadar(PUMP_OK)
    const w = mount(TradingRadars)
    await flushPromises()

    expect(w.text()).toContain('1 candidatos')
    expect(w.text()).toContain('1 pasaron filtros')
    w.unmount()
  })

  it('"escaneó y no encontró" NO es lo mismo que "no se consultó"', async () => {
    mockRadar({ success: true, count: 0, candidates: [], scanned_at: Date.now() / 1000 })
    const w = mount(TradingRadars)
    await flushPromises()

    const text = w.text()
    expect(text).toContain('Escaneó y no encontró')
    expect(text).not.toContain('No se pudo consultar')
    w.unmount()
  })

  it('error de red se dice, no muestra tabla vacía', async () => {
    vi.spyOn(api, 'get').mockRejectedValue(new Error('boom'))
    const w = mount(TradingRadars)
    await flushPromises()

    expect(w.text()).toContain('No se pudo consultar')
    expect(w.text()).toContain('boom')
    w.unmount()
  })

  it('el panel es sólo lectura: declara que no ejecuta fondos', async () => {
    mockRadar(PUMP_OK)
    const w = mount(TradingRadars)
    await flushPromises()

    expect(w.text()).toContain('Sólo lectura')
    expect(w.text()).toContain('Human Gate')
    // Y no hay ningun boton que dispare una operacion
    const buttons = w.findAll('button').map((b) => b.text())
    expect(buttons.join(' ')).not.toMatch(/ejecutar|comprar|activar live/i)
    w.unmount()
  })

  it('cambiar de tab consulta el radar correspondiente', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ ...PUMP_OK, candidates: [] } as never)
    const w = mount(TradingRadars)
    await flushPromises()
    expect(get).toHaveBeenCalledWith('/trading/pump/radar')

    const dipTab = w.findAll('[role="tab"]').find((t) => t.text() === 'Dip')!
    await dipTab.trigger('click')
    await flushPromises()

    expect(get).toHaveBeenCalledWith('/trading/dip/radar')
    w.unmount()
  })

  it('spread muestra la columna de spread, no el 24h', async () => {
    mockRadar({
      success: true,
      count: 1,
      scanned_at: Date.now() / 1000,
      candidates: [
        { pair: 'SOL/USDC', spread_pct: 0.42, spread_net_pct: 0.31, entry_price: 142.5 },
      ],
    })
    const w = mount(TradingRadars)
    await flushPromises()
    const spreadTab = w.findAll('[role="tab"]').find((t) => t.text() === 'Spread')!
    await spreadTab.trigger('click')
    await flushPromises()

    const text = w.text()
    expect(text).toContain('SOL/USDC')
    expect(text).toContain('+0.3%')
    w.unmount()
  })
})
