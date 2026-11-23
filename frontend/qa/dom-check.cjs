const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const HOME = process.env.HOME;
const exe = path.join(HOME, '.cache/ms-playwright/chromium-1234/chrome-linux64/chrome');

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: fs.existsSync(exe) ? exe : undefined });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const routes = process.argv[2] ? process.argv[2].split(',') : ['/'];
  for (const r of routes) {
    await page.goto('http://localhost:5173' + r, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    const info = await page.evaluate(() => {
      const app = document.querySelector('#app');
      const text = app ? app.innerText : '';
      return {
        textLen: text.length,
        textHead: text.slice(0, 400),
        navItems: document.querySelectorAll('nav a, aside a, [class*=sidebar] a').length,
        h1: document.querySelector('h1')?.innerText || null,
        buttons: document.querySelectorAll('button').length,
        bodyClasses: document.body.className,
      };
    });
    console.log(`=== ${r} ===`);
    console.log(JSON.stringify(info, null, 2));
  }
  await browser.close();
})();
