/* ════════════════════════════════════════════════════════════
   SHARED TYPES — OWNEX Motion & Readiness
   ══════════════════════════════════════════════════════════ */

export interface SpringPreset {
  stiffness: number
  damping: number
  mass?: number
}

export const SpringPresets = {
  snappy: { stiffness: 200, damping: 20, mass: 0.5 },
  gentle: { stiffness: 120, damping: 14, mass: 1 },
  bouncy: { stiffness: 100, damping: 8, mass: 1 },
  liquid: { stiffness: 80, damping: 12, mass: 1.2 },
  stiff: { stiffness: 300, damping: 30, mass: 0.8 },
  loading: { stiffness: 150, damping: 18, mass: 1 },
} as const

export interface ServiceCheck {
  id: string
  name: string
  category: 'infrastructure' | 'tools' | 'ai' | 'security' | 'config' | 'data'
  status: 'pending' | 'checking' | 'installing' | 'configuring' | 'passed' | 'warning' | 'error'
  message: string
  version?: string
  autoDetected: boolean
  canFix: boolean
}

export type ReadinessPhase = 'idle' | 'scanning' | 'preparing' | 'ready'

export interface SystemSpecs {
  os: string
  cpu: string
  ram_gb: number
  gpu?: string
  disk_free_gb: number
}

export interface PrepareProgressEvent {
  id: string
  status: ServiceCheck['status']
  message: string
  version?: string
}

export interface PrepareCompleteEvent {
  type: 'complete'
  score: number
  duration: number
}

export type PrepareEvent = PrepareProgressEvent | PrepareCompleteEvent
