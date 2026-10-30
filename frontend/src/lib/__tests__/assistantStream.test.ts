import { describe, expect, it, vi, beforeEach } from 'vitest'

/**
 * Contrato del stream de assistant (medido contra el backend 2026-10-05).
 *
 * `api/routers/assistant.py:113` emite SSE con **texto plano**:
 *     data: <token>\n\n
 *     data: [DONE]\n\n
 *
 * El cliente hacía `JSON.parse(data)` sobre cada token: `"hola"` no es JSON ⇒
 * excepción ⇒ `catch` la descartaba. El streaming NUNCA mostró nada y la IA
 * parecía colgada aunque el provider respondiera.
 */

const streamOf = (chunks: string[]) =>
  new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder()
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })

async function run(chunks: string[]) {
  const { assistantStreamChat } = await import('@/lib/api')
  const fetchSpy = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue({ ok: true, status: 200, body: streamOf(chunks) } as Response)
  const tokens: string[] = []
  await assistantStreamChat('hola', [], (t: string) => tokens.push(t))
  fetchSpy.mockRestore()
  return tokens
}

describe('assistantStreamChat — tokens en texto plano', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('acumula tokens sin JSON.parse', async () => {
    const tokens = await run(['data: Hola\n\n', 'data: , ¿qué tal\n\n', 'data: ?\n\n', 'data: [DONE]\n\n'])
    expect(tokens.join('')).toBe('Hola, ¿qué tal?')
  })

  it('corta en [DONE] y no lo emite como token', async () => {
    const tokens = await run(['data: a\n\n', 'data: [DONE]\n\n', 'data: no-debe-aparecer\n\n'])
    expect(tokens).toEqual(['a'])
  })

  it('acepta también el formato JSON {token} por si un provider lo usa', async () => {
    const tokens = await run(['data: {"token":"hola"}\n\n', 'data: [DONE]\n\n'])
    expect(tokens).toEqual(['hola'])
  })

  it('un token que parece JSON pero es texto no se pierde', async () => {
    // `{"a":1}` sí es JSON válido pero sin `token`: no debe tragarse el texto.
    const tokens = await run(['data: {"precio": 500}\n\n', 'data: [DONE]\n\n'])
    expect(tokens.join('')).toContain('500')
  })

  it('stream vacío (sin provider) no cuelga', async () => {
    // Observado en vivo con 0 credenciales: el backend responde 200 y sólo
    // `data: [DONE]`.
    const tokens = await run(['data: [DONE]\n\n'])
    expect(tokens).toEqual([])
  })

  it('ignora líneas que no son eventos data', async () => {
    const tokens = await run(['event: ping\n\n', 'data: hola\n\n', ': comentario\n\n', 'data: [DONE]\n\n'])
    expect(tokens).toEqual(['hola'])
  })
})
