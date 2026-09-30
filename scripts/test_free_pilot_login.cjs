// Read-only browser regression: does not create, edit or delete application data.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  if (!process.env.FM_TEST_PIN) throw new Error('Set FM_TEST_PIN to the pilot PIN');
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
  });
  try {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      if (process.env.FM_USE_LOCAL_ASSETS) {
        await page.route('**/faculdademaria/**', async route => {
          const suffix = new URL(route.request().url()).pathname.replace('/faculdademaria/', '');
          const file = suffix === '' ? 'free-pilot/index.html' : suffix;
          if (['free-pilot/index.html', 'free-pilot/app.js', 'free-pilot/free-pilot.css'].includes(file)) {
            await route.fulfill({ body: fs.readFileSync(path.join(__dirname, '../static', file)),
              contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html' });
          } else await route.continue();
        });
      }
      await page.goto('https://free-pilot.radarpulse.com.br/faculdademaria/');
      assert.equal(await page.locator('#app').isVisible(), false, 'Dashboard must be hidden before login');
      await page.locator('[name=pin]').fill('intentionally-invalid-test-pin');
      await page.locator('#login-form button').click();
      await page.waitForFunction(() => document.querySelector('#login-error').textContent.includes('PIN inválido'));
      await page.locator('[name=pin]').fill(process.env.FM_TEST_PIN);
      await page.locator('#login-form button').click();
      await page.locator('#login').waitFor({ state: 'hidden' });
      assert.equal(await page.locator('#app').isVisible(), true);
      assert.ok(await page.locator('#dashboard-operations tr').count() > 0);
      await page.locator('a[data-screen=closed]').first().click();
      assert.equal(await page.locator('#closed-screen').isVisible(), true);
      assert.equal(await page.locator('#dashboard-screen').isVisible(), false);
      await page.reload();
      await page.locator('#login').waitFor({ state: 'hidden' });
      assert.equal(await page.locator('#app').isVisible(), true);
      await page.locator('#logout').click();
      await page.locator('#app').waitFor({ state: 'hidden' });
      assert.equal(await page.locator('#login').isVisible(), true);
      await page.route('**/api/dashboard', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"test failure"}' }));
      await page.locator('[name=pin]').fill(process.env.FM_TEST_PIN);
      await page.locator('#login-form button').click();
      await page.waitForFunction(() => document.querySelector('#login-error').textContent.includes('carregar o sistema'));
      assert.equal(await page.locator('#login-form button').isEnabled(), true);
      assert.deepEqual(errors, []);
      console.log(`PASS ${viewport.width}px: invalid PIN, login, visible dashboard, navigation, reload, logout, load error`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
