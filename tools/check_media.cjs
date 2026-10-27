// Run against a local preview: node tools/check_media.cjs http://127.0.0.1:8782/
// Set PLAYWRIGHT_MODULE to a bundled Playwright package path when needed.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.platform === 'win32' ? { channel: 'msedge' } : {}) });
  try {
    const url = process.argv[2] || 'http://127.0.0.1:8782/';
    // Project titles and descriptions must survive a completely blocked script.
    const staticContext = await browser.newContext({ javaScriptEnabled: false });
    const staticPage = await staticContext.newPage();
    await staticPage.route(/\.(webp|jpg|png|gif|mp4|pdf)(\?|$)/, route => route.abort());
    await staticPage.goto(url, { waitUntil: 'load' });
    assert.equal(await staticPage.locator('#project-grid > .project-card').count(), 9);
    assert.equal(await staticPage.locator('#project-grid .project-summary').count(), 9);
    assert.ok((await staticPage.locator('#project-grid').innerText()).includes('海龟汤 · 汤之馆'));
    await staticPage.locator('#works').scrollIntoViewIfNeeded();
    await staticPage.locator('#project-grid h3').first().waitFor({ state: 'visible' });
    await staticContext.close();

    // A blocked local database must not prevent the first interactive render.
    const blockedContext = await browser.newContext();
    await blockedContext.addInitScript(() => {
      Object.defineProperty(window, 'indexedDB', { value: { open() { return {}; } } });
    });
    const blockedPage = await blockedContext.newPage();
    await blockedPage.goto(url, { waitUntil: 'load' });
    await blockedPage.waitForFunction(() => document.body.dataset.ready === 'true', { timeout: 5000 });
    assert.equal(await blockedPage.locator('#project-grid > .project-card').count(), 9);
    await blockedContext.close();

    // Reproduce the user's stale HTML without a filter bar against the new script.
    const compatibilityContext = await browser.newContext();
    const compatibilityPage = await compatibilityContext.newPage(), compatibilityErrors = [];
    compatibilityPage.on('pageerror', e => compatibilityErrors.push(e.message));
    await compatibilityPage.route(url, async route => {
      const response = await route.fetch();
      const body = (await response.text()).replace(/<div class="filter-bar"[\s\S]*?<\/div>/, '');
      await route.fulfill({ response, body });
    });
    await compatibilityPage.goto(url, { waitUntil: 'load' });
    await compatibilityPage.waitForFunction(() => document.body.dataset.ready === 'true');
    assert.equal(await compatibilityPage.locator('#project-grid > .project-card').count(), 9);
    assert.deepEqual(compatibilityErrors, []);
    await compatibilityContext.close();

    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage(), errors = [], requested = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requested.push(r.url()));
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(() => document.body.dataset.ready === 'true');
    assert.equal(requested.some(url => /\.(mp4|pdf|gif)(\?|$)/.test(url)), false, 'No eager video/GIF/PDF');
    assert.equal(requested.filter(url => /app\.js/.test(url)).length, 1, 'No duplicate startup source fetch');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);

    for (const id of ['turtle-soup', 'solar-vr', 'alien-vr', 'nba', 'evil-hero']) {
      await page.locator(`[data-open="${id}"]`).first().click();
      const dialog = page.locator('#project-dialog');
      assert.equal(await dialog.locator('.gif-preview').count(), 1);
      if (id === 'turtle-soup') {
        assert.equal(await dialog.locator('.gif-preview-actions a').count(), 0, 'No invented full video link');
        assert.ok(await dialog.locator('.legacy-gallery figure').count() >= 8, 'Every current main interface has a still image');
        for (const toggle of await dialog.locator('[data-gif-toggle]').all()) {
          await toggle.click();
          await page.waitForFunction(() => [...document.querySelectorAll('#project-dialog .gif-preview img')].filter(img => img.src.startsWith('blob:')).every(img => img.complete && img.naturalWidth > 0));
          await toggle.click();
        }
      } else assert.ok(await dialog.locator('.project-video-links a').count());
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
