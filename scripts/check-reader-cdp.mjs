// Browser checks using Chrome's pipe protocol; no npm dependency required.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';

const root = path.resolve(process.argv[2] ?? path.join(import.meta.dirname, '..'));
const output = path.resolve(process.argv[3] ?? os.tmpdir());
const chrome = process.env.CHROMIUM_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'stafford-reader-check-'));
const browser = spawn(chrome, ['--headless', '--no-sandbox', '--disable-gpu',
  '--disable-background-networking', '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=' + profile, '--remote-debugging-pipe'],
  {stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe']});
let nextId = 0, buffer = '', diagnostics = '';
const pending = new Map(), errors = [], external = [];
browser.stderr.on('data', b => { diagnostics += b; });
browser.stdio[4].on('data', b => {
  buffer += b;
  for (let end; (end = buffer.indexOf('\0')) >= 0;) {
    const text = buffer.slice(0, end); buffer = buffer.slice(end + 1);
    if (!text) continue;
    const message = JSON.parse(text);
    if (message.id && pending.has(message.id)) {
      const p = pending.get(message.id); pending.delete(message.id); clearTimeout(p.timer);
      message.error ? p.reject(Error(JSON.stringify(message.error))) : p.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') {
      errors.push(message.params.exceptionDetails.text);
    } else if (message.method === 'Network.requestWillBeSent' && /^https?:/.test(message.params.request.url)) {
      external.push(message.params.request.url);
    }
  }
});
function send(method, params = {}, sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(Error('CDP timeout: ' + method)); }, 20000);
    pending.set(id, {resolve, reject, timer});
    browser.stdio[3].write(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}) + '\0');
  });
}
browser.on('exit', (code, signal) => {
  for (const p of pending.values()) { clearTimeout(p.timer); p.reject(Error(`Chrome exited ${code}/${signal}: ${diagnostics.slice(-1000)}`)); }
  pending.clear();
});
let session;
async function evaluate(expression) {
  const r = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true}, session);
  if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
