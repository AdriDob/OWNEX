import { chromium } from '/home/adrie/projects/Rastro/node_modules/playwright-core/index.mjs'
import { mkdirSync } from 'node:fs'

const API = 'http://127.0.0.1:8000'
const BASE = 'http://localhost:5173'
const OUT = '/home/adrie/projects/Rastro/docs/assets/screenshots/desktop'
mkdirSync(OUT, { recursive: true })

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
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2, colorScheme: 'dark' })
const page = await ctx.newPage()
page.on('pageerror', (e) => console.log('PAGEERROR', e.message.slice(0, 100)))

await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 25000 })
await page.evaluate((t) => { localStorage.setItem('CATEYE-token', t) }, token)
await page.waitForTimeout(500)

const shots = [
  ['mission-control', '/', 'mission-control'],
  ['good-morning', '/dashboard', 'dashboard'],
  ['intelligence', '/intelligence/findings', 'intelligence'],
  ['targets', '/targets/list', 'targets'],
  ['capital-dashboard', '/capital', 'capital'],
  ['executive-dashboard', '/security/executive', 'executive'],
  ['operations', '/operations/dashboard', 'operations'],
  ['merlin', '/merlin', 'merlin'],
  ['agent-center', '/copilot/notifications', 'notifications'],
]
for (const [name, path, label] of shots) {
  try {
    await page.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 25000 })
    await page.waitForTimeout(5000)
    await page.screenshot({ path: `${OUT}/${name}.png` })
    console.log('OK', name)
  } catch (e) {
    console.log('FAIL', name, e.message.slice(0, 100))
  }
}
await browser.close()
console.log('DONE')