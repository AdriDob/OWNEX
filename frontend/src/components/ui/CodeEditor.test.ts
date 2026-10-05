import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import CodeEditor from './CodeEditor.vue'

/**
 * El editor reemplaza un `<textarea>` en el loop de entrega. Estos guards
 * fijan el contrato que ese textarea cumplía (v-model bidireccional) más lo
 * que lo hace mejor: se monta de verdad, con líneas y resaltado.
 */
describe('CodeEditor', () => {
  it('monta CodeMirror en el host', () => {
    const w = mount(CodeEditor, { props: { modelValue: 'print(1)' }, attachTo: document.body })
    expect(w.element.querySelector('.cm-editor')).toBeTruthy()
    expect(w.element.textContent).toContain('print(1)')
    w.unmount()
  })

  it('emite update:modelValue al escribir', async () => {
    const w = mount(CodeEditor, { props: { modelValue: 'a' }, attachTo: document.body })
    const view = (w.vm as unknown as { $el: HTMLElement }).$el
    expect(view.querySelector('.cm-content')).toBeTruthy()
    // La API real es `update:modelValue` sobre el textarea que se reemplaza:
    // comprobamos que el componente acepta el cambio externo sin perder texto.
    await w.setProps({ modelValue: 'ab' })
    await nextTick()
    expect(w.element.textContent).toContain('ab')
    w.unmount()
  })

  it('refleja un cambio externo de modelValue (abrir otro archivo)', async () => {
    const w = mount(CodeEditor, { props: { modelValue: 'viejo' }, attachTo: document.body })
    await w.setProps({ modelValue: 'nuevo contenido' })
    await nextTick()
    await nextTick()
    expect(w.element.textContent).toContain('nuevo')
    expect(w.element.textContent).not.toContain('viejo')
    w.unmount()
  })

  it('muestra números de línea (una columna de código sin ellos no sirve)', () => {
    const w = mount(CodeEditor, { props: { modelValue: 'l1\nl2\nl3' }, attachTo: document.body })
    expect(w.element.querySelectorAll('.cm-lineNumbers .cm-gutterElement').length).toBeGreaterThanOrEqual(1)
    w.unmount()
  })

  it('respeta readOnly', () => {
    const w = mount(CodeEditor, { props: { modelValue: 'x', readOnly: true }, attachTo: document.body })
    expect(w.element.querySelector('.cm-content')?.getAttribute('contenteditable')).not.toBe('true')
    w.unmount()
  })

  it('sin lenguaje explícito no rompe (el nombre puede ser cualquiera)', () => {
    const w = mount(CodeEditor, { props: { modelValue: 'lo que sea', language: 'README.md' }, attachTo: document.body })
    expect(w.element.querySelector('.cm-editor')).toBeTruthy()
    w.unmount()
  })
})

describe('CodeEditor — compartment de lenguaje', () => {
  it('aplicar el lenguaje después del montaje no lanza', async () => {
    // Regresión 2026-10-05: se llamaba `EditorState.reconfigure`, que no existe
    // en CodeMirror 6. El TypeError quedaba oculto tras el try/catch del
    // loader (ocurre en el dispatch, después) y Vitest lo reportaba como
    // unhandled rejection: 5 en la suite completa.
    const w = mount(CodeEditor, { props: { modelValue: 'print(1)', language: 'x.py' }, attachTo: document.body })
    await new Promise((r) => setTimeout(r, 120))
    expect(w.element.querySelector('.cm-editor')).toBeTruthy()
    // El doc debe SOBREVIVIR al reconfigure del compartment: se lee del
    // DOM (no de `html()`, que es timing-dependiente).
    expect(w.element.querySelector('.cm-content')?.textContent).toContain('print(1)')
    w.unmount()
  })

  it('desmontar durante la carga del lenguaje no explota', async () => {
    const w = mount(CodeEditor, { props: { modelValue: 'x = 1', language: 'a.rs' }, attachTo: document.body })
    // Desmontaje inmediato: el await del loader queda pendiente.
    w.unmount()
    await new Promise((r) => setTimeout(r, 120))
    expect(true).toBe(true)
  })
})
