/* ════════════════════════════════════════════════════════════
   readinessStore — Pinia store for Mission Control
   Manages service checks, auto-detect, and the "Prepare OWNEX" pipeline.
   ══════════════════════════════════════════════════════════ */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { wsUrl } from '@/lib/backend'
import type { ServiceCheck, SystemSpecs, ReadinessPhase, PrepareEvent } from '@/shared/types'

export const useReadinessStore = defineStore('readiness', () => {
  // ── State ──
  const checks = ref<ServiceCheck[]>([
    // Infrastructure
    { id: 'docker',          name: 'Docker',            category: 'infrastructure', status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'python',          name: 'Python 3',          category: 'infrastructure', status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'node',            name: 'Node.js',           category: 'infrastructure', status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'git',             name: 'Git',               category: 'infrastructure', status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'ollama',          name: 'Ollama',            category: 'ai',             status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'fcc',             name: 'FCC Proxy',         category: 'ai',             status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'claude-code',     name: 'Claude Code',       category: 'ai',             status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'opencode',        name: 'OpenCode',          category: 'ai',             status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'hermes',          name: 'Hermes Agent',      category: 'ai',             status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'vscode',          name: 'VS Code',           category: 'tools',          status: 'pending', message: 'Verificando...', autoDetected: false, canFix: false },
    { id: 'burp',            name: 'Burp Suite',        category: 'security',       status: 'pending', message: 'Verificando...', autoDetected: false, canFix: false },
    { id: 'ffuf',            name: 'FFUF',              category: 'security',       status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'nuclei',          name: 'Nuclei',            category: 'security',       status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'subfinder',       name: 'Subfinder',         category: 'security',       status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
    { id: 'httpx',           name: 'httpx',             category: 'security',       status: 'pending', message: 'Verificando...', autoDetected: false, canFix: true },
  ])

  const specs = ref<SystemSpecs>({
    os: '',
    cpu: '',
    ram_gb: 0,
    disk_free_gb: 0,
  })

  const phase = ref<ReadinessPhase>('idle')
  const score = computed(() => {
    const total = checks.value.length
    const passed = checks.value.filter(c => c.status === 'passed').length
    const errors = checks.value.filter(c => c.status === 'error').length
    return total > 0 ? Math.round((passed / total) * 100) : 0
  })

  const isReady = computed(() => score.value >= 80)
  const isPreparing = computed(() => phase.value === 'preparing')

  let ws: WebSocket | null = null
  let abortController: AbortController | null = null

  // ── Actions ──

  /** Connect to WebSocket for live readiness updates */
  function connectWS() {
    ws = new WebSocket(wsUrl('/api/ws/readiness'))

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as ServiceCheck
        const idx = checks.value.findIndex(c => c.id === data.id)
        if (idx >= 0) {
          checks.value[idx] = { ...checks.value[idx], ...data }
        }
      } catch {
        // skip malformed messages
      }
    }

    ws.onclose = () => {
      // Auto-reconnect after 3s
      setTimeout(() => connectWS(), 3000)
    }
  }

  /** Run auto-detection scan (fetches current system state) */
  async function startScan() {
    phase.value = 'scanning'
    checks.value.forEach(c => {
      if (c.status === 'pending') c.status = 'checking'
    })

    try {
      const res = await fetch('/api/system/auto-detect')
      if (res.ok) {
        const data = await res.json()
        if (data.checks) {
          data.checks.forEach((update: Partial<ServiceCheck>) => {
            const idx = checks.value.findIndex(c => c.id === update.id)
            if (idx >= 0) {
              checks.value[idx] = { ...checks.value[idx], ...update, autoDetected: true }
            }
          })
        }
        if (data.specs) {
          specs.value = data.specs
        }
      }
    } catch {
      // Backend offline — leave checks as pending/checking
    }

    phase.value = 'idle'
  }

  /** Execute the "Prepare OWNEX" pipeline via SSE */
  async function prepare() {
    if (isPreparing.value) return
    phase.value = 'preparing'
    abortController = new AbortController()

    try {
      const res = await fetch('/api/system/prepare', {
        method: 'POST',
        signal: abortController.signal,
      })

      if (!res.ok) {
        phase.value = 'idle'
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        phase.value = 'idle'
        return
      }

      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6)) as PrepareEvent

            if ((event as any).type === 'complete') {
              phase.value = 'ready'
            } else {
              const ev = event as any
              const idx = checks.value.findIndex(c => c.id === ev.id)
              if (idx >= 0) {
                checks.value[idx] = {
                  ...checks.value[idx],
                  status: ev.status || 'passed',
                  message: ev.message || '',
                  version: ev.version || checks.value[idx].version,
                }
              }
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch {
      phase.value = 'idle'
    }

    if (phase.value !== 'ready') {
      phase.value = 'idle'
    }
  }

  /** Cancel an ongoing prepare operation */
  function cancelPrepare() {
    abortController?.abort()
    phase.value = 'idle'
  }

  /** Disconnect WebSocket on unmount */
  function disconnectWS() {
    ws?.close()
    ws = null
  }

  return {
    checks,
    specs,
    phase,
    score,
    isReady,
    isPreparing,
    connectWS,
    startScan,
    prepare,
    cancelPrepare,
    disconnectWS,
  }
})
