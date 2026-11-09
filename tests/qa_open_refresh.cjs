const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8767/';
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'screenshots');
fs.mkdirSync(output, { recursive: true });

async function run() {
  const browser = await chromium.launch({ headless: true, executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' });
  try {
    for (const app of ['vocabulary', 'sentences']) {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
      const page = await context.newPage();
      let loads = 0;
      const errors = [];
      page.on('load', () => loads++);
      page.on('pageerror', error => errors.push(error.message));
      const relative = app === 'vocabulary' ? '' : 'sentences/';
      const release = JSON.parse(fs.readFileSync(path.join(root, relative, 'app-version.json'), 'utf8'));
      let revision = release.revision;
      await context.route('**/app-version.json', route => route.fulfill({ json: { schema_version: 1, revision } }));
      await page.goto(base + relative);
      await page.waitForFunction(key => sessionStorage.getItem(key), app === 'vocabulary' ? 'eddy-vocabulary-version' : 'eddy-sentences-version');
      await page.waitForLoadState('networkidle');
      assert.equal(loads, 2, 'First open must refresh once without a loop');
      const latest = app === 'vocabulary'
        ? [...new Set(JSON.parse(fs.readFileSync(path.join(root, 'vocab_data.json'), 'utf8')).filter(card => card[14] !== 'life').map(card => card[10]))].sort().at(-1)
        : [...new Set(JSON.parse(fs.readFileSync(path.join(root, relative, 'data.json'), 'utf8')).cards.filter(card => card.type === 'class').map(card => card.date))].sort().at(-1);
      if (app === 'vocabulary') {
        assert.equal(await page.locator('#source-class').getAttribute('aria-pressed'), 'true');
        assert.ok((await page.locator('#s-date-badge').textContent()).includes(latest));
      } else {
        assert.equal(await page.locator('#view-title').textContent(), '課堂句子');
        assert.equal(await page.locator('#filters .active').textContent(), latest);
        await page.locator('#reveal').click();
        await page.locator('[data-rating="3"]').click();
        await page.waitForFunction(() => document.getElementById('seen-count').textContent === '1');
      }
      await page.screenshot({ path: path.join(output, `${app}-latest-mobile.png`), fullPage: true });
      const foreground = async () => page.evaluate(() => {
        Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
        document.dispatchEvent(new Event('visibilitychange'));
        Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      await foreground();
      await page.waitForLoadState('networkidle');
      assert.equal(loads, 2, 'Same version must not reset a practice session');
      revision += '-qa-update';
      await page.evaluate(key => sessionStorage.setItem(key + ':reload', '1'), app === 'vocabulary' ? 'eddy-vocabulary-version' : 'eddy-sentences-version');
      const updated = page.waitForEvent('load');
      await foreground();
      await updated;
      await page.waitForLoadState('networkidle');
      assert.equal(loads, 3, 'Foreground must load a newer version exactly once');
      if (app === 'sentences') assert.equal(await page.locator('#seen-count').textContent(), '1', 'Reviews must survive refresh');
      await page.evaluate(() => navigator.serviceWorker.ready);
      await context.setOffline(true);
      await page.reload();
      const word = app === 'vocabulary' ? '#s-word' : '#view-title';
      await page.locator(word).waitFor({ state: 'visible' });
      assert.ok(await page.locator(word).textContent());
      const offlineLoads = loads;
      await foreground();
      assert.equal(loads, offlineLoads, 'Offline use must not trigger reloads');
      assert.deepEqual(errors, []);
      console.log(`${app}: initial refresh, latest ${latest}, unchanged version, foreground update, offline use, and preserved reviews passed`);
      await context.close();
    }
  } finally { await browser.close(); }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
