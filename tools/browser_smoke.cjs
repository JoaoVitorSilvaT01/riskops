/* Optional browser QA using an already-installed Chromium and ws module.
 * node tools/browser_smoke.cjs <absolute path to ws module>
 * Chromium must expose CDP on localhost:9223. No dependency is downloaded.
 */
const fs = require('node:fs');
const assert = require('node:assert/strict');
const WebSocket = require(process.argv[2] || 'ws');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  const targets = await (await fetch('http://127.0.0.1:9223/json/list')).json();
  const target = targets.find(t => t.type === 'page');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.on('open', resolve); ws.on('error', reject); });
  const pending = new Map(); let seq = 0; const errors = [];
  ws.on('message', bytes => {
    const message = JSON.parse(bytes);
    if (message.id) {
      const task = pending.get(message.id); if (!task) return;
      pending.delete(message.id); clearTimeout(task.timer);
      if (message.error) task.reject(new Error(JSON.stringify(message.error))); else task.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
  });
  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++seq;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 15000);
      pending.set(id, { resolve, reject, timer }); ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function waitFor(expression) {
    for (let n = 0; n < 100; n++) { if (await evaluate(expression)) return; await sleep(100); }
    throw new Error('Timed out waiting: ' + expression);
  }
  fs.mkdirSync('artifacts', { recursive: true });
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:8000' });
  await waitFor(`document.querySelector('#login-dialog')?.open || document.querySelector('#metrics')?.children.length > 0`);
  if (await evaluate(`document.querySelector('#login-dialog').open`)) {
    await evaluate(`document.querySelector('#login-form').elements.password.value='demo-local-2026';document.querySelector('#login-form').requestSubmit()`);
  }
  await waitFor(`document.querySelector('#metrics').children.length===4`);
  assert.equal(await evaluate(`document.querySelector('#login-dialog').open`), false);
  let shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); fs.writeFileSync('artifacts/overview-desktop.png', Buffer.from(shot.data, 'base64'));
  await evaluate(`document.querySelector('#new-incident').click();document.querySelector('[data-example="injection"]').click();document.querySelector('#create-form').requestSubmit()`);
  await waitFor(`document.querySelector('#detail-dialog').open && document.querySelector('.review-form')`);
  assert.ok(await evaluate(`document.querySelector('#detail-content').textContent.includes('Possível instrução')`));
  assert.equal(await evaluate(`state.detail.priority`), 'P2');
  await evaluate(`document.querySelector('.review-form').elements.assigned_to.value='Equipe de QA';document.querySelector('.review-form').elements.reason.value='Cenário sintético revisado durante o teste completo da interface.';document.querySelector('.review-form').requestSubmit()`);
  await waitFor(`state.detail.reviewed_priority === 'P2'`);
  shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); fs.writeFileSync('artifacts/review-desktop.png', Buffer.from(shot.data, 'base64'));
  await evaluate(`document.querySelector('#detail-dialog').close();location.hash='evaluation'`);
  await waitFor(`document.querySelector('#evaluation-content table')`);
  assert.ok(await evaluate(`document.querySelector('#evaluation-content').textContent.includes('36')`));
  await evaluate(`location.hash='policies'`); await waitFor(`document.querySelectorAll('.policy-card').length === 7`);
  await evaluate(`location.hash='integrations'`); await waitFor(`document.querySelectorAll('.integration-card').length === 2`);
  await evaluate(`location.hash='incidents'`); await waitFor(`document.querySelector('#incidents-table tr')`);
  await evaluate(`document.querySelector('#search').value='ZZZ-no-results';document.querySelector('#search').dispatchEvent(new Event('input'))`);
  await waitFor(`document.querySelector('#incidents-table').textContent.includes('Nenhuma ocorrência')`);
  await evaluate(`document.querySelector('#search').value='';location.hash='overview'`);
  await waitFor(`!document.querySelector('#page-overview').hidden`);
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await sleep(200);
  await evaluate(`document.querySelector('#toasts').replaceChildren()`);
  assert.ok(await evaluate(`document.documentElement.scrollWidth <= window.innerWidth`), 'Mobile layout overflows horizontally');
  shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); fs.writeFileSync('artifacts/overview-mobile.png', Buffer.from(shot.data, 'base64'));
  assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log(JSON.stringify({ ok: true, checks: ['login', 'dashboard', 'create', 'injection flag', 'review', 'evaluation', 'policies', 'integrations', 'search empty state', 'mobile overflow', 'no JS exceptions'], screenshots: 3 }));
  ws.close();
}
main().catch(error => { console.error(error); process.exit(1); });
