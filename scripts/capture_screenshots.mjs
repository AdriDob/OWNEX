import { chromium } from '/home/adrie/projects/Rastro/node_modules/playwright-core/index.mjs'
import { mkdirSync } from 'node:fs'

const API = 'http://127.0.0.1:8000'
const BASE = 'http://localhost:5173'
const OUT_DARK = '/home/adrie/projects/Rastro/docs/assets/screenshots/desktop'
const OUT_LIGHT = '/home/adrie/projects/Rastro/docs/assets/screenshots/desktop-light'

const LIGHT_CSS = `
:root {
  --color-background: #f6f8fa;
  --color-surface: #ffffff;
  --color-surface-hover: #f0f3f6;
  --color-border: #d0d7de;
  --color-border-light: #eaeef2;
  --color-muted: #818b98;
  --color-muted-foreground: #59636e;
  --color-foreground: #1f2328;
  --color-primary: #1f2328;
  --color-primary-foreground: #ffffff;
  --color-warning: #9a6700;
  --color-gold: #9a6700;
  --ownex-bg: #f6f8fa;
  --ownex-bg-deep: #f6f8fa;
  --ownex-bg-base: #ffffff;
  --ownex-bg-surface: #ffffff;
  --ownex-bg-glass: rgba(255, 255, 255, 0.75);
  --ownex-bg-glass-border: rgba(0, 0, 0, 0.08);
  --ownex-blue: #1f2328;
  --ownex-white: #1f2328;
  --ownex-gold: #9a6700;
  --ownex-text-primary: #1f2328;
  --ownex-text-secondary: #59636e;
  --ownex-text-muted: #818b98;
  --ownex-text-disabled: #afb8c1;
  --ownex-bg-elevated: #ffffff;
  --ownex-bg-card: #ffffff;
  --ownex-border: #d0d7de;
  --ownex-border-light: #eaeef2;
  --ownex-text: #1f2328;
  --ownex-text-dim: #59636e;
  --ownex-text-muted: #818b98;
  --ownex-accent: #e82127;
  --ownex-accent-glow: rgba(232, 33, 39, 0.25);
  --ownex-accent-dim: rgba(232, 33, 39, 0.08);
  --ownex-info: #0969da;
  --ownex-info-dim: rgba(9, 105, 218, 0.1);
  --ownex-info-glow: rgba(9, 105, 218, 0.25);
  --ownex-success: #1a7f37;
  --ownex-success-dim: rgba(26, 127, 55, 0.1);
  --ownex-success-glow: rgba(26, 127, 55, 0.25);
  --ownex-warning: #9a6700;
  --ownex-warning-glow: rgba(154, 103, 0, 0.25);
  --bg-primary: #f6f8fa;
  --bg-secondary: #ffffff;
  --bg-tertiary: #ffffff;
  --bg-elevated: #ffffff;
  --bg-hover: #eaeef2;
  --foreground: #1f2328;
  --text-primary: #1f2328;
  --text-secondary: #59636e;
  --text-muted: #818b98;
  --border-color: #d0d7de;
}
html, body { background: #f6f8fa !important; color: #1f2328 !important; color-scheme: light; }
#app > div { background-color: transparent !important; background-image: none !important; }
.gaming-console, .welcome-page { background: #f6f8fa !important; background-color: #f6f8fa !important; }
.core-visualization canvas { visibility: hidden !important; }
.jarvis-background { display: none !important; }
.card-base, .panel, .tactical-panel, .glass-terminal {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 255, 255, 0.9)) !important;
}
.glass, .glass-strong {
  background: rgba(255, 255, 255, 0.82) !important;
}
.card-blue, .card-blue:hover {
  border-color: rgba(0, 0, 0, 0.1) !important;
  box-shadow: none !important;
}
.hover-lift:hover { border-color: rgba(0, 0, 0, 0.12) !important; }
.merlin-jarvis { background: #f6f8fa !important; }
.jarvis-sidebar { background: #ffffff !important; }
.message-body { background: #ffffff !important; }
.action-card, .stat-card, .status-card, .activity-item { background: rgba(255, 255, 255, 0.95) !important; }
.text-gradient, .text-gradient-gold {
  background: linear-gradient(135deg, #1f2328, #59636e) !important;
}
`

async function getToken() {
  const csrfRes = await fetch(`${API}/api/version`)
  const cookies = csrfRes.headers.getSetCookie?.() ?? []
  const csrfMatch = cookies.find(c => c.startsWith('csrf-token='))
  const csrfCookie = csrfMatch ? csrfMatch.split(';')[0] : ''
  const csrfToken = csrfCookie.replace('csrf-token=', '')
  const headers = { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, Cookie: csrfCookie }
  const register = await fetch(`${API}/api/auth/users/register`, { method: 'POST', headers, body: JSON.stringify({ username: 'operator', email: 'op@ownex.local', password: 'ownex-secret-2026' }) })
  if (register.ok) return (await register.json()).access_token
  const login = await fetch(`${API}/api/auth/users/login`, { method: 'POST', headers, body: JSON.stringify({ username: 'operator', password: 'ownex-secret-2026' }) })
  if (login.ok) return (await login.json()).access_token
  throw new Error(`auth failed: ${register.status} ${login.status}`)
}

const token = await getToken()
console.log('AUTH OK')

const browser = await chromium.launch({
  executablePath: '/home/adrie/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell',
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-device-scale-factor=2', '--hide-scrollbars'],
})

const shots = [
  ['mission-control', '/'],
  ['intelligence', '/intelligence/findings'],
  ['targets', '/targets/list'],
  ['capital', '/capital'],
  ['merlin', '/merlin'],
  ['agents', '/agents'],
  ['reports', '/reports'],
  ['settings', '/operations/settings'],
]

// Kill the boot splash overlay immediately: it is a fixed z-200 layer that
// unmounts on its own after ~16s, but the app renders below it from mount.
const SPLASH_KILL = `
const style = document.createElement('style')
style.textContent = '.splash-bg{display:none!important}'
document.head.appendChild(style)
`

async function capture(theme, out) {
  mkdirSync(out, { recursive: true })
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2, colorScheme: theme })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.log(`PAGEERROR[${theme}]`, e.message.slice(0, 100)))
  await page.addInitScript((t) => { localStorage.setItem('CATEYE-token', t) }, token)
  await page.addInitScript(SPLASH_KILL)

  for (const [name, path] of shots) {
    try {
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 })
      await page.waitForTimeout(1500)
      // Wait for the real app (not the splash) to be present
      try {
        await page.waitForFunction(() => document.querySelector('#app > div') && !document.querySelector('.splash-bg'), { timeout: 30000 })
      } catch {
        console.log(`WARN[${theme}/${name}] app content not detected, shooting anyway`)
      }
      if (theme === 'light') {
        await page.addStyleTag({ content: LIGHT_CSS })
      }
      await page.waitForTimeout(4000)
      await page.screenshot({ path: `${out}/${name}.png` })
      console.log('OK', theme, name)
    } catch (e) {
      console.log('FAIL', theme, name, e.message.slice(0, 100))
    }
  }
  await ctx.close()
}

const only = process.argv[2]
if (!only || only === 'dark') await capture('dark', OUT_DARK)
if (!only || only === 'light') await capture('light', OUT_LIGHT)
await browser.close()
console.log('DONE')
