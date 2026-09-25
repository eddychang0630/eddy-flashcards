// Optional browser smoke test: NODE_PATH=<bundled node_modules> node tests/qa_audio_browser.js
const assert = require('assert');
const path = require('path');
const os = require('os');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const browserPath = process.env.BROWSER_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const appUrl = process.env.APP_URL || pathToFileURL(path.join(__dirname, '..', 'index.html')).href;

async function waitForAudio(page) {
  await page.waitForFunction(() => activeAudio && activeAudio.readyState >= 2);
  const state = await page.evaluate(() => ({ duration: activeAudio.duration, playing: !activeAudio.paused }));
  assert(state.duration > 0 && state.playing, 'Audio did not start playing');
  return state.duration.toFixed(2);
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: browserPath });
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(appUrl);
    if (process.env.APP_URL) {
      await page.evaluate(() => navigator.serviceWorker.ready);
      await page.reload();
    }
    assert(await page.evaluate(() => CARDS.length) > 0, 'No cards loaded');
    assert(await page.locator('#screen-study').evaluate(el => el.classList.contains('active')));
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(os.tmpdir(), 'qa-mobile-study.png') });

    await page.locator('#s-word-audio').click();
    console.log('Study word:', await waitForAudio(page), 'seconds');
    if (process.env.APP_URL) {
      await page.waitForFunction(async () => {
        const cache = await caches.open('eddy-flashcard-v4');
        return !!(await cache.match(new URL(CARDS[0][12], location.href).href));
      });
      console.log('Audio cache: OK');
    }
    await page.locator('#s-example-audio').click();
    console.log('Study example:', await waitForAudio(page), 'seconds');

    await page.locator('#tab-quiz').click();
    await page.locator('#q-word-audio').click();
    console.log('Quiz word:', await waitForAudio(page), 'seconds');
    assert.strictEqual(await page.evaluate(() => qFlipped), false, 'Audio button flipped the card');
    await page.locator('#btn-flip').click();
    await page.waitForTimeout(400);
    await page.locator('#q-example-audio').click();
    console.log('Quiz example:', await waitForAudio(page), 'seconds');
    await page.screenshot({ path: path.join(os.tmpdir(), 'qa-mobile-quiz.png') });

    assert.deepStrictEqual(errors, [], `Browser errors: ${errors.join('; ')}`);
    const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    assert(!horizontalOverflow, 'Mobile page overflows horizontally');
    console.log('Mobile layout and playback OK');

    for (const width of [320, 375, 768, 1280]) {
      await page.setViewportSize({ width, height: width < 400 ? 667 : 900 });
      await page.locator('#tab-study').click();
      const bounds = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        buttons: ['s-word-audio', 's-example-audio'].map(id => {
          const box = document.getElementById(id).getBoundingClientRect();
          return { left: box.left, right: box.right };
        }),
      }));
      assert(!bounds.overflow && bounds.buttons.every(box => box.left >= 0 && box.right <= width),
        `Audio button clips at ${width}px: ${JSON.stringify(bounds)}`);
    }
    console.log('Responsive widths: 320, 375, 768, 1280 OK');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
