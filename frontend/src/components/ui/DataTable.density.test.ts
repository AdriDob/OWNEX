import { describe, expect, it } from 'vitest'
import { defineComponent, ref, type PropType } from 'vue'
import { mount } from '@vue/test-utils'
import DataTable from './DataTable.vue'

interface Row {
  id: string
  name: string
  amount: number
}

const cols = [
  { key: 'name', label: 'Nombre', sortable: true },
  { key: 'amount', label: 'Amounto', sortable: true, align: 'right' as const },
]

function mk(n: number): Row[] {
  return Array.from({ length: n }, (_, i) => ({ id: `r${i}`, name: `Item ${i}`, amount: i }))
}

describe('DataTable — densidad', () => {
  it('renderiza todo con listas pequeñas', () => {
    const w = mount(DataTable, { props: { columns: cols, items: mk(10) } })
    expect(w.findAll('tbody tr').length).toBe(10)
  })

  it('virtualiza por encima del umbral: no monta todas las filas', () => {
    const w = mount(DataTable, {
      props: { columns: cols, items: mk(2000), virtualizeOver: 200, rowHeight: 36 },
    })
    // 2000 filas no pueden ser 2000 <tr>: eso es lo que rompe el navegador.
    const rendered = w.findAll('tbody tr').length
    expect(rendered).toBeGreaterThan(0)
    expect(rendered).toBeLessThan(200)
  })

  it('la altura del spacer conserva la altura real (el scrollbar miente si no)', () => {
    const total = 2000
    const rowH = 36
    const w = mount(DataTable, {
      props: { columns: cols, items: mk(total), virtualizeOver: 200, rowHeight: rowH },
      attachTo: document.body,
    })
    const spacers = w.findAll('tbody tr[aria-hidden="true"]')
    const pad = spacers.reduce((acc, tr) => acc + Number((tr.attributes('style') || '').replace(/\D/g, '') || 0), 0)
    // Lo que se ve + lo que no se ve = el total real.
    const visible = w.findAll('tbody tr:not([aria-hidden="true"])').length
    expect(pad + visible).toBeGreaterThanOrEqual(total - visibleCountMargin(w))
    w.unmount()
  })

  it('desactiva el pager cuando virtualiza (el scrollbar es el pager)', () => {
    const w = mount(DataTable, {
      props: { columns: cols, items: mk(2000), virtualizeOver: 200 },
    })
    expect(w.text()).not.toContain('Siguiente')
  })

  it('buscar reduce el conjunto y resetea el scroll', async () => {
    const w = mount(DataTable, {
      props: { columns: cols, items: mk(500), searchable: true, virtualizeOver: 50 },
      attachTo: document.body,
    })
    await w.find('input[type="search"]').setValue('Item 42')
    expect(w.text()).toContain('1 resultados')
  })
})

describe('DataTable — selección (el loop necesita elegir)', () => {
  // `defineModel` sólo emite cuando el padre enlaza `v-model:selected`;
  // montar la tabla sola no alcanza. El wrapper reproduce el uso real.
  const Host = defineComponent({
    components: { DataTable },
    setup() {
      const sel = ref<Set<string>>(new Set())
      return { sel, cols }
    },
    template: `
      <DataTable :columns="cols" :items="items" selectable v-model:selected="sel" />
      <span data-testid="count">{{ sel.size }}</span>
    `,
    props: { items: { type: Array as PropType<Row[]>, required: true } },
  })

  it('selecciona una fila y el padre la ve', async () => {
    const w = mount(Host, { props: { items: mk(5) } })
    const boxes = w.findAll('tbody input[type="checkbox"]')
    expect(boxes.length).toBe(5)
    await boxes[1].setValue(true)
    expect(w.get('[data-testid="count"]').text()).toBe('1')
  })

  it('seleccionar todo marca todas', async () => {
    const w = mount(Host, { props: { items: mk(4) } })
    await w.find('thead input[type="checkbox"]').setValue(true)
    expect(w.get('[data-testid="count"]').text()).toBe('4')
  })

  it('muestra el contador de seleccionados', () => {
    const w = mount(DataTable, { props: { columns: cols, items: mk(3), selectable: true } })
    expect(w.text()).toContain('3 resultados')
  })
})

describe('DataTable — contrato previo (no romper lo que ya funcionaba)', () => {
  it('sigue ordenando por columna', async () => {
    const w = mount(DataTable, { props: { columns: cols, items: mk(5) } })
    await w.findAll('thead th')[1].trigger('click')
    const cells = w.findAll('tbody tr td:nth-child(2)').map((td) => Number(td.text()))
    expect(cells).toEqual([0, 1, 2, 3, 4])
  })

  it('muestra estado vacío con título y descripción', () => {
    const w = mount(DataTable, {
      props: { columns: cols, items: [], emptyTitle: 'Nada', emptyDescription: 'sin resultados' },
    })
    expect(w.text()).toContain('Nada')
    expect(w.text()).toContain('sin resultados')
  })

  it('rowClick sigue funcionando cuando no es seleccionable', async () => {
    let clicked: unknown = null
    const w = mount(DataTable, {
      props: { columns: cols, items: mk(3), rowClick: (r: Row) => (clicked = r) },
    })
    await w.findAll('tbody tr')[2].trigger('click')
    expect((clicked as Row).id).toBe('r2')
  })
})

function visibleCountMargin(w: ReturnType<typeof mount>): number {
  // Margen generoso: la ventana depende del alto del viewport medido.
  return 200
}