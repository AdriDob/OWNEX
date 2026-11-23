const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const HOME = process.env.HOME;
const exe = path.join(HOME, '.cache/ms-playwright/chromium-1234/chrome-linux64/chrome');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: fs.existsSync(exe) ? exe : undefined });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('pageerror', (err) => console.log('PAGEERROR:', err.stack || err));
  page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE:', m.text().slice(0, 200), m.location()?.url || ''); });
  await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);
  await browser.close();
})();
