/**
 * Shared semantic-label helpers for all chat UIs.
 *
 * Backend contract (POST /api/copilot/chat, POST /api/merlin/chat):
 *   semantics?: { FACT: string[]; INFERENCE: string[]; RECOMMENDATION: string[]; UNKNOWN: string[] }
 * Model output is INFERENCE by contract, never FACT. These helpers only MAP
 * authoritative labels to display blocks — they never re-derive tags.
 */
import type { SemanticBlock } from '@/types/ownex'

export type BackendLabels = Partial<Record<'FACT' | 'INFERENCE' | 'RECOMMENDATION' | 'UNKNOWN', string[]>>

const ORDER = ['FACT', 'INFERENCE', 'RECOMMENDATION', 'UNKNOWN'] as const

/** Map backend labels to display blocks (capped). Empty when no labels. */
export function blocksFromLabels(
  labels?: BackendLabels | null,
  perTag = 3,
  maxBlocks = 12,
  maxLen = 220,
): SemanticBlock[] {
  if (!labels) return []
  const blocks: SemanticBlock[] = []
  for (const tag of ORDER) {
    for (const line of (labels[tag] ?? []).slice(0, perTag)) {
      blocks.push({ tag, text: String(line).slice(0, maxLen) })
      if (blocks.length >= maxBlocks) return blocks
    }
  }
  return blocks
}

/** Short legend hint per tag (ES). */
export const TAG_HINT: Record<string, string> = {
  FACT: 'Dato verificado',
  INFERENCE: 'Inferencia del modelo',
  RECOMMENDATION: 'Recomendación',
  UNKNOWN: 'Sin verificar',
}
