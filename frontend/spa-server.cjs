#!/usr/bin/env node
/**
 * OWNEX — static server for the production build (zero dependencies).
 *
 * Por qué existe: `spa-server.cjs` anterior hacía `require('express')`, pero
 * express NO está instalado en ningún node_modules del repo, así que el script
 * no podía ejecutarse y no había forma de servir `dist/` por HTTP para el QA
 * de release. Este reemplazo usa sólo módulos nativos de Node (http, fs, path),
 * por lo que no agrega ninguna dependencia (presupuesto de arquitectura: 1).
 *
 * Uso:
 *   node frontend/spa-server.cjs [--port 8080] [--dist frontend/dist]
 *
 * Contrato:
 *   - Sirve `dist/` como estático.
 *   - SPA fallback: cualquier ruta sin extensión → index.html (Vue Router).
 *   - /api y los root-mounted namespaces NO se sirven: el frontend espera que
 *     el backend los-atend[a] aparte (Vite proxy en dev, backend en :8000).
 *     Para no devolver index.html con 200 donde el cliente espera JSON, esas
 *     rutas responden 502 con un mensaje explícito.
 */
'use strict'

const http = require('http')
const net = require('net')
const crypto = require('crypto')
const fs = require('fs')
const path = require('path')

function parseArgs(argv) {
  const out = {
    port: Number(process.env.OWNEX_STATIC_PORT || 8080),
    dist: '',
    // Backend al que proxeamos /api y los root-mounted namespaces. Vacío = sin
    // proxy (el frontend entonces ve 502 explícito en vez de HTML engañoso).
    proxy: process.env.OWNEX_BACKEND_ORIGIN || '',
  }
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--port' && argv[i + 1]) out.port = Number(argv[++i])
    else if (argv[i] === '--dist' && argv[i + 1]) out.dist = argv[++i]
    else if (argv[i] === '--proxy' && argv[i + 1]) out.proxy = argv[++i]
  }
  return out
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.map': 'application/json; charset=utf-8',
  '.wasm': 'application/wasm',
  '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8',
}

// Prefijos que pertenecen al backend. Servirlos desde el static server
// devolvería index.html (200 HTML) donde el cliente espera JSON: un fallo
// silencioso. El backend es un proceso separado (uvicorn :8000).
const BACKEND_PREFIXES = [
  '/api', '/career', '/decision', '/dev-bounty', '/devin', '/direct-work',
  '/enhanced-personalization', '/finance', '/first-money', '/fiverr',
  '/life-management', '/mission-hub', '/mobile', '/oar', '/onboarding',
  '/opensource', '/platform-guides', '/productivity', '/remote',
  '/result-based', '/revenue-timeline', '/supabase', '/today',
  '/version-backup', '/voice', '/wear-os', '/webhook', '/zero-barrier',
]

