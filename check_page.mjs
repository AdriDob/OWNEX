import { chromium } from '/home/adrie/projects/Rastro/node_modules/playwright-core/index.mjs'

const API = 'http://127.0.0.1:8000'
const BASE = 'http://localhost:5173'

async function login() {
  const csrfRes = await fetch(`${API}/api/version`)
  const cookies = csrfRes.headers.getSetCookie?.() ?? []
  const csrfMatch = cookies.find(c => c.startsWith('csrf-token='))
  const csrfCookie = csrfMatch ? csrfMatch.split(';')[0] : ''
  const csrfToken = csrfCookie.replace('csrf-token=', '')
  const headers = { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, Cookie: csrfCookie }
  const loginRes = await fetch(`${API}/api/auth/users/login`, { method: 'POST', headers, body: JSON.stringify({ username: 'operator', password: 'ownex-secret-2026' }) })
  if (loginRes.ok) return (await loginRes.json()).access_token
  throw new Error(`login failed: ${loginRes.status}`)
}

const token = await login()
console.log('AUTH OK')

const browser = await chromium.launch({
  executablePath: '/home/adrie/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell',
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--hide-scrollbars'],
})
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } })
const page = await ctx.newPage()
await page.addInitScript((t) => { localStorage.setItem('CATEYE-token', t) }, token)
const SPLASH_KILL = `
const style = document.createElement('style')
style.textContent = '.splash-bg{display:none!important}'
document.head.appendChild(style)
`
await page.addInitScript(SPLASH_KILL)

async function dump(name, path) {
  await page.goto(BASE + path, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await page.waitForTimeout(3000)
  const info = await page.evaluate(() => ({
    title: document.title,
    bodyText: document.body.innerText.slice(0, 500),
    h1: document.querySelector('h1')?.textContent ?? null,
    h2: document.querySelector('h2')?.textContent ?? null,
    innerHTML: document.body.innerHTML.slice(0, 3000),
  }))
  console.log(`=== ${name} (${path}) ===`)
  console.log('h1:', info.h1)
  console.log('h2:', info.h2)
  console.log('text:', info.bodyText)
  console.log()
}

await dump('Mission Control', '/')
await dump('Intelligence', '/intelligence/findings')
await dump('Targets', '/targets/list')
await dump('Capital', '/capital')
await dump('MERLIN', '/merlin')
await dump('Agents', '/agents')
await dump('Reports', '/reports')
await dump('Settings', '/operations/settings')

await browser.close()
