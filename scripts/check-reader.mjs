import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const generator = process.argv[2];
if (!generator) throw new Error('Usage: node scripts/check-reader.mjs GENERATOR_CHECKOUT');
const { chromium } = await import(pathToFileURL(path.resolve(generator, 'node_modules/playwright-core/index.mjs')));
const root = path.resolve(import.meta.dirname, '..');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH,
  headless: true, args: ['--no-sandbox'] });
const errors = [], external = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', error => errors.push(String(error)));
  page.on('request', request => { if (/^https?:/.test(request.url())) external.push(request.url()); });
  await page.goto(pathToFileURL(path.join(root, 'index.html')).href);
  const missing = await page.evaluate(() => [...document.querySelectorAll('a.definition-link')]
    .filter(a => !document.getElementById(a.hash.slice(1))).map(a => a.textContent));
  assert.deepEqual(missing, []);
  assert.equal(await page.locator('[id="definition-formal:Stafford38Challenge.WeylAlg"]').count(), 1);
  for (const [id, owner] of [
    ['definition-formal:Stafford.Reduction.Stafford38', 'This project'],
    ['definition-mathlib:MvPolynomial.weightedTotalDegree', 'Mathlib'],
  ]) {
    await page.evaluate(id => {
      const link = [...document.querySelectorAll('a.definition-link')].find(a => a.hash === '#' + id);
      if (!link) throw new Error('Missing definition link: ' + id);
      for (let p = link.parentElement; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
    }, id);
    await page.locator('a.definition-link[href="#' + id + '"]').first().click();
    assert.equal(await page.locator('[id="' + id + '"]').evaluate(el => el.open), true);
    assert.match(await page.locator('[id="' + id + '"] .definition-origin').innerText(), new RegExp(owner));
  }
  const localLinks = await page.locator('a[href^="./sources/"]').evaluateAll(links => [...new Set(links.map(a => a.getAttribute('href')))]);
  for (const href of localLinks) {
    const [file, anchor] = href.split('#');
    const source = fs.readFileSync(path.resolve(root, file), 'utf8');
    assert.ok(!anchor || source.includes('id="' + anchor + '"'), href);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  console.log(JSON.stringify({ status: 'passed', definition_links: 'all targets present',
    canonical_weyl_definitions: 1, local_source_links: localLinks.length,
    ownership_labels: true, definition_clicks: true, mobile_overflow: false,
    javascript_errors: errors, offline_requests: external.length }, null, 2));
} finally {
  await browser.close();
}
