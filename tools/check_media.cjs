// Run against a local preview: node tools/check_media.cjs http://127.0.0.1:8782/
// Set PLAYWRIGHT_MODULE to a bundled Playwright package path when needed.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.platform === 'win32' ? { channel: 'msedge' } : {}) });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage(), errors = [], requested = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requested.push(r.url()));
    await page.goto(process.argv[2] || 'http://127.0.0.1:8782/', { waitUntil: 'load' });
    await page.waitForFunction(() => document.body.dataset.ready === 'true');
    assert.equal(requested.some(url => /\.(mp4|pdf|gif)(\?|$)/.test(url)), false, 'No eager video/GIF/PDF');
    assert.equal(requested.filter(url => /app\.js/.test(url)).length, 1, 'No duplicate startup source fetch');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    for (const id of ['solar-vr', 'alien-vr', 'nba', 'evil-hero']) {
      await page.locator(`[data-open="${id}"]`).first().click();
      const dialog = page.locator('#project-dialog');
      assert.equal(await dialog.locator('.gif-preview').count(), 1);
      assert.ok(await dialog.locator('.project-video-links a').count());
      if (id === 'solar-vr') {
        const toggle = dialog.locator('[data-gif-toggle]');
        await toggle.click();
        await page.waitForFunction(() => document.querySelector('#project-dialog [data-gif-toggle]').getAttribute('aria-pressed') === 'true');
        await page.waitForFunction(() => document.querySelector('#project-dialog .gif-preview img').naturalWidth > 0);
        await toggle.click();
        await page.waitForFunction(() => document.querySelector('#project-dialog [data-gif-toggle]').getAttribute('aria-pressed') === 'false');
      }
      await dialog.locator('.close-dialog').click();
    }
    assert.ok(await page.evaluate(async () => (await (await caches.open(MEDIA_CACHE)).keys()).length));
    await page.reload({ waitUntil: 'load' });
    await page.waitForFunction(() => document.body.dataset.ready === 'true');
    const before = requested.length;
    assert.equal(await page.evaluate(async () => {
      const result = await cachedMediaURL(GIF_PREVIEWS['solar-vr'].src);
      return result.startsWith('blob:');
    }), true);
    assert.equal(requested.slice(before).some(url => url.endsWith('.gif')), false, 'Reuse persisted GIF cache');
    assert.equal(await page.evaluate(async () => {
      const result = await inlineMediaForExport('const poster="' + GIF_PREVIEWS['solar-vr'].poster + '";');
      return result.includes('data:image/webp;base64,');
    }), true);
    for (const width of [768, 375, 320]) {
      await page.setViewportSize({ width, height: 812 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    assert.deepEqual(errors, []);
    console.log('PASS: lazy loading, GIF controls/links, persisted cache, export embedding, responsive layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
