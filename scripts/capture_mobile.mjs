import { chromium } from '/home/adrie/projects/Rastro/node_modules/playwright-core/index.mjs'
import { mkdirSync } from 'node:fs'

const API = 'http://127.0.0.1:8000'
const BASE = 'http://localhost:5173'
const OUT_DARK = '/home/adrie/projects/Rastro/docs/assets/screenshots/mobile'
const OUT_LIGHT = '/home/adrie/projects/Rastro/docs/assets/screenshots/mobile-light'

const LIGHT_CSS = `
:root {
  --color-background: #f6f8fa; --color-surface: #ffffff; --color-surface-hover: #f0f3f6;
  --color-border: #d0d7de; --color-border-light: #eaeef2; --color-muted: #818b98;
  --color-muted-foreground: #59636e; --color-foreground: #1f2328; --color-primary: #1f2328;
  --color-primary-foreground: #ffffff; --color-warning: #9a6700; --color-gold: #9a6700;
  --ownex-bg: #f6f8fa; --ownex-bg-deep: #f6f8fa; --ownex-bg-base: #ffffff; --ownex-bg-surface: #ffffff;
  --ownex-bg-glass: rgba(255, 255, 255, 0.75); --ownex-bg-glass-border: rgba(0, 0, 0, 0.08);
  --ownex-blue: #1f2328; --ownex-white: #1f2328; --ownex-gold: #9a6700;
  --ownex-text-primary: #1f2328; --ownex-text-secondary: #59636e; --ownex-text-muted: #818b98;
  --ownex-text-disabled: #afb8c1; --ownex-bg-elevated: #ffffff; --ownex-bg-card: #ffffff;
  --ownex-border: #d0d7de; --ownex-border-light: #eaeef2; --ownex-text: #1f2328; --ownex-text-dim: #59636e;
  --ownex-accent: #e82127; --ownex-accent-glow: rgba(232, 33, 39, 0.25); --ownex-accent-dim: rgba(232, 33, 39, 0.08);
  --ownex-info: #0969da; --ownex-success: #1a7f37; --ownex-warning: #9a6700;
}
html, body { background: #f6f8fa !important; color: #1f2328 !important; color-scheme: light; }
#app > div { background-color: transparent !important; background-image: none !important; }
.gaming-console, .welcome-page { background: #f6f8fa !important; background-color: #f6f8fa !important; }
.core-visualization canvas { visibility: hidden !important; }
.merlin-jarvis { background: #f6f8fa !important; }
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
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--hide-scrollbars'],
})

const shots = [
  ['mission-control', '/'],
  ['good-morning', '/dashboard'],
  ['intelligence', '/intelligence/findings'],
  ['targets', '/targets/list'],
  ['merlin', '/merlin'],
]

async function capture(theme, out) {
  mkdirSync(out, { recursive: true })
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, colorScheme: theme })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.log(`PAGEERROR[${theme}]`, e.message.slice(0, 100)))
  await page.addInitScript((t) => { localStorage.setItem('CATEYE-token', t) }, token)

  for (const [name, path] of shots) {
    try {
      await page.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 })
      await page.waitForTimeout(1200)
      try {
        await page.waitForSelector('.splash-bg', { state: 'detached', timeout: 40000 })
      } catch {
        console.log(`WARN[${theme}/${name}] splash still visible, shooting anyway`)
      }
      if (theme === 'light') {
        await page.addStyleTag({ content: LIGHT_CSS })
      }
      await page.waitForTimeout(2000)
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