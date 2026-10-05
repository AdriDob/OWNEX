<script setup lang="ts">
/**
 * CodeEditor — CodeMirror 6 wrapper.
 *
 * Por qué existe: los deliverables de un bounty son código de verdad (el
 * diff del PR, un PoC, un test). Un `<textarea>` no da números de línea,
 * indentación por Tab, resaltado ni selección múltiple, y en un PR de
 * seguridad cada línea importa.
 *
 * CodeMirror 6 y no Monaco: pesa ~1/3 con tree-shaking real en Vite, no
 * necesita workers, y el theme se integra con los tokens existentes.
 *
 * Expone la misma superficie que el textarea que reemplaza (v-model) para
 * que el llamador no cambie, más `language` explícito y eventos de cambio.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const logger = { debug: (..._a: unknown[]) => console.debug('[CodeEditor]', ..._a) }
import { Compartment, EditorState, StateEffect, type Extension } from '@codemirror/state'
import {
  drawSelection,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import { autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap } from '@codemirror/autocomplete'
import {
  bracketMatching,
  defaultHighlightStyle,
  foldGutter,
  foldKeymap,
  indentOnInput,
  syntaxHighlighting,
} from '@codemirror/language'
import { oneDark } from '@codemirror/theme-one-dark'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    readOnly?: boolean
    placeholder?: string
    minHeight?: string
    maxHeight?: string
  }>(),
  {
    language: '',
    readOnly: false,
    placeholder: '',
    minHeight: '12rem',
    maxHeight: '34rem',
  },
)

const emit = defineEmits<{
  'update:modelValue': [string]
  save: []
}>()

const host = ref<HTMLDivElement | null>(null)
let view: EditorView | null = null
/** Reconfigurable sólo para el resaltado: el resto de la config no cambia. */
const langCompartment = new Compartment()

/**
 * Idioma explícito si viene; si no, se deduce del nombre de archivo.
 *
 * Los paquetes de lenguaje se cargan **dinámicamente**: importarlos todos en
 * estático sumaba ~500 KB al chunk de WorkRoom (medido: 744 KB) aunque se
 * editara un solo README.md. Con carga bajo demanda queda el core + el
 * lenguaje que corresponde.
 */
const LANG_BY_EXT: Record<string, () => Promise<Extension[]>> = {
  py: async () => [(await import('@codemirror/lang-python')).python()],
  python: async () => [(await import('@codemirror/lang-python')).python()],
  js: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  ts: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  jsx: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  tsx: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  javascript: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  typescript: async () => [(await import('@codemirror/lang-javascript')).javascript()],
  rs: async () => [(await import('@codemirror/lang-rust')).rust()],
  rust: async () => [(await import('@codemirror/lang-rust')).rust()],
  go: async () => [(await import('@codemirror/lang-go')).go()],
  golang: async () => [(await import('@codemirror/lang-go')).go()],
  md: async () => [(await import('@codemirror/lang-markdown')).markdown()],
  markdown: async () => [(await import('@codemirror/lang-markdown')).markdown()],
}

/** Mapa de extensiones → paquete, para que `test_foo.py` resuelva a Python. */
const EXT_TO_LANG: Record<string, string> = {
  py: 'py',
  js: 'js',
  mjs: 'js',
  jsx: 'jsx',
  ts: 'ts',
  tsx: 'tsx',
  rs: 'rs',
  go: 'go',
  md: 'md',
}

function resolveLangKey(lang: string, filename?: string): string | null {
  const raw = (lang || filename || '').toLowerCase()
  if (!raw) return null
  const direct = LANG_BY_EXT[raw]
  if (direct) return Object.keys(LANG_BY_EXT).find((k) => LANG_BY_EXT[k] === direct)!
  const ext = raw.includes('.') ? raw.split('.').pop()! : raw
  if (LANG_BY_EXT[ext]) return ext
  const mapped = EXT_TO_LANG[ext]
  return mapped && LANG_BY_EXT[mapped] ? mapped : null
}

/**
 * Aplica el lenguaje cuando llega; si falla, el editor sigue usable sin color.
 *
 * Usa un `Compartment` (la API correcta para reconfigurar en caliente): antes
 * se llamaba `EditorState.reconfigure`, que **no existe** en CodeMirror 6 —
 * el TypeError quedaba oculto detrás del `try/catch` del loader porque el
 * fallo ocurre en el `dispatch`, después. Vitest lo reporta como unhandled
 * rejection (5 en la suite completa).
 */
async function applyLanguage(key: string | null): Promise<void> {
  let lang: Extension = []
  try {
    const loader = key ? LANG_BY_EXT[key] : null
    if (loader) lang = (await loader()) as Extension
  } catch (exc) {
    logger.debug('language support unavailable', exc)
  }
  // `await` cede el control y `onBeforeUnmount` pone `view = null` mientras
  // esperamos: hay que capturar la referencia y releerla después.
  const current = view
  if (!current) return
  try {
    current.dispatch({ effects: langCompartment.reconfigure([...lang]) })
  } catch (exc) {
    logger.debug('language reconfigure failed', exc)
  }
}

const baseExtensions = (): Extension => [
    lineNumbers(),
    history(),
    foldGutter(),
    drawSelection(),
    indentOnInput(),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    highlightActiveLine(),
    highlightActiveLineGutter(),
    highlightSelectionMatches(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    keymap.of([
      ...closeBracketsKeymap,
      ...defaultKeymap,
      ...searchKeymap,
      ...historyKeymap,
      ...foldKeymap,
      ...completionKeymap,
      indentWithTab,
    ]),
    EditorView.lineWrapping,
    oneDark,
]

onMounted(() => {
  if (!host.value) return
  const ext: Extension[] = [
    baseExtensions(),
    // El compartment debe estar en la config inicial; sin él, cualquier
    // `reconfigure` posterior lanza.
    langCompartment.of([]),
    EditorView.updateListener.of((u) => {
      if (u.docChanged) emit('update:modelValue', u.state.doc.toString())
    }),
    EditorState.readOnly.of(props.readOnly),
    EditorView.editable.of(!props.readOnly),
  ]
  if (props.placeholder) {
    ext.push(EditorView.contentAttributes.of({ 'aria-label': props.placeholder }))
  }
  view = new EditorView({
    state: EditorState.create({ doc: props.modelValue ?? '', extensions: ext }),
    parent: host.value,
  })
  void applyLanguage(resolveLangKey(props.language))
})

// Cambiar de archivo cambia el highlighting sin recrear el editor.
watch(
  () => props.language,
  (lang) => void applyLanguage(resolveLangKey(lang)),
)

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})

// Cambios externos (abrir otro archivo, undo externo) ⇒ se sincroniza.
watch(
  () => props.modelValue,
  (v) => {
    if (!view) return
    const current = view.state.doc.toString()
    if (v === current) return
    view.dispatch({ changes: { from: 0, to: current.length, insert: v ?? '' } })
  },
)

watch(
  () => props.readOnly,
  (ro) => {
    if (!view) return
    // `EditorState.reconfigure` no existe en CodeMirror 6: el API para
    // reconfigurar en caliente es `StateEffect.reconfigure.of(...)`. Con el
    // antiguo, togglear read-only lanzaba TypeError en runtime.
    view.dispatch({ effects: StateEffect.reconfigure.of([EditorState.readOnly.of(ro), EditorView.editable.of(!ro)]) })
  },
)

defineExpose({ focus: () => view?.focus() })
</script>

<template>
  <div
    ref="host"
    class="overflow-hidden rounded-lg border border-border/50"
    :style="{ minHeight, maxHeight }"
  />
</template>
