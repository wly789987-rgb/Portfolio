// Local regression: fresh scene imagery, narrow layouts, and full-size zoom.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.argv[2] || 'http://127.0.0.1:8782/');
    await page.locator('[data-open="turtle-soup"]').first().click();
    assert.equal(await page.locator('.turtle-art-group').count(), 4);
    assert.equal(await page.locator('.turtle-art-grid figure').count(), 11);
    assert.equal(await page.locator('.turtle-ta article').count(), 6);
    assert.equal(await page.locator('.legacy-gallery figure').count(), 8);
    for (const width of [1440, 375, 320]) {
      await page.setViewportSize({ width, height: 900 });
      for (const group of await page.locator('.turtle-art-group').all()) {
        await group.scrollIntoViewIfNeeded();
        await group.locator('img').evaluateAll(images => Promise.all(images.map(image => {
          if (image.complete && image.naturalWidth) return;
          return new Promise((resolve, reject) => {
            image.addEventListener('load', resolve, { once: true });
            image.addEventListener('error', reject, { once: true });
          });
        })));
      }
      assert.equal(await page.evaluate(() => document.querySelector('#project-detail').scrollWidth > document.querySelector('#project-detail').clientWidth), false);
      assert.equal(await page.locator('.turtle-art-grid img').evaluateAll(images => images.filter(image => image.complete && image.naturalWidth > 0).length), 11);
    }
    await page.locator('.turtle-art-group').first().locator('[data-zoom-asset]').first().click();
    await page.waitForFunction(() => document.querySelector('#expanded-image').naturalWidth >= 1920);
    assert.ok(await page.locator('#image-dialog').evaluate(dialog => dialog.open));
    assert.deepEqual(errors, []);
    console.log('PASS: 11 art figures, 8 interface stills, 6 technical notes; image loading and zoom; 1440/375/320 layouts.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