try {
  const target = await send('Target.createTarget', {url: 'about:blank'});
  ({sessionId: session} = await send('Target.attachToTarget', {targetId: target.targetId, flatten: true}));
  for (const name of ['Page', 'Runtime', 'Network']) await send(name + '.enable', {}, session);
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false}, session);
  await send('Page.navigate', {url: pathToFileURL(path.join(root, 'index.html')).href}, session);
  await evaluate(`new Promise(resolve => { if (document.readyState === 'complete') resolve(); else addEventListener('load', resolve, {once:true}); })`);
  await evaluate('document.fonts.ready');
  const map = JSON.parse(fs.readFileSync(path.join(root, 'paper-lean-map.json'), 'utf8'));
  assert.equal(await evaluate('document.querySelectorAll(".card").length'), map.items.length);
  assert.equal(await evaluate('window.AUDIT_META.paper'), map.sources.paper.commit);
  assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('a.definition-link')).filter(a => !document.getElementById(a.hash.slice(1))).map(a => a.textContent)`), []);
  assert.equal(await evaluate(`document.querySelectorAll('[id="definition-formal:Stafford38Challenge.WeylAlg"]').length`), 1);
  for (const id of ['def:localization', 'def:supp', 'lem:supp-criterion', 'lem:place', 'lem:kappa', 'lem:tangent', 'thm:nss'])
    assert.equal(await evaluate(`Boolean(document.getElementById(${JSON.stringify('item-' + id)}))`), true, id);
  for (const id of ['conv:H', 'lem:tangent-limit', 'def:noncar', 'prop:noncar'])
    assert.equal(await evaluate(`Boolean(document.getElementById(${JSON.stringify('item-' + id)}))`), false, id);
  for (const [id, owner] of [
    ['definition-formal:Stafford.Reduction.Stafford38', 'This project'],
    ['definition-mathlib:MvPolynomial.weightedTotalDegree', 'Mathlib'],
  ]) {
    await evaluate(`(() => { const a = Array.from(document.querySelectorAll('a.definition-link')).find(a => a.hash === '#' + ${JSON.stringify(id)}); if(!a) throw Error('Missing definition'); for(let p=a.parentElement;p;p=p.parentElement) if(p.tagName==='DETAILS')p.open=true; a.click(); })()`);
    assert.equal(await evaluate(`document.getElementById(${JSON.stringify(id)}).open`), true);
    assert.match(await evaluate(`document.getElementById(${JSON.stringify(id)}).querySelector('.definition-origin').innerText`), new RegExp(owner));
  }
  const links = await evaluate(`Array.from(new Set(Array.from(document.querySelectorAll('a[href^="./sources/"]'), a => a.getAttribute('href'))))`);
  for (const href of links) {
    const [file, anchor] = href.split('#');
    const source = fs.readFileSync(path.resolve(root, file), 'utf8');
    assert.ok(!anchor || source.includes('id="' + anchor + '"'), href);
  }
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('.col.paper a.source-link')).every(a => a.getAttribute('href').startsWith('./sources/paper/'))`), true);
  assert.equal(await evaluate(`document.querySelectorAll('.katex-error, .tex-error').length`), 0);
  assert.equal(await evaluate(`document.querySelectorAll('[id^="issue-MS18-"]').length`), 5);
  await evaluate(`document.getElementById('filter').value='Residue field'; document.getElementById('filter').dispatchEvent(new Event('input', {bubbles:true}));`);
  assert.equal(await evaluate(`getComputedStyle(document.getElementById('item-lem:kappa')).display !== 'none'`), true);
  assert.equal(await evaluate(`getComputedStyle(document.getElementById('item-abstract')).display === 'none'`), true);
  await evaluate(`document.getElementById('filter').value=''; document.getElementById('filter').dispatchEvent(new Event('input', {bubbles:true})); document.querySelector('[data-guided-start]').click();`);
  assert.equal(await evaluate('location.hash'), '#item-' + map.items[0].id);
  await evaluate(`document.querySelector('#clean-text').click()`);
  assert.equal(await evaluate(`document.querySelector('#clean-text').checked`), true);
  await evaluate(`(() => { const r=document.querySelector('#reviewer'); r.value='Automated browser check'; r.dispatchEvent(new Event('input',{bubbles:true})); const n=document.querySelector('.review [data-notes]'); n.value='Persistence check'; n.dispatchEvent(new Event('input',{bubbles:true})); n.value=''; })()`);
  await send('Page.reload', {}, session);
  await evaluate(`new Promise(resolve => setTimeout(resolve, 350))`);
  assert.equal(await evaluate(`document.querySelector('.review [data-notes]').value`), 'Persistence check');
  const exported = await evaluate(`new Promise(resolve => { URL.createObjectURL=blob=>{blob.text().then(text=>resolve(JSON.parse(text)));return 'blob:automated-check';}; HTMLAnchorElement.prototype.click=function(){};document.querySelector('#export').click(); })`);
  assert.equal(exported.paper_commit, map.sources.paper.commit);
  assert.equal(exported.mapping_version, map.version);
  assert.equal(exported.items[map.items[0].id].notes, 'Persistence check');
  await evaluate('localStorage.clear()');
  await send('Page.reload', {}, session);
  await evaluate(`new Promise(resolve => setTimeout(resolve, 350))`);
  await evaluate(`document.documentElement.style.scrollBehavior='auto'; document.querySelectorAll('main details').forEach(d=>d.open=false); location.hash='overview'; window.scrollTo({top:0,left:0,behavior:'instant'}); new Promise(requestAnimationFrame);`);
  fs.mkdirSync(output, {recursive: true});
  const desktop = await send('Page.captureScreenshot', {format: 'png'}, session);
  fs.writeFileSync(path.join(output, 'reader-desktop.png'), Buffer.from(desktop.data, 'base64'));
  await send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true}, session);
  await evaluate(`window.scrollTo({top:0,left:0,behavior:'instant'}); new Promise(requestAnimationFrame);`);
  assert.equal(await evaluate('document.documentElement.scrollWidth > innerWidth + 1'), false);
  const mobile = await send('Page.captureScreenshot', {format: 'png'}, session);
  fs.writeFileSync(path.join(output, 'reader-mobile.png'), Buffer.from(mobile.data, 'base64'));
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  const receipt = {status: 'passed', cards: map.items.length, paper: map.sources.paper.commit,
    source_links: links.length, definition_links: 'all targets present', canonical_weyl_definitions: 1,
    ownership_labels: true, definition_clicks: true, new_cards: 7, obsolete_cards_absent: true,
    paper_source_links_local: true, search: true, guided_navigation: true, manuscript_annotations: true,
    notes_reload: true, review_export: true,
    review_findings: 5, math_errors: 0, mobile_overflow: false, javascript_errors: errors, offline_requests: external.length};
  fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt));
} finally {
  try { await send('Browser.close'); } catch {}
  browser.kill();
}
