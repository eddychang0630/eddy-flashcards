const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');

async function run() {
  let server;
  let base = process.env.QA_BASE_URL;
  if (!base) {
    server = http.createServer((request, response) => {
      let file = path.resolve(root, '.' + decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
      if (file !== root && !file.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      fs.readFile(file, (error, data) => {
        if (error) { response.writeHead(404).end(); return; }
        const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png' };
        response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' }).end(data);
      });
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    base = `http://127.0.0.1:${server.address().port}/sentences/`;
  }
  const browser = await chromium.launch({ headless: true, executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' });
  try {
    for (const width of [390, 320, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 844 } });
      await context.addInitScript(() => sessionStorage.setItem('eddy-sentences-version', 'date-qa'));
      await context.route('**/app-version.json', route => route.fulfill({ json: { schema_version: 1, revision: 'date-qa' } }));
      const page = await context.newPage();
      await page.goto(base, { waitUntil: 'networkidle' });
      const dates = page.locator('#filters .filter-button');
      await dates.first().waitFor();
      const tops = await dates.evaluateAll(buttons => buttons.map(button => button.getBoundingClientRect().top));
      assert.ok(Math.max(...tops) - Math.min(...tops) < 2, `Dates must stay on one row at ${width}px`);
      assert.ok(await page.locator('#filters').evaluate(box => box.scrollWidth > box.clientWidth), 'Dates must scroll horizontally');
      assert.equal(await dates.first().getAttribute('class'), 'filter-button active');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'The page itself must not overflow sideways');
      if (width === 390) {
        fs.mkdirSync(path.join(root, 'screenshots'), { recursive: true });
        await page.screenshot({ path: path.join(root, 'screenshots/sentence-date-strip-mobile.png'), fullPage: true });
      }
      const oldest = await dates.last().textContent();
      await dates.last().click();
      assert.ok((await page.locator('#card-type').textContent()).includes(oldest));
      const selectedVisible = await page.locator('#filters').evaluate(box => {
        const selected = box.querySelector('.active').getBoundingClientRect();
        const strip = box.getBoundingClientRect();
        return selected.left >= strip.left - 2 && selected.right <= strip.right + 2;
      });
      assert.ok(selectedVisible, 'Selected older date must remain visible');
      await context.close();
      console.log(`Date strip ${width}px: single row, horizontal scrolling, latest default, and old-date selection passed`);
    }
  } finally {
    await browser.close();
    if (server) await new Promise(resolve => server.close(resolve));
  }
}
run().catch(error => { console.error(error); process.exitCode = 1; });
