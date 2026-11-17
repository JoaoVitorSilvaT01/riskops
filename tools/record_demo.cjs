/* Record real UI interactions with chapter captions; no microphone or fabricated narration.
 * node tools/record_demo.cjs <ws module path> <ffmpeg executable>
 * Prerequisites: tools/prepare_video.py on :8001, Chromium CDP on :9223, local receiver on :9001.
 */
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const W = require(process.argv[2] || 'ws');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  const target = (await (await fetch('http://127.0.0.1:9223/json/list')).json()).find(t => t.type === 'page');
  const socket = new W(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.on('open', resolve); socket.on('error', reject); });
  let sequence = 0; const pending = new Map(); const exceptions = [];
  socket.on('message', bytes => {
    const message = JSON.parse(bytes);
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    if (!message.id || !pending.has(message.id)) return;
    const promise = pending.get(message.id); pending.delete(message.id); clearTimeout(promise.timer);
    if (message.error) promise.reject(new Error(message.error.message)); else promise.resolve(message.result);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence, timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 60000);
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error('A interação no navegador falhou.');
    return result.result.value;
  };
  const wait = async expression => {
    for (let n = 0; n < 180; n++) { if (await evaluate(expression)) return; await pause(250); }
    throw new Error('A interface não concluiu a etapa: ' + expression);
  };
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:8001' });
  await wait(`document.querySelector('#login-dialog')?.open || document.querySelector('#metrics')?.children.length === 4`);
  if (await evaluate(`document.querySelector('#login-dialog').open`)) {
    await evaluate(`document.querySelector('#login-form').elements.password.value='demo-local-2026';document.querySelector('#login-form').requestSubmit()`);
  }
  await wait(`document.querySelector('#metrics').children.length===4`);
  if (!await evaluate(`state.stats.synthetic_count===state.stats.total && state.stats.provider.provider==='gemini'`)) throw new Error('A gravação exige dados exclusivamente sintéticos e Gemini configurado.');
  fs.mkdirSync('docs/demo', { recursive: true });
  const output = 'docs/demo/riskops.webm';
  const encoder = spawn(process.argv[3], ['-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-r', '3', '-i', 'pipe:0',
    '-an', '-c:v', 'libvpx-vp9', '-b:v', '700k', '-crf', '35', '-deadline', 'realtime', '-cpu-used', '8', '-threads', '2', '-f', 'webm', '-y', output], { windowsHide: true });
  let encoderError = ''; encoder.stderr.on('data', b => encoderError += b.toString());
  const encoded = new Promise((resolve, reject) => { encoder.on('error', reject); encoder.on('close', code => code === 0 ? resolve() : reject(new Error('Erro na codificação: ' + encoderError))); });
  encoder.stdin.on('error', () => {});
  let recording = true, frames = 0, captureError = null;
  const capture = (async () => {
    while (recording) {
      const start = Date.now();
      try {
        const frame = await send('Page.captureScreenshot', { format: 'jpeg', quality: 72, captureBeyondViewport: false });
        if (!encoder.stdin.write(Buffer.from(frame.data, 'base64'))) await new Promise(resolve => encoder.stdin.once('drain', resolve));
        frames++;
      } catch (error) { captureError = error; break; }
      await pause(Math.max(0, 333 - (Date.now() - start)));
    }
  })();
  const chapter = async (title, text, milliseconds) => {
    await evaluate(`(()=>{let box=document.querySelector('#recording-caption');if(!box){box=document.createElement('div');box.id='recording-caption';box.style.cssText='position:fixed;bottom:16px;left:280px;right:24px;z-index:1000;background:#153e35f5;color:white;padding:15px 22px;border:1px solid #91b18d;border-radius:8px;box-shadow:0 5px 25px #102a2940;font:14px/1.6 Segoe UI,Arial,sans-serif;pointer-events:none';}const container=document.querySelector('dialog[open]')||document.body;container.append(box);box.replaceChildren();const heading=document.createElement('strong');heading.textContent=${JSON.stringify(title)};heading.style.cssText='display:block;color:#d2edbd;font-size:15px';const detail=document.createElement('span');detail.textContent=${JSON.stringify(text)};box.append(heading,detail);document.querySelector('#toasts').replaceChildren();})()`);
    console.log(title); await pause(milliseconds);
  };
  try {
    await chapter('01 / Um relato de campo vira uma ocorrência acompanhável', 'RiskOps · protótipo de João Vitor Silva. Dados sintéticos e procedimentos demonstrativos.', 8000);
    await evaluate(`document.querySelector('#new-incident').click();document.querySelector('[data-example="urgent"]').click()`);
    await chapter('02 / Entrada em linguagem natural', 'O usuário informa o que observou. O relato é salvo antes da chamada à IA.', 8000);
    await evaluate(`document.querySelector('#create-form').requestSubmit()`);
    await wait(`document.querySelector('#detail-dialog').open && document.querySelector('.review-form')`);
    if (!await evaluate(`state.detail.analysis_status==='completed' && state.detail.analysis.is_llm`)) throw new Error('O provedor não concluiu uma análise real; a gravação foi interrompida para não simular sucesso.');
    await chapter('03 / Gemini real com resposta estruturada', 'Categoria, prioridade, resumo e evidências. O servidor verifica o contrato JSON e as citações.', 10000);
    await evaluate(`document.querySelectorAll('.detail-section')[2].scrollIntoView({block:'start'})`);
    await chapter('04 / Evidências e informações ausentes', 'A análise apresenta o contexto disponível e o que ainda precisa ser confirmado por uma pessoa.', 10000);
    await evaluate(`document.querySelector('.review-form').scrollIntoView({block:'center'});document.querySelector('.review-form').elements.assigned_to.value='Equipe operacional';document.querySelector('.review-form').elements.reason.value='Cenário sintético: encaminhamento prioritário confirmado para avaliação da equipe responsável.'`);
    await chapter('05 / Uma pessoa confirma a decisão', 'Revisão com justificativa e responsável. Controle de versão evita sobrescrever outra revisão.', 9000);
    await evaluate(`document.querySelector('.review-form').requestSubmit()`);
    await wait(`state.detail.reviewed_priority==='P1'`);
    await evaluate(`document.querySelector('#detail-dialog').scrollTop=document.querySelector('#detail-dialog').scrollHeight`);
    await chapter('06 / Histórico verificável', 'Registro, análise e revisão ficam no histórico. A cadeia de hashes permite conferir sua consistência.', 8000);
    const delivery = spawnSync('python', ['manage.py', 'deliver_alerts'], { cwd: process.cwd(), env: { ...process.env, DATABASE_PATH: path.resolve('artifacts/video-demo.sqlite3') }, encoding: 'utf8', windowsHide: true, timeout: 20000 });
    if (delivery.status !== 0) throw new Error('Não foi possível executar o worker de alertas.');
    await evaluate(`document.querySelector('#detail-dialog').close();location.hash='integrations'`);
    await wait(`document.querySelectorAll('.integration-card').length===2`);
    if (!await evaluate(`document.querySelector('#integrations-content').textContent.includes('Entregue')`)) throw new Error('A entrega do alerta não foi confirmada pelo receptor.');
    await chapter('07 / Alerta com entrega confirmada', 'Webhook local real: assinatura HMAC, identificação do evento e tentativas persistentes.', 10000);
    await evaluate(`location.hash='evaluation'`); await wait(`document.querySelector('#evaluation-content table')`);
    await chapter('08 / Resultados e falhas à vista', '36 cenários sintéticos: 31 concordantes, três divergências e duas falhas. Avaliação exploratória.', 12000);
    await evaluate(`location.hash='policies'`); await wait(`document.querySelectorAll('.policy-card').length===7`);
    await chapter('09 / Critérios explícitos e versionados', 'Recuperação lexical de procedimentos fictícios. Sem uso de documentos corporativos confidenciais.', 8000);
    await evaluate(`location.hash='overview';window.scrollTo(0,0)`);
    await chapter('RiskOps / IA aplicada a um processo completo', 'Interface, API, Gemini, persistência, revisão, auditoria e alertas. Sem alegação de impacto operacional validado.', 8000);
  } finally {
    recording = false; await capture; encoder.stdin.end(); await encoded; socket.close();
  }
  if (captureError) throw captureError;
  if (exceptions.length) throw new Error('Foram observados erros de JavaScript durante a gravação.');
  fs.writeFileSync('artifacts/video-manifest.json', JSON.stringify({ file: output, frames, fps: 3, seconds: frames / 3, real_gemini: true, signed_delivery_confirmed: true, audio: false }, null, 2));
  console.log(JSON.stringify({ file: output, seconds: Math.round(frames / 3), bytes: fs.statSync(output).size, audio: false }));
}
main().catch(error => { console.error(error.message); process.exit(1); });
