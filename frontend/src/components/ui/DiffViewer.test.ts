import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DiffViewer from './DiffViewer.vue'

/**
 * El riesgo clásico de un diff es mentir: mostrar "+1 -1" sobre un cambio de
 * 40 líneas. Estos guards fijan que las estadísticas salen de las líneas
 * reales y que el colapso de contexto no pierde contenido.
 */
function stats(original: string, modified: string) {
  const w = mount(DiffViewer, { props: { original, modified } })
  // Leemos el encabezado por data-testid: un regex sobre el texto entero
  // capturaba los números de línea del gutter ("41") y daba falso positivo.
  // Los badges sólo existen si hay cambios; si no hay, los ceros son 0.
  const addEl = w.find('[data-testid="diff-added"]')
  const delEl = w.find('[data-testid="diff-removed"]')
  const add = addEl.exists() ? Number(addEl.text().replace('+', '')) : 0
  const del = delEl.exists() ? Number(delEl.text().replace('−', '')) : 0
  const text = w.text()
  w.unmount()
  return { add, del, text }
}

describe('DiffViewer', () => {
  it('sin cambios: no inventa adiciones ni borrados', () => {
    const s = stats('uno\ndos\ntres', 'uno\ndos\ntres')
    expect(s.add).toBe(0)
    expect(s.del).toBe(0)
    expect(s.text).toContain('sin cambios')
  })

  it('cuenta las líneas agregadas reales', () => {
    const s = stats('uno\ndos', 'uno\ndos\ntres\ncuatro\ncinco')
    expect(s.add).toBe(3)
    expect(s.del).toBe(0)
  })

  it('cuenta las líneas borradas reales', () => {
    const s = stats('a\nb\nc\nd', 'a')
    expect(s.del).toBe(3)
    expect(s.add).toBe(0)
  })

  it('un reemplazo cuenta 1 borrada y 1 agregada', () => {
    const s = stats('lineaVieja', 'lineaNueva')
    expect(s.del).toBe(1)
    expect(s.add).toBe(1)
  })

  it('no cuenta la última línea vacía por el \\n final', () => {
    const conNl = stats('uno\ndos\n', 'uno\ndos\n')
    expect(conNl.add).toBe(0)
    expect(conNl.del).toBe(0)
  })

  it('maneja archivo vacío de un lado', () => {
    expect(stats('', 'nueva').add).toBe(1)
    expect(stats('vieja', '').del).toBe(1)
  })

  it('colapsa contexto largo sin perder el contenido', () => {
    const base = Array.from({ length: 40 }, (_, i) => `ctx ${i}`).join('\n')
    const w = mount(DiffViewer, { props: { original: base, modified: `${base}\nNUEVA` } })
    const text = w.text()
    // Colapsado: muestra el hueco y el cambio, no las 40 líneas.
    expect(text).toContain('líneas sin cambios')
    expect(text).toContain('NUEVA')
    expect(text).not.toContain('ctx 20')
    w.unmount()
  })

  it('sin colapso cuando el contexto es chico', () => {
    // 8 líneas con context=10: el hueco nunca supera el contexto, así que
    // TODO se muestra. (Un test anterior afirmaba 'ctx 3' sobre datos
    // 'a'..'h' — comprobaba una cadena que su propio fixture no tenía.)
    const base = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'].join('\n')
    const w = mount(DiffViewer, { props: { original: base, modified: `${base}\nNUEVA`, context: 10 } })
    const text = w.text()
    expect(text).toContain('d')
    expect(text).toContain('NUEVA')
    expect(text).not.toContain('líneas sin cambios')
    w.unmount()
  })

  it('muestra el nombre del archivo en el encabezado', () => {
    const w = mount(DiffViewer, { props: { original: 'a', modified: 'b', filename: 'poc.py' } })
    expect(w.text()).toContain('poc.py')
    w.unmount()
  })

  it('avisa cuando ambos lados están vacíos', () => {
    const w = mount(DiffViewer, { props: { original: '', modified: '' } })
    expect(w.text()).toContain('vacío')
    w.unmount()
  })
})