function isBackendPath(pathname) {
  return BACKEND_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

/**
 * Proxy de WebSocket (upgrade HTTP → TCP crudo).
 *
 * En browser (no-Tauri) la app deriva el WS del origen actual
 * (lib/backend.ts::getWsBase → `ws://${window.location.host}`), así que en el
 * build de producción el handshake cae contra este servidor. Sin esto, cada
 * notificacionesstore() falla con 403 y la app queda sin eventos en vivo.
 */
function proxyWebSocket(req, clientSocket, head, backendOrigin) {
  const target = new URL(req.url, backendOrigin)
  const secure = target.protocol === 'https:'
  const port = Number(target.port) || (secure ? 443 : 80)
  const key = req.headers['sec-websocket-key']

  if (!key) {
    clientSocket.end('HTTP/1.1 400 Bad Request\r\n\r\n')
    return
  }

  const upstream = net.connect({ host: target.hostname, port }, () => {
    const accept = crypto
      .createHash('sha1')
      .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11')
      .digest('base64')
    const lines = [
      `GET ${target.pathname}${target.search} HTTP/1.1`,
      `Host: ${target.host}`,
      'Upgrade: websocket',
      'Connection: Upgrade',
      `Sec-WebSocket-Accept: ${accept}`,
    ]
    for (const [k, v] of Object.entries(req.headers)) {
      const lk = k.toLowerCase()
      if (['host', 'upgrade', 'connection', 'sec-websocket-key', 'sec-websocket-version', 'sec-websocket-extensions'].includes(lk)) continue
      if (Array.isArray(v)) v.forEach((x) => lines.push(`${k}: ${x}`))
      else lines.push(`${k}: ${v}`)
    }
    upstream.write(`${lines.join('\r\n')}\r\n\r\n`)
    if (head && head.length) upstream.write(head)
    upstream.pipe(clientSocket)
    clientSocket.pipe(upstream)
  })

  const teardown = () => {
    upstream.destroy()
    clientSocket.destroy()
  }
  upstream.on('error', () => {
    try {
      clientSocket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n')
    } catch {
      /* socket ya cerrado */
    }
  })
  clientSocket.on('error', teardown)
  upstream.on('close', teardown)
  clientSocket.on('close', teardown)
}

function main() {
  const { port, dist: distArg, proxy } = parseArgs(process.argv)
  const distPath = path.resolve(
    __dirname,
    distArg || path.join(__dirname, 'dist'),
  )

  if (!fs.existsSync(path.join(distPath, 'index.html'))) {
    console.error(
      `[spa-server] No existe ${path.join(distPath, 'index.html')}.\n` +
        `[spa-server] Ejecutá primero:  npm run build --prefix frontend`,
    )
    process.exit(1)
  }

  const indexFile = path.join(distPath, 'index.html')
  // Normaliza el origen del backend sin barra final.
  const backendOrigin = proxy ? proxy.replace(/\/+$/, '') : ''

  const server = http.createServer((req, res) => {
    let pathname = '/'
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    } catch {
      /* URL malformada → raíz */
    }

    if (isBackendPath(pathname)) {
      if (!backendOrigin) {
        res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(
          JSON.stringify({
            error: 'backend_not_proxied',
            path: pathname,
            hint: 'Este servidor sólo sirve el frontend. Para estas rutas necesitás el backend OWNEX en :8000 (o el proxy de Vite en dev).',
          }),
        )
        return
      }

      // Proxy transparente hacia el backend OWNEX.
      const target = new URL(req.url, backendOrigin)
      const headers = { ...req.headers, host: target.host }
      const upstream = http.request(
        {
          protocol: target.protocol,
          hostname: target.hostname,
          port: target.port || 80,
          path: target.pathname + target.search,
          method: req.method,
          headers,
        },
        (upRes) => {
          res.writeHead(upRes.statusCode || 502, upRes.headers)
          upRes.pipe(res)
        },
      )
      upstream.on('error', (err) => {
        if (res.headersSent) return
        res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(
          JSON.stringify({
            error: 'backend_unreachable',
            path: pathname,
            detail: err.message,
            hint: `El backend OWNEX no respondió en ${backendOrigin}. ¿Está corriendo?`,
          }),
        )
      })
      req.pipe(upstream)
      return
    }

    // Resolve dentro de dist y bloquea path traversal.
    const rel = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '')
    const candidate = path.resolve(distPath, rel)
    const withinDist = candidate === distPath || candidate.startsWith(distPath + path.sep)

    let filePath = null
    if (withinDist && fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      filePath = candidate
    } else if (!path.extname(rel)) {
      // SPA fallback para rutas de router (/capital, /mission, …).
      filePath = indexFile
    }

    if (!filePath) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
      res.end('404 — asset not found')
      return
    }

    const ext = path.extname(filePath).toLowerCase()
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=3600',
    })
    fs.createReadStream(filePath).pipe(res)
  })

  // WebSocket: la app (no-Tauri) conecta a ws://<mismo origen>/api/ws.
  server.on('upgrade', (req, socket, head) => {
    if (!backendOrigin) {
      socket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n')
      return
    }
    let pathname = '/'
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
    } catch {
      /* ignore */
    }
    if (!isBackendPath(pathname)) {
      socket.end('HTTP/1.1 404 Not Found\r\n\r\n')
      return
    }
    proxyWebSocket(req, socket, head, backendOrigin)
  })

  server.listen(port, '127.0.0.1', () => {
    console.log(`[spa-server] OWNEX production build en http://127.0.0.1:${port}`)
    console.log(`[spa-server] sirviendo ${distPath}`)
    if (backendOrigin) {
      console.log(`[spa-server] proxy /api y root-mounted → ${backendOrigin}`)
    } else {
      console.log('[spa-server] sin proxy de backend (las rutas /api devuelven 502)')
    }
  })
}

main()
