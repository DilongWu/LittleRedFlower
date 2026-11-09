import assert from 'node:assert/strict';
import { createWorker } from './worker.mjs';
const origin=process.env.TEST_ORIGIN,code=process.env.TEST_CODE,secret=process.env.TEST_WORKER_SECRET;
const login=await fetch(origin+'/api/login',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({username:'test-owner',password:code})});
assert.equal(login.status,200);
const cookie=login.headers.get('set-cookie').split(';')[0];
async function submit(text){const r=await fetch(origin+'/api/voice/jobs',{method:'POST',headers:{Origin:origin,Cookie:cookie,'Content-Type':'application/json'},body:JSON.stringify({text,idempotencyKey:crypto.randomUUID(),issuedAt:Date.now()/1000})});assert.equal(r.status,200);return (await r.json()).id;}
async function result(id){return (await fetch(origin+'/api/voice/jobs/'+id,{headers:{Cookie:cookie}})).json();}
const worker=createWorker({relay:origin,secret,localTest:true,mock:true});
for(const text of ['第一轮','第二轮']){const id=await submit(text);await worker.tick();const r=await result(id);assert.equal(r.state,'done');assert.equal(r.reply,'[MOCK agent] '+text);}
console.log('HTTP relay → outbound worker → MOCK agent → persisted answer: 2 rounds PASS');
// Optional reuse of the existing reviewed bridge with an injected mock agent.
if(process.env.TEST_BRIDGE_MODULE){
 const {createServer}=await import(process.env.TEST_BRIDGE_MODULE);
 let count=0;
 const bridge=createServer({code,port:0,agent:async text=>{count++;return '[MOCK via real bridge] '+text;}});
 await new Promise(resolve=>bridge.listen(0,'127.0.0.1',resolve));
 try{
  const realBridgeWorker=createWorker({relay:origin,secret,localTest:true,bridge:'http://127.0.0.1:'+bridge.address().port,code});
  const id=await submit('桥接测试');await realBridgeWorker.tick();const r=await result(id);assert.equal(r.state,'done');assert.equal(r.reply,'[MOCK via real bridge] 桥接测试');assert.equal(count,1);
  console.log('HTTP relay → outbound worker → original loopback bridge (MOCK agent): PASS');
 }finally{await new Promise(resolve=>bridge.close(resolve));}
}
// Explicit opt-in real CLI/Gateway verification in an isolated voice conversation.
if(process.env.TEST_REAL_AGENT==='1'){
 assert.ok(process.env.TEST_BRIDGE_MODULE,'Provide the reviewed local bridge module');
 const {createServer}=await import(process.env.TEST_BRIDGE_MODULE);
 const bridge=createServer({code,port:0});
 await new Promise(resolve=>bridge.listen(0,'127.0.0.1',resolve));
 try{
  const live=createWorker({relay:origin,secret,localTest:true,bridge:'http://127.0.0.1:'+bridge.address().port,code});
  for(const text of ['语音集成验证专用。请记住测试标记“青竹九号”。只回复“已记住青竹九号”，不要使用任何工具。','上一条测试标记是什么？只回复该标记，不要使用任何工具。']){
   const id=await submit(text);await live.tick();const r=await result(id);
   assert.equal(r.state,'done');assert.ok(r.reply.includes('青竹九号'),'real agent must retain the first turn');
  }
  console.log('REAL Gateway/main: HTTP relay → worker → loopback CLI bridge, two rounds/context PASS (no real audio)');
 }finally{await new Promise(resolve=>bridge.close(resolve));}
}
// Browser fixture: speech recognition and synthesis are explicit mocks.
if(process.env.TEST_PLAYWRIGHT_MODULE){
 const {chromium}=await import(process.env.TEST_PLAYWRIGHT_MODULE);
 const browser=await chromium.launch({headless:true,executablePath:process.env.TEST_CHROMIUM});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844}});
  await context.addInitScript(()=>{
   window.__listens=0;window.__speaks=0;
   window.SpeechRecognition=class {start(){window.__listens++;window.__recognition=this;}abort(){}};
   window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
   Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[],cancel(){},speak(u){if(u.text){window.__speaks++;setTimeout(()=>u.onend?.(),20);}}}});
  });
  const page=await context.newPage();
  // Finance fixtures only; website auth and every voice request use the real HTTP backend.
  await page.route('**/api/reports',route=>route.fulfill({json:[]}));
  await page.goto(origin+'/voice/index.html');
  await context.addCookies([{name:'redflower_session',value:cookie.split('=')[1],url:origin}]);await page.reload();await page.waitForSelector('#controls:visible');
  await page.click('#start');await page.waitForFunction(()=>window.__listens===1);
  await page.evaluate(()=>window.__recognition.onresult({resultIndex:0,results:[Object.assign([{transcript:'手机语音测试'}],{isFinal:true})]}));
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('正在想'));
  for(let i=0;i<20;i++){if(await worker.tick())break;await new Promise(r=>setTimeout(r,100));}await page.waitForFunction(()=>window.__speaks===1&&window.__listens>=2);
  await page.click('#stop');assert.match(await page.textContent('#status'),/已停止/);
  await page.fill('#text','文字后备测试');await page.click('#send');
  await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('正在想'));
  for(let i=0;i<20;i++){if(await worker.tick())break;await new Promise(r=>setTimeout(r,100));}
  await page.waitForFunction(()=>document.querySelectorAll('#history .reply').length===2);
  assert.equal(await page.evaluate(()=>window.__speaks),1,'stopped conversations must not autoplay');
  const fallback=await context.newPage();
  await fallback.addInitScript(()=>{Object.defineProperty(window,'SpeechRecognition',{value:undefined});Object.defineProperty(window,'webkitSpeechRecognition',{value:undefined});});
  await fallback.goto(origin+'/voice/index.html');await fallback.locator('#controls').waitFor({state:'visible'});
  assert.match(await fallback.textContent('#support'),/文字或键盘听写/);await fallback.close();
  await page.click('#logout');await page.waitForURL(origin+'/');
  await page.fill('input[placeholder="请输入用户名"]','test-owner');
  await page.fill('input[placeholder="请输入密码"]',code);
  await page.click('.login-button');
  await page.locator('.mobile-group-tab').filter({hasText:'工具'}).click();
  await page.locator('.mobile-sub-item').filter({hasText:'语音'}).click();
  await page.frameLocator('iframe[title="白总语音"]').locator('#controls').waitFor({state:'visible'});
  assert.equal(await page.frameLocator('iframe[title="白总语音"]').locator('#login').isVisible(),false);
  await page.reload();await page.locator('.mobile-nav').waitFor({state:'visible'});
  await page.locator('.mobile-group-tab').filter({hasText:'工具'}).click();
  await page.locator('.mobile-sub-item').filter({hasText:'语音'}).click();
  await page.frameLocator('iframe[title="白总语音"]').locator('#controls').waitFor({state:'visible'});
  await page.locator('.mobile-logout').click();await page.locator('.login-button').waitFor();
  assert.equal((await context.request.get(origin+'/api/voice/status')).status(),401);
  console.log('Actual React login → activeTab voice iframe → reload persistence → website logout revokes voice PASS');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  console.log('Mobile 390px UI: shared website session, start, recognized transcript, typed/no-STT fallback, reply, TTS → auto-listen, stop, logout PASS (speech APIs mocked)');
 }finally{await browser.close();}
}
