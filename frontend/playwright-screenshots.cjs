const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:8081';
const OUTPUT_DIR = path.join(__dirname, 'screenshots');
const VIEWPORTS = {
  desktop: { width: 1920, height: 1080 },
  laptop: { width: 1366, height: 768 },
  mobile: { width: 390, height: 844 },
};

const ROUTES = [
  { path: '/', name: 'welcome', waitFor: '.hero, .welcome, h1', desc: 'Página de bienvenida' },
  { path: '/dashboard', name: 'gaming-console', waitFor: '.gaming-console, .dashboard, [data-testid="dashboard"]', desc: 'Gaming Console / Dashboard principal' },
  { path: '/classic', name: 'mission-control', waitFor: '.mission-control, .agent-fleet, .opportunity-radar', desc: 'Mission Control clásico' },
  { path: '/intelligence', name: 'intelligence', waitFor: '.intelligence, .findings, .hypothesis', desc: 'Intelligence Dashboard' },
  { path: '/targets', name: 'targets', waitFor: '.targets, .discovery, .attack-surface', desc: 'Targets & Discovery' },
  { path: '/reports', name: 'reports', waitFor: '.reports, .report-center, .report-queue', desc: 'Report Center' },
  { path: '/capital', name: 'capital', waitFor: '.capital, .revenue, .wealth', desc: 'Capital / Wealth Dashboard' },
  { path: '/operations', name: 'operations', waitFor: '.operations, .terminal, .workflows', desc: 'Operations & Terminal' },
  { path: '/copilot', name: 'copilot', waitFor: '.copilot, .merlin, .chat', desc: 'MERLIN Copilot' },
  { path: '/security/executive', name: 'executive-dashboard', waitFor: '.executive, .ceo-view, .verdict', desc: 'Executive Dashboard (CEO View)' },
  { path: '/settings', name: 'settings', waitFor: '.settings, .config', desc: 'Settings' },
  { path: '/mobile', name: 'mobile-companion', waitFor: '.mobile-companion, .companion', desc: 'Mobile Companion' },
];

async function waitForContent(page, selector, timeout = 10000) {
  try {
    await page.waitForSelector(selector, { timeout, state: 'visible' });
  } catch (e) {
    // Try alternative: wait for network idle
    await page.waitForLoadState('networkidle', { timeout: 5000 });
  }
}

async function captureRoute(browser, route, viewportName, viewport) {
  const page = await browser.newPage({ viewport });
  const fullName = `${route.name}-${viewportName}`;

  try {
    console.log(`📸 Capturing ${route.path} (${viewportName})...`);
    await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('domcontentloaded');
    await waitForContent(page, route.waitFor);

    // Wait a bit for animations to settle
    await page.waitForTimeout(1000);

    const screenshotPath = path.join(OUTPUT_DIR, `${fullName}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`   ✅ Saved: ${screenshotPath}`);

    // Also capture viewport-only for hero images
    if (viewportName === 'desktop') {
      const heroPath = path.join(OUTPUT_DIR, `hero-${route.name}.png`);
      await page.screenshot({ path: heroPath, fullPage: false });
      console.log(`   🎯 Hero saved: ${heroPath}`);
    }

    return { success: true, path: screenshotPath };
  } catch (error) {
    console.error(`   ❌ Failed ${route.path}: ${error.message}`);
    return { success: false, error: error.message };
  } finally {
    await page.close();
  }
}

async function main() {
  // Create output directory
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const route of ROUTES) {
    for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
      const result = await captureRoute(browser, route, viewportName, viewport);
      results.push({ route: route.path, viewport: viewportName, ...result });
    }
  }

  await browser.close();

  // Generate summary
  const summary = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    viewports: VIEWPORTS,
    routes: ROUTES.map(r => ({ path: r.path, name: r.name, desc: r.desc })),
    results: results.filter(r => r.success).map(r => ({ route: r.route, viewport: r.viewport, path: r.path })),
    failed: results.filter(r => !r.success).map(r => ({ route: r.route, viewport: r.viewport, error: r.error })),
  };

  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'capture-summary.json'),
    JSON.stringify(summary, null, 2)
  );

  console.log('\n📊 Capture Summary:');
  console.log(`   ✅ Successful: ${summary.results.length}`);
  console.log(`   ❌ Failed: ${summary.failed.length}`);
  console.log(`   📁 Output: ${OUTPUT_DIR}`);

  if (summary.failed.length > 0) {
    console.log('\n❌ Failed captures:');
    summary.failed.forEach(f => console.log(`   ${f.route} (${f.viewport}): ${f.error}`));
  }
}

main().catch(console.error);