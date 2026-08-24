<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { wsUrl } from '@/lib/backend'

const terminalEl = ref<HTMLDivElement | null>(null)
const theme = ref<'dark' | 'light'>('dark')
let terminal: any = null
let fitAddon: any = null

// Determinar backend: PowerShell en Windows nativo, bash en Linux/WSL
const shell = navigator.userAgent.includes('Windows NT')
  ? ['powershell.exe', '-NoLogo']
  : ['/bin/bash', '--login']

let ws: WebSocket | null = null
let backendProcess: any = null
const WS_OPEN = WebSocket.OPEN

onMounted(async () => {
  await nextTick()
  if (!terminalEl.value) return

  // Cargar xterm dinámicamente
  const { Terminal } = await import('xterm')
  const { FitAddon } = await import('@xterm/addon-fit')

  terminal = new Terminal({
    cursorBlink: true,
    cursorStyle: 'block',
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace",
    theme: {
      background: '#0a0a0f',
      foreground: '#e0e0e0',
      cursor: '#0070d1',
      cursorAccent: '#ffffff',
      selectionBackground: 'rgba(255, 255, 255, 0.4)',
      black: '#1a1a2e',
      red: '#ff5555',
      green: '#50fa7b',
      yellow: '#f1fa8c',
      blue: '#0070d1',
      magenta: '#ff79c6',
      cyan: '#8be9fd',
      white: '#f0f0f0',
      brightBlack: '#44475a',
      brightRed: '#ff6e6e',
      brightGreen: '#69ff94',
      brightYellow: '#ffffa5',
      brightBlue: '#0070d1',
      brightMagenta: '#ff92d0',
      brightCyan: '#a4ffff',
      brightWhite: '#ffffff',
    },
    allowTransparency: true,
    convertEol: true,
    scrollback: 10000,
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalEl.value)
  fitAddon.fit()

  terminal.write('\x1b[36m╔════════════════════════════════════════════╗\x1b[0m\r\n')
  terminal.write('\x1b[36m║  \x1b[1;34mOWNEX Terminal v5.0.0\x1b[0m\x1b[36m                  ║\x1b[0m\r\n')
  terminal.write('\x1b[36m║  \x1b[0mBuilt-in shell — ejecuta cualquier comando  \x1b[36m║\x1b[0m\r\n')
  terminal.write('\x1b[36m║  \x1b[0mDashboard + Terminal en la misma ventana     \x1b[36m║\x1b[0m\r\n')
  terminal.write('\x1b[36m╚════════════════════════════════════════════╝\x1b[0m\r\n\r\n')

  // Intentar conectar al backend Python via WebSocket
  try {
    ws = new WebSocket(wsUrl('/api/ws/terminal'))
    ws.onopen = () => {
      terminal.write('\x1b[32m✓ Backend conectado\x1b[0m\r\n')
    }
    ws.onmessage = (event) => {
      terminal.write(event.data)
    }
    ws.onerror = () => {
      terminal.write('\x1b[33m⚠ Backend no disponible — usando shell local\x1b[0m\r\n')
      startLocalShell()
    }
    ws.onclose = () => {
      terminal.write('\r\n\x1b[33m⚠ Conexión con backend perdida\x1b[0m\r\n')
    }
  } catch {
    startLocalShell()
  }

  // Manejar input del usuario
  terminal.onData((data: string) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
    if (backendProcess?.stdin) {
      backendProcess.stdin.write(data)
    }
  })

  // Fit on resize
  window.addEventListener('resize', handleResize)
})

function startLocalShell() {
  // En Tauri, usaríamos el sidecar. En browser, shell por WebSocket.
  terminal.write('\x1b[33mUsando shell local (comandos básicos)\x1b[0m\r\n')
  terminal.write('\x1b[33m> Conecta el backend Python para shell completo\x1b[0m\r\n\r\n')
}

function handleResize() {
  if (fitAddon) {
    try { fitAddon.fit() } catch {}
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (ws) ws.close()
  if (terminal) terminal.dispose()
})

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

function clearTerminal() {
  if (terminal) terminal.clear()
}

</script>

<template>
  <div class="terminal-page h-full flex flex-col">
    <!-- Header bar -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-accent/20">
      <div class="flex items-center gap-3">
        <span class="font-mono text-[10px] font-bold tracking-widest text-primary uppercase">Terminal</span>
        <span class="text-[10px] text-muted-foreground font-mono">OWNEX Shell v5.0.0</span>
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-success/10 text-success text-[9px] font-mono">
          <span class="w-1.5 h-1.5 rounded-full bg-success"></span>
          {{ ws?.readyState === WS_OPEN ? 'Connected' : 'Local' }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button @click="clearTerminal"
          class="px-2 py-1 text-[10px] font-mono rounded bg-accent/30 hover:bg-accent/60 text-muted-foreground hover:text-foreground transition-colors">
          Clear
        </button>
        <button @click="toggleTheme"
          class="px-2 py-1 text-[10px] font-mono rounded bg-accent/30 hover:bg-accent/60 text-muted-foreground hover:text-foreground transition-colors">
          {{ theme === 'dark' ? '☀︎' : '☾' }}
        </button>
      </div>
    </div>

    <!-- Terminal container -->
    <div ref="terminalEl" class="flex-1 min-h-0 px-1 py-1"></div>
  </div>
</template>

<style>
/* xterm overrides */
.terminal-page .xterm {
  height: 100%;
  padding: 4px;
}
.terminal-page .xterm-viewport {
  scrollbar-width: thin;
  scrollbar-color: #0070d1 transparent;
}
.terminal-page .xterm-viewport::-webkit-scrollbar {
  width: 6px;
}
.terminal-page .xterm-viewport::-webkit-scrollbar-thumb {
  background: #0070d1;
  border-radius: 3px;
}
.terminal-page .xterm-viewport::-webkit-scrollbar-track {
  background: transparent;
}
</style>
