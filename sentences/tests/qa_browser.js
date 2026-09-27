const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('playwright');

async function run() {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' });
  const output = path.join(__dirname, 'screenshots');
  fs.mkdirSync(output, { recursive: true });
  try {
    const desktop = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: true });
    const page = await desktop.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8765/sentences/', { waitUntil: 'networkidle' });
    await page.locator('#due-count').getByText('100').waitFor();
    assert.equal(await page.locator('#view-title').textContent(), '今日複習');
    await page.screenshot({ path: path.join(output, 'desktop-front.png'), fullPage: true });
    await page.locator('#reveal').click();
    assert.ok(await page.locator('#answer-en').textContent());
    assert.ok(await page.locator('#grammar-pattern').textContent());
    await page.locator('#play-answer').click();
    await page.waitForTimeout(500);
    assert.equal(await page.locator('audio').count(), 0);
    assert.equal(await page.evaluate(() => [...document.querySelectorAll('.audio-button')].some(button => button.classList.contains('playing'))), true);
    await page.screenshot({ path: path.join(output, 'desktop-answer.png'), fullPage: true });
    await page.locator('[data-rating="3"]').click();
    await page.locator('#seen-count').getByText('1').waitFor();
    await page.locator('[data-view="lessons"]').click();
    assert.equal(await page.locator('#card-position').textContent(), '1 / 10');
    await page.locator('#reveal').click();
    assert.ok(await page.locator('#original').textContent());
    await page.locator('[data-view="scenarios"]').click();
    await page.locator('#reveal').click();
    assert.ok(await page.locator('#question-en').textContent());
    await page.locator('#play-question').click();
    await page.waitForTimeout(350);
    assert.equal(await page.locator('#play-question').evaluate(button => button.classList.contains('playing')), true);
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#export-progress').click();
    const download = await downloadPromise;
    assert.ok(download.suggestedFilename().endsWith('.json'));
    const restore = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const restorePage = await restore.newPage();
    await restorePage.goto('http://127.0.0.1:8765/sentences/', { waitUntil: 'networkidle' });
    await restorePage.locator('#seen-count').getByText('0').waitFor();
    restorePage.on('dialog', dialog => dialog.accept());
    await restorePage.locator('#import-file').setInputFiles(await download.path());
    await restorePage.locator('#seen-count').getByText('1').waitFor();
    await restore.close();
    await desktop.setOffline(true);
    await page.reload();
    await page.locator('#class-count').getByText('80').waitFor();
    assert.deepEqual(errors, []);
    await desktop.close();

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    const mobilePage = await mobile.newPage();
    const mobileErrors = [];
    mobilePage.on('pageerror', error => mobileErrors.push(error.message));
    await mobilePage.goto('http://127.0.0.1:8765/sentences/', { waitUntil: 'networkidle' });
    await mobilePage.locator('#due-count').getByText('100').waitFor();
    await mobilePage.locator('#reveal').click();
    await mobilePage.screenshot({ path: path.join(output, 'mobile-answer.png'), fullPage: true });
    assert.equal(await mobilePage.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(mobileErrors, []);
    await mobile.close();
    console.log('Desktop and mobile QA passed');
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
