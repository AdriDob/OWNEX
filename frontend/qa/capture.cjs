// OWNEX Frontend QA capture — baseline visual + console/request errors.
// Usage: node qa/capture.cjs [baseUrl] [outDir]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.argv[2] || 'http://localhost:5173';
const OUTPUT_DIR = process.argv[3] || path.join(__dirname, 'screenshots');
// Optional: QA_TOKEN env injects an authenticated session (CATEYE-token).
const QA_TOKEN = process.env.QA_TOKEN || '';
const QA_TOKEN_EXPIRY = process.env.QA_TOKEN_EXPIRY || '';

const VIEWPORTS = {
  '1366x768': { width: 1366, height: 768 },
  '1440x900': { width: 1440, height: 900 },
  '1920x1080': { width: 1920, height: 1080 },
};

// 8 módulos del App Shell V2.1 + satellites importantes
const ROUTES = [
  { path: '/', name: 'command-center' },
  { path: '/targets/prioritization', name: 'opportunities' },
  { path: '/operations/work-queue', name: 'work-bank' },
  { path: '/operations/workflows', name: 'engineering-factory' },
  { path: '/operations/dashboard', name: 'operations' },
  { path: '/investments', name: 'investment-hub' },
  { path: '/capital', name: 'financial-hub' },
  { path: '/integrations/connections', name: 'integrations' },
  { path: '/operations/settings', name: 'settings' },
  { path: '/operations/health', name: 'health' },
  { path: '/merlin', name: 'merlin' },
  { path: '/intelligence/findings', name: 'findings' },
];

async function captureRoute(browser, route, viewportName, viewport) {
  const page = await browser.newPage({ viewport });
  if (QA_TOKEN) {
    await page.addInitScript(([token, expiry]) => {
      try {
        localStorage.setItem('CATEYE-token', token);
        if (expiry) localStorage.setItem('CATEYE-session-expires', expiry);
      } catch { /* */ }
    }, [QA_TOKEN, QA_TOKEN_EXPIRY]);
  }
  const errors = [];
  const failedReqs = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text().slice(0, 300));
  });
  page.on('pageerror', (err) => errors.push(`PAGEERROR: ${String(err).slice(0, 300)}`));
  page.on('requestfailed', (req) => {
    failedReqs.push(`${req.url().slice(0, 140)} :: ${req.failure()?.errorText || ''}`);
  });
  page.on('response', (res) => {
    if (res.status() >= 500) failedReqs.push(`HTTP ${res.status()} ${res.url().slice(0, 140)}`);
  });

  const fullName = `${route.name}-${viewportName}`;
  try {
    await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1200);
    const screenshotPath = path.join(OUTPUT_DIR, `${fullName}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });
    return { route: route.path, viewport: viewportName, ok: true, errors, failedReqs };
  } catch (e) {
    return { route: route.path, viewport: viewportName, ok: false, error: String(e).slice(0, 200), errors, failedReqs };
  } finally {
    await page.close();
  }
}

async function main() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const candidates = [
    path.join(process.env.HOME, '.cache/ms-playwright/chromium-1234/chrome-linux64/chrome'),
    path.join(process.env.HOME, '.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell'),
  ];
  const exe = candidates.find((p) => fs.existsSync(p));
  const browser = await chromium.launch({ headless: true, ...(exe ? { executablePath: exe } : {}) });
  const results = [];

  for (const route of ROUTES) {
    for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
      const r = await captureRoute(browser, route, vpName, vp);
      results.push(r);
      const flag = r.ok ? 'OK ' : 'ERR';
      console.log(`${flag} ${r.route} @${vpName}  consoleErr=${r.errors.length} reqFail=${r.failedReqs.length}${r.error ? ' :: ' + r.error : ''}`);
      for (const e of r.errors.slice(0, 3)) console.log(`    console: ${e}`);
      for (const f of r.failedReqs.slice(0, 5)) console.log(`    req: ${f}`);
    }
  }

  await browser.close();
  fs.writeFileSync(path.join(OUTPUT_DIR, 'capture-report.json'), JSON.stringify({ ts: new Date().toISOString(), baseUrl: BASE_URL, results }, null, 2));
  const bad = results.filter((r) => !r.ok || r.errors.length || r.failedReqs.length);
  console.log(`\nDone. ${results.length} captures, ${bad.length} with issues -> ${OUTPUT_DIR}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
